"""Authenticated buyer payment routes and administrator transaction monitoring."""

from datetime import date, datetime, time, timedelta
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, status
from sqlalchemy import and_, case, desc, func
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin, require_buyer_only, require_seller
from app.models.auction import Auction, AuctionStatus
from app.models.product import Product
from app.models.transaction import (
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentStatus,
    SettlementType,
    Transaction,
)
from app.models.user import User
from app.schemas.payment import (
    AdminPaymentTransactionOut,
    AdminPaymentTransactionPage,
    PaymentOrderOut,
    PaymentTransactionOut,
    PaymentTransactionPage,
    PaymentVerificationIn,
    PaymentVerificationOut,
    PaymentWebhookOut,
    SellerPaymentSummary,
    SellerPaymentTransactionOut,
    SellerPaymentTransactionPage,
    WonAuctionPaymentPage,
    WonAuctionPaymentOut,
)
from app.services.payment_service import payment_service

router = APIRouter()


def _require_payment_tables(db: Session, *, webhook_events: bool = False) -> None:
    required = ["transactions", "payment_attempts"]
    if webhook_events:
        required.append("payment_webhook_events")
    inspector = sqlalchemy_inspect(db.get_bind())
    missing = [table for table in required if not inspector.has_table(table)]
    if not missing and not {"settlement_type", "payment_status", "settled_at"}.issubset(
        {column["name"] for column in inspector.get_columns("transactions")}
    ):
        missing = ["transactions lifecycle columns"]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Payment features are temporarily unavailable because required "
                "database schema is missing. Contact the platform administrator."
            ),
        )


def _payment_required(payment_status: Optional[PaymentStatus]) -> bool:
    return payment_status in {
        PaymentStatus.SETTLEMENT_PENDING_DEMO,
        PaymentStatus.SETTLEMENT_FAILED_DEMO,
    }


def _payment_verified(transaction: Optional[Transaction], attempt: Optional[PaymentAttempt]) -> bool:
    return bool(
        transaction
        and transaction.payment_status == PaymentStatus.SETTLEMENT_COMPLETED_DEMO
        and transaction.settlement_type == SettlementType.SIMULATED_DEMO
        and transaction.settled_at is not None
        and attempt
        and attempt.status == PaymentAttemptStatus.PAYMENT_COMPLETED
        and attempt.provider_payment_id
        and attempt.currency == "USD"
        and attempt.amount_minor == transaction.amount * 100
    )


def _transaction_out(row, *, admin: bool = False):
    transaction, product, attempt = row
    values = {
        "transaction_id": transaction.id,
        "auction_id": transaction.auction_id,
        "product_title": product.title,
        "amount": transaction.amount,
        "payment_status": transaction.payment_status,
        "created_at": transaction.created_at,
        "settled_at": transaction.settled_at,
        "payment_verified": _payment_verified(transaction, attempt),
    }
    if admin:
        values.update(buyer_id=transaction.buyer_id, seller_id=transaction.seller_id)
        return AdminPaymentTransactionOut(**values)
    return PaymentTransactionOut(**values)


def _page(*, page: int, page_size: int, total: int) -> int:
    return max(1, ceil(total / page_size)) if total else 1


@router.get(
    "/me/won-auctions",
    response_model=WonAuctionPaymentPage,
    summary="List completed auctions won by the authenticated buyer",
)
def list_won_auction_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_buyer: User = Depends(require_buyer_only),
):
    _require_payment_tables(db)
    query = (
        db.query(Auction, Product, Transaction, PaymentAttempt)
        .join(Product, Product.id == Auction.product_id)
        .outerjoin(
            Transaction,
            (Transaction.auction_id == Auction.id)
            & (Transaction.buyer_id == current_buyer.id),
        )
        .outerjoin(
            PaymentAttempt,
            PaymentAttempt.transaction_id == Transaction.id,
        )
        .filter(
            Auction.status == AuctionStatus.COMPLETED,
            Auction.winner_id == current_buyer.id,
        )
    )
    total = query.count()
    rows = (
        query.order_by(desc(Auction.end_time), desc(Auction.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return WonAuctionPaymentPage(
        items=[
            WonAuctionPaymentOut(
                auction_id=auction.id,
                product_title=product.title,
                product_image_url=product.image_url,
                auction_status=auction.status.value,
                start_time=auction.start_time,
                end_time=auction.end_time,
                amount=transaction.amount if transaction else None,
                payment_status=transaction.payment_status if transaction else None,
                payment_required=(
                    _payment_required(transaction.payment_status)
                    if transaction
                    else False
                ),
                payment_verified=_payment_verified(transaction, attempt),
            )
            for auction, product, transaction, attempt in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=_page(page=page, page_size=page_size, total=total),
    )


@router.post(
    "/auctions/{auction_id}/orders",
    response_model=PaymentOrderOut,
    summary="Create or reuse a payment order for the winning buyer",
)
def create_payment_order(
    auction_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_buyer: User = Depends(require_buyer_only),
):
    _require_payment_tables(db)
    return payment_service.create_order(
        db, buyer_id=current_buyer.id, auction_id=auction_id
    )


@router.post(
    "/verify",
    response_model=PaymentVerificationOut,
    summary="Verify a Razorpay payment with the provider",
)
def verify_payment(
    payment_in: PaymentVerificationIn,
    db: Session = Depends(get_db),
    current_buyer: User = Depends(require_buyer_only),
):
    _require_payment_tables(db)
    return payment_service.verify_payment(
        db,
        buyer_id=current_buyer.id,
        order_id=payment_in.order_id,
        payment_id=payment_in.payment_id,
        signature=payment_in.signature,
    )


@router.post(
    "/webhook",
    response_model=PaymentWebhookOut,
    summary="Receive and verify a Razorpay payment webhook",
)
async def receive_payment_webhook(
    request: Request,
    db: Session = Depends(get_db),
    signature: str = Header(..., alias="X-Razorpay-Signature"),
    event_id: Optional[str] = Header(None, alias="X-Razorpay-Event-Id"),
):
    _require_payment_tables(db, webhook_events=True)
    raw_body = await request.body()
    return payment_service.process_webhook(
        db,
        raw_body=raw_body,
        signature=signature,
        event_id=event_id,
    )


@router.get(
    "/me/transactions",
    response_model=PaymentTransactionPage,
    summary="List payment history for the authenticated buyer",
)
def list_my_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_buyer: User = Depends(require_buyer_only),
):
    _require_payment_tables(db)
    query = (
        db.query(Transaction, Product, PaymentAttempt)
        .join(Auction, Auction.id == Transaction.auction_id)
        .join(Product, Product.id == Auction.product_id)
        .outerjoin(PaymentAttempt, PaymentAttempt.transaction_id == Transaction.id)
        .filter(Transaction.buyer_id == current_buyer.id)
    )
    total = query.count()
    rows = (
        query.order_by(desc(Transaction.created_at), desc(Transaction.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaymentTransactionPage(
        items=[_transaction_out(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=_page(page=page, page_size=page_size, total=total),
    )


@router.get(
    "/me/seller-transactions",
    response_model=SellerPaymentTransactionPage,
    summary="List settlement history for the authenticated seller",
)
def list_my_seller_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_seller: User = Depends(require_seller),
):
    _require_payment_tables(db)
    query = (
        db.query(Transaction, Product, PaymentAttempt)
        .join(Auction, Auction.id == Transaction.auction_id)
        .join(Product, Product.id == Auction.product_id)
        .outerjoin(PaymentAttempt, PaymentAttempt.transaction_id == Transaction.id)
        .filter(
            Transaction.seller_id == current_seller.id,
            Product.seller_id == current_seller.id,
        )
    )
    verified_settlement = and_(
        Auction.status == AuctionStatus.COMPLETED,
        Transaction.buyer_id == Auction.winner_id,
        Transaction.seller_id == Product.seller_id,
        Transaction.payment_status == PaymentStatus.SETTLEMENT_COMPLETED_DEMO,
        Transaction.settlement_type == SettlementType.SIMULATED_DEMO,
        Transaction.settled_at.isnot(None),
        PaymentAttempt.status == PaymentAttemptStatus.PAYMENT_COMPLETED,
        PaymentAttempt.provider_payment_id.isnot(None),
        PaymentAttempt.currency == "USD",
        PaymentAttempt.amount_minor == Transaction.amount * 100,
    )
    verified_payment = and_(
        Auction.status == AuctionStatus.COMPLETED,
        Transaction.buyer_id == Auction.winner_id,
        Transaction.seller_id == Product.seller_id,
        Transaction.settlement_type == SettlementType.SIMULATED_DEMO,
        PaymentAttempt.status == PaymentAttemptStatus.PAYMENT_COMPLETED,
        PaymentAttempt.provider_payment_id.isnot(None),
        PaymentAttempt.currency == "USD",
        PaymentAttempt.amount_minor == Transaction.amount * 100,
    )
    summary_row = (
        db.query(
            func.coalesce(
                func.sum(case(
                    (verified_settlement, Transaction.amount), else_=0
                )),
                0,
            ).label("completed_settlements"),
            func.coalesce(
                func.sum(case(
                    (and_(
                        Transaction.payment_status == PaymentStatus.SETTLEMENT_PENDING_DEMO,
                        Transaction.settlement_type == SettlementType.SIMULATED_DEMO,
                    ),
                     Transaction.amount),
                    else_=0,
                )),
                0,
            ).label("pending_settlements"),
            func.coalesce(
                func.sum(case(
                    (verified_payment, Transaction.amount), else_=0
                )),
                0,
            ).label("verified_payment_total"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .outerjoin(PaymentAttempt, PaymentAttempt.transaction_id == Transaction.id)
        .join(Auction, Transaction.auction_id == Auction.id)
        .join(Product, Auction.product_id == Product.id)
        .filter(
            Transaction.seller_id == current_seller.id,
            Product.seller_id == current_seller.id,
        )
        .one()
    )
    total = query.count()
    rows = (
        query.order_by(desc(Transaction.created_at), desc(Transaction.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return SellerPaymentTransactionPage(
        items=[
            SellerPaymentTransactionOut(
                **_transaction_out((transaction, product, attempt)).model_dump(),
                settlement_type=transaction.settlement_type,
            )
            for transaction, product, attempt in rows
        ],
        summary=SellerPaymentSummary(
            # Keep total_sales for compatibility; this is verified demo
            # payment volume, not seller payout or completed-settlement value.
            total_sales=summary_row.verified_payment_total,
            verified_payment_total=summary_row.verified_payment_total,
            simulated_settlement_total=summary_row.completed_settlements,
            pending_settlements=summary_row.pending_settlements,
            completed_settlements=summary_row.completed_settlements,
            transaction_count=summary_row.transaction_count,
        ),
        total=total,
        page=page,
        page_size=page_size,
        pages=_page(page=page, page_size=page_size, total=total),
    )


@router.get(
    "/admin/transactions",
    response_model=AdminPaymentTransactionPage,
    summary="Monitor payment transactions (administrator only)",
)
def list_all_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    payment_status: Optional[PaymentStatus] = Query(None),
    buyer_id: Optional[int] = Query(None, ge=1),
    auction_id: Optional[int] = Query(None, ge=1),
    created_from: Optional[date] = Query(None),
    created_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    _require_payment_tables(db)
    if created_from and created_to and created_to < created_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="created_to must be on or after created_from.",
        )
    query = (
        db.query(Transaction, Product, PaymentAttempt)
        .join(Auction, Auction.id == Transaction.auction_id)
        .join(Product, Product.id == Auction.product_id)
        .outerjoin(PaymentAttempt, PaymentAttempt.transaction_id == Transaction.id)
    )
    if payment_status is not None:
        query = query.filter(Transaction.payment_status == payment_status)
    if buyer_id is not None:
        query = query.filter(Transaction.buyer_id == buyer_id)
    if auction_id is not None:
        query = query.filter(Transaction.auction_id == auction_id)
    if created_from is not None:
        query = query.filter(
            Transaction.created_at >= datetime.combine(created_from, time.min)
        )
    if created_to is not None:
        query = query.filter(
            Transaction.created_at
            < datetime.combine(created_to + timedelta(days=1), time.min)
        )

    total = query.count()
    rows = (
        query.order_by(desc(Transaction.created_at), desc(Transaction.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AdminPaymentTransactionPage(
        items=[_transaction_out(row, admin=True) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=_page(page=page, page_size=page_size, total=total),
    )

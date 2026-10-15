"""
BidSmart Analytics — Auction Closing & Winner Settlement Service
Features:
- Idempotent winner determination and reserve price enforcement
- Pessimistic locking (SELECT ... FOR UPDATE) to prevent duplicate winner settlement
- Zero-bid unsold auction resolution
- Simulated demo transaction record creation
- Comprehensive in-app notifications (AUCTION_WON, AUCTION_ENDED to winner, seller & losers)
- Cryptographic audit logging of auction conclusion
"""

from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, text

from app.models.auction import Auction, AuctionStatus
from app.models.product import Product
from app.models.user import User
from app.models.bid import Bid
from app.models.transaction import Transaction, SettlementType, PaymentStatus
from app.models.notification import Notification, NotificationType
from app.models.audit_log import AuditLog
from app.schemas.settlement import AuctionCloseResult, BatchCloseResponse

logger = logging.getLogger("bidsmart_api.auction_closing")


def close_single_auction(
    db: Session,
    auction_id: int,
    closing_user_id: Optional[int] = None,
    force_close: bool = False
) -> AuctionCloseResult:
    """
    Closes a single auction, settles the winner, generates transaction records,
    and dispatches notifications.
    Strictly idempotent: Calling on an already closed auction produces no duplicate actions.
    """
    # 1. Acquire exclusive lock on the auction record
    auction = db.query(Auction).options(
        joinedload(Auction.product).joinedload(Product.seller),
        joinedload(Auction.transaction)
    ).filter(Auction.id == auction_id).with_for_update().first()

    if not auction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auction with ID {auction_id} not found."
        )

    # 2. Permission and privilege verification
    closing_user = None
    is_admin = False
    is_owner = False

    if closing_user_id is not None:
        closing_user = db.query(User).options(
            joinedload(User.role)
        ).filter(User.id == closing_user_id).first()

        if closing_user:
            is_admin = bool(
                closing_user.role and closing_user.role.name == "ADMIN"
            )
            is_owner = bool(
                auction.product and auction.product.seller_id == closing_user.id
            )

            if not is_admin and not is_owner:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied: You do not own this auction listing."
                )

    is_privileged = is_admin or is_owner

    if force_close and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only administrators can force close an auction before its deadline."
        )

    visible_reserve = auction.reserve_price if is_privileged else None

    # 3. Idempotency Check: If already in terminal status, return immediately without duplicate work
    terminal_statuses = [
        AuctionStatus.COMPLETED,
        AuctionStatus.UNSOLD,
        AuctionStatus.RESERVE_NOT_MET,
        AuctionStatus.CANCELLED
    ]
    if auction.status in terminal_statuses:
        tx_id = auction.transaction.id if auction.transaction else None
        tx_ref = auction.transaction.payment_reference if auction.transaction else None
        winner_name = auction.winner.username if auction.winner else None
        visible_reserve_met = (
            bool(auction.current_highest_bid >= auction.reserve_price)
            if (is_privileged and auction.reserve_price and auction.current_highest_bid)
            else None
        )
        return AuctionCloseResult(
            auction_id=auction.id,
            status=auction.status.value,
            already_closed=True,
            winner_id=auction.winner_id,
            winner_username=winner_name,
            final_price=auction.current_highest_bid,
            reserve_price=visible_reserve,
            reserve_met=visible_reserve_met,
            total_bids=auction.total_bids,
            transaction_id=tx_id,
            transaction_reference=tx_ref,
            notifications_dispatched=0,
            message=f"Auction was already closed with status '{auction.status.value}'. No duplicate settlement performed."
        )

    # 4. Temporal deadline check (unless force_close is set by admin)
    now_utc = datetime.now(timezone.utc)
    now_naive = now_utc.replace(tzinfo=None)
    end_comp = auction.end_time.astimezone(timezone.utc).replace(tzinfo=None) if auction.end_time.tzinfo else auction.end_time

    if not force_close and now_naive < end_comp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot close auction #{auction.id}: Auction deadline has not passed yet."
        )

    # 5. Fetch the highest valid accepted bid
    highest_bid = db.query(Bid).options(joinedload(Bid.bidder))\
        .filter(Bid.auction_id == auction.id)\
        .order_by(desc(Bid.bid_amount), desc(Bid.bid_time))\
        .first()

    notifications_to_add: List[Notification] = []
    seller_id = auction.product.seller_id
    product_title = auction.product.title

    # -------------------------------------------------------------------------
    # CASE A: ZERO BIDS RECEIVED -> UNSOLD
    # -------------------------------------------------------------------------
    if auction.total_bids == 0 or highest_bid is None:
        auction.status = AuctionStatus.UNSOLD
        auction.winner_id = None
        auction.winning_bid_id = None

        # Notify seller
        notifications_to_add.append(
            Notification(
                user_id=seller_id,
                type=NotificationType.AUCTION_ENDED,
                title="Auction Closed Unsold",
                message=f"Your listing for '{product_title}' closed without any bids.",
                link_url=f"/auctions/{auction.id}"
            )
        )

        audit = AuditLog(
            user_id=closing_user_id or seller_id,
            action="AUCTION_CLOSED_UNSOLD",
            entity_type="AUCTION",
            entity_id=auction.id,
            old_values={"status": "ACTIVE"},
            new_values={"status": "UNSOLD", "total_bids": 0}
        )
        db.add(audit)

        for n in notifications_to_add:
            db.add(n)

        db.commit()
        db.refresh(auction)

        return AuctionCloseResult(
            auction_id=auction.id,
            status=AuctionStatus.UNSOLD.value,
            already_closed=False,
            winner_id=None,
            winner_username=None,
            final_price=None,
            reserve_price=visible_reserve,
            reserve_met=False if (is_privileged and auction.reserve_price is not None) else None,
            total_bids=0,
            transaction_id=None,
            transaction_reference=None,
            notifications_dispatched=len(notifications_to_add),
            message="Auction closed as UNSOLD (zero bids received)."
        )

    # -------------------------------------------------------------------------
    # CASE B: BIDS RECEIVED, BUT BELOW PRIVATE RESERVE PRICE -> RESERVE_NOT_MET
    # -------------------------------------------------------------------------
    if auction.reserve_price is not None and highest_bid.bid_amount < auction.reserve_price:
        auction.status = AuctionStatus.RESERVE_NOT_MET
        auction.winner_id = None
        auction.winning_bid_id = None

        # Demote all bids so no winning bid flag remains
        db.query(Bid).filter(Bid.auction_id == auction.id).update({"is_winning_bid": False})

        # 1. Notify seller
        notifications_to_add.append(
            Notification(
                user_id=seller_id,
                type=NotificationType.AUCTION_ENDED,
                title="Reserve Price Not Reached",
                message=(
                    f"Your auction for '{product_title}' ended at ${highest_bid.bid_amount:.2f}, "
                    f"which did not reach your private reserve price of ${auction.reserve_price:.2f}."
                ),
                link_url=f"/auctions/{auction.id}"
            )
        )

        # 2. Notify highest bidder (private reserve amount is NOT disclosed)
        notifications_to_add.append(
            Notification(
                user_id=highest_bid.bidder_id,
                type=NotificationType.AUCTION_ENDED,
                title="Auction Ended — Reserve Not Met",
                message=(
                    f"Auction for '{product_title}' closed. Although you held the highest bid of "
                    f"${highest_bid.bid_amount:.2f}, the seller's reserve price was not met."
                ),
                link_url=f"/auctions/{auction.id}"
            )
        )

        # 3. Notify other participating bidders (private reserve amount is NOT disclosed)
        other_bidders = db.query(Bid.bidder_id)\
            .filter(Bid.auction_id == auction.id, Bid.bidder_id != highest_bid.bidder_id)\
            .distinct().all()
        for (other_bidder_id,) in other_bidders:
            if other_bidder_id != seller_id:
                notifications_to_add.append(
                    Notification(
                        user_id=other_bidder_id,
                        type=NotificationType.AUCTION_ENDED,
                        title="Auction Ended — Reserve Not Met",
                        message=(
                            f"The auction for '{product_title}' has closed. The seller's reserve price was not met."
                        ),
                        link_url=f"/auctions/{auction.id}"
                    )
                )

        audit = AuditLog(
            user_id=closing_user_id or seller_id,
            action="AUCTION_RESERVE_NOT_MET",
            entity_type="AUCTION",
            entity_id=auction.id,
            old_values={"status": "ACTIVE"},
            new_values={
                "status": "RESERVE_NOT_MET",
                "highest_bid": str(highest_bid.bid_amount),
                "reserve_price": str(auction.reserve_price)
            }
        )
        db.add(audit)

        for n in notifications_to_add:
            db.add(n)

        db.commit()
        db.refresh(auction)

        return AuctionCloseResult(
            auction_id=auction.id,
            status=AuctionStatus.RESERVE_NOT_MET.value,
            already_closed=False,
            winner_id=None,
            winner_username=None,
            final_price=None,
            reserve_price=visible_reserve,
            reserve_met=False if (is_privileged and auction.reserve_price is not None) else None,
            total_bids=auction.total_bids,
            transaction_id=None,
            transaction_reference=None,
            notifications_dispatched=len(notifications_to_add),
            message="Auction closed as RESERVE_NOT_MET (bids did not reach private reserve)."
        )

    # -------------------------------------------------------------------------
    # CASE C: WINNER DECLARED (RESERVE MET OR NO RESERVE) -> COMPLETED
    # -------------------------------------------------------------------------
    auction.status = AuctionStatus.COMPLETED
    auction.winner_id = highest_bid.bidder_id
    auction.winning_bid_id = highest_bid.id
    highest_bid.is_winning_bid = True

    # Demote all other bids
    db.query(Bid).filter(Bid.auction_id == auction.id, Bid.id != highest_bid.id).update({"is_winning_bid": False})

    # Generate simulated demo settlement transaction (idempotent check)
    tx = db.query(Transaction).filter(Transaction.auction_id == auction.id).first()
    if not tx:
        payment_ref = f"TX-DEMO-{auction.id}-{int(now_utc.timestamp())}"
        tx = Transaction(
            auction_id=auction.id,
            buyer_id=highest_bid.bidder_id,
            seller_id=seller_id,
            amount=highest_bid.bid_amount,
            settlement_type=SettlementType.SIMULATED_DEMO,
            payment_status=PaymentStatus.SETTLEMENT_PENDING_DEMO,
            payment_reference=payment_ref
        )
        db.add(tx)
        db.flush()

    # 1. Notify Winner (AUCTION_WON)
    notifications_to_add.append(
        Notification(
            user_id=highest_bid.bidder_id,
            type=NotificationType.AUCTION_WON,
            title="Victory! You Won the Auction",
            message=(
                f"Congratulations! You won '{product_title}' with a winning bid of "
                f"${highest_bid.bid_amount:.2f}."
            ),
            link_url=f"/auctions/{auction.id}"
        )
    )

    # 2. Notify Seller (AUCTION_ENDED)
    winner_name = highest_bid.bidder.username if highest_bid.bidder else "Buyer"
    notifications_to_add.append(
        Notification(
            user_id=seller_id,
            type=NotificationType.AUCTION_ENDED,
            title="Listing Sold Successfully",
            message=(
                f"Your auction for '{product_title}' completed successfully at "
                f"${highest_bid.bid_amount:.2f} to winner @{winner_name}."
            ),
            link_url=f"/auctions/{auction.id}"
        )
    )

    # 3. Notify Outbid / Losing Participants
    losing_bidders = db.query(Bid.bidder_id)\
        .filter(Bid.auction_id == auction.id, Bid.bidder_id != highest_bid.bidder_id)\
        .distinct().all()

    for (loser_id,) in losing_bidders:
        if loser_id != seller_id:  # Double check not notifying seller as loser
            notifications_to_add.append(
                Notification(
                    user_id=loser_id,
                    type=NotificationType.AUCTION_ENDED,
                    title="Auction Closed",
                    message=(
                        f"The auction for '{product_title}' has closed. The winning bid was "
                        f"${highest_bid.bid_amount:.2f}."
                    ),
                    link_url=f"/auctions/{auction.id}"
                )
            )

    audit = AuditLog(
        user_id=closing_user_id or seller_id,
        action="AUCTION_COMPLETED",
        entity_type="AUCTION",
        entity_id=auction.id,
        old_values={"status": "ACTIVE"},
        new_values={
            "status": "COMPLETED",
            "winner_id": highest_bid.bidder_id,
            "final_price": str(highest_bid.bid_amount),
            "transaction_reference": tx.payment_reference
        }
    )
    db.add(audit)

    for n in notifications_to_add:
        db.add(n)

    db.commit()
    db.refresh(auction)

    return AuctionCloseResult(
        auction_id=auction.id,
        status=AuctionStatus.COMPLETED.value,
        already_closed=False,
        winner_id=highest_bid.bidder_id,
        winner_username=winner_name,
        final_price=highest_bid.bid_amount,
        reserve_price=visible_reserve,
        reserve_met=True if (is_privileged and auction.reserve_price is not None) else None,
        total_bids=auction.total_bids,
        transaction_id=tx.id,
        transaction_reference=tx.payment_reference,
        notifications_dispatched=len(notifications_to_add),
        message="Auction successfully closed and settled with winning buyer."
    )


def close_all_expired_auctions(
    db: Session,
    closing_user_id: Optional[int] = None,
    seller_id: Optional[int] = None
) -> BatchCloseResponse:
    """
    Identifies and closes expired active auctions.
    Security:
    - If caller is a non-admin SELLER, ONLY sweep auctions belonging to that seller.
    - If seller_id is explicitly passed, filters to that seller (only permitted for ADMIN or matching own id).
    """
    now_utc = datetime.now(timezone.utc)
    now_naive = now_utc.replace(tzinfo=None)

    closing_user = None
    if closing_user_id is not None:
        closing_user = db.query(User).options(joinedload(User.role)).filter(User.id == closing_user_id).first()
        if closing_user and closing_user.role and closing_user.role.name not in ("ADMIN", "SELLER"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Only sellers and administrators can trigger auction closing."
            )

    # Scoping rule: Non-admin sellers can ONLY sweep their own inventory
    effective_seller_id = seller_id
    if closing_user and closing_user.role and closing_user.role.name == "SELLER":
        effective_seller_id = closing_user.id

    # Find candidate expired auction IDs. SCHEDULED listings can expire without
    # ever being viewed after their start time, so the closing service settles
    # them through the same audit/notification path as ACTIVE listings.
    query = db.query(Auction.id).join(Auction.product)\
        .filter(
            Auction.status.in_([AuctionStatus.ACTIVE, AuctionStatus.SCHEDULED]),
            Auction.end_time <= now_naive
        )

    if effective_seller_id is not None:
        query = query.filter(Product.seller_id == effective_seller_id)

    expired_ids = query.all()

    results: List[AuctionCloseResult] = []
    completed_count = 0
    unsold_count = 0
    reserve_failed_count = 0
    already_closed_count = 0

    for (a_id,) in expired_ids:
        try:
            res = close_single_auction(db, a_id, closing_user_id=closing_user_id)
            results.append(res)
            if res.status == AuctionStatus.COMPLETED.value:
                completed_count += 1
            elif res.status == AuctionStatus.UNSOLD.value:
                unsold_count += 1
            elif res.status == AuctionStatus.RESERVE_NOT_MET.value:
                reserve_failed_count += 1
            else:
                already_closed_count += 1
        except Exception:
            db.rollback()
            logger.exception("Failed to close expired auction id=%s during batch close", a_id)

    return BatchCloseResponse(
        processed_count=len(results),
        completed_count=completed_count,
        unsold_count=unsold_count,
        reserve_failed_count=reserve_failed_count,
        already_closed_count=already_closed_count,
        results=results
    )

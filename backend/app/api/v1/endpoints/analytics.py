"""Role-scoped marketplace analytics backed by persisted application records."""

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, false, func
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.auction import Auction, AuctionStatus
from app.models.bid import Bid
from app.models.category import Category
from app.models.product import Product
from app.models.role import Role
from app.models.transaction import (
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentStatus,
    SettlementType,
    Transaction,
)
from app.models.user import User
from app.models.watchlist import Watchlist
from app.services.auction_lifecycle import activate_due_scheduled_auctions
from app.schemas.analytics import (
    ActivityTrend,
    AnalyticsFilters,
    AnalyticsKpis,
    AnalyticsResponse,
    AuctionStatusCount,
    CategoryPerformance,
    PerformanceRanking,
)

router = APIRouter()
SETTLED_STATUS = PaymentStatus.SETTLEMENT_COMPLETED_DEMO


REQUIRED_TRANSACTION_COLUMNS = {"settlement_type", "payment_status", "settled_at"}


def _payment_attempts_available(db: Session) -> bool:
    """True only when the payment lifecycle schema (migrations 002 and 003) exists.

    Only a missing schema is treated as "unavailable"; connection or other database
    errors still propagate so they are not hidden.
    """
    cached = db.info.get("payment_attempts_available")
    if cached is None:
        inspector = sqlalchemy_inspect(db.get_bind())
        cached = (
            inspector.has_table("payment_attempts")
            and inspector.has_table("transactions")
            and REQUIRED_TRANSACTION_COLUMNS.issubset(
                {column["name"] for column in inspector.get_columns("transactions")}
            )
        )
        db.info["payment_attempts_available"] = cached
    return cached


def _date_bounds(start_date: date, end_date: date):
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be on or after start_date.",
        )
    start = datetime.combine(start_date, time.min)
    end_exclusive = datetime.combine(end_date + timedelta(days=1), time.min)
    return start, end_exclusive


def _apply_date_range(query, column, start, end):
    return query.filter(column >= start, column < end)


def _product_base(db: Session, start, end, category_id, seller_id=None):
    query = db.query(Product).filter(Product.created_at >= start, Product.created_at < end)
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if seller_id is not None:
        query = query.filter(Product.seller_id == seller_id)
    return query


def _auction_base(db: Session, start, end, category_id, seller_id=None):
    query = db.query(Auction).join(Product, Auction.product_id == Product.id)
    query = _apply_date_range(query, Auction.created_at, start, end)
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if seller_id is not None:
        query = query.filter(Product.seller_id == seller_id)
    return query


def _bid_base(
    db: Session,
    start,
    end,
    category_id,
    *,
    bidder_id=None,
    seller_id=None,
    valid_only=False,
):
    query = db.query(Bid).join(Auction, Bid.auction_id == Auction.id).join(
        Product, Auction.product_id == Product.id
    )
    query = _apply_date_range(query, Bid.bid_time, start, end)
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if bidder_id is not None:
        query = query.filter(Bid.bidder_id == bidder_id)
    if seller_id is not None:
        query = query.filter(Product.seller_id == seller_id)
    if valid_only:
        query = query.filter(Bid.is_flagged_anomaly.is_(False))
    return query


def _settlement_base(
    db: Session,
    start,
    end,
    category_id,
    *,
    seller_id=None,
    buyer_id=None,
):
    query = db.query(Transaction).join(
        Auction, Transaction.auction_id == Auction.id
    ).join(
        Product, Auction.product_id == Product.id
    )
    if not _payment_attempts_available(db):
        return query.filter(false())

    query = query.join(
        PaymentAttempt, PaymentAttempt.transaction_id == Transaction.id
    ).filter(
        Auction.status == AuctionStatus.COMPLETED,
        Transaction.buyer_id == Auction.winner_id,
        Transaction.seller_id == Product.seller_id,
        Transaction.settlement_type == SettlementType.SIMULATED_DEMO,
        Transaction.payment_status == SETTLED_STATUS,
        PaymentAttempt.status == PaymentAttemptStatus.PAYMENT_COMPLETED,
        PaymentAttempt.provider_payment_id.isnot(None),
        PaymentAttempt.currency == "USD",
        PaymentAttempt.amount_minor == Transaction.amount * 100,
    )
    query = _apply_date_range(query, Transaction.settled_at, start, end)
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if seller_id is not None:
        query = query.filter(
            Transaction.seller_id == seller_id,
            Product.seller_id == seller_id,
        )
    if buyer_id is not None:
        query = query.filter(Transaction.buyer_id == buyer_id)
    return query


def _aggregate_settlements(query):
    result = query.with_entities(
        func.count(Transaction.id),
        func.coalesce(func.sum(Transaction.amount), 0),
        func.coalesce(func.avg(Transaction.amount), 0),
    ).one()
    return int(result[0] or 0), Decimal(result[1] or 0), Decimal(result[2] or 0)


def _make_bid_aggregate(db, start, end, category_id, *, bidder_id=None, seller_id=None):
    query = _bid_base(
        db,
        start,
        end,
        category_id,
        bidder_id=bidder_id,
        seller_id=seller_id,
        valid_only=True,
    )
    return query.with_entities(
        Bid.auction_id.label("auction_id"),
        func.count(Bid.id).label("valid_bids"),
    ).group_by(Bid.auction_id).subquery()


def _make_settlement_aggregate(query):
    return query.with_entities(
        Transaction.auction_id.label("auction_id"),
        func.count(Transaction.id).label("settled_transactions"),
        func.coalesce(func.sum(Transaction.amount), 0).label("settled_sales_value"),
    ).group_by(Transaction.auction_id).subquery()


def _performance_rankings(
    db: Session,
    start,
    end,
    category_id,
    *,
    seller_id=None,
    buyer_id=None,
    buyer_auction_ids=None,
):
    bid_aggregate = _make_bid_aggregate(
        db, start, end, category_id, bidder_id=buyer_id, seller_id=seller_id
    )
    settlements = _settlement_base(
        db, start, end, category_id, seller_id=seller_id, buyer_id=buyer_id
    )
    settlement_aggregate = _make_settlement_aggregate(settlements)

    product_query = db.query(
        Product.id,
        Product.title,
        Category.name,
        Auction.id,
        Auction.status,
        func.coalesce(bid_aggregate.c.valid_bids, 0),
        func.coalesce(settlement_aggregate.c.settled_transactions, 0),
        func.coalesce(settlement_aggregate.c.settled_sales_value, 0),
    ).join(Category, Product.category_id == Category.id).outerjoin(
        Auction, Auction.product_id == Product.id
    ).outerjoin(bid_aggregate, bid_aggregate.c.auction_id == Auction.id).outerjoin(
        settlement_aggregate, settlement_aggregate.c.auction_id == Auction.id
    )
    if buyer_auction_ids is None:
        product_query = product_query.filter(Product.created_at >= start, Product.created_at < end)
    if category_id is not None:
        product_query = product_query.filter(Product.category_id == category_id)
    if seller_id is not None:
        product_query = product_query.filter(Product.seller_id == seller_id)
    if buyer_auction_ids is not None:
        product_query = product_query.filter(Auction.id.in_(buyer_auction_ids))

    product_rows = product_query.order_by(
        func.coalesce(bid_aggregate.c.valid_bids, 0).desc(),
        func.coalesce(settlement_aggregate.c.settled_sales_value, 0).desc(),
        Product.id.desc(),
    ).limit(10).all()

    auction_query = db.query(
        Auction.product_id,
        Product.title,
        Category.name,
        Auction.id,
        Auction.status,
        func.coalesce(bid_aggregate.c.valid_bids, 0),
        func.coalesce(settlement_aggregate.c.settled_transactions, 0),
        func.coalesce(settlement_aggregate.c.settled_sales_value, 0),
    ).join(Product, Auction.product_id == Product.id).join(
        Category, Product.category_id == Category.id
    ).outerjoin(bid_aggregate, bid_aggregate.c.auction_id == Auction.id).outerjoin(
        settlement_aggregate, settlement_aggregate.c.auction_id == Auction.id
    )
    if buyer_auction_ids is None:
        auction_query = _apply_date_range(auction_query, Auction.created_at, start, end)
    if category_id is not None:
        auction_query = auction_query.filter(Product.category_id == category_id)
    if seller_id is not None:
        auction_query = auction_query.filter(Product.seller_id == seller_id)
    if buyer_auction_ids is not None:
        auction_query = auction_query.filter(Auction.id.in_(buyer_auction_ids))
    auction_rows = auction_query.order_by(
        func.coalesce(bid_aggregate.c.valid_bids, 0).desc(),
        func.coalesce(settlement_aggregate.c.settled_sales_value, 0).desc(),
        Auction.id.desc(),
    ).limit(10).all()

    def format_rows(rows):
        return [
            PerformanceRanking(
                product_id=row[0],
                product_title=row[1],
                category_name=row[2],
                auction_id=row[3],
                auction_status=row[4].value if row[4] is not None else None,
                valid_bids=int(row[5] or 0),
                settled_transactions=int(row[6] or 0),
                settled_sales_value=Decimal(row[7] or 0),
            )
            for row in rows
        ]

    return format_rows(product_rows), format_rows(auction_rows)


def _category_performance(
    db: Session,
    start,
    end,
    category_id,
    *,
    seller_id=None,
    bidder_id=None,
):
    categories_query = db.query(Category)
    if category_id is not None:
        categories_query = categories_query.filter(Category.id == category_id)
    categories = categories_query.order_by(Category.name).all()

    if bidder_id is not None:
        participant_auctions = db.query(
            Auction.id.label("auction_id"),
            Auction.product_id.label("product_id"),
            Product.category_id.label("category_id"),
        ).join(Product, Auction.product_id == Product.id).join(
            Bid, Bid.auction_id == Auction.id
        ).filter(
            Bid.bidder_id == bidder_id,
            Bid.is_flagged_anomaly.is_(False),
            Bid.bid_time >= start,
            Bid.bid_time < end,
        )
        if category_id is not None:
            participant_auctions = participant_auctions.filter(Product.category_id == category_id)
        participant_auctions = participant_auctions.distinct().subquery()
        product_counts = dict(
            db.query(participant_auctions.c.category_id,
                     func.count(func.distinct(participant_auctions.c.product_id)))
            .group_by(participant_auctions.c.category_id).all()
        )
        auction_counts = dict(
            db.query(participant_auctions.c.category_id,
                     func.count(func.distinct(participant_auctions.c.auction_id)))
            .group_by(participant_auctions.c.category_id).all()
        )
        bids = _bid_base(
            db, start, end, category_id, bidder_id=bidder_id, valid_only=True
        )
    else:
        products = _product_base(db, start, end, category_id, seller_id)
        product_counts = dict(
            products.with_entities(Product.category_id, func.count(Product.id))
            .group_by(Product.category_id).all()
        )
        auctions = _auction_base(db, start, end, category_id, seller_id)
        auction_counts = dict(
            auctions.with_entities(Product.category_id, func.count(Auction.id))
            .group_by(Product.category_id).all()
        )
        bids = _bid_base(
            db, start, end, category_id, seller_id=seller_id, valid_only=True
        )

    bid_counts = dict(
        bids.with_entities(Product.category_id, func.count(Bid.id))
        .group_by(Product.category_id).all()
    )
    settled = _settlement_base(
        db, start, end, category_id, seller_id=seller_id,
        buyer_id=bidder_id if seller_id is None and bidder_id is not None else None,
    )
    settlement_rows = settled.with_entities(
        Product.category_id,
        func.count(Transaction.id),
        func.coalesce(func.sum(Transaction.amount), 0),
    ).group_by(Product.category_id).all()
    settlement_metrics = {row[0]: (int(row[1]), Decimal(row[2] or 0)) for row in settlement_rows}

    return [
        CategoryPerformance(
            category_id=category.id,
            category_name=category.name,
            products=int(product_counts.get(category.id, 0)),
            auctions=int(auction_counts.get(category.id, 0)),
            bids=int(bid_counts.get(category.id, 0)),
            settled_transactions=settlement_metrics.get(category.id, (0, Decimal("0.00")))[0],
            settled_sales_value=settlement_metrics.get(category.id, (0, Decimal("0.00")))[1],
        )
        for category in categories
    ]


def _trend_rows(query, timestamp_column, value_column=None):
    grouped = query.with_entities(
        func.date(timestamp_column),
        func.count(),
        func.coalesce(func.sum(value_column), 0) if value_column is not None else func.count(),
    ).group_by(func.date(timestamp_column)).all()
    output = {}
    for period, count, value in grouped:
        key = period.isoformat() if hasattr(period, "isoformat") else str(period)
        output[key] = (int(count or 0), Decimal(value or 0))
    return output


def _trends(
    db: Session,
    start,
    end,
    category_id,
    *,
    seller_id=None,
    bidder_id=None,
    buyer_id=None,
    buyer_auction_ids=None,
):
    auction_q = _auction_base(db, start, end, category_id, seller_id)
    bid_q = _bid_base(
        db, start, end, category_id, bidder_id=bidder_id, seller_id=seller_id,
        valid_only=bidder_id is not None or seller_id is not None,
    )
    settlement_q = _settlement_base(
        db, start, end, category_id, seller_id=seller_id, buyer_id=buyer_id
    )
    if buyer_auction_ids is not None:
        bid_q = bid_q.filter(Bid.auction_id.in_(buyer_auction_ids))
    auctions_by_day = (
        _trend_rows(auction_q, Auction.created_at)
        if buyer_auction_ids is None else {}
    )
    bids_by_day = _trend_rows(bid_q, Bid.bid_time)
    settlements_by_day = (
        _trend_rows(settlement_q, Transaction.settled_at, Transaction.amount)
        if _payment_attempts_available(db) else {}
    )

    days = sorted(set(auctions_by_day) | set(bids_by_day) | set(settlements_by_day))
    daily = []
    for day in days:
        auction_count = auctions_by_day.get(day, (0, Decimal("0")))[0]
        bid_count = bids_by_day.get(day, (0, Decimal("0")))[0]
        settlement_count, sales_value = settlements_by_day.get(day, (0, Decimal("0")))
        daily.append({
            "period": day,
            "auctions": auction_count,
            "bids": bid_count,
            "settlements": settlement_count,
            "settled_sales_value": sales_value,
        })

    monthly_data: Dict[str, dict] = defaultdict(
        lambda: {
            "period": "",
            "auctions": 0,
            "bids": 0,
            "settlements": 0,
            "settled_sales_value": Decimal("0.00"),
        }
    )
    for day in daily:
        month = day["period"][:7]
        row = monthly_data[month]
        row["period"] = month
        for key in ("auctions", "bids", "settlements"):
            row[key] += day[key]
        row["settled_sales_value"] += day["settled_sales_value"]
    return [ActivityTrend(**row) for row in daily], [
        ActivityTrend(**monthly_data[key]) for key in sorted(monthly_data)
    ]


def _auction_kpis(query, now_naive):
    total = query.with_entities(func.count(Auction.id)).scalar() or 0
    status_counts = dict(
        query.with_entities(Auction.status, func.count(Auction.id))
        .group_by(Auction.status).all()
    )
    active = query.filter(
        Auction.status == AuctionStatus.ACTIVE,
        Auction.start_time <= now_naive,
        Auction.end_time > now_naive,
    ).count()
    upcoming = query.filter(
        Auction.status == AuctionStatus.SCHEDULED,
        Auction.start_time > now_naive,
        Auction.end_time > now_naive,
    ).count()
    distribution = [
        AuctionStatusCount(status=key.value, count=int(value))
        for key, value in sorted(status_counts.items(), key=lambda entry: entry[0].value)
    ]
    return int(total), int(active), int(upcoming), int(
        status_counts.get(AuctionStatus.COMPLETED, 0)
    ), int(status_counts.get(AuctionStatus.CANCELLED, 0)), distribution


@router.get("", response_model=AnalyticsResponse, summary="Get role-scoped analytics")
def get_analytics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    category_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AnalyticsResponse:
    """Return marketplace totals for admins and private, owner-scoped metrics otherwise."""
    role = current_user.role.name.upper() if current_user.role else ""
    if role not in {"ADMIN", "SELLER", "BUYER"}:
        raise HTTPException(status_code=403, detail="Analytics are not available for this role.")

    today = datetime.now(timezone.utc).date()
    selected_start = start_date or (today - timedelta(days=29))
    selected_end = end_date or today
    start, end = _date_bounds(selected_start, selected_end)
    current_time = datetime.now(timezone.utc)
    activate_due_scheduled_auctions(db, now=current_time)
    now_naive = current_time.replace(tzinfo=None)

    is_admin = role == "ADMIN"
    is_seller = role == "SELLER"
    seller_id = current_user.id if is_seller else None
    buyer_id = current_user.id if role == "BUYER" else None

    buyer_bid_query = None
    buyer_auction_ids = None
    if buyer_id is not None:
        buyer_bid_query = _bid_base(
            db, start, end, category_id, bidder_id=buyer_id, valid_only=True
        )
        buyer_auction_ids = buyer_bid_query.with_entities(Bid.auction_id).distinct()
        auction_query = db.query(Auction).join(Product, Auction.product_id == Product.id).filter(
            Auction.id.in_(buyer_auction_ids)
        )
        if category_id is not None:
            auction_query = auction_query.filter(Product.category_id == category_id)
    else:
        auction_query = _auction_base(db, start, end, category_id, seller_id)

    total_auctions, active, upcoming, completed, cancelled, distribution = _auction_kpis(
        auction_query, now_naive
    )
    if buyer_id is not None:
        product_query = db.query(Product).filter(
            Product.id.in_(
                db.query(Auction.product_id).filter(Auction.id.in_(buyer_auction_ids))
            )
        )
        if category_id is not None:
            product_query = product_query.filter(Product.category_id == category_id)
    else:
        product_query = _product_base(db, start, end, category_id, seller_id)
    total_products = int(product_query.with_entities(func.count(Product.id)).scalar() or 0)

    if is_admin:
        role_counts = dict(
            db.query(Role.name, func.count(User.id))
            .join(User, User.role_id == Role.id)
            .filter(User.created_at >= start, User.created_at < end)
            .group_by(Role.name).all()
        )
        registered_users = int(sum(role_counts.values()))
        buyers = int(role_counts.get("BUYER", 0))
        sellers = int(role_counts.get("SELLER", 0))
        recorded_bids = int(
            _bid_base(db, start, end, category_id).with_entities(func.count(Bid.id)).scalar() or 0
        )
        valid_bids = int(
            _bid_base(db, start, end, category_id, valid_only=True)
            .with_entities(func.count(Bid.id)).scalar() or 0
        )
        settlement_query = _settlement_base(db, start, end, category_id)
        settled_count, settled_value, average_price = _aggregate_settlements(settlement_query)
        purchases = 0
        spending = Decimal("0.00")
        auctions_participated = 0
        auctions_won = 0
        watchlist_items = 0
        scope = "admin"
    elif is_seller:
        recorded_bids = int(
            _bid_base(db, start, end, category_id, seller_id=seller_id, valid_only=True)
            .with_entities(func.count(Bid.id)).scalar() or 0
        )
        valid_bids = recorded_bids
        settled_count, settled_value, average_price = _aggregate_settlements(
            _settlement_base(db, start, end, category_id, seller_id=seller_id)
        )
        role_counts = {}
        registered_users = buyers = sellers = 0
        purchases = 0
        spending = Decimal("0.00")
        auctions_participated = 0
        auctions_won = 0
        watchlist_items = 0
        scope = "seller"
    else:
        valid_bids = int(buyer_bid_query.with_entities(func.count(Bid.id)).scalar() or 0)
        recorded_bids = valid_bids
        auctions_participated = int(
            buyer_bid_query.with_entities(
                func.count(func.distinct(Bid.auction_id))
            ).scalar() or 0
        )
        won_query = db.query(Auction.id).join(
            Product, Auction.product_id == Product.id
        ).filter(
            Auction.winner_id == buyer_id,
            Auction.status == AuctionStatus.COMPLETED,
            Auction.updated_at >= start,
            Auction.updated_at < end,
        )
        if category_id is not None:
            won_query = won_query.filter(Product.category_id == category_id)
        auctions_won = int(won_query.count())
        settled_count, spending, average_price = _aggregate_settlements(
            _settlement_base(db, start, end, category_id, buyer_id=buyer_id)
        )
        settled_value = spending
        purchases = settled_count
        watchlist_query = db.query(func.count(Watchlist.id)).join(
            Auction, Watchlist.auction_id == Auction.id
        ).join(Product, Auction.product_id == Product.id).filter(
            Watchlist.user_id == buyer_id,
            Watchlist.created_at >= start,
            Watchlist.created_at < end,
        )
        if category_id is not None:
            watchlist_query = watchlist_query.filter(Product.category_id == category_id)
        watchlist_items = int(watchlist_query.scalar() or 0)
        role_counts = {}
        registered_users = buyers = sellers = 0
        scope = "buyer"

    category_rows = _category_performance(
        db,
        start,
        end,
        category_id,
        seller_id=seller_id,
        bidder_id=buyer_id,
    )

    product_rankings, auction_rankings = _performance_rankings(
        db,
        start,
        end,
        category_id,
        seller_id=seller_id,
        buyer_id=buyer_id,
        buyer_auction_ids=buyer_auction_ids,
    )
    daily_trends, monthly_trends = _trends(
        db,
        start,
        end,
        category_id,
        seller_id=seller_id,
        bidder_id=buyer_id,
        buyer_id=buyer_id,
        buyer_auction_ids=buyer_auction_ids,
    )

    return AnalyticsResponse(
        scope=scope,
        settlement_metrics_available=_payment_attempts_available(db),
        filters=AnalyticsFilters(
            start_date=selected_start, end_date=selected_end, category_id=category_id
        ),
        kpis=AnalyticsKpis(
            registered_users=registered_users,
            buyers=buyers,
            sellers=sellers,
            total_products=total_products,
            total_auctions=total_auctions,
            active_auctions=active,
            upcoming_auctions=upcoming,
            completed_auctions=completed,
            cancelled_auctions=cancelled,
            recorded_bids=recorded_bids,
            valid_bids=valid_bids,
            auctions_participated=auctions_participated,
            auctions_won=auctions_won,
            watchlist_items=watchlist_items,
            settled_transactions=settled_count,
            settled_sales_value=settled_value,
            average_settled_selling_price=average_price,
            purchases=purchases,
            spending=spending,
        ),
        auction_status_distribution=distribution,
        category_performance=category_rows,
        product_rankings=product_rankings,
        auction_rankings=auction_rankings,
        daily_trends=daily_trends,
        monthly_trends=monthly_trends,
    )

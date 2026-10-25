"""
Isolated auction catalog lifecycle tests.

These tests use an in-memory SQLite database so they do not touch Aiven data.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.endpoints.auctions import _utc_naive, list_auctions, update_auction
from app.api.v1.endpoints.bids import _place_bid_sqlalchemy_fallback
from app.schemas.auction import AuctionCreate, AuctionUpdate
from app.db.base_class import Base
import app.models  # noqa: F401 - register all ORM tables with Base metadata
from app.services.auction_closing import close_all_expired_auctions
from app.models.auction import Auction, AuctionStatus
from app.models.category import Category
from app.models.product import Product, ProductCondition
from app.models.role import Role
from app.models.user import User, UserStatus
from app.services.auction_lifecycle import activate_due_scheduled_auctions


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _seed_catalog(db):
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    seller_role = Role(id=1, name="SELLER", description="Seller")
    buyer_role = Role(id=2, name="BUYER", description="Buyer")
    seller = User(
        id=1,
        username="seller_one",
        email="seller@example.com",
        password_hash="x",
        full_name="Seller One",
        role=seller_role,
        status=UserStatus.ACTIVE,
    )
    buyer = User(
        id=2,
        username="buyer_one",
        email="buyer@example.com",
        password_hash="x",
        full_name="Buyer One",
        role=buyer_role,
        status=UserStatus.ACTIVE,
    )
    category = Category(id=1, name="Electronics", slug="electronics", icon_name="Cpu")
    db.add_all([seller_role, buyer_role, seller, buyer, category])

    products = [
        Product(
            id=1,
            seller=seller,
            category=category,
            title="Active Sony PlayStation 5 Slim Disc Edition",
            description="Active console auction",
            condition_status=ProductCondition.NEW,
            image_url="https://example.com/active.jpg",
        ),
        Product(
            id=2,
            seller=seller,
            category=category,
            title="Upcoming Sony PlayStation 5 Slim Disc Edition",
            description="Upcoming console auction",
            condition_status=ProductCondition.NEW,
            image_url="https://example.com/upcoming.jpg",
        ),
        Product(
            id=3,
            seller=seller,
            category=category,
            title="Completed Console",
            description="Completed auction",
            condition_status=ProductCondition.USED,
            image_url="https://example.com/completed.jpg",
        ),
        Product(
            id=4,
            seller=seller,
            category=category,
            title="Expired Scheduled Console",
            description="Expired scheduled auction",
            condition_status=ProductCondition.USED,
            image_url="https://example.com/expired.jpg",
        ),
    ]
    db.add_all(products)
    db.flush()

    auctions = [
        Auction(
            id=1,
            product_id=1,
            starting_price=Decimal("10.00"),
            reserve_price=Decimal("20.00"),
            minimum_increment=Decimal("1.00"),
            start_time=now - timedelta(minutes=5),
            end_time=now + timedelta(hours=1),
            status=AuctionStatus.ACTIVE,
        ),
        Auction(
            id=2,
            product_id=2,
            starting_price=Decimal("10.00"),
            reserve_price=Decimal("20.00"),
            minimum_increment=Decimal("1.00"),
            start_time=now + timedelta(minutes=30),
            end_time=now + timedelta(hours=2),
            status=AuctionStatus.SCHEDULED,
        ),
        Auction(
            id=3,
            product_id=3,
            starting_price=Decimal("10.00"),
            reserve_price=Decimal("20.00"),
            minimum_increment=Decimal("1.00"),
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
            status=AuctionStatus.COMPLETED,
        ),
        Auction(
            id=4,
            product_id=4,
            starting_price=Decimal("10.00"),
            reserve_price=Decimal("20.00"),
            minimum_increment=Decimal("1.00"),
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
            status=AuctionStatus.SCHEDULED,
        ),
    ]
    db.add_all(auctions)
    db.commit()
    return buyer


def _list(db, status_filter="AVAILABLE", search=None, condition=None):
    return list_auctions(
        page=1,
        page_size=20,
        status_filter=status_filter,
        search=search,
        category_id=None,
        category_slug=None,
        seller_id=None,
        condition=condition,
        min_price=None,
        max_price=None,
        sort_by="newest",
        db=db,
        optional_user=None,
    )


def test_default_catalog_returns_active_and_upcoming_only(db):
    _seed_catalog(db)

    response = _list(db)
    statuses = {item.status for item in response.items}

    assert response.total == 2
    assert statuses == {"ACTIVE", "SCHEDULED"}
    assert all(item.start_time.utcoffset() == timedelta(0) for item in response.items)
    assert all(item.end_time.utcoffset() == timedelta(0) for item in response.items)
    assert db.get(Auction, 4).status == AuctionStatus.SCHEDULED


def test_catalog_search_matches_product_title(db):
    _seed_catalog(db)

    response = _list(db, search="PlayStation 5 Slim")

    assert response.total == 2
    assert all("PlayStation 5 Slim" in item.product.title for item in response.items)


def test_active_and_upcoming_filters_use_time_boundaries(db):
    _seed_catalog(db)

    active = _list(db, status_filter="ACTIVE")
    upcoming = _list(db, status_filter="SCHEDULED")

    assert active.total == 1
    assert active.items[0].status == "ACTIVE"
    assert upcoming.total == 1
    assert upcoming.items[0].status == "SCHEDULED"


def test_scheduled_auction_activates_at_its_start_time(db):
    _seed_catalog(db)
    auction = db.get(Auction, 2)
    start_time = auction.start_time.replace(tzinfo=timezone.utc)

    assert activate_due_scheduled_auctions(db, start_time - timedelta(microseconds=1)) == 0
    db.refresh(auction)
    assert auction.status == AuctionStatus.SCHEDULED

    assert activate_due_scheduled_auctions(db, start_time) == 1
    db.refresh(auction)
    assert auction.status == AuctionStatus.ACTIVE
    assert activate_due_scheduled_auctions(db, start_time) == 0


def test_condition_all_does_not_exclude_active_or_upcoming_auctions(db):
    _seed_catalog(db)

    response = _list(db, condition="ALL")

    assert response.total == 2
    assert {item.status for item in response.items} == {"ACTIVE", "SCHEDULED"}


def test_buyer_cannot_bid_before_scheduled_start(db):
    buyer = _seed_catalog(db)

    with pytest.raises(HTTPException) as exc:
        _place_bid_sqlalchemy_fallback(
            db=db,
            auction_id=2,
            bidder=buyer,
            bid_amount=Decimal("10.00"),
            ip_address="127.0.0.1",
        )

    assert exc.value.status_code == 400
    assert "SCHEDULED" in exc.value.detail


def test_expired_scheduled_auction_is_settled_by_closing_service(db):
    _seed_catalog(db)

    result = close_all_expired_auctions(db=db, closing_user_id=1)

    assert result.processed_count == 1
    assert result.unsold_count == 1
    assert db.get(Auction, 4).status == AuctionStatus.UNSOLD


def test_timezone_aware_datetimes_normalize_to_naive_utc():
    aware = datetime.now(timezone(timedelta(hours=5, minutes=30)))

    normalized = _utc_naive(aware)

    assert normalized == aware.astimezone(timezone.utc).replace(tzinfo=None)
    assert normalized.tzinfo is None


def test_auction_create_rejects_past_start_and_end_times():
    now = datetime.now(timezone.utc)
    common = {
        "product_id": 1,
        "starting_price": Decimal("10.00"),
        "end_time": now + timedelta(hours=2),
    }

    with pytest.raises(ValueError, match="start time cannot be in the past"):
        AuctionCreate(**{**common, "start_time": now - timedelta(minutes=1)})

    with pytest.raises(ValueError, match="end time cannot be in the past"):
        AuctionCreate(
            product_id=1,
            starting_price=Decimal("10.00"),
            start_time=now + timedelta(hours=2),
            end_time=now - timedelta(hours=1),
        )


def test_auction_create_rejects_end_at_or_before_start_across_timezones():
    now = datetime.now(timezone.utc)
    offset = timezone(timedelta(hours=5, minutes=30))
    start_time = (now + timedelta(hours=2)).astimezone(offset)
    end_time = (now + timedelta(hours=1)).astimezone(timezone.utc)

    with pytest.raises(ValueError, match="strictly greater than start time"):
        AuctionCreate(
            product_id=1,
            starting_price=Decimal("10.00"),
            start_time=start_time,
            end_time=end_time,
        )


def test_auction_create_accepts_future_times_with_different_timezones():
    now = datetime.now(timezone.utc)
    offset = timezone(timedelta(hours=5, minutes=30))
    start_time = (now + timedelta(hours=1)).astimezone(offset)
    end_time = now + timedelta(hours=2)

    auction = AuctionCreate(
        product_id=1,
        starting_price=Decimal("10.00"),
        start_time=start_time,
        end_time=end_time,
    )

    assert _utc_naive(auction.start_time) == _utc_naive(start_time)
    assert _utc_naive(auction.end_time) == _utc_naive(end_time)


def test_auction_update_rejects_past_times():
    with pytest.raises(ValueError, match="start time cannot be in the past"):
        AuctionUpdate(start_time=datetime.now(timezone.utc) - timedelta(minutes=1))


def test_auction_update_rejects_end_before_start_across_timezones():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="strictly greater than start time"):
        AuctionUpdate(
            start_time=(now + timedelta(hours=2)).astimezone(
                timezone(timedelta(hours=5, minutes=30))
            ),
            end_time=now + timedelta(hours=1),
        )


def test_auction_update_cannot_activate_or_reschedule_before_future_start(db):
    _seed_catalog(db)
    seller = db.get(User, 1)

    with pytest.raises(HTTPException, match="cannot be activated before"):
        update_auction(
            auction_id=2,
            auction_in=AuctionUpdate(status="ACTIVE"),
            db=db,
            current_seller=seller,
        )

    future_start = datetime.now(timezone.utc) + timedelta(minutes=10)
    future_end = future_start + timedelta(hours=2)
    with pytest.raises(HTTPException, match="cannot be rescheduled"):
        update_auction(
            auction_id=1,
            auction_in=AuctionUpdate(start_time=future_start, end_time=future_end),
            db=db,
            current_seller=seller,
        )

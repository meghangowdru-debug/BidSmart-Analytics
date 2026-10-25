"""Analytics tests using an isolated in-memory SQLite database."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.endpoints.analytics import get_analytics
from app.db.base_class import Base
import app.models  # noqa: F401 - register all ORM tables
from app.models.auction import Auction, AuctionStatus
from app.models.bid import Bid
from app.models.category import Category
from app.models.product import Product, ProductCondition
from app.models.role import Role
from app.models.transaction import (
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentStatus,
    SettlementType,
    Transaction,
)
from app.models.user import User, UserStatus
from app.models.watchlist import Watchlist
from app.services.payment_service import PaymentService


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, future=True)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _user(db, user_id, username, role):
    role_row = db.query(Role).filter(Role.name == role).first()
    if role_row is None:
        role_row = Role(name=role, description=role.title())
        db.add(role_row)
        db.flush()
    user = User(
        id=user_id,
        username=username,
        email=f"{username}@example.com",
        password_hash="test-hash",
        full_name=username,
        role_id=role_row.id,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    return user


def _seed(db):
    admin = _user(db, 1, "admin", "ADMIN")
    seller_one = _user(db, 2, "seller_one", "SELLER")
    seller_two = _user(db, 3, "seller_two", "SELLER")
    buyer_one = _user(db, 4, "buyer_one", "BUYER")
    buyer_two = _user(db, 5, "buyer_two", "BUYER")
    category_one = Category(name="Electronics", slug="electronics", icon_name="Cpu")
    category_two = Category(name="Books", slug="books", icon_name="Book")
    db.add_all([category_one, category_two])
    db.flush()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    products = [
        Product(
            id=1, seller_id=seller_one.id, category_id=category_one.id,
            title="Seller One Completed Product", description="Product one",
            condition_status=ProductCondition.NEW, image_url="https://example.test/1",
        ),
        Product(
            id=2, seller_id=seller_one.id, category_id=category_two.id,
            title="Seller One Upcoming Product", description="Product two",
            condition_status=ProductCondition.USED, image_url="https://example.test/2",
        ),
        Product(
            id=3, seller_id=seller_two.id, category_id=category_one.id,
            title="Seller Two Product", description="Product three",
            condition_status=ProductCondition.VINTAGE, image_url="https://example.test/3",
        ),
    ]
    db.add_all(products)
    db.flush()

    auctions = [
        Auction(
            id=1, product_id=1, starting_price=Decimal("10.00"),
            current_highest_bid=Decimal("120.00"), reserve_price=Decimal("100.00"),
            minimum_increment=Decimal("1.00"), start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=1), status=AuctionStatus.COMPLETED,
            winner_id=buyer_one.id, total_bids=2,
        ),
        Auction(
            id=2, product_id=2, starting_price=Decimal("20.00"),
            reserve_price=None, minimum_increment=Decimal("1.00"),
            start_time=now + timedelta(days=1), end_time=now + timedelta(days=2),
            status=AuctionStatus.SCHEDULED, total_bids=0,
        ),
        Auction(
            id=3, product_id=3, starting_price=Decimal("30.00"),
            current_highest_bid=Decimal("50.00"), minimum_increment=Decimal("1.00"),
            start_time=now - timedelta(days=2), end_time=now - timedelta(days=1),
            status=AuctionStatus.COMPLETED, winner_id=buyer_two.id, total_bids=1,
        ),
    ]
    db.add_all(auctions)
    db.flush()

    db.add_all([
        Bid(
            auction_id=1, bidder_id=buyer_one.id, bid_amount=Decimal("120.00"),
            bid_time=now - timedelta(hours=1), is_winning_bid=True,
            is_flagged_anomaly=False, ip_address="127.0.0.1",
        ),
        Bid(
            auction_id=1, bidder_id=buyer_two.id, bid_amount=Decimal("110.00"),
            bid_time=now - timedelta(minutes=30), is_winning_bid=False,
            is_flagged_anomaly=True, ip_address="127.0.0.1",
        ),
        Bid(
            auction_id=3, bidder_id=buyer_two.id, bid_amount=Decimal("50.00"),
            bid_time=now - timedelta(minutes=20), is_winning_bid=True,
            is_flagged_anomaly=False, ip_address="127.0.0.1",
        ),
    ])
    settled_transaction = Transaction(
        auction_id=1, buyer_id=buyer_one.id, seller_id=seller_one.id,
        amount=Decimal("120.00"), settlement_type=SettlementType.SIMULATED_DEMO,
        payment_status=PaymentStatus.SETTLEMENT_COMPLETED_DEMO,
        payment_reference="TEST-SETTLED-1", created_at=now - timedelta(minutes=10),
        settled_at=now - timedelta(minutes=10),
    )
    pending_transaction = Transaction(
        auction_id=3, buyer_id=buyer_two.id, seller_id=seller_two.id,
        amount=Decimal("50.00"), settlement_type=SettlementType.SIMULATED_DEMO,
        payment_status=PaymentStatus.SETTLEMENT_PENDING_DEMO,
        payment_reference="TEST-PENDING-2", created_at=now - timedelta(minutes=5),
    )
    db.add_all([settled_transaction, pending_transaction])
    db.flush()
    db.add(PaymentAttempt(
        transaction_id=settled_transaction.id,
        provider_order_id="order_analytics_seed",
        provider_payment_id="pay_analytics_seed",
        amount_minor=12000,
        currency="USD",
        status=PaymentAttemptStatus.PAYMENT_COMPLETED,
    ))
    db.add(Watchlist(user_id=buyer_one.id, auction_id=2, created_at=now))
    db.commit()
    return {
        "admin": admin,
        "seller_one": seller_one,
        "seller_two": seller_two,
        "buyer_one": buyer_one,
        "buyer_two": buyer_two,
        "category_one": category_one,
        "category_two": category_two,
        "now": now,
    }


def _get(db, user, **filters):
    return get_analytics(
        start_date=filters.get("start_date"),
        end_date=filters.get("end_date"),
        category_id=filters.get("category_id"),
        db=db,
        current_user=user,
    )


def test_admin_metrics_count_only_authoritative_settlements(db):
    seeded = _seed(db)

    result = _get(db, seeded["admin"])

    assert result.scope == "admin"
    assert result.kpis.registered_users == 5
    assert result.kpis.buyers == 2
    assert result.kpis.sellers == 2
    assert result.kpis.total_products == 3
    assert result.kpis.total_auctions == 3
    assert result.kpis.upcoming_auctions == 1
    assert result.kpis.completed_auctions == 2
    assert result.kpis.recorded_bids == 3
    assert result.kpis.valid_bids == 2
    assert result.kpis.settled_transactions == 1
    assert result.kpis.settled_sales_value == Decimal("120.00")
    assert result.kpis.average_settled_selling_price == Decimal("120.00")
    assert sum(item.count for item in result.auction_status_distribution) == 3


def test_nonpayment_analytics_remain_available_without_payment_attempts_table(db):
    seeded = _seed(db)
    PaymentAttempt.__table__.drop(bind=db.get_bind())

    result = _get(db, seeded["admin"])

    assert result.settlement_metrics_available is False
    assert result.kpis.total_products == 3
    assert result.kpis.total_auctions == 3
    assert result.kpis.valid_bids == 2
    assert result.kpis.settled_transactions == 0
    assert result.kpis.settled_sales_value == Decimal("0.00")
    assert all(item.settled_transactions == 0 for item in result.category_performance)


def test_analytics_survive_legacy_transactions_table_without_settled_at(db):
    from sqlalchemy import text

    seeded = _seed(db)
    bind = db.get_bind()
    PaymentAttempt.__table__.drop(bind=bind)
    with bind.begin() as connection:
        connection.execute(text("DROP INDEX IF EXISTS idx_transactions_settled_at"))
        connection.execute(text("ALTER TABLE transactions DROP COLUMN settled_at"))
    db.info.clear()

    for user_key in ("admin", "seller_one"):
        result = _get(db, seeded[user_key])

        assert result.settlement_metrics_available is False
        assert result.kpis.total_auctions >= 1
        assert result.kpis.settled_transactions == 0
        assert all(day.settlements == 0 for day in result.daily_trends)


def test_product_auction_bid_and_settlement_changes_are_reflected_from_database(db):
    seeded = _seed(db)
    today = seeded["now"].date()
    filters = {
        "start_date": today - timedelta(days=1),
        "end_date": today + timedelta(days=1),
    }

    initial = _get(db, seeded["admin"], **filters)
    assert initial.kpis.total_products == 3
    assert initial.kpis.total_auctions == 3
    assert initial.kpis.recorded_bids == 3
    assert initial.kpis.settled_transactions == 1

    category = seeded["category_one"]
    added_product = Product(
        seller_id=seeded["seller_one"].id,
        category_id=category.id,
        title="New Analytics Product",
        description="Created for analytics regression coverage",
        condition_status=ProductCondition.NEW,
        image_url="https://example.test/new",
        created_at=seeded["now"],
    )
    db.add(added_product)
    db.flush()
    added_auction = Auction(
        product_id=added_product.id,
        starting_price=Decimal("25.00"),
        current_highest_bid=None,
        reserve_price=None,
        minimum_increment=Decimal("1.00"),
        start_time=seeded["now"] - timedelta(minutes=1),
        end_time=seeded["now"] + timedelta(days=1),
        status=AuctionStatus.ACTIVE,
        total_bids=0,
        created_at=seeded["now"],
    )
    db.add(added_auction)
    db.commit()

    after_listing = _get(db, seeded["admin"], **filters)
    assert after_listing.kpis.total_products == 4
    assert after_listing.kpis.total_auctions == 4

    added_product.title = "Updated Analytics Product"
    db.commit()
    after_product_update = _get(db, seeded["admin"], **filters)
    assert any(
        row.product_title == "Updated Analytics Product"
        for row in after_product_update.product_rankings
    )

    valid_bid = Bid(
        auction_id=added_auction.id,
        bidder_id=seeded["buyer_one"].id,
        bid_amount=Decimal("25.00"),
        bid_time=seeded["now"],
        is_winning_bid=True,
        is_flagged_anomaly=False,
        ip_address="127.0.0.1",
    )
    db.add(valid_bid)
    added_auction.total_bids = 1
    added_auction.current_highest_bid = Decimal("25.00")
    db.commit()

    after_bid = _get(db, seeded["admin"], **filters)
    assert after_bid.kpis.recorded_bids == 4
    assert sum(row.bids for row in after_bid.daily_trends) == 4
    assert any(
        row.product_title == "Updated Analytics Product" and row.valid_bids == 1
        for row in after_bid.auction_rankings
    )

    settled_transaction = Transaction(
        auction_id=added_auction.id,
        buyer_id=seeded["buyer_one"].id,
        seller_id=seeded["seller_one"].id,
        amount=Decimal("25.00"),
        settlement_type=SettlementType.SIMULATED_DEMO,
        payment_status=PaymentStatus.SETTLEMENT_PENDING_DEMO,
        payment_reference="TEST-PENDING-ANALYTICS",
        created_at=seeded["now"],
    )
    db.add(settled_transaction)
    db.commit()
    pending = _get(db, seeded["admin"], **filters)
    assert pending.kpis.settled_transactions == 1
    assert pending.kpis.settled_sales_value == Decimal("120.00")

    settled_transaction.payment_status = PaymentStatus.SETTLEMENT_COMPLETED_DEMO
    settled_transaction.settled_at = seeded["now"]
    added_auction.status = AuctionStatus.COMPLETED
    added_auction.winner_id = seeded["buyer_one"].id
    db.add(PaymentAttempt(
        transaction_id=settled_transaction.id,
        provider_order_id="order_analytics_update",
        provider_payment_id="pay_analytics_update",
        amount_minor=2500,
        currency="USD",
        status=PaymentAttemptStatus.PAYMENT_COMPLETED,
    ))
    db.commit()
    completed = _get(db, seeded["admin"], **filters)
    assert completed.kpis.settled_transactions == 2
    assert completed.kpis.settled_sales_value == Decimal("145.00")
    assert completed.kpis.average_settled_selling_price == Decimal("72.50")

    removable_product = db.query(Product).filter(Product.id == 2).one()
    db.delete(removable_product)
    db.commit()
    after_product_delete = _get(db, seeded["admin"], **filters)
    assert after_product_delete.kpis.total_products == 3
    assert after_product_delete.kpis.total_auctions == 3
    assert all(
        row.product_title != "Seller One Upcoming Product"
        for row in after_product_delete.product_rankings
    )


def test_due_scheduled_auction_is_activated_before_analytics_are_aggregated(db):
    seeded = _seed(db)
    auction = db.query(Auction).filter(Auction.id == 2).one()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    auction.start_time = now - timedelta(seconds=1)
    auction.end_time = now + timedelta(hours=1)
    db.commit()
    assert auction.status == AuctionStatus.SCHEDULED

    result = _get(db, seeded["admin"])

    db.refresh(auction)
    assert auction.status == AuctionStatus.ACTIVE
    assert result.kpis.active_auctions == 1
    assert result.kpis.upcoming_auctions == 0


def test_seller_analytics_are_limited_to_the_authenticated_seller(db):
    seeded = _seed(db)

    result = _get(db, seeded["seller_one"])

    assert result.scope == "seller"
    assert result.kpis.total_products == 2
    assert result.kpis.total_auctions == 2
    assert result.kpis.recorded_bids == 1
    assert result.kpis.settled_sales_value == Decimal("120.00")
    assert sum(row.bids for row in result.daily_trends) == 1
    assert {item.product_title for item in result.product_rankings} == {
        "Seller One Completed Product",
        "Seller One Upcoming Product",
    }
    assert {
        item.category_name: item.products
        for item in result.category_performance
        if item.products
    } == {"Books": 1, "Electronics": 1}


def test_seller_category_performance_excludes_anomalous_bids(db):
    seeded = _seed(db)

    result = _get(db, seeded["seller_one"])

    bids_by_category = {
        item.category_name: item.bids for item in result.category_performance
    }
    assert bids_by_category == {"Books": 0, "Electronics": 1}


def test_settlement_metrics_and_trends_use_completion_update_date(db):
    seeded = _seed(db)
    transaction = db.query(Transaction).filter(Transaction.auction_id == 3).one()
    completion_time = seeded["now"] - timedelta(days=2)
    transaction.created_at = completion_time - timedelta(days=3)
    transaction.payment_status = PaymentStatus.SETTLEMENT_COMPLETED_DEMO
    transaction.updated_at = completion_time + timedelta(days=1)
    transaction.settled_at = completion_time
    db.add(PaymentAttempt(
        transaction_id=transaction.id,
        provider_order_id="order_analytics_date",
        provider_payment_id="pay_analytics_date",
        amount_minor=5000,
        currency="USD",
        status=PaymentAttemptStatus.PAYMENT_COMPLETED,
    ))
    db.commit()

    result = _get(
        db,
        seeded["admin"],
        start_date=completion_time.date(),
        end_date=completion_time.date(),
    )

    assert result.kpis.settled_transactions == 1
    assert result.kpis.settled_sales_value == Decimal("50.00")
    assert result.kpis.average_settled_selling_price == Decimal("50.00")
    assert len(result.daily_trends) == 1
    assert result.daily_trends[0].period == completion_time.date().isoformat()
    assert result.daily_trends[0].settlements == 1
    assert result.daily_trends[0].settled_sales_value == Decimal("50.00")


@pytest.mark.parametrize(
    ("payment_status", "attempt_status", "payment_id", "amount_minor"),
    [
        (PaymentStatus.SETTLEMENT_PENDING_DEMO, PaymentAttemptStatus.ORDER_CREATED, None, 5000),
        (PaymentStatus.SETTLEMENT_FAILED_DEMO, PaymentAttemptStatus.PAYMENT_FAILED, None, 5000),
        (PaymentStatus.CANCELLED, PaymentAttemptStatus.ORDER_CREATED, None, 5000),
        (PaymentStatus.SETTLEMENT_COMPLETED_DEMO, PaymentAttemptStatus.ORDER_CREATED, None, 5000),
        (PaymentStatus.SETTLEMENT_COMPLETED_DEMO, PaymentAttemptStatus.PAYMENT_COMPLETED, None, 5000),
        (PaymentStatus.SETTLEMENT_COMPLETED_DEMO, PaymentAttemptStatus.PAYMENT_COMPLETED, "pay_mismatch", 4999),
    ],
)
def test_revenue_requires_a_matching_verified_payment_attempt(
    db, payment_status, attempt_status, payment_id, amount_minor
):
    seeded = _seed(db)
    transaction = db.query(Transaction).filter(Transaction.auction_id == 3).one()
    transaction.payment_status = payment_status
    transaction.settled_at = seeded["now"]
    db.add(PaymentAttempt(
        transaction_id=transaction.id,
        provider_order_id="order_unverified_" + payment_status.value.lower(),
        provider_payment_id=payment_id,
        amount_minor=amount_minor,
        currency="USD",
        status=attempt_status,
    ))
    db.commit()

    result = _get(
        db,
        seeded["admin"],
        start_date=seeded["now"].date(),
        end_date=seeded["now"].date(),
    )

    assert result.kpis.settled_transactions == 1
    assert result.kpis.settled_sales_value == Decimal("120.00")
    assert sum(row.settlements for row in result.daily_trends) == 1
    assert sum((row.settled_sales_value for row in result.monthly_trends), Decimal("0")) == Decimal("120.00")


def test_verified_webhook_is_attributed_to_settlement_date_once_and_scoped_by_owner(db):
    seeded = _seed(db)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    transaction = db.query(Transaction).filter(Transaction.auction_id == 3).one()
    transaction.created_at = now - timedelta(days=3)
    first_transaction = db.query(Transaction).filter(Transaction.auction_id == 1).one()
    first_transaction.settled_at = now - timedelta(days=2)
    order_id = "order_analytics_webhook"
    payment_id = "pay_analytics_webhook"
    db.add(PaymentAttempt(
        transaction_id=transaction.id,
        provider_order_id=order_id,
        amount_minor=5000,
        currency="USD",
        status=PaymentAttemptStatus.ORDER_CREATED,
    ))
    db.commit()

    payload = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": {
            "id": payment_id,
            "order_id": order_id,
            "status": "captured",
            "amount": 5000,
            "currency": "USD",
        }}},
    }
    raw_body = json.dumps(payload, separators=(",", ":")).encode()
    webhook_secret = "isolated-test-webhook-secret"
    signature = hmac.new(
        webhook_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    service = PaymentService(
        config=SimpleNamespace(
            RAZORPAY_MODE="test",
            RAZORPAY_KEY_ID="rzp_test_analytics",
            RAZORPAY_KEY_SECRET="isolated-test-key-secret",
            RAZORPAY_WEBHOOK_SECRET=webhook_secret,
            RAZORPAY_CURRENCY="USD",
        )
    )

    first = service.process_webhook(
        db, raw_body=raw_body, signature=signature, event_id="evt_analytics_1"
    )
    settled_at = transaction.settled_at
    duplicate = service.process_webhook(
        db, raw_body=raw_body, signature=signature, event_id="evt_analytics_1"
    )
    assert first["payment_status"] == PaymentStatus.SETTLEMENT_COMPLETED_DEMO.value
    assert duplicate["status"] == "duplicate"
    assert transaction.settled_at == settled_at
    assert settled_at is not None
    assert transaction.created_at.date() != settled_at.date()

    settlement_date = settled_at.date()
    filters = {"start_date": settlement_date, "end_date": settlement_date}
    admin = _get(db, seeded["admin"], **filters)
    seller_one = _get(db, seeded["seller_one"], **filters)
    seller_two = _get(db, seeded["seller_two"], **filters)
    buyer_one = _get(db, seeded["buyer_one"], **filters)
    buyer_two = _get(db, seeded["buyer_two"], **filters)

    assert admin.kpis.settled_transactions == 1
    assert admin.kpis.settled_sales_value == Decimal("50.00")
    assert len(admin.daily_trends) == 1
    assert admin.daily_trends[0].period == settlement_date.isoformat()
    assert admin.daily_trends[0].settled_sales_value == Decimal("50.00")
    assert [row.settled_sales_value for row in admin.monthly_trends] == [Decimal("50.00")]
    assert seller_one.kpis.settled_transactions == 0
    assert seller_two.kpis.settled_sales_value == Decimal("50.00")
    assert buyer_one.kpis.spending == Decimal("0.00")
    assert buyer_two.kpis.spending == Decimal("50.00")


def test_buyer_analytics_are_private_and_use_winner_and_settlement_records(db):
    seeded = _seed(db)

    result = _get(db, seeded["buyer_one"])

    assert result.scope == "buyer"
    assert result.kpis.valid_bids == 1
    assert result.kpis.auctions_participated == 1
    assert result.kpis.auctions_won == 1
    assert result.kpis.purchases == 1
    assert result.kpis.spending == Decimal("120.00")
    assert result.kpis.watchlist_items == 1
    assert all(item.product_title != "Seller Two Product" for item in result.auction_rankings)
    assert sum(category.bids for category in result.category_performance) == 1


def test_buyer_period_includes_recent_activity_on_older_auction(db):
    seeded = _seed(db)
    older_creation_time = seeded["now"] - timedelta(days=60)
    db.query(Product).filter(Product.id == 1).update(
        {Product.created_at: older_creation_time}
    )
    db.query(Auction).filter(Auction.id == 1).update(
        {Auction.created_at: older_creation_time}
    )
    db.commit()

    today = seeded["now"].date()
    result = _get(
        db,
        seeded["buyer_one"],
        start_date=today - timedelta(days=1),
        end_date=today + timedelta(days=1),
    )

    assert result.kpis.total_products == 1
    assert result.kpis.total_auctions == 1
    assert [item.product_title for item in result.product_rankings] == [
        "Seller One Completed Product"
    ]
    assert [item.product_title for item in result.auction_rankings] == [
        "Seller One Completed Product"
    ]


def test_category_and_date_filters_scope_marketplace_metrics(db):
    seeded = _seed(db)
    today = datetime.now(timezone.utc).date()

    result = _get(
        db,
        seeded["admin"],
        start_date=today - timedelta(days=1),
        end_date=today + timedelta(days=1),
        category_id=seeded["category_one"].id,
    )

    assert result.filters.category_id == seeded["category_one"].id
    assert result.kpis.total_products == 2
    assert result.kpis.total_auctions == 2
    assert result.kpis.recorded_bids == 3
    assert result.kpis.settled_transactions == 1
    assert all(category.category_id == seeded["category_one"].id for category in result.category_performance)


def test_date_range_excludes_records_outside_selected_period(db):
    seeded = _seed(db)
    old_day = seeded["now"].date() - timedelta(days=10)

    result = _get(
        db,
        seeded["admin"],
        start_date=old_day,
        end_date=old_day,
    )

    assert result.kpis.total_products == 0
    assert result.kpis.total_auctions == 0
    assert result.kpis.recorded_bids == 0
    assert result.kpis.settled_transactions == 0


def test_empty_datasets_return_zero_metrics_and_empty_trends(db):
    admin = _user(db, 1, "admin", "ADMIN")
    db.commit()

    result = _get(db, admin)

    assert result.kpis.total_products == 0
    assert result.kpis.total_auctions == 0
    assert result.kpis.recorded_bids == 0
    assert result.kpis.settled_sales_value == Decimal("0.00")
    assert result.daily_trends == []
    assert result.monthly_trends == []
    assert result.product_rankings == []


def test_invalid_date_range_and_unsupported_role_are_rejected(db):
    admin = _user(db, 1, "admin", "ADMIN")
    unsupported = _user(db, 2, "visitor", "VISITOR")
    db.commit()

    with pytest.raises(HTTPException) as date_error:
        _get(db, admin, start_date=date(2026, 10, 2), end_date=date(2026, 10, 1))
    assert date_error.value.status_code == 422

    with pytest.raises(HTTPException) as role_error:
        _get(db, unsupported)
    assert role_error.value.status_code == 403

"""Isolated API tests for payment routes, ownership, validation, and RBAC."""

from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register all ORM tables
from app.api.deps import get_current_active_user, get_db
from app.api.v1.api import api_router
from app.models.auction import Auction, AuctionStatus
from app.models.category import Category
from app.models.product import Product, ProductCondition
from app.models.role import Role
from app.models.transaction import (
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentStatus,
    Transaction,
)
from app.models.user import User, UserStatus


@pytest.fixture()
def payment_api():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    session_factory = sessionmaker(bind=engine, future=True)
    actor = {"id": 1}

    def override_get_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    def get_test_user(db: Session = Depends(get_db)):
        return db.query(User).filter(User.id == actor["id"]).one()

    app.dependency_overrides[get_current_active_user] = get_test_user
    from app.db.base_class import Base

    Base.metadata.create_all(bind=engine)
    with session_factory() as db:
        roles = {
            name: Role(name=name, description=name.title())
            for name in ("BUYER", "SELLER", "ADMIN")
        }
        db.add_all(roles.values())
        db.flush()
        users = {
            1: User(
                id=1, username="buyer_one", email="buyer1@test",
                password_hash="test", full_name="Buyer One",
                role_id=roles["BUYER"].id, status=UserStatus.ACTIVE,
            ),
            2: User(
                id=2, username="buyer_two", email="buyer2@test",
                password_hash="test", full_name="Buyer Two",
                role_id=roles["BUYER"].id, status=UserStatus.ACTIVE,
            ),
            3: User(
                id=3, username="administrator", email="admin@test",
                password_hash="test", full_name="Admin",
                role_id=roles["ADMIN"].id, status=UserStatus.ACTIVE,
            ),
            4: User(
                id=4, username="seller", email="seller@test",
                password_hash="test", full_name="Seller",
                role_id=roles["SELLER"].id, status=UserStatus.ACTIVE,
            ),
        }
        db.add_all(users.values())
        category = Category(name="Electronics", slug="electronics", icon_name="Cpu")
        db.add(category)
        db.flush()
        products = [
            Product(
                id=index,
                seller_id=users[4].id,
                category_id=category.id,
                title=f"Product {index}",
                description="Test product",
                condition_status=ProductCondition.NEW,
                image_url=f"https://example.test/{index}.png",
            )
            for index in (1, 2, 3)
        ]
        db.add_all(products)
        db.flush()
        now = datetime.utcnow()
        auctions = [
            Auction(
                id=index,
                product_id=index,
                starting_price=Decimal("10.00"),
                current_highest_bid=Decimal("100.00"),
                minimum_increment=Decimal("1.00"),
                start_time=now - timedelta(days=2),
                end_time=now - timedelta(days=1),
                status=AuctionStatus.COMPLETED,
                winner_id=winner_id,
                total_bids=1,
            )
            for index, winner_id in ((1, 1), (2, 2), (3, 1))
        ]
        db.add_all(auctions)
        db.flush()
        transactions = [
            Transaction(
                auction_id=index,
                buyer_id=buyer_id,
                seller_id=users[4].id,
                amount=Decimal(amount),
                payment_reference=f"TX-API-{index}",
                payment_status=payment_status,
                settled_at=now if payment_status == PaymentStatus.SETTLEMENT_COMPLETED_DEMO else None,
            )
            for index, buyer_id, amount, payment_status in (
                (1, 1, "100.00", PaymentStatus.SETTLEMENT_PENDING_DEMO),
                (2, 2, "200.00", PaymentStatus.SETTLEMENT_COMPLETED_DEMO),
            )
        ]
        db.add_all(transactions)
        db.flush()
        completed_transaction = (
            db.query(Transaction).filter_by(auction_id=2).one()
        )
        db.add(
            PaymentAttempt(
                transaction_id=completed_transaction.id,
                provider_order_id="order_api_verified",
                provider_payment_id="pay_api_verified",
                amount_minor=20000,
                currency="USD",
                status=PaymentAttemptStatus.PAYMENT_COMPLETED,
            )
        )
        db.commit()

    try:
        with TestClient(app) as client:
            yield SimpleNamespace(
                app=app,
                client=client,
                actor=actor,
                session_factory=session_factory,
                engine=engine,
            )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

def test_payment_routes_are_registered_under_api_v1(payment_api):
    paths = set(payment_api.app.openapi()["paths"])
    assert "/api/v1/payments/me/won-auctions" in paths
    assert "/api/v1/payments/auctions/{auction_id}/orders" in paths
    assert "/api/v1/payments/verify" in paths
    assert "/api/v1/payments/webhook" in paths
    assert "/api/v1/payments/me/transactions" in paths
    assert "/api/v1/payments/admin/transactions" in paths


def test_buyer_payment_routes_require_authentication():
    from app.api.v1.endpoints.payments import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/payments")
    with TestClient(app) as client:
        response = client.get("/api/v1/payments/me/transactions")
    assert response.status_code == 401


def test_won_auctions_and_payment_history_are_scoped_to_authenticated_buyer(
    payment_api,
):
    won = payment_api.client.get("/api/v1/payments/me/won-auctions")
    history = payment_api.client.get("/api/v1/payments/me/transactions")

    assert won.status_code == 200
    won_data = won.json()
    assert won_data["total"] == 2
    unpaid = next(item for item in won_data["items"] if item["auction_id"] == 1)
    no_transaction = next(item for item in won_data["items"] if item["auction_id"] == 3)
    assert unpaid["payment_status"] == "SETTLEMENT_PENDING_DEMO"
    assert unpaid["payment_required"] is True
    assert unpaid["payment_verified"] is False
    assert unpaid["amount"] == "100.00"
    assert no_transaction["payment_status"] is None
    assert no_transaction["payment_required"] is False
    assert no_transaction["payment_verified"] is False

    assert history.status_code == 200
    history_data = history.json()
    assert history_data["total"] == 1
    assert [item["auction_id"] for item in history_data["items"]] == [1]
    assert history_data["items"][0]["payment_verified"] is False

    with payment_api.session_factory() as db:
        transaction = db.query(Transaction).filter_by(auction_id=1).one()
        transaction.payment_status = PaymentStatus.SETTLEMENT_COMPLETED_DEMO
        transaction.settled_at = datetime.utcnow()
        db.commit()
    legacy_completed_history = payment_api.client.get(
        "/api/v1/payments/me/transactions"
    ).json()
    assert legacy_completed_history["items"][0]["payment_status"] == (
        PaymentStatus.SETTLEMENT_COMPLETED_DEMO.value
    )
    assert legacy_completed_history["items"][0]["payment_verified"] is False

    payment_api.actor["id"] = 2
    other_buyer_history = payment_api.client.get(
        "/api/v1/payments/me/transactions"
    ).json()
    other_buyer_wins = payment_api.client.get(
        "/api/v1/payments/me/won-auctions"
    ).json()
    assert other_buyer_history["total"] == 1
    assert other_buyer_history["items"][0]["auction_id"] == 2
    assert other_buyer_history["items"][0]["payment_verified"] is True
    assert other_buyer_wins["items"][0]["payment_verified"] is True

@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/payments/me/won-auctions",
        "/api/v1/payments/me/transactions",
        "/api/v1/payments/auctions/1/orders",
        "/api/v1/payments/verify",
    ],
)
def test_only_buyer_role_can_use_buyer_payment_routes(payment_api, path):
    payment_api.actor["id"] = 4
    response = (
        payment_api.client.post(path, json={})
        if path.endswith("/verify")
        else payment_api.client.post(path)
        if path.endswith("/orders")
        else payment_api.client.get(path)
    )
    assert response.status_code == 403


def test_completed_transaction_without_settlement_timestamp_is_not_reported_paid(
    payment_api,
):
    with payment_api.session_factory() as db:
        transaction = db.query(Transaction).filter_by(auction_id=2).one()
        transaction.settled_at = None
        db.commit()

    payment_api.actor["id"] = 2
    response = payment_api.client.get("/api/v1/payments/me/transactions")
    assert response.status_code == 200
    transaction_data = response.json()["items"][0]
    assert transaction_data["payment_status"] == (
        PaymentStatus.SETTLEMENT_COMPLETED_DEMO.value
    )
    assert transaction_data["payment_verified"] is False


def test_order_route_passes_authenticated_buyer_and_auction_to_service(
    payment_api, monkeypatch
):
    from app.api.v1.endpoints import payments

    called = {}

    def create_order(db, *, buyer_id, auction_id):
        called.update(buyer_id=buyer_id, auction_id=auction_id)
        return {
            "key_id": "rzp_test_unit",
            "order_id": "order_test_1",
            "amount": 10000,
            "currency": "USD",
        }

    monkeypatch.setattr(payments.payment_service, "create_order", create_order)
    response = payment_api.client.post("/api/v1/payments/auctions/1/orders")

    assert response.status_code == 200, response.text
    assert response.json()["amount"] == 10000
    assert called == {"buyer_id": 1, "auction_id": 1}


def test_verify_route_validates_provider_identifiers_and_delegates(
    payment_api, monkeypatch
):
    from app.api.v1.endpoints import payments

    called = {}

    def verify(db, **kwargs):
        called.update(kwargs)
        return {
            "transaction_id": 1,
            "payment_status": PaymentStatus.SETTLEMENT_COMPLETED_DEMO.value,
            "settled_at": datetime.utcnow(),
            "already_processed": False,
        }

    monkeypatch.setattr(payments.payment_service, "verify_payment", verify)
    invalid = payment_api.client.post(
        "/api/v1/payments/verify",
        json={"order_id": "invalid", "payment_id": "pay_test_1", "signature": "ok"},
    )
    assert invalid.status_code == 422
    assert called == {}

    response = payment_api.client.post(
        "/api/v1/payments/verify",
        json={
            "order_id": "order_test_1",
            "payment_id": "pay_test_1",
            "signature": "a" * 64,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["payment_status"] == "SETTLEMENT_COMPLETED_DEMO"
    assert called["buyer_id"] == 1
    assert called["order_id"] == "order_test_1"
    assert called["payment_id"] == "pay_test_1"


def test_webhook_forwards_exact_body_and_signature_without_authentication(
    payment_api, monkeypatch
):
    from app.api.v1.endpoints import payments

    called = {}

    def process_webhook(db, **kwargs):
        called.update(kwargs)
        return {"status": "processed", "event_id": "evt_test_1"}

    monkeypatch.setattr(payments.payment_service, "process_webhook", process_webhook)
    raw_body = b'{"event":"payment.captured","payload":{}}'
    response = payment_api.client.post(
        "/api/v1/payments/webhook",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": "signature-value",
            "X-Razorpay-Event-Id": "evt_test_1",
        },
    )

    assert response.status_code == 200
    assert called == {
        "raw_body": raw_body,
        "signature": "signature-value",
        "event_id": "evt_test_1",
    }


def test_webhook_requires_signature_header(payment_api):
    response = payment_api.client.post("/api/v1/payments/webhook", content=b"{}")
    assert response.status_code == 422


def test_admin_transaction_filters_pagination_and_role_restriction(payment_api):
    buyer_response = payment_api.client.get(
        "/api/v1/payments/admin/transactions"
    )
    assert buyer_response.status_code == 403
    payment_api.actor["id"] = 4
    seller_response = payment_api.client.get(
        "/api/v1/payments/admin/transactions"
    )
    assert seller_response.status_code == 403

    payment_api.actor["id"] = 3
    response = payment_api.client.get(
        "/api/v1/payments/admin/transactions",
        params={
            "payment_status": "SETTLEMENT_COMPLETED_DEMO",
            "buyer_id": 2,
            "page": 1,
            "page_size": 1,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["pages"] == 1
    assert data["items"][0]["auction_id"] == 2
    assert data["items"][0]["buyer_id"] == 2
    assert data["items"][0]["payment_verified"] is True
    assert "email" not in data["items"][0]
    assert "payment_reference" not in data["items"][0]


def test_admin_date_range_and_pagination_validation(payment_api):
    payment_api.actor["id"] = 3
    invalid_dates = payment_api.client.get(
        "/api/v1/payments/admin/transactions",
        params={"created_from": "2026-10-02", "created_to": "2026-10-01"},
    )
    invalid_page_size = payment_api.client.get(
        "/api/v1/payments/admin/transactions",
        params={"page_size": 101},
    )
    assert invalid_dates.status_code == 422
    assert invalid_page_size.status_code == 422

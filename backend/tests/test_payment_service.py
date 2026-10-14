"""Payment service tests using mocked Razorpay responses and isolated SQLite."""

import hashlib
import hmac
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base_class import Base
import app.models  # noqa: F401 - register all ORM tables
from app.models.auction import Auction, AuctionStatus
from app.models.category import Category
from app.models.product import Product, ProductCondition
from app.models.role import Role
from app.models.transaction import (
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentStatus,
    PaymentWebhookEvent,
    Transaction,
)
from app.models.user import User, UserStatus
from app.services.payment_service import PaymentService


class FakeRazorpay:
    def __init__(self):
        self.orders = []
        self.payments = {}
        self.create_order_calls = 0
        self.get_payment_calls = 0
        self.order_response_override = None

    def create_order(self, *, amount, currency, receipt, notes):
        self.create_order_calls += 1
        self.orders.append({
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
            "notes": notes,
        })
        return self.order_response_override or {
            "id": "order_test_1",
            "amount": amount,
            "currency": currency,
        }

    def get_payment(self, payment_id):
        self.get_payment_calls += 1
        return self.payments[payment_id]


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    try:
        with Session(engine) as session:
            yield session
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def payment_context(db):
    buyer_role = Role(name="BUYER", description="Buyer")
    seller_role = Role(name="SELLER", description="Seller")
    db.add_all([buyer_role, seller_role])
    db.flush()
    buyer = User(
        id=1, username="winner", email="winner@example.test",
        password_hash="test-hash", full_name="Winner",
        role_id=buyer_role.id, status=UserStatus.ACTIVE,
    )
    other_buyer = User(
        id=2, username="other", email="other@example.test",
        password_hash="test-hash", full_name="Other",
        role_id=buyer_role.id, status=UserStatus.ACTIVE,
    )
    seller = User(
        id=3, username="seller", email="seller@example.test",
        password_hash="test-hash", full_name="Seller",
        role_id=seller_role.id, status=UserStatus.ACTIVE,
    )
    db.add_all([buyer, other_buyer, seller])
    category = Category(name="Test", slug="test", icon_name="Tag")
    db.add(category)
    db.flush()
    product = Product(
        seller_id=seller.id,
        category_id=category.id,
        title="Test product",
        description="Test product",
        condition_status=ProductCondition.NEW,
        image_url="https://example.test/product",
    )
    db.add(product)
    db.flush()
    auction = Auction(
        product_id=product.id,
        starting_price=Decimal("10.00"),
        current_highest_bid=Decimal("123.45"),
        minimum_increment=Decimal("1.00"),
        start_time=datetime.utcnow() - timedelta(days=2),
        end_time=datetime.utcnow() - timedelta(days=1),
        status=AuctionStatus.COMPLETED,
        winner_id=buyer.id,
        total_bids=1,
    )
    db.add(auction)
    db.flush()
    transaction = Transaction(
        auction_id=auction.id,
        buyer_id=buyer.id,
        seller_id=seller.id,
        amount=Decimal("123.45"),
        payment_reference="TX-TEST-1",
        payment_status=PaymentStatus.SETTLEMENT_PENDING_DEMO,
    )
    db.add(transaction)
    db.commit()
    return {
        "auction": auction,
        "buyer": buyer,
        "other_buyer": other_buyer,
        "transaction": transaction,
    }


@pytest.fixture()
def provider():
    return FakeRazorpay()


@pytest.fixture()
def service(provider):
    config = SimpleNamespace(
        RAZORPAY_MODE="test",
        RAZORPAY_KEY_ID="rzp_test_unit",
        RAZORPAY_KEY_SECRET="not-a-real-secret-used-by-tests",
        RAZORPAY_WEBHOOK_SECRET="not-a-real-webhook-secret",
        RAZORPAY_CURRENCY="USD",
    )
    return PaymentService(config=config, provider=provider)


def _create_order(service, db, context, buyer_id=None):
    return service.create_order(
        db,
        buyer_id=buyer_id or context["buyer"].id,
        auction_id=context["auction"].id,
    )


def _signature(order_id, payment_id, secret="not-a-real-secret-used-by-tests"):
    return hmac.new(
        secret.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _webhook(service, db, payload, event_id="evt_test_1", secret="not-a-real-webhook-secret"):
    raw_body = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return service.process_webhook(
        db, raw_body=raw_body, signature=signature, event_id=event_id
    )


def _captured_payment(order_id, payment_id="pay_test_1"):
    return {
        "id": payment_id,
        "order_id": order_id,
        "status": "captured",
        "amount": 12345,
        "currency": "USD",
    }


def _captured_webhook(order_id, payment_id="pay_test_1"):
    return {
        "event": "payment.captured",
        "payload": {"payment": {"entity": _captured_payment(order_id, payment_id)}},
    }


def test_order_uses_only_authoritative_transaction_amount_and_is_reused(
    db, payment_context, service, provider
):
    result = _create_order(service, db, payment_context)

    assert result == {
        "key_id": "rzp_test_unit",
        "order_id": "order_test_1",
        "amount": 12345,
        "currency": "USD",
    }
    assert provider.orders[0]["amount"] == 12345
    assert provider.orders[0]["notes"]["transaction_id"] == str(
        payment_context["transaction"].id
    )
    assert db.query(PaymentAttempt).count() == 1

    repeated = _create_order(service, db, payment_context)

    assert repeated == result
    assert provider.create_order_calls == 1


def test_order_creation_rejects_non_winner(db, payment_context, service, provider):
    with pytest.raises(HTTPException) as error:
        _create_order(
            service, db, payment_context, buyer_id=payment_context["other_buyer"].id
        )

    assert error.value.status_code == 403
    assert provider.create_order_calls == 0


def test_order_creation_requires_completed_winning_auction(
    db, payment_context, service, provider
):
    payment_context["auction"].status = AuctionStatus.ACTIVE
    db.commit()

    with pytest.raises(HTTPException) as error:
        _create_order(service, db, payment_context)

    assert error.value.status_code == 409
    assert provider.create_order_calls == 0


def test_order_creation_requires_existing_pending_transaction(
    db, payment_context, service, provider
):
    db.delete(payment_context["transaction"])
    db.commit()

    with pytest.raises(HTTPException) as error:
        _create_order(service, db, payment_context)

    assert error.value.status_code == 404
    assert provider.create_order_calls == 0


def test_order_response_must_match_authoritative_amount(
    db, payment_context, service, provider
):
    provider.order_response_override = {
        "id": "order_test_bad",
        "amount": 1,
        "currency": "USD",
    }

    with pytest.raises(HTTPException) as error:
        _create_order(service, db, payment_context)

    assert error.value.status_code == 502
    assert db.query(PaymentAttempt).count() == 0
    assert payment_context["transaction"].payment_status == PaymentStatus.SETTLEMENT_PENDING_DEMO


def test_payment_service_fails_closed_without_test_credentials(
    db, payment_context, provider
):
    config = SimpleNamespace(
        RAZORPAY_MODE="test",
        RAZORPAY_KEY_ID="",
        RAZORPAY_KEY_SECRET="",
        RAZORPAY_WEBHOOK_SECRET="",
        RAZORPAY_CURRENCY="USD",
    )
    service = PaymentService(config=config, provider=provider)

    with pytest.raises(HTTPException) as error:
        _create_order(service, db, payment_context)

    assert error.value.status_code == 503
    assert provider.create_order_calls == 0


def test_payment_service_fails_closed_outside_test_mode(
    db, payment_context, provider
):
    config = SimpleNamespace(
        RAZORPAY_MODE="live",
        RAZORPAY_KEY_ID="rzp_live_unusable",
        RAZORPAY_KEY_SECRET="not-a-real-secret",
        RAZORPAY_WEBHOOK_SECRET="not-a-real-webhook-secret",
        RAZORPAY_CURRENCY="USD",
    )
    service = PaymentService(config=config, provider=provider)

    with pytest.raises(HTTPException) as error:
        _create_order(service, db, payment_context)

    assert error.value.status_code == 503
    assert provider.create_order_calls == 0


def test_order_provider_error_does_not_persist_attempt(
    db, payment_context, service, provider
):
    def fail_create_order(**_kwargs):
        raise httpx.ConnectError("mock provider unavailable")

    provider.create_order = fail_create_order

    with pytest.raises(HTTPException) as error:
        _create_order(service, db, payment_context)

    assert error.value.status_code == 502
    assert db.query(PaymentAttempt).count() == 0


def test_invalid_payment_signature_does_not_query_provider_or_complete(
    db, payment_context, service, provider
):
    order = _create_order(service, db, payment_context)

    with pytest.raises(HTTPException) as error:
        service.verify_payment(
            db,
            buyer_id=payment_context["buyer"].id,
            order_id=order["order_id"],
            payment_id="pay_test_1",
            signature="invalid",
        )

    assert error.value.status_code == 400
    assert provider.get_payment_calls == 0
    assert payment_context["transaction"].payment_status == PaymentStatus.SETTLEMENT_PENDING_DEMO
    assert payment_context["transaction"].settled_at is None


def test_signature_is_not_enough_without_captured_provider_payment(
    db, payment_context, service, provider
):
    order = _create_order(service, db, payment_context)
    provider.payments["pay_test_1"] = {
        **_captured_payment(order["order_id"]),
        "status": "authorized",
    }

    with pytest.raises(HTTPException) as error:
        service.verify_payment(
            db,
            buyer_id=payment_context["buyer"].id,
            order_id=order["order_id"],
            payment_id="pay_test_1",
            signature=_signature(order["order_id"], "pay_test_1"),
        )

    assert error.value.status_code == 409
    assert payment_context["transaction"].payment_status == PaymentStatus.SETTLEMENT_PENDING_DEMO
    assert payment_context["transaction"].settled_at is None


def test_provider_payment_amount_must_match_saved_order(
    db, payment_context, service, provider
):
    order = _create_order(service, db, payment_context)
    provider.payments["pay_test_1"] = {
        **_captured_payment(order["order_id"]),
        "amount": 1,
    }

    with pytest.raises(HTTPException) as error:
        service.verify_payment(
            db,
            buyer_id=payment_context["buyer"].id,
            order_id=order["order_id"],
            payment_id="pay_test_1",
            signature=_signature(order["order_id"], "pay_test_1"),
        )

    assert error.value.status_code == 409
    assert payment_context["transaction"].payment_status == PaymentStatus.SETTLEMENT_PENDING_DEMO
    assert payment_context["transaction"].settled_at is None


def test_payment_verification_completes_once_after_provider_capture(
    db, payment_context, service, provider
):
    order = _create_order(service, db, payment_context)
    provider.payments["pay_test_1"] = _captured_payment(order["order_id"])

    result = service.verify_payment(
        db,
        buyer_id=payment_context["buyer"].id,
        order_id=order["order_id"],
        payment_id="pay_test_1",
        signature=_signature(order["order_id"], "pay_test_1"),
    )
    settled_at = payment_context["transaction"].settled_at

    assert result["payment_status"] == PaymentStatus.SETTLEMENT_COMPLETED_DEMO.value
    assert settled_at is not None
    assert payment_context["transaction"].payment_attempt.status == PaymentAttemptStatus.PAYMENT_COMPLETED

    duplicate = service.verify_payment(
        db,
        buyer_id=payment_context["buyer"].id,
        order_id=order["order_id"],
        payment_id="pay_test_1",
        signature=_signature(order["order_id"], "pay_test_1"),
    )

    assert duplicate["already_processed"] is True
    assert payment_context["transaction"].settled_at == settled_at
    assert provider.get_payment_calls == 1


def test_verification_rejects_different_buyer_even_with_valid_signature(
    db, payment_context, service, provider
):
    order = _create_order(service, db, payment_context)

    with pytest.raises(HTTPException) as error:
        service.verify_payment(
            db,
            buyer_id=payment_context["other_buyer"].id,
            order_id=order["order_id"],
            payment_id="pay_test_1",
            signature=_signature(order["order_id"], "pay_test_1"),
        )

    assert error.value.status_code == 403
    assert provider.get_payment_calls == 0


def test_captured_webhook_completes_and_duplicate_event_is_idempotent(
    db, payment_context, service
):
    order = _create_order(service, db, payment_context)
    payload = _captured_webhook(order["order_id"])

    first = _webhook(service, db, payload)
    settled_at = payment_context["transaction"].settled_at
    duplicate = _webhook(service, db, payload)

    assert first["payment_status"] == PaymentStatus.SETTLEMENT_COMPLETED_DEMO.value
    assert settled_at is not None
    assert duplicate["status"] == "duplicate"
    assert payment_context["transaction"].settled_at == settled_at
    assert db.query(PaymentWebhookEvent).count() == 1


def test_webhook_rejects_invalid_signature_without_database_changes(
    db, payment_context, service
):
    order = _create_order(service, db, payment_context)
    raw_body = json.dumps(_captured_webhook(order["order_id"])).encode()

    with pytest.raises(HTTPException) as error:
        service.process_webhook(
            db, raw_body=raw_body, signature="invalid", event_id="evt_invalid"
        )

    assert error.value.status_code == 400
    assert db.query(PaymentWebhookEvent).count() == 0
    assert payment_context["transaction"].payment_status == PaymentStatus.SETTLEMENT_PENDING_DEMO


def test_failed_webhook_marks_failed_and_retry_reuses_existing_order(
    db, payment_context, service, provider
):
    order = _create_order(service, db, payment_context)
    payload = {
        "event": "payment.failed",
        "payload": {"payment": {"entity": {
            **_captured_payment(order["order_id"]),
            "status": "failed",
        }}},
    }
    result = _webhook(service, db, payload)

    assert result["payment_status"] == PaymentStatus.SETTLEMENT_FAILED_DEMO.value
    assert payment_context["transaction"].settled_at is None
    assert payment_context["transaction"].payment_attempt.status == PaymentAttemptStatus.PAYMENT_FAILED

    retry = _create_order(service, db, payment_context)

    assert retry["order_id"] == order["order_id"]
    assert payment_context["transaction"].payment_status == PaymentStatus.SETTLEMENT_PENDING_DEMO
    assert provider.create_order_calls == 1


def test_webhook_rejects_amount_mismatch(db, payment_context, service):
    order = _create_order(service, db, payment_context)
    payload = _captured_webhook(order["order_id"])
    payload["payload"]["payment"]["entity"]["amount"] = 1

    with pytest.raises(HTTPException) as error:
        _webhook(service, db, payload)

    assert error.value.status_code == 409
    assert payment_context["transaction"].payment_status == PaymentStatus.SETTLEMENT_PENDING_DEMO
    assert db.query(PaymentWebhookEvent).count() == 0


def test_webhook_requires_webhook_secret(db, payment_context, provider):
    config = SimpleNamespace(
        RAZORPAY_MODE="test",
        RAZORPAY_KEY_ID="rzp_test_unit",
        RAZORPAY_KEY_SECRET="not-a-real-secret-used-by-tests",
        RAZORPAY_WEBHOOK_SECRET="",
        RAZORPAY_CURRENCY="USD",
    )
    service = PaymentService(config=config, provider=provider)

    with pytest.raises(HTTPException) as error:
        _webhook(service, db, {})

    assert error.value.status_code == 503


def test_second_captured_payment_cannot_complete_same_transaction(
    db, payment_context, service, provider
):
    order = _create_order(service, db, payment_context)
    provider.payments["pay_test_1"] = _captured_payment(order["order_id"])
    service.verify_payment(
        db,
        buyer_id=payment_context["buyer"].id,
        order_id=order["order_id"],
        payment_id="pay_test_1",
        signature=_signature(order["order_id"], "pay_test_1"),
    )

    with pytest.raises(HTTPException) as error:
        _webhook(
            service, db, _captured_webhook(order["order_id"], "pay_test_2"),
            event_id="evt_test_2",
        )

    assert error.value.status_code == 409
    assert payment_context["transaction"].payment_attempt.provider_payment_id == "pay_test_1"
    assert db.query(PaymentWebhookEvent).filter(
        PaymentWebhookEvent.event_id == "evt_test_2"
    ).count() == 0


def test_payment_persistence_migration_matches_fresh_schema():
    root = Path(__file__).resolve().parents[2]
    schema = (root / "database" / "schema.sql").read_text(encoding="utf-8")
    migration = (
        root / "database" / "migrations" / "003_razorpay_payment_attempts.sql"
    ).read_text(encoding="utf-8")

    for table_name in ("payment_attempts", "payment_webhook_events"):
        assert f"CREATE TABLE {table_name}" in schema
        assert f"CREATE TABLE {table_name}" in migration
    for column in (
        "transaction_id INT NOT NULL UNIQUE",
        "provider_order_id VARCHAR(64) NOT NULL UNIQUE",
        "provider_payment_id VARCHAR(64) NULL UNIQUE",
        "amount_minor BIGINT NOT NULL",
        "event_id VARCHAR(64) PRIMARY KEY",
        "chk_payment_attempt_amount CHECK (amount_minor >= 1)",
    ):
        assert column in schema
        assert column in migration

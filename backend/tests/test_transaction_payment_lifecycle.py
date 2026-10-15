"""Focused tests for transaction payment lifecycle foundations."""

from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base_class import Base
import app.models  # noqa: F401 - register all ORM tables
from app.models.transaction import (
    PAYMENT_STATUS_TRANSITIONS,
    PaymentAttempt,
    PaymentStatus,
    Transaction,
    is_payment_status_transition_allowed,
)
from app.models.seller_payment_profile import SellerPaymentProfile


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


def test_transaction_defaults_to_pending_with_no_settlement_timestamp(db):
    assert Transaction.__table__.c.settled_at.nullable
    assert any(
        index.name == "idx_transactions_settled_at"
        for index in Transaction.__table__.indexes
    )

    transaction = Transaction(
        auction_id=1,
        buyer_id=1,
        seller_id=2,
        amount=Decimal("12.50"),
        payment_reference="TEST-PENDING",
    )
    db.add(transaction)
    db.commit()

    assert transaction.payment_status == PaymentStatus.SETTLEMENT_PENDING_DEMO
    assert transaction.settled_at is None


def test_one_transaction_per_auction_constraint_is_preserved(db):
    db.add_all([
        Transaction(
            auction_id=1, buyer_id=1, seller_id=2,
            amount=Decimal("12.50"), payment_reference="TEST-FIRST",
        ),
        Transaction(
            auction_id=1, buyer_id=1, seller_id=2,
            amount=Decimal("12.50"), payment_reference="TEST-SECOND",
        ),
    ])

    with pytest.raises(IntegrityError):
        db.commit()


def test_payment_status_transition_policy():
    assert is_payment_status_transition_allowed(
        PaymentStatus.SETTLEMENT_PENDING_DEMO,
        PaymentStatus.SETTLEMENT_COMPLETED_DEMO,
    )
    assert is_payment_status_transition_allowed(
        PaymentStatus.SETTLEMENT_PENDING_DEMO,
        PaymentStatus.SETTLEMENT_FAILED_DEMO,
    )
    assert is_payment_status_transition_allowed(
        PaymentStatus.SETTLEMENT_PENDING_DEMO,
        PaymentStatus.CANCELLED,
    )
    assert is_payment_status_transition_allowed(
        PaymentStatus.SETTLEMENT_FAILED_DEMO,
        PaymentStatus.SETTLEMENT_PENDING_DEMO,
    )
    assert not is_payment_status_transition_allowed(
        PaymentStatus.SETTLEMENT_COMPLETED_DEMO,
        PaymentStatus.SETTLEMENT_PENDING_DEMO,
    )
    assert not is_payment_status_transition_allowed(
        PaymentStatus.CANCELLED,
        PaymentStatus.SETTLEMENT_COMPLETED_DEMO,
    )
    assert not PAYMENT_STATUS_TRANSITIONS[PaymentStatus.SETTLEMENT_COMPLETED_DEMO]


def test_razorpay_configuration_accepts_test_mode_only():
    assert Settings(_env_file=None).RAZORPAY_MODE == "test"
    assert Settings(_env_file=None, RAZORPAY_MODE="TEST").RAZORPAY_MODE == "test"


@pytest.mark.parametrize("mode", ["live", "production", "", "test-live"])
def test_razorpay_configuration_fails_closed_for_non_test_mode(mode):
    with pytest.raises(ValidationError, match="Razorpay is restricted to TEST mode"):
        Settings(_env_file=None, RAZORPAY_MODE=mode)


def test_schema_and_migration_include_compatible_payment_lifecycle():
    root = Path(__file__).resolve().parents[2]
    schema = (root / "database" / "schema.sql").read_text(encoding="utf-8")
    migration = (
        root / "database" / "migrations" / "002_transaction_payment_lifecycle.sql"
    ).read_text(encoding="utf-8")

    for status in (
        "SETTLEMENT_PENDING_DEMO",
        "SETTLEMENT_COMPLETED_DEMO",
        "SETTLEMENT_FAILED_DEMO",
        "CANCELLED",
    ):
        assert status in schema
        assert status in migration
    assert "settled_at TIMESTAMP NULL DEFAULT NULL" in schema
    assert "ADD COLUMN settled_at TIMESTAMP NULL DEFAULT NULL" in migration
    assert "idx_transactions_settled_at" in schema
    assert "idx_transactions_settled_at" in migration


def test_payment_migration_indexes_match_orm_metadata():
    root = Path(__file__).resolve().parents[2]
    payment_migration = (
        root / "database" / "migrations" / "003_razorpay_payment_attempts.sql"
    ).read_text(encoding="utf-8")
    seller_migration = (
        root / "database" / "migrations" / "004_seller_payment_profiles.sql"
    ).read_text(encoding="utf-8")

    assert any(
        index.name == "idx_payment_attempts_status"
        for index in PaymentAttempt.__table__.indexes
    )
    assert "idx_payment_attempts_status" in payment_migration
    assert any(
        index.name == "idx_seller_payment_profiles_status"
        for index in SellerPaymentProfile.__table__.indexes
    )
    assert "idx_seller_payment_profiles_status" in seller_migration

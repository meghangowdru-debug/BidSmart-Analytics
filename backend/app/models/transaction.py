"""
BidSmart Analytics — Transaction (Simulated Demo Settlement) ORM Model
"""

import enum
from sqlalchemy import Column, Integer, Numeric, String, Enum as SQLEnum, DateTime, ForeignKey, func, CheckConstraint, Index, BigInteger
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class SettlementType(str, enum.Enum):
    SIMULATED_DEMO = "SIMULATED_DEMO"


class PaymentStatus(str, enum.Enum):
    SETTLEMENT_PENDING_DEMO = "SETTLEMENT_PENDING_DEMO"
    SETTLEMENT_COMPLETED_DEMO = "SETTLEMENT_COMPLETED_DEMO"
    SETTLEMENT_FAILED_DEMO = "SETTLEMENT_FAILED_DEMO"
    CANCELLED = "CANCELLED"


PAYMENT_STATUS_TRANSITIONS = {
    PaymentStatus.SETTLEMENT_PENDING_DEMO: frozenset({
        PaymentStatus.SETTLEMENT_COMPLETED_DEMO,
        PaymentStatus.SETTLEMENT_FAILED_DEMO,
        PaymentStatus.CANCELLED,
    }),
    PaymentStatus.SETTLEMENT_FAILED_DEMO: frozenset({
        PaymentStatus.SETTLEMENT_PENDING_DEMO,
        PaymentStatus.CANCELLED,
    }),
    PaymentStatus.SETTLEMENT_COMPLETED_DEMO: frozenset(),
    PaymentStatus.CANCELLED: frozenset(),
}


def is_payment_status_transition_allowed(
    current_status: PaymentStatus,
    next_status: PaymentStatus,
) -> bool:
    """Check lifecycle policy without changing or completing a transaction."""
    return next_status in PAYMENT_STATUS_TRANSITIONS[current_status]


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    auction_id = Column(Integer, ForeignKey("auctions.id", ondelete="RESTRICT", onupdate="CASCADE"), unique=True, nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    settlement_type = Column(SQLEnum(SettlementType, native_enum=True), default=SettlementType.SIMULATED_DEMO, nullable=False)
    payment_status = Column(SQLEnum(PaymentStatus, native_enum=True), default=PaymentStatus.SETTLEMENT_PENDING_DEMO, nullable=False, index=True)
    payment_reference = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    settled_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("amount >= 0.01", name="chk_transaction_amount"),
        Index("idx_transactions_settled_at", "settled_at"),
    )

    # Relationships
    auction = relationship("Auction", back_populates="transaction")
    buyer = relationship("User", back_populates="buyer_transactions", foreign_keys=[buyer_id])
    seller = relationship("User", back_populates="seller_transactions", foreign_keys=[seller_id])
    payment_attempt = relationship(
        "PaymentAttempt", back_populates="transaction", uselist=False
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, auction_id={self.auction_id}, amount={self.amount}, status='{self.payment_status}')>"


class PaymentAttemptStatus(str, enum.Enum):
    ORDER_CREATED = "ORDER_CREATED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"


class PaymentAttempt(Base):
    """One reusable Razorpay order for a transaction, with its verified payment ID."""

    __tablename__ = "payment_attempts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="RESTRICT", onupdate="CASCADE"),
        unique=True,
        nullable=False,
    )
    provider_order_id = Column(String(64), unique=True, nullable=False)
    provider_payment_id = Column(String(64), unique=True, nullable=True)
    amount_minor = Column(BigInteger, nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(
        SQLEnum(PaymentAttemptStatus, native_enum=True),
        default=PaymentAttemptStatus.ORDER_CREATED,
        server_default=PaymentAttemptStatus.ORDER_CREATED.value,
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("amount_minor >= 1", name="chk_payment_attempt_amount"),
    )

    transaction = relationship("Transaction", back_populates="payment_attempt")


class PaymentWebhookEvent(Base):
    """Minimal durable deduplication record; provider payloads are not retained."""

    __tablename__ = "payment_webhook_events"

    event_id = Column(String(64), primary_key=True)
    event_type = Column(String(64), nullable=False)
    received_at = Column(DateTime, server_default=func.now(), nullable=False)

"""
BidSmart Analytics — Transaction (Simulated Demo Settlement) ORM Model
"""

import enum
from sqlalchemy import Column, Integer, Numeric, String, Enum as SQLEnum, DateTime, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class SettlementType(str, enum.Enum):
    SIMULATED_DEMO = "SIMULATED_DEMO"


class PaymentStatus(str, enum.Enum):
    SETTLEMENT_PENDING_DEMO = "SETTLEMENT_PENDING_DEMO"
    SETTLEMENT_COMPLETED_DEMO = "SETTLEMENT_COMPLETED_DEMO"
    CANCELLED = "CANCELLED"


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

    __table_args__ = (
        CheckConstraint("amount >= 0.01", name="chk_transaction_amount"),
    )

    # Relationships
    auction = relationship("Auction", back_populates="transaction")
    buyer = relationship("User", back_populates="buyer_transactions", foreign_keys=[buyer_id])
    seller = relationship("User", back_populates="seller_transactions", foreign_keys=[seller_id])

    def __repr__(self):
        return f"<Transaction(id={self.id}, auction_id={self.auction_id}, amount={self.amount}, status='{self.payment_status}')>"

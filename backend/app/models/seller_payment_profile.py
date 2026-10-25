"""
BidSmart Analytics — Seller payment setup tracking.

Stores only the setup state. No bank, card, or provider credentials are kept here.
A seller without a row is treated as NOT_STARTED, so existing accounts need no backfill.
"""

import enum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, func

from app.db.base_class import Base


class SellerPaymentSetupMode(str, enum.Enum):
    DEMO_SIMULATED = "DEMO_SIMULATED"


class SellerPaymentSetupStatus(str, enum.Enum):
    PENDING = "PENDING"
    DEMO_COMPLETED = "DEMO_COMPLETED"


class SellerPaymentProfile(Base):
    __tablename__ = "seller_payment_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seller_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        unique=True,
        nullable=False,
    )
    setup_mode = Column(
        SQLEnum(SellerPaymentSetupMode, native_enum=True),
        default=SellerPaymentSetupMode.DEMO_SIMULATED,
        nullable=False,
    )
    status = Column(
        SQLEnum(SellerPaymentSetupStatus, native_enum=True),
        default=SellerPaymentSetupStatus.PENDING,
        nullable=False,
    )
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (Index("idx_seller_payment_profiles_status", "status"),)

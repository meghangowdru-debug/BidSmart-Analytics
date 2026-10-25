"""
BidSmart Analytics — User ORM Model
"""

import enum
from sqlalchemy import Column, Integer, String, Enum as SQLEnum, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True)
    status = Column(SQLEnum(UserStatus, native_enum=True), default=UserStatus.ACTIVE, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    role = relationship("Role", back_populates="users")
    products = relationship("Product", back_populates="seller", foreign_keys="Product.seller_id")
    bids = relationship("Bid", back_populates="bidder", foreign_keys="Bid.bidder_id")
    won_auctions = relationship("Auction", back_populates="winner", foreign_keys="Auction.winner_id")
    watchlist_items = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    buyer_transactions = relationship("Transaction", back_populates="buyer", foreign_keys="Transaction.buyer_id")
    seller_transactions = relationship("Transaction", back_populates="seller", foreign_keys="Transaction.seller_id")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role_id={self.role_id})>"

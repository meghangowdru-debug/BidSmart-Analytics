"""
BidSmart Analytics — Auction ORM Model
"""

import enum
from sqlalchemy import Column, Integer, Numeric, Enum as SQLEnum, DateTime, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class AuctionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    UNSOLD = "UNSOLD"
    RESERVE_NOT_MET = "RESERVE_NOT_MET"
    CANCELLED = "CANCELLED"


class Auction(Base):
    __tablename__ = "auctions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE", onupdate="CASCADE"), unique=True, nullable=False)
    starting_price = Column(Numeric(12, 2), nullable=False)
    current_highest_bid = Column(Numeric(12, 2), nullable=True, index=True)
    reserve_price = Column(Numeric(12, 2), nullable=True)
    minimum_increment = Column(Numeric(10, 2), default=1.00, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False, index=True)
    status = Column(SQLEnum(AuctionStatus, native_enum=True), default=AuctionStatus.DRAFT, nullable=False, index=True)
    winner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)
    winning_bid_id = Column(Integer, ForeignKey("bids.id", ondelete="SET NULL", onupdate="CASCADE", use_alter=True, name="fk_auctions_winning_bid"), nullable=True)
    total_bids = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="chk_auction_times"),
        CheckConstraint("starting_price >= 0.01", name="chk_starting_price"),
        CheckConstraint("minimum_increment >= 0.01", name="chk_minimum_increment"),
    )

    # Relationships
    product = relationship("Product", back_populates="auction", foreign_keys=[product_id])
    winner = relationship("User", back_populates="won_auctions", foreign_keys=[winner_id])
    bids = relationship("Bid", back_populates="auction", foreign_keys="Bid.auction_id", cascade="all, delete-orphan")
    winning_bid = relationship("Bid", foreign_keys=[winning_bid_id], post_update=True)
    watchlist_entries = relationship("Watchlist", back_populates="auction", cascade="all, delete-orphan")
    transaction = relationship("Transaction", back_populates="auction", uselist=False)

    def __repr__(self):
        return f"<Auction(id={self.id}, product_id={self.product_id}, status='{self.status}', highest_bid={self.current_highest_bid})>"

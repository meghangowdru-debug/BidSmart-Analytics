"""
BidSmart Analytics — Bid ORM Model
"""

from sqlalchemy import Column, Integer, Numeric, Boolean, String, DateTime, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import TIMESTAMP
from app.db.base_class import Base


class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    auction_id = Column(Integer, ForeignKey("auctions.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)
    bidder_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True)
    bid_amount = Column(Numeric(12, 2), nullable=False)
    # Using TIMESTAMP(fsp=3) for millisecond accuracy matching schema
    bid_time = Column(TIMESTAMP(fsp=3), server_default=func.now(3), nullable=False, index=True)
    is_winning_bid = Column(Boolean, default=False, nullable=False)
    is_flagged_anomaly = Column(Boolean, default=False, nullable=False, index=True)
    ip_address = Column(String(45), default="127.0.0.1", nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("bid_amount >= 0.01", name="chk_bid_amount"),
    )

    # Relationships
    auction = relationship("Auction", back_populates="bids", foreign_keys=[auction_id])
    bidder = relationship("User", back_populates="bids", foreign_keys=[bidder_id])

    def __repr__(self):
        return f"<Bid(id={self.id}, auction_id={self.auction_id}, bidder_id={self.bidder_id}, amount={self.bid_amount})>"

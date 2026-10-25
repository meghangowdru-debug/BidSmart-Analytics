"""
BidSmart Analytics — Watchlist ORM Model
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)
    auction_id = Column(Integer, ForeignKey("auctions.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "auction_id", name="uq_user_auction_watchlist"),
    )

    # Relationships
    user = relationship("User", back_populates="watchlist_items")
    auction = relationship("Auction", back_populates="watchlist_entries")

    def __repr__(self):
        return f"<Watchlist(id={self.id}, user_id={self.user_id}, auction_id={self.auction_id})>"

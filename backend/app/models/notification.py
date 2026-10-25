"""
BidSmart Analytics — Notification ORM Model
"""

import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, Enum as SQLEnum, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class NotificationType(str, enum.Enum):
    OUTBID = "OUTBID"
    AUCTION_WON = "AUCTION_WON"
    AUCTION_ENDED = "AUCTION_ENDED"
    PRICE_ALERT = "PRICE_ALERT"
    ANOMALY_ALERT = "ANOMALY_ALERT"
    SYSTEM = "SYSTEM"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)
    type = Column(SQLEnum(NotificationType, native_enum=True), default=NotificationType.SYSTEM, nullable=False)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    link_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type='{self.type}', is_read={self.is_read})>"

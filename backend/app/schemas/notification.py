"""
BidSmart Analytics — Notification Schemas
Defines request and response schemas for in-app user notifications.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class NotificationOut(BaseModel):
    id: int
    user_id: int
    type: str = Field(..., description="Notification type: 'OUTBID', 'AUCTION_WON', 'AUCTION_ENDED', 'PRICE_ALERT', etc.")
    title: str
    message: str
    is_read: bool
    link_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: List[NotificationOut]
    total: int
    unread_count: int
    page: int
    page_size: int
    pages: int


class NotificationUnreadCount(BaseModel):
    unread_count: int

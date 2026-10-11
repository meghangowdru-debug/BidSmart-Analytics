"""
BidSmart Analytics — Settlement & Auction Closing Schemas
"""

from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class AuctionCloseResult(BaseModel):
    auction_id: int
    status: str = Field(..., description="Final auction status: 'COMPLETED', 'UNSOLD', 'RESERVE_NOT_MET', or 'ALREADY_CLOSED'")
    already_closed: bool = Field(False, description="Whether auction was already closed prior to this call")
    winner_id: Optional[int] = None
    winner_username: Optional[str] = None
    final_price: Optional[Decimal] = None
    reserve_price: Optional[Decimal] = None
    reserve_met: Optional[bool] = None
    total_bids: int = 0
    transaction_id: Optional[int] = None
    transaction_reference: Optional[str] = None
    notifications_dispatched: int = 0
    message: str


class BatchCloseResponse(BaseModel):
    processed_count: int
    completed_count: int
    unsold_count: int
    reserve_failed_count: int
    already_closed_count: int
    results: List[AuctionCloseResult]

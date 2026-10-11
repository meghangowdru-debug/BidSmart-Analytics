"""
BidSmart Analytics — Bidding Schemas
Defines request and response schemas for atomic bid submission and bid history retrieval.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class BidCreate(BaseModel):
    bid_amount: Decimal = Field(
        ...,
        ge=Decimal("0.01"),
        description="Monetary amount of the bid in USD. Must be greater than current highest bid + minimum increment."
    )


class BidOut(BaseModel):
    id: int
    auction_id: int
    bidder_id: int
    bidder_username: str
    bid_amount: Decimal
    bid_time: datetime
    is_winning_bid: bool
    anti_snipe_extended: bool = False
    new_end_time: Optional[datetime] = None
    new_highest_bid: Decimal
    new_total_bids: int
    minimum_next_bid: Decimal

    model_config = ConfigDict(from_attributes=True)


class BidHistoryOut(BaseModel):
    id: int
    auction_id: int
    bid_amount: Decimal
    bid_time: datetime
    is_winning_bid: bool
    bidder_id: Optional[int] = None
    bidder_username: str
    is_own_bid: bool = False

    model_config = ConfigDict(from_attributes=True)


class BidHistoryListResponse(BaseModel):
    items: List[BidHistoryOut]
    total: int
    auction_id: int
    starting_price: Decimal
    current_highest_bid: Optional[Decimal] = None
    minimum_increment: Decimal
    next_minimum_bid: Decimal
    status: str
    end_time: datetime


class BuyerBidSummary(BaseModel):
    id: int
    auction_id: int
    product_title: str
    product_image_url: str
    bid_amount: Decimal
    bid_time: datetime
    is_winning_bid: bool
    current_highest_bid: Optional[Decimal] = None
    auction_status: str
    auction_end_time: datetime

    model_config = ConfigDict(from_attributes=True)

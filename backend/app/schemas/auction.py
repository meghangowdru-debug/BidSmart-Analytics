"""
BidSmart Analytics — Auction Schemas
Defines request and response models for auction listings and lifecycle management.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict
from app.schemas.product import ProductOut


class AuctionBase(BaseModel):
    starting_price: Decimal = Field(..., ge=Decimal("0.01"), description="Initial minimum opening bid")
    reserve_price: Optional[Decimal] = Field(None, ge=Decimal("0.01"), description="Optional hidden minimum reserve price")
    minimum_increment: Decimal = Field(Decimal("1.00"), ge=Decimal("0.01"), description="Mandatory minimum increment above highest bid")
    start_time: Optional[datetime] = Field(None, description="Scheduled auction opening timestamp (UTC)")
    end_time: datetime = Field(..., description="Auction closing deadline timestamp (UTC)")


class AuctionCreate(AuctionBase):
    product_id: int = Field(..., ge=1, description="Associated product ID owned by the seller")
    status: Optional[str] = Field("ACTIVE", description="Initial status: 'ACTIVE', 'SCHEDULED', or 'DRAFT'")

    @field_validator("status")
    @classmethod
    def validate_initial_status(cls, v: Optional[str]) -> str:
        val = (v or "ACTIVE").upper().strip()
        allowed = {"DRAFT", "SCHEDULED", "ACTIVE"}
        if val not in allowed:
            raise ValueError(f"Initial auction status must be one of: {sorted(list(allowed))}")
        return val

    @model_validator(mode="after")
    def validate_auction_rules(self) -> "AuctionCreate":
        now = datetime.now(timezone.utc)
        start = self.start_time
        if start is None:
            start = now
            self.start_time = start

        # Normalize timezones for comparison
        start_comp = start if start.tzinfo else start.replace(tzinfo=timezone.utc)
        end_comp = self.end_time if self.end_time.tzinfo else self.end_time.replace(tzinfo=timezone.utc)

        if end_comp <= start_comp:
            raise ValueError("Auction closing time ('end_time') must be strictly greater than start time ('start_time').")

        if self.reserve_price is not None and self.reserve_price < self.starting_price:
            raise ValueError("Reserve price cannot be less than starting price.")

        return self


class AuctionUpdate(BaseModel):
    starting_price: Optional[Decimal] = Field(None, ge=Decimal("0.01"))
    reserve_price: Optional[Decimal] = Field(None, ge=Decimal("0.01"))
    minimum_increment: Optional[Decimal] = Field(None, ge=Decimal("0.01"))
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_update_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            val = v.upper().strip()
            allowed = {"DRAFT", "SCHEDULED", "ACTIVE", "CANCELLED"}
            if val not in allowed:
                raise ValueError(f"Permitted update status values: {sorted(list(allowed))}")
            return val
        return v


class AuctionOut(BaseModel):
    id: int
    product_id: int
    starting_price: Decimal
    current_highest_bid: Optional[Decimal] = None
    effective_price: Decimal
    reserve_price: Optional[Decimal] = None
    reserve_met: Optional[bool] = None
    minimum_increment: Decimal
    start_time: datetime
    end_time: datetime
    status: str
    total_bids: int
    winner_id: Optional[int] = None
    winner_username: Optional[str] = None
    seconds_remaining: int
    is_expired: bool
    created_at: datetime
    updated_at: datetime
    product: Optional[ProductOut] = None

    model_config = ConfigDict(from_attributes=True)


class AuctionDetailOut(AuctionOut):
    """Detailed auction model with full product information and live metrics."""
    pass


class AuctionListResponse(BaseModel):
    items: List[AuctionOut]
    total: int
    page: int
    page_size: int
    pages: int

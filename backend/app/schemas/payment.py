"""Payment API request and response models."""

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.models.transaction import PaymentStatus


class PaymentOrderOut(BaseModel):
    key_id: str
    order_id: str
    amount: int = Field(..., ge=1)
    currency: Literal["USD"]


class PaymentVerificationIn(BaseModel):
    order_id: str = Field(..., min_length=7, max_length=64, pattern=r"^order_[A-Za-z0-9_]+$")
    payment_id: str = Field(..., min_length=5, max_length=64, pattern=r"^pay_[A-Za-z0-9_]+$")
    signature: str = Field(..., min_length=64, max_length=64, pattern=r"^[A-Fa-f0-9]{64}$")


class PaymentVerificationOut(BaseModel):
    transaction_id: int
    payment_status: PaymentStatus
    settled_at: Optional[datetime] = None
    already_processed: bool


class PaymentWebhookOut(BaseModel):
    status: Literal["processed", "duplicate"]
    event_id: str
    transaction_id: Optional[int] = None
    payment_status: Optional[PaymentStatus] = None


class WonAuctionPaymentOut(BaseModel):
    auction_id: int
    product_title: str
    product_image_url: str
    auction_status: str
    start_time: datetime
    end_time: datetime
    amount: Optional[Decimal] = None
    payment_status: Optional[PaymentStatus] = None
    payment_required: bool
    payment_verified: bool


class WonAuctionPaymentPage(BaseModel):
    items: List[WonAuctionPaymentOut]
    total: int
    page: int
    page_size: int
    pages: int


class PaymentTransactionOut(BaseModel):
    transaction_id: int
    auction_id: int
    product_title: str
    amount: Decimal
    currency: Literal["USD"] = "USD"
    payment_status: PaymentStatus
    created_at: datetime
    settled_at: Optional[datetime] = None
    payment_verified: bool


class AdminPaymentTransactionOut(PaymentTransactionOut):
    buyer_id: int
    seller_id: int


class PaymentTransactionPage(BaseModel):
    items: List[PaymentTransactionOut]
    total: int
    page: int
    page_size: int
    pages: int


class AdminPaymentTransactionPage(BaseModel):
    items: List[AdminPaymentTransactionOut]
    total: int
    page: int
    page_size: int
    pages: int

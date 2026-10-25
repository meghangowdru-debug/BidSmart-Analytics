"""Schemas for the seller payment setup status."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class SellerPaymentSetupOut(BaseModel):
    status: Literal[
        "NOT_STARTED", "PENDING", "DEMO_COMPLETED", "NOT_REQUIRED", "DISABLED"
    ]
    mode: Literal["DEMO_SIMULATED"] = "DEMO_SIMULATED"
    required: bool = Field(description="Whether this account must finish setup before listing.")
    can_list: bool = Field(description="Whether the backend currently allows product and auction creation.")
    simulated: bool = True
    payouts_enabled: bool = Field(
        False, description="Always false: demo setup never enables real payouts."
    )
    provider_onboarding_available: bool = Field(
        False, description="Verified payment-provider onboarding is not implemented."
    )
    completed_at: Optional[datetime] = None
    message: str


class SellerPaymentSetupDemoIn(BaseModel):
    acknowledge_simulated: bool = Field(
        description="Seller confirms this is a simulated demo setup with no real payouts."
    )

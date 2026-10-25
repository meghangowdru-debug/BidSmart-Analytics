"""
BidSmart Analytics — Product Schemas
Defines request and response schemas for product catalog management.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.schemas.category import CategoryOut


class SellerSummary(BaseModel):
    id: int
    username: str
    full_name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=150, description="Product listing title")
    description: str = Field(..., min_length=10, description="Detailed product description and specs")
    condition_status: str = Field("USED", description="Product condition: 'NEW', 'LIKE_NEW', 'USED', or 'VINTAGE'")
    image_url: str = Field(..., min_length=5, max_length=500, description="Primary high-resolution image URL")
    thumbnail_url: Optional[str] = Field(None, max_length=500, description="Optional thumbnail image URL")
    category_id: int = Field(..., ge=1, description="Target category taxonomy ID")

    @field_validator("condition_status")
    @classmethod
    def validate_condition(cls, v: str) -> str:
        val = v.upper().strip()
        allowed = {"NEW", "LIKE_NEW", "USED", "VINTAGE"}
        if val not in allowed:
            raise ValueError(f"Invalid condition '{v}'. Allowed values: {sorted(list(allowed))}")
        return val


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=150)
    description: Optional[str] = Field(None, min_length=10)
    condition_status: Optional[str] = None
    image_url: Optional[str] = Field(None, min_length=5, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    category_id: Optional[int] = Field(None, ge=1)

    @field_validator("condition_status")
    @classmethod
    def validate_condition(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            val = v.upper().strip()
            allowed = {"NEW", "LIKE_NEW", "USED", "VINTAGE"}
            if val not in allowed:
                raise ValueError(f"Invalid condition '{v}'. Allowed values: {sorted(list(allowed))}")
            return val
        return v


class ProductOut(BaseModel):
    id: int
    seller_id: int
    category_id: int
    title: str
    description: str
    condition_status: str
    image_url: str
    thumbnail_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    seller: Optional[SellerSummary] = None
    category: Optional[CategoryOut] = None
    has_auction: bool = False
    auction_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    items: List[ProductOut]
    total: int
    page: int
    page_size: int
    pages: int

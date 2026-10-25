"""
BidSmart Analytics — Category Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    icon_name: str = "Tag"
    item_count: Optional[int] = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

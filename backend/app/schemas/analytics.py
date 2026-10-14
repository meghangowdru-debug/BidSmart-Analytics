"""Authenticated analytics response models."""

from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class AnalyticsFilters(BaseModel):
    start_date: date
    end_date: date
    category_id: Optional[int] = None


class AnalyticsKpis(BaseModel):
    registered_users: int = 0
    buyers: int = 0
    sellers: int = 0
    total_products: int = 0
    total_auctions: int = 0
    active_auctions: int = 0
    upcoming_auctions: int = 0
    completed_auctions: int = 0
    cancelled_auctions: int = 0
    recorded_bids: int = 0
    valid_bids: int = 0
    auctions_participated: int = 0
    auctions_won: int = 0
    watchlist_items: int = 0
    settled_transactions: int = 0
    settled_sales_value: Decimal = Decimal("0.00")
    average_settled_selling_price: Decimal = Decimal("0.00")
    purchases: int = 0
    spending: Decimal = Decimal("0.00")


class AuctionStatusCount(BaseModel):
    status: str
    count: int


class CategoryPerformance(BaseModel):
    category_id: int
    category_name: str
    products: int = 0
    auctions: int = 0
    bids: int = 0
    settled_transactions: int = 0
    settled_sales_value: Decimal = Decimal("0.00")


class PerformanceRanking(BaseModel):
    product_id: int
    product_title: str
    category_name: str
    auction_id: Optional[int] = None
    auction_status: Optional[str] = None
    valid_bids: int = 0
    settled_transactions: int = 0
    settled_sales_value: Decimal = Decimal("0.00")


class ActivityTrend(BaseModel):
    period: str
    auctions: int = 0
    bids: int = 0
    settlements: int = 0
    settled_sales_value: Decimal = Decimal("0.00")


class AnalyticsResponse(BaseModel):
    scope: str
    currency: str = "USD"
    date_basis: str = "UTC"
    filters: AnalyticsFilters
    kpis: AnalyticsKpis
    auction_status_distribution: List[AuctionStatusCount]
    category_performance: List[CategoryPerformance]
    product_rankings: List[PerformanceRanking]
    auction_rankings: List[PerformanceRanking]
    daily_trends: List[ActivityTrend]
    monthly_trends: List[ActivityTrend]

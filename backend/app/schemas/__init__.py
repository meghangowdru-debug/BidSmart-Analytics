"""
BidSmart Analytics — Schemas Package
"""

from app.schemas.health import HealthResponse, DatabaseHealth
from app.schemas.common import MessageResponse, ErrorResponse, PaginatedResponse
from app.schemas.token import Token, TokenPayload, RefreshTokenRequest
from app.schemas.user import (
    UserRegister,
    UserLogin,
    UserOut,
    UserUpdate,
    UserRoleUpdate,
    UserStatusUpdate
)
from app.schemas.category import CategoryOut
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductOut,
    ProductListResponse,
    SellerSummary
)
from app.schemas.auction import (
    AuctionCreate,
    AuctionUpdate,
    AuctionOut,
    AuctionDetailOut,
    AuctionListResponse
)
from app.schemas.bid import (
    BidCreate,
    BidOut,
    BidHistoryOut,
    BidHistoryListResponse,
    BuyerBidSummary
)
from app.schemas.notification import (
    NotificationOut,
    NotificationListResponse,
    NotificationUnreadCount
)
from app.schemas.settlement import (
    AuctionCloseResult,
    BatchCloseResponse
)

__all__ = [
    "HealthResponse",
    "DatabaseHealth",
    "MessageResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "Token",
    "TokenPayload",
    "RefreshTokenRequest",
    "UserRegister",
    "UserLogin",
    "UserOut",
    "UserUpdate",
    "UserRoleUpdate",
    "UserStatusUpdate",
    "CategoryOut",
    "ProductCreate",
    "ProductUpdate",
    "ProductOut",
    "ProductListResponse",
    "SellerSummary",
    "AuctionCreate",
    "AuctionUpdate",
    "AuctionOut",
    "AuctionDetailOut",
    "AuctionListResponse",
    "BidCreate",
    "BidOut",
    "BidHistoryOut",
    "BidHistoryListResponse",
    "BuyerBidSummary",
    "NotificationOut",
    "NotificationListResponse",
    "NotificationUnreadCount",
    "AuctionCloseResult",
    "BatchCloseResponse"
]

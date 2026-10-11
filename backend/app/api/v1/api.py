"""
BidSmart Analytics — API v1 Router Aggregator
Combines health, auth, users, categories, products, auctions, and bidding under the /api/v1 prefix.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    users,
    categories,
    products,
    auctions,
    bids,
    notifications
)

api_router = APIRouter()

# Phase 3: Health Router
api_router.include_router(health.router, tags=["Health"])

# Phase 4: Authentication & User Governance Routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users & RBAC"])

# Phase 5: Categories, Products & Auctions Routers
api_router.include_router(categories.router, prefix="/categories", tags=["Categories"])
api_router.include_router(products.router, prefix="/products", tags=["Products"])
api_router.include_router(auctions.router, prefix="/auctions", tags=["Auctions"])

# Phase 6: Secure Bidding Engine Router
api_router.include_router(bids.router, tags=["Bidding Engine"])

# Phase 7: In-App Notifications Router
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])


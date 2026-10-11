"""
BidSmart Analytics — Auction Management & Browsing Router
Public active auction catalog browsing, search/filtering/sorting, and seller-only lifecycle management.
"""

from datetime import datetime, timezone
from decimal import Decimal
from math import ceil
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc, asc, func, and_

from app.api.deps import (
    get_db,
    get_optional_current_user,
    require_seller
)
from app.models.user import User
from app.models.product import Product
from app.models.category import Category
from app.models.auction import Auction, AuctionStatus
from app.models.audit_log import AuditLog
from app.schemas.auction import (
    AuctionCreate,
    AuctionUpdate,
    AuctionOut,
    AuctionDetailOut,
    AuctionListResponse
)
from app.schemas.settlement import AuctionCloseResult, BatchCloseResponse
from app.services.auction_closing import close_single_auction, close_all_expired_auctions
from app.api.v1.endpoints.products import _format_product_out

router = APIRouter()

# Strictly whitelisted sort columns to eliminate any possibility of SQL injection
ALLOWED_SORT_ORDERS = {
    "ending_soon": lambda: asc(Auction.end_time),
    "ending_latest": lambda: desc(Auction.end_time),
    "price_asc": lambda: asc(func.coalesce(Auction.current_highest_bid, Auction.starting_price)),
    "price_desc": lambda: desc(func.coalesce(Auction.current_highest_bid, Auction.starting_price)),
    "most_bids": lambda: desc(Auction.total_bids),
    "bids_desc": lambda: desc(Auction.total_bids),
    "newest": lambda: desc(Auction.created_at),
    "oldest": lambda: asc(Auction.created_at)
}


def _format_auction_out(a: Auction, viewer: Optional[User] = None) -> AuctionOut:
    """
    Constructs a sanitized AuctionOut schema.
    Security: Masks the reserve_price unless the viewer is the owning seller or an administrator.
    """
    now = datetime.now(timezone.utc)
    end_utc = a.end_time.astimezone(timezone.utc) if getattr(a.end_time, "tzinfo", None) else a.end_time.replace(tzinfo=timezone.utc)
    seconds_remaining = max(0, int((end_utc - now).total_seconds()))
    is_expired = now >= end_utc

    effective_price = a.current_highest_bid if a.current_highest_bid is not None else a.starting_price

    # Check if viewer has privilege to view the private reserve price
    is_privileged = False
    if viewer:
        if viewer.role and viewer.role.name == "ADMIN":
            is_privileged = True
        elif a.product and a.product.seller_id == viewer.id:
            is_privileged = True

    visible_reserve = a.reserve_price if is_privileged else None

    # Determine if reserve was met - ONLY revealed to privileged viewers
    reserve_met = None
    if is_privileged and a.reserve_price is not None and a.current_highest_bid is not None:
        reserve_met = a.current_highest_bid >= a.reserve_price

    winner_name = a.winner.username if a.winner else None
    product_out = _format_product_out(a.product) if a.product else None

    return AuctionOut(
        id=a.id,
        product_id=a.product_id,
        starting_price=a.starting_price,
        current_highest_bid=a.current_highest_bid,
        effective_price=effective_price,
        reserve_price=visible_reserve,
        reserve_met=reserve_met,
        minimum_increment=a.minimum_increment,
        start_time=a.start_time,
        end_time=a.end_time,
        status=a.status.value if hasattr(a.status, "value") else str(a.status),
        total_bids=a.total_bids,
        winner_id=a.winner_id,
        winner_username=winner_name,
        seconds_remaining=seconds_remaining,
        is_expired=is_expired,
        created_at=a.created_at,
        updated_at=a.updated_at,
        product=product_out
    )


# -----------------------------------------------------------------------------
# 1. PUBLIC AUCTION CATALOG BROWSING & SEARCH
# -----------------------------------------------------------------------------

@router.get(
    "",
    response_model=AuctionListResponse,
    summary="List active auctions with multi-facet filters and sorting"
)
def list_auctions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query("ACTIVE", description="Auction status ('ACTIVE', 'SCHEDULED', 'COMPLETED', or 'ALL')"),
    search: Optional[str] = Query(None, description="Search keyword matching product title or description"),
    category_id: Optional[int] = Query(None, description="Filter by category taxonomy ID"),
    category_slug: Optional[str] = Query(None, description="Filter by category slug"),
    seller_id: Optional[int] = Query(None, description="Filter auctions by seller user ID"),
    condition: Optional[str] = Query(None, description="Product condition ('NEW', 'LIKE_NEW', 'USED', 'VINTAGE')"),
    min_price: Optional[Decimal] = Query(None, ge=Decimal("0.00"), description="Minimum effective bid/price"),
    max_price: Optional[Decimal] = Query(None, ge=Decimal("0.00"), description="Maximum effective bid/price"),
    sort_by: str = Query("ending_soon", description="Sort order ('ending_soon', 'ending_latest', 'price_asc', 'price_desc', 'most_bids', 'newest', 'oldest')"),
    db: Session = Depends(get_db),
    optional_user: Optional[User] = Depends(get_optional_current_user)
) -> Any:
    """
    Publicly browsable catalog of active auctions with:
    - Multi-keyword search
    - Category & seller filtering
    - Real-time effective price filtering (COALESCE(current_highest_bid, starting_price))
    - Secure whitelisted sorting
    - Pagination metadata
    """
    # Normalize query params if called internally
    sort_str = sort_by if isinstance(sort_by, str) else "ending_soon"
    sort_key = sort_str.lower().strip()
    if sort_key not in ALLOWED_SORT_ORDERS:
        allowed_list = list(ALLOWED_SORT_ORDERS.keys())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort parameter '{sort_by}'. Allowed options: {allowed_list}"
        )

    query = db.query(Auction).join(Product, Auction.product_id == Product.id)\
        .options(
            joinedload(Auction.product).joinedload(Product.seller),
            joinedload(Auction.product).joinedload(Product.category),
            joinedload(Auction.winner)
        )

    # 2. Status filter
    status_val = status_filter if isinstance(status_filter, str) else "ACTIVE"
    if status_val and status_val.upper() != "ALL":
        target_status = status_val.upper()
        if target_status == "ACTIVE":
            query = query.filter(Auction.status == AuctionStatus.ACTIVE)
        else:
            try:
                query = query.filter(Auction.status == AuctionStatus(target_status))
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status '{status_filter}'.")

    # 3. Search filter
    if search and isinstance(search, str) and search.strip():
        search_fmt = f"%{search.strip()}%"
        query = query.filter(or_(Product.title.ilike(search_fmt), Product.description.ilike(search_fmt)))

    # 4. Category filters
    if category_id and isinstance(category_id, int):
        query = query.filter(Product.category_id == category_id)
    if category_slug and isinstance(category_slug, str) and category_slug.strip():
        query = query.join(Category, Product.category_id == Category.id).filter(Category.slug == category_slug.strip().lower())

    # 5. Seller filter
    if seller_id and isinstance(seller_id, int):
        query = query.filter(Product.seller_id == seller_id)

    # 6. Condition filter
    if condition and isinstance(condition, str) and condition.strip():
        cond_upper = condition.upper().strip()
        query = query.filter(Product.condition_status == cond_upper)

    # 7. Price filters (evaluated on effective price)
    effective_price_expr = func.coalesce(Auction.current_highest_bid, Auction.starting_price)
    if min_price is not None and isinstance(min_price, (int, float, Decimal)):
        query = query.filter(effective_price_expr >= min_price)
    if max_price is not None and isinstance(max_price, (int, float, Decimal)):
        query = query.filter(effective_price_expr <= max_price)

    # 8. Count total matches before pagination
    total = query.count()
    pages = max(1, ceil(total / page_size)) if total > 0 else 1
    offset = (page - 1) * page_size

    # 9. Apply whitelisted sort and execute paginated query
    sort_expr = ALLOWED_SORT_ORDERS[sort_key]()
    auctions = query.order_by(sort_expr).offset(offset).limit(page_size).all()

    return AuctionListResponse(
        items=[_format_auction_out(a, viewer=optional_user) for a in auctions],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get(
    "/seller/me",
    response_model=AuctionListResponse,
    summary="[Seller] List all auctions owned by the current seller"
)
def list_my_auctions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query("ALL", description="Filter by auction status or 'ALL'"),
    sort_by: str = Query("newest"),
    db: Session = Depends(get_db),
    current_seller: User = Depends(require_seller)
) -> Any:
    """Seller console view of all their auction listings with unmasked reserve prices."""
    return list_auctions(
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        search=None,
        category_id=None,
        category_slug=None,
        seller_id=current_seller.id,
        condition=None,
        min_price=None,
        max_price=None,
        sort_by=sort_by,
        db=db,
        optional_user=current_seller
    )


@router.get(
    "/{auction_id}",
    response_model=AuctionDetailOut,
    summary="Get auction details by ID"
)
def get_auction_by_id(
    auction_id: int,
    db: Session = Depends(get_db),
    optional_user: Optional[User] = Depends(get_optional_current_user)
) -> Any:
    """
    Retrieves full details for an auction listing.
    Includes product information, current highest bid, bid count, auction status, and end time.
    Masks the reserve price unless requested by the seller owner or an administrator.
    """
    auction = db.query(Auction).options(
        joinedload(Auction.product).joinedload(Product.seller),
        joinedload(Auction.product).joinedload(Product.category),
        joinedload(Auction.winner)
    ).filter(Auction.id == auction_id).first()

    if not auction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auction with ID {auction_id} not found."
        )

    return _format_auction_out(auction, viewer=optional_user)


# -----------------------------------------------------------------------------
# 2. SELLER-ONLY AUCTION MANAGEMENT (OWNERSHIP & LIFECYCLE ENFORCED)
# -----------------------------------------------------------------------------

@router.post(
    "",
    response_model=AuctionOut,
    status_code=status.HTTP_201_CREATED,
    summary="[Seller] Create and schedule a new auction"
)
def create_auction(
    auction_in: AuctionCreate,
    db: Session = Depends(get_db),
    current_seller: User = Depends(require_seller)
) -> Any:
    """
    Creates and schedules a new auction listing.
    Enforces:
    - Product existence and seller ownership
    - Unique product-to-auction constraint
    - Pricing rules: starting_price >= 0.01, reserve_price >= starting_price
    - Timing rule: end_time > start_time
    """
    # 1. Fetch target product and verify ownership
    product = db.query(Product).options(joinedload(Product.auction)).filter(Product.id == auction_in.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {auction_in.product_id} not found."
        )

    if product.seller_id != current_seller.id and current_seller.role.name != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You cannot create an auction for a product you do not own."
        )

    # 2. Check if product already has an auction
    if product.auction:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product #{product.id} ('{product.title}') already has an auction (Auction #{product.auction.id})."
        )

    # 3. Determine start time and initial status
    now = datetime.now(timezone.utc)
    start_time = auction_in.start_time
    if start_time is None:
        start_time = now

    # Convert datetimes to naive UTC for consistent MySQL TIMESTAMP storage
    start_time_naive = start_time.astimezone(timezone.utc).replace(tzinfo=None) if start_time.tzinfo else start_time
    end_time_naive = auction_in.end_time.astimezone(timezone.utc).replace(tzinfo=None) if auction_in.end_time.tzinfo else auction_in.end_time

    target_status = auction_in.status or "ACTIVE"
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    if start_time_naive > now_naive and target_status == "ACTIVE":
        target_status = "SCHEDULED"

    new_auction = Auction(
        product_id=product.id,
        starting_price=auction_in.starting_price,
        current_highest_bid=None,
        reserve_price=auction_in.reserve_price,
        minimum_increment=auction_in.minimum_increment,
        start_time=start_time_naive,
        end_time=end_time_naive,
        status=AuctionStatus(target_status),
        total_bids=0
    )
    db.add(new_auction)
    db.flush()

    # 4. Audit log entry
    audit = AuditLog(
        user_id=current_seller.id,
        action="AUCTION_CREATED",
        entity_type="AUCTION",
        entity_id=new_auction.id,
        new_values={
            "product_id": new_auction.product_id,
            "starting_price": str(new_auction.starting_price),
            "reserve_price": str(new_auction.reserve_price) if new_auction.reserve_price else None,
            "status": new_auction.status.value
        }
    )
    db.add(audit)
    db.commit()
    db.refresh(new_auction)

    return _format_auction_out(new_auction, viewer=current_seller)


@router.put(
    "/{auction_id}",
    response_model=AuctionOut,
    summary="[Seller] Update an existing auction"
)
def update_auction(
    auction_id: int,
    auction_in: AuctionUpdate,
    db: Session = Depends(get_db),
    current_seller: User = Depends(require_seller)
) -> Any:
    """
    Updates an auction listing.
    Enforces:
    - Ownership: Seller must own the listing (or be admin)
    - Closed state protection: Terminal auctions cannot be modified
    - Active auction protection: Starting price and reserve cannot be altered once bids are placed
    """
    auction = db.query(Auction).options(
        joinedload(Auction.product).joinedload(Product.seller),
        joinedload(Auction.product).joinedload(Product.category)
    ).filter(Auction.id == auction_id).first()

    if not auction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auction with ID {auction_id} not found."
        )

    # 1. Enforce ownership
    if auction.product.seller_id != current_seller.id and current_seller.role.name != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You do not own this auction listing."
        )

    # 2. Enforce closed state protection
    closed_states = [
        AuctionStatus.COMPLETED,
        AuctionStatus.UNSOLD,
        AuctionStatus.RESERVE_NOT_MET,
        AuctionStatus.CANCELLED
    ]
    if auction.status in closed_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify auction: Auction is already closed with status '{auction.status.value}'."
        )

    # 3. Enforce active bidding protections
    has_bids = auction.total_bids > 0 or auction.current_highest_bid is not None
    if auction.status == AuctionStatus.ACTIVE and has_bids:
        if auction_in.starting_price is not None and auction_in.starting_price != auction.starting_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot alter starting price: Auction has already received active bids."
            )
        if auction_in.reserve_price is not None and auction_in.reserve_price != auction.reserve_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot alter reserve price: Auction has already received active bids."
            )
        if auction_in.minimum_increment is not None and auction_in.minimum_increment != auction.minimum_increment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify minimum increment while active bidding is underway."
            )

    # 4. Validate time changes (normalized to UTC naive for consistent database storage)
    start_val = auction_in.start_time or auction.start_time
    end_val = auction_in.end_time or auction.end_time
    start_comp = start_val.astimezone(timezone.utc).replace(tzinfo=None) if getattr(start_val, "tzinfo", None) else start_val
    end_comp = end_val.astimezone(timezone.utc).replace(tzinfo=None) if getattr(end_val, "tzinfo", None) else end_val

    if end_comp <= start_comp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auction end time must be strictly greater than start time."
        )

    # 5. Validate price changes
    starting_comp = auction_in.starting_price if auction_in.starting_price is not None else auction.starting_price
    reserve_comp = auction_in.reserve_price if auction_in.reserve_price is not None else auction.reserve_price
    if reserve_comp is not None and reserve_comp < starting_comp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reserve price cannot be less than starting price."
        )

    # 6. Apply updates
    if auction_in.starting_price is not None:
        auction.starting_price = auction_in.starting_price
    if auction_in.reserve_price is not None:
        auction.reserve_price = auction_in.reserve_price
    if auction_in.minimum_increment is not None:
        auction.minimum_increment = auction_in.minimum_increment
    if auction_in.start_time is not None:
        auction.start_time = start_comp
    if auction_in.end_time is not None:
        auction.end_time = end_comp
    if auction_in.status is not None:
        new_status = AuctionStatus(auction_in.status)
        # Cannot directly transition to automated closed states (must use engine or cancel)
        if new_status in [AuctionStatus.COMPLETED, AuctionStatus.UNSOLD, AuctionStatus.RESERVE_NOT_MET]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot set auction to automated settlement status directly. Use automated closing engine."
            )
        if new_status == AuctionStatus.CANCELLED and has_bids and current_seller.role.name != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel active auction with bids without administrative override."
            )
        auction.status = new_status

    db.add(auction)
    db.commit()
    db.refresh(auction)

    return _format_auction_out(auction, viewer=current_seller)


@router.post(
    "/{auction_id}/cancel",
    response_model=AuctionOut,
    summary="[Seller/Admin] Cancel an auction"
)
def cancel_auction(
    auction_id: int,
    db: Session = Depends(get_db),
    current_seller: User = Depends(require_seller)
) -> Any:
    """
    Cancels an active or scheduled auction.
    Enforces:
    - Ownership: Seller must own the listing (or be admin)
    - Closed state protection: Already completed/unsold/cancelled auctions cannot be cancelled again
    - Zero-bid rule: Active auctions with bids can only be cancelled by administrators
    """
    auction = db.query(Auction).options(
        joinedload(Auction.product).joinedload(Product.seller)
    ).filter(Auction.id == auction_id).first()

    if not auction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auction with ID {auction_id} not found."
        )

    # 1. Enforce ownership
    if auction.product.seller_id != current_seller.id and current_seller.role.name != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You do not own this auction listing."
        )

    # 2. Check already closed
    closed_states = [
        AuctionStatus.COMPLETED,
        AuctionStatus.UNSOLD,
        AuctionStatus.RESERVE_NOT_MET,
        AuctionStatus.CANCELLED
    ]
    if auction.status in closed_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Auction is already closed with status '{auction.status.value}'."
        )

    # 3. Check zero-bid rule for non-admin sellers
    if auction.status == AuctionStatus.ACTIVE and auction.total_bids > 0:
        if current_seller.role.name != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel an active auction that has received valid bids. Contact administration for assistance."
            )

    old_status = auction.status.value
    auction.status = AuctionStatus.CANCELLED

    audit = AuditLog(
        user_id=current_seller.id,
        action="AUCTION_CANCELLED",
        entity_type="AUCTION",
        entity_id=auction.id,
        old_values={"status": old_status},
        new_values={"status": "CANCELLED"}
    )
    db.add(audit)
    db.commit()
    db.refresh(auction)

    return _format_auction_out(auction, viewer=current_seller)


# -----------------------------------------------------------------------------
# 3. AUCTION CLOSING & WINNER SETTLEMENT ENDPOINTS
# -----------------------------------------------------------------------------

@router.post(
    "/close-expired",
    response_model=BatchCloseResponse,
    summary="[Admin/Seller] Close expired active auctions"
)
def batch_close_expired(
    seller_id: Optional[int] = Query(None, description="[Admin Only] Filter sweep to a specific seller ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_seller)
) -> Any:
    """
    Sweeps the database for all active auctions whose end_time has elapsed,
    resolves winners, handles zero-bid items (UNSOLD), enforces reserve prices,
    generates simulated demo transactions, and dispatches in-app notifications.
    Security:
    - If caller is a non-admin SELLER, ONLY sweep auctions belonging to that seller.
    - If seller_id is explicitly passed, filters to that seller (only permitted for ADMIN or matching own id).
    """
    if current_user.role.name != "ADMIN" and seller_id is not None and seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Sellers cannot close other sellers' auctions."
        )

    target_seller_id = current_user.id if current_user.role.name != "ADMIN" else seller_id
    return close_all_expired_auctions(
        db=db,
        closing_user_id=current_user.id,
        seller_id=target_seller_id
    )


@router.post(
    "/{auction_id}/close",
    response_model=AuctionCloseResult,
    summary="[Seller/Admin] Close a single auction and settle winner"
)
def close_auction_endpoint(
    auction_id: int,
    force: bool = Query(False, description="[Admin Only] Force close before scheduled deadline"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_seller)
) -> Any:
    """
    Closes a specific auction.
    Ownership: Permitted for the owning seller or an administrator.
    Idempotency: Calling on an already closed auction returns its final state without duplicate settlement.
    """
    auction = db.query(Auction).options(joinedload(Auction.product)).filter(Auction.id == auction_id).first()
    if not auction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Auction with ID {auction_id} not found.")

    if auction.product.seller_id != current_user.id and current_user.role.name != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You do not own this auction listing."
        )

    if force and current_user.role.name != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only administrators can force close an auction before its deadline."
        )

    return close_single_auction(
        db=db,
        auction_id=auction_id,
        closing_user_id=current_user.id,
        force_close=force
    )


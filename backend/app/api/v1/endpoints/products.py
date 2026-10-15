"""
BidSmart Analytics — Product Management Router
Provides public product browsing and seller-only product lifecycle management.
"""

from typing import Any, Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc, asc

from app.api.deps import (
    get_db,
    get_current_active_user,
    require_seller,
    require_seller_payment_setup,
)
from app.models.user import User
from app.models.product import Product, ProductCondition
from app.models.category import Category
from app.models.auction import Auction, AuctionStatus
from app.models.audit_log import AuditLog
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductOut,
    ProductListResponse,
    SellerSummary
)
from app.schemas.category import CategoryOut

router = APIRouter()


def _format_product_out(p: Product) -> ProductOut:
    """Helper to convert Product model to sanitized ProductOut schema."""
    seller_summary = None
    if p.seller:
        seller_summary = SellerSummary(
            id=p.seller.id,
            username=p.seller.username,
            full_name=p.seller.full_name,
            email=p.seller.email
        )

    cat_out = None
    if p.category:
        cat_out = CategoryOut(
            id=p.category.id,
            name=p.category.name,
            slug=p.category.slug,
            description=p.category.description,
            icon_name=p.category.icon_name,
            item_count=0,
            created_at=p.category.created_at
        )

    has_auction = p.auction is not None
    auction_id = p.auction.id if p.auction else None

    return ProductOut(
        id=p.id,
        seller_id=p.seller_id,
        category_id=p.category_id,
        title=p.title,
        description=p.description,
        condition_status=p.condition_status.value if hasattr(p.condition_status, "value") else str(p.condition_status),
        image_url=p.image_url,
        thumbnail_url=p.thumbnail_url,
        created_at=p.created_at,
        updated_at=p.updated_at,
        seller=seller_summary,
        category=cat_out,
        has_auction=has_auction,
        auction_id=auction_id
    )


# -----------------------------------------------------------------------------
# 1. PUBLIC PRODUCT BROWSING
# -----------------------------------------------------------------------------

@router.get(
    "",
    response_model=ProductListResponse,
    summary="List and filter catalog products"
)
def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term in title or description"),
    category_id: Optional[int] = Query(None, description="Filter by category taxonomy ID"),
    seller_id: Optional[int] = Query(None, description="Filter by seller user ID"),
    condition: Optional[str] = Query(None, description="Filter by condition ('NEW', 'LIKE_NEW', 'USED', 'VINTAGE')"),
    has_auction: Optional[bool] = Query(None, description="Filter products that currently have an auction attached"),
    db: Session = Depends(get_db)
) -> Any:
    """Publicly browsable list of products with pagination, search, and category/seller filters."""
    query = db.query(Product).options(
        joinedload(Product.seller),
        joinedload(Product.category),
        joinedload(Product.auction)
    )

    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(or_(Product.title.ilike(search_fmt), Product.description.ilike(search_fmt)))

    if category_id:
        query = query.filter(Product.category_id == category_id)

    if seller_id:
        query = query.filter(Product.seller_id == seller_id)

    if condition:
        cond_upper = condition.upper().strip()
        query = query.filter(Product.condition_status == cond_upper)

    if has_auction is True:
        query = query.filter(Product.auction.has())
    elif has_auction is False:
        query = query.filter(~Product.auction.has())

    total = query.count()
    pages = max(1, ceil(total / page_size)) if total > 0 else 1
    offset = (page - 1) * page_size
    products = query.order_by(Product.id.desc()).offset(offset).limit(page_size).all()

    return ProductListResponse(
        items=[_format_product_out(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get(
    "/seller/me",
    response_model=ProductListResponse,
    summary="[Seller] List seller's own inventory"
)
def list_my_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    has_auction: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_seller: User = Depends(require_seller)
) -> Any:
    """Seller-specific catalog view of their own items."""
    return list_products(
        page=page,
        page_size=page_size,
        search=None,
        category_id=None,
        seller_id=current_seller.id,
        condition=None,
        has_auction=has_auction,
        db=db
    )


@router.get(
    "/{product_id}",
    response_model=ProductOut,
    summary="Get single product details"
)
def get_product_by_id(
    product_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """Retrieves full specification for a single product."""
    product = db.query(Product).options(
        joinedload(Product.seller),
        joinedload(Product.category),
        joinedload(Product.auction)
    ).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found."
        )

    return _format_product_out(product)


# -----------------------------------------------------------------------------
# 2. SELLER-ONLY PRODUCT MUTATIONS (OWNERSHIP STRICTLY ENFORCED)
# -----------------------------------------------------------------------------

@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    summary="[Seller] Create a new product listing"
)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_seller: User = Depends(require_seller_payment_setup)
) -> Any:
    """
    Creates a new product listing owned by the authenticated seller.
    Validates category taxonomy existence and sets seller_id automatically.
    """
    # 1. Validate category existence
    cat = db.query(Category).filter(Category.id == product_in.category_id).first()
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category ID {product_in.category_id} does not exist."
        )

    # 2. Instantiate and persist product
    new_product = Product(
        seller_id=current_seller.id,
        category_id=product_in.category_id,
        title=product_in.title.strip(),
        description=product_in.description.strip(),
        condition_status=ProductCondition(product_in.condition_status),
        image_url=product_in.image_url.strip(),
        thumbnail_url=product_in.thumbnail_url.strip() if product_in.thumbnail_url else None
    )
    db.add(new_product)
    db.flush()

    # 3. Audit log entry
    audit = AuditLog(
        user_id=current_seller.id,
        action="PRODUCT_CREATED",
        entity_type="PRODUCT",
        entity_id=new_product.id,
        new_values={"title": new_product.title, "category_id": new_product.category_id}
    )
    db.add(audit)
    db.commit()
    db.refresh(new_product)

    return _format_product_out(new_product)


@router.put(
    "/{product_id}",
    response_model=ProductOut,
    summary="[Seller] Update an existing product"
)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    current_seller: User = Depends(require_seller)
) -> Any:
    """
    Updates a product listing.
    Ownership Rule: Only the owning seller or an administrator can update this listing.
    """
    product = db.query(Product).options(
        joinedload(Product.seller),
        joinedload(Product.category),
        joinedload(Product.auction)
    ).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found."
        )

    # Enforce seller ownership
    if product.seller_id != current_seller.id and current_seller.role.name != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You do not own this product listing."
        )

    # If product has an active auction with bids, restrict title/category mutations
    if product.auction and product.auction.status == AuctionStatus.ACTIVE and product.auction.total_bids > 0:
        if product_in.title is not None and product_in.title != product.title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify product title while an active auction has received bids."
            )
        if product_in.category_id is not None and product_in.category_id != product.category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify product category while an active auction has received bids."
            )

    # Apply updates
    if product_in.title is not None:
        product.title = product_in.title.strip()
    if product_in.description is not None:
        product.description = product_in.description.strip()
    if product_in.condition_status is not None:
        product.condition_status = ProductCondition(product_in.condition_status)
    if product_in.image_url is not None:
        product.image_url = product_in.image_url.strip()
    if product_in.thumbnail_url is not None:
        product.thumbnail_url = product_in.thumbnail_url.strip() if product_in.thumbnail_url else None
    if product_in.category_id is not None:
        cat = db.query(Category).filter(Category.id == product_in.category_id).first()
        if not cat:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target category does not exist.")
        product.category_id = product_in.category_id

    db.add(product)
    db.commit()
    db.refresh(product)

    return _format_product_out(product)


@router.delete(
    "/{product_id}",
    summary="[Seller] Delete an unauctioned product"
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_seller: User = Depends(require_seller)
) -> Any:
    """
    Deletes a product listing.
    Ownership Rule: Only the owning seller or an administrator can delete this listing.
    Integrity Rule: Products attached to active or completed auctions cannot be deleted.
    """
    product = db.query(Product).options(joinedload(Product.auction)).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found."
        )

    # Enforce seller ownership
    if product.seller_id != current_seller.id and current_seller.role.name != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You do not own this product listing."
        )

    # Integrity check: auction attached
    if product.auction:
        if product.auction.status in [AuctionStatus.ACTIVE, AuctionStatus.COMPLETED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete product with auction in '{product.auction.status.value}' status."
            )

        if product.auction.total_bids > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a product whose auction has bid history."
            )

        # If auction is DRAFT or CANCELLED, remove the auction first
        db.delete(product.auction)

    db.delete(product)
    db.commit()

    return {"message": "Product successfully deleted.", "product_id": product_id}

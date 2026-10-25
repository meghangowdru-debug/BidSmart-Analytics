"""
BidSmart Analytics — Categories Router
Provides category taxonomy endpoints for marketplace browsing and catalog navigation.
"""

from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db
from app.models.category import Category
from app.models.product import Product
from app.schemas.category import CategoryOut

router = APIRouter()


@router.get(
    "",
    response_model=List[CategoryOut],
    summary="List all product categories"
)
def list_categories(
    db: Session = Depends(get_db)
) -> Any:
    """Returns all product categories along with the count of listed products."""
    categories = db.query(
        Category,
        func.count(Product.id).label("item_count")
    ).outerjoin(Product, Product.category_id == Category.id)\
     .group_by(Category.id)\
     .order_by(Category.name.asc())\
     .all()

    result = []
    for cat, count in categories:
        cat_out = CategoryOut(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            icon_name=cat.icon_name,
            item_count=count,
            created_at=cat.created_at
        )
        result.append(cat_out)
    return result


@router.get(
    "/{category_id}",
    response_model=CategoryOut,
    summary="Get category details by ID"
)
def get_category_by_id(
    category_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """Returns details for a single category taxonomy."""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Category with ID {category_id} not found.")

    count = db.query(func.count(Product.id)).filter(Product.category_id == category_id).scalar() or 0
    return CategoryOut(
        id=cat.id,
        name=cat.name,
        slug=cat.slug,
        description=cat.description,
        icon_name=cat.icon_name,
        item_count=count,
        created_at=cat.created_at
    )


"""
BidSmart Analytics — Product Management Test Suite (Phase 5)
Tests:
1. Public Product Catalog Browsing & Search
2. Category Taxonomy Endpoints
3. Seller Product Creation & Validation
4. Seller Ownership Enforcement (Sellers cannot modify other sellers' products)
5. Product Update Lifecycle
6. Product Deletion Restrictions (Integrity checks against active auctions)
7. Missing Records (404) & Unauthorized Access (401/403)
"""

import pytest
from fastapi import status
from sqlalchemy.orm import Session
from app.models.product import Product
from app.models.user import User


@pytest.fixture
def seller_tokens(client):
    """Provides access tokens for two distinct sellers and one buyer."""
    # Seller 1: vance_estates (id: 3)
    r1 = client.post("/api/v1/auth/login", json={"username_or_email": "vance_estates", "password": "password123"})
    token1 = r1.json()["access_token"]

    # Seller 2: apex_electronics (id: 4)
    r2 = client.post("/api/v1/auth/login", json={"username_or_email": "apex_electronics", "password": "password123"})
    token2 = r2.json()["access_token"]

    # Buyer: elena_r (id: 8)
    r3 = client.post("/api/v1/auth/login", json={"username_or_email": "elena_r", "password": "password123"})
    token3 = r3.json()["access_token"]

    # Admin: admin_sarah (id: 1)
    r4 = client.post("/api/v1/auth/login", json={"username_or_email": "admin_sarah", "password": "password123"})
    token4 = r4.json()["access_token"]

    return {
        "seller1": token1,
        "seller2": token2,
        "buyer": token3,
        "admin": token4
    }


# -----------------------------------------------------------------------------
# 1. CATEGORY TESTS
# -----------------------------------------------------------------------------

def test_list_categories_success(client):
    """Verify listing all categories with item counts."""
    response = client.get("/api/v1/categories")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 6
    names = [c["name"] for c in data]
    assert "Electronics & Computing" in names
    assert "Fine Art & Antiques" in names
    for c in data:
        assert "item_count" in c
        assert c["item_count"] >= 0


def test_get_category_by_id(client):
    """Verify getting single category and 404 for missing ID."""
    r = client.get("/api/v1/categories/1")
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["slug"] == "electronics-computing"

    r_missing = client.get("/api/v1/categories/99999")
    assert r_missing.status_code == status.HTTP_404_NOT_FOUND


# -----------------------------------------------------------------------------
# 2. PUBLIC PRODUCT BROWSING & SEARCH TESTS
# -----------------------------------------------------------------------------

def test_list_products_pagination(client):
    """Verify product list pagination metadata and default limit."""
    response = client.get("/api/v1/products?page=1&page_size=10")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total"] >= 40
    assert len(data["items"]) == 10
    # Zero password hash leakage verification
    for p in data["items"]:
        assert "password_hash" not in str(p)
        assert p["seller"]["username"] is not None


def test_list_products_search_and_filters(client):
    """Verify search keyword and category/seller filters."""
    # Search for Macintosh
    r_search = client.get("/api/v1/products?search=Macintosh")
    assert r_search.status_code == status.HTTP_200_OK
    data = r_search.json()
    assert data["total"] >= 1
    for p in data["items"]:
        assert "macintosh" in p["title"].lower() or "macintosh" in p["description"].lower()

    # Filter by category
    r_cat = client.get("/api/v1/products?category_id=1")
    assert r_cat.status_code == status.HTTP_200_OK
    for p in r_cat.json()["items"]:
        assert p["category_id"] == 1


def test_get_product_by_id_and_404(client):
    """Verify single product retrieval and 404 error response."""
    r_valid = client.get("/api/v1/products/1")
    assert r_valid.status_code == status.HTTP_200_OK
    assert r_valid.json()["id"] == 1

    r_invalid = client.get("/api/v1/products/999999")
    assert r_invalid.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in r_invalid.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 3. SELLER PRODUCT CREATION & VALIDATION TESTS
# -----------------------------------------------------------------------------

def test_create_product_unauthenticated_and_buyer_forbidden(client, seller_tokens):
    """Verify unauthenticated returns 401 and buyer returns 403."""
    payload = {
        "title": "Unauthorized Listing Test",
        "description": "Attempting to create listing without permissions.",
        "condition_status": "NEW",
        "image_url": "https://images.unsplash.com/test.jpg",
        "category_id": 1
    }

    # 1. Unauthenticated -> 401
    r_unauth = client.post("/api/v1/products", json=payload)
    assert r_unauth.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Buyer -> 403 Forbidden
    r_buyer = client.post(
        "/api/v1/products",
        json=payload,
        headers={"Authorization": f"Bearer {seller_tokens['buyer']}"}
    )
    assert r_buyer.status_code == status.HTTP_403_FORBIDDEN


def test_create_product_success_and_validation(client, seller_tokens, db: Session):
    """Verify clean seller product creation and validation rules."""
    valid_payload = {
        "title": "Vintage Mechanical Chronograph 1972",
        "description": "Authentic mechanical chronograph with original patina and leather strap.",
        "condition_status": "VINTAGE",
        "image_url": "https://images.unsplash.com/photo-watch.jpg",
        "thumbnail_url": "https://images.unsplash.com/thumb-watch.jpg",
        "category_id": 3
    }

    response = client.post(
        "/api/v1/products",
        json=valid_payload,
        headers={"Authorization": f"Bearer {seller_tokens['seller1']}"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    created_id = data["id"]
    assert data["title"] == valid_payload["title"]
    assert data["seller"]["username"] == "vance_estates"
    assert data["has_auction"] is False

    # Cleanup product created during test
    created_prod = db.query(Product).filter(Product.id == created_id).first()
    if created_prod:
        db.delete(created_prod)
        db.commit()


def test_create_product_invalid_category(client, seller_tokens):
    """Verify 400 Bad Request when category does not exist."""
    payload = {
        "title": "Invalid Category Product",
        "description": "This product has a non-existent category taxonomy ID.",
        "condition_status": "USED",
        "image_url": "https://images.unsplash.com/invalid.jpg",
        "category_id": 99999
    }
    response = client.post(
        "/api/v1/products",
        json=payload,
        headers={"Authorization": f"Bearer {seller_tokens['seller1']}"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "does not exist" in response.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 4. SELLER OWNERSHIP ENFORCEMENT & UPDATE TESTS
# -----------------------------------------------------------------------------

def test_seller_cannot_modify_another_sellers_product(client, seller_tokens, db: Session):
    """
    CRITICAL RBAC REQUIREMENT:
    Seller 1 creates a product.
    Seller 2 attempts to update Seller 1's product -> MUST RETURN 403 FORBIDDEN.
    """
    # 1. Seller 1 creates product
    create_resp = client.post(
        "/api/v1/products",
        json={
            "title": "Seller 1 Exclusive Art Piece",
            "description": "Authentic oil on canvas painting from private collection.",
            "condition_status": "LIKE_NEW",
            "image_url": "https://images.unsplash.com/art.jpg",
            "category_id": 2
        },
        headers={"Authorization": f"Bearer {seller_tokens['seller1']}"}
    )
    product_id = create_resp.json()["id"]

    try:
        # 2. Seller 2 attempts to UPDATE Seller 1's product -> 403 Forbidden
        update_attempt = client.put(
            f"/api/v1/products/{product_id}",
            json={"title": "Hacked Title by Competitor"},
            headers={"Authorization": f"Bearer {seller_tokens['seller2']}"}
        )
        assert update_attempt.status_code == status.HTTP_403_FORBIDDEN
        assert "you do not own this product" in update_attempt.json()["detail"].lower()

        # 3. Seller 2 attempts to DELETE Seller 1's product -> 403 Forbidden
        delete_attempt = client.delete(
            f"/api/v1/products/{product_id}",
            headers={"Authorization": f"Bearer {seller_tokens['seller2']}"}
        )
        assert delete_attempt.status_code == status.HTTP_403_FORBIDDEN

        # 4. Seller 1 (Owner) can successfully update own product -> 200 OK
        valid_update = client.put(
            f"/api/v1/products/{product_id}",
            json={"title": "Seller 1 Exclusive Art Piece (Verified)"},
            headers={"Authorization": f"Bearer {seller_tokens['seller1']}"}
        )
        assert valid_update.status_code == status.HTTP_200_OK
        assert valid_update.json()["title"] == "Seller 1 Exclusive Art Piece (Verified)"

        # 5. Seller 1 (Owner) can successfully delete unauctioned product -> 200 OK
        valid_delete = client.delete(
            f"/api/v1/products/{product_id}",
            headers={"Authorization": f"Bearer {seller_tokens['seller1']}"}
        )
        assert valid_delete.status_code == status.HTTP_200_OK

    finally:
        # Ensure cleanup in all failure modes
        prod = db.query(Product).filter(Product.id == product_id).first()
        if prod:
            db.delete(prod)
            db.commit()


def test_cannot_delete_product_with_active_auction(client, seller_tokens):
    """Verify integrity protection: cannot delete product attached to active auction."""
    # Product 1 is attached to Auction 1 (active) and owned by apex_electronics (seller 2)
    # 1. Cross-seller deletion attempt -> 403 Forbidden
    r_forbidden = client.delete(
        "/api/v1/products/1",
        headers={"Authorization": f"Bearer {seller_tokens['seller1']}"}
    )
    assert r_forbidden.status_code == status.HTTP_403_FORBIDDEN

    # 2. Owner deletion attempt on active auction product -> 400 Bad Request
    r_owner = client.delete(
        "/api/v1/products/1",
        headers={"Authorization": f"Bearer {seller_tokens['seller2']}"}
    )
    assert r_owner.status_code == status.HTTP_400_BAD_REQUEST
    assert "cannot delete product with auction" in r_owner.json()["detail"].lower()

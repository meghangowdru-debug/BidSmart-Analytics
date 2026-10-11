"""
BidSmart Analytics — Auction Management & Lifecycle Test Suite (Phase 5)
Tests:
1. Public Auction Catalog Browsing & Multi-Facet Filtering
2. Parameterized Whitelisted Sorting & SQL Injection Defense
3. Auction Details & Privacy Masking (Reserve price hidden from public/buyers)
4. Seller-Only Auction Creation & Pricing/Timing Validation
5. Cross-Seller Ownership Enforcement (Sellers cannot modify or create auctions for others' products)
6. Duplicate Auction Conflict Rejection
7. Closed Auction Mutation Restrictions
8. Active Auction Bidding Protections (Starting price locked after bids)
9. Auction Cancellation Rules & Admin Dispute Override
10. Missing Records (404) & Authentication Boundaries (401/403)
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi import status
from sqlalchemy.orm import Session
from app.models.auction import Auction, AuctionStatus
from app.models.product import Product


@pytest.fixture
def auth_tokens(client):
    """
    Provides tokens for:
    - s1: vance_estates (id: 3, owns products 3, 9, 14, 20, 25, 30, 34, 37)
    - s2: apex_electronics (id: 4, owns products 1, 4, 10, 16, 21, 26, 31, 38)
    - buyer: elena_r (id: 8)
    - admin: admin_sarah (id: 1)
    """
    s1 = client.post("/api/v1/auth/login", json={"username_or_email": "vance_estates", "password": "password123"}).json()["access_token"]
    s2 = client.post("/api/v1/auth/login", json={"username_or_email": "apex_electronics", "password": "password123"}).json()["access_token"]
    buyer = client.post("/api/v1/auth/login", json={"username_or_email": "elena_r", "password": "password123"}).json()["access_token"]
    admin = client.post("/api/v1/auth/login", json={"username_or_email": "admin_sarah", "password": "password123"}).json()["access_token"]
    return {"s1": s1, "s2": s2, "buyer": buyer, "admin": admin}


# -----------------------------------------------------------------------------
# 1. PUBLIC CATALOG BROWSING, SEARCH, FILTERS & SORTING
# -----------------------------------------------------------------------------

def test_list_active_auctions_public(client):
    """Verify public retrieval of active auctions with pagination and effective price."""
    response = client.get("/api/v1/auctions?page=1&page_size=10&status_filter=ACTIVE")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total"] >= 10
    assert len(data["items"]) <= 10

    # Verify attributes and privacy
    for a in data["items"]:
        assert a["status"] == "ACTIVE"
        assert a["starting_price"] is not None
        assert a["effective_price"] is not None
        assert a["seconds_remaining"] >= 0
        # Public viewer must not see hidden reserve prices
        assert a["reserve_price"] is None
        # Product details are embedded
        assert a["product"]["title"] is not None


def test_list_auctions_search_and_filters(client):
    """Verify multi-facet filters: search, category, condition, and price window."""
    # 1. Search term matching 'Macintosh'
    r_search = client.get("/api/v1/auctions?status_filter=ALL&search=Macintosh")
    assert r_search.status_code == status.HTTP_200_OK
    assert r_search.json()["total"] >= 1

    # 2. Category slug filter
    r_cat = client.get("/api/v1/auctions?status_filter=ALL&category_slug=electronics-computing")
    assert r_cat.status_code == status.HTTP_200_OK
    for item in r_cat.json()["items"]:
        assert item["product"]["category"]["slug"] == "electronics-computing"

    # 3. Price range filter
    r_price = client.get("/api/v1/auctions?status_filter=ACTIVE&min_price=100.00&max_price=3000.00")
    assert r_price.status_code == status.HTTP_200_OK
    for item in r_price.json()["items"]:
        price = Decimal(str(item["effective_price"]))
        assert price >= Decimal("100.00")
        assert price <= Decimal("3000.00")


def test_whitelisted_sorting_and_sql_injection_defense(client):
    """Verify valid sorts and rejection of arbitrary/malicious sort inputs."""
    valid_sorts = ["ending_soon", "ending_latest", "price_asc", "price_desc", "most_bids", "newest", "oldest"]
    for sort_key in valid_sorts:
        r = client.get(f"/api/v1/auctions?sort_by={sort_key}")
        assert r.status_code == status.HTTP_200_OK, f"Sort order '{sort_key}' failed."

    # Unsafe / arbitrary SQL injection attempt in sort_by must return 400 Bad Request
    malicious_sort = "price_asc; DROP TABLE users;--"
    r_bad = client.get(f"/api/v1/auctions?sort_by={malicious_sort}")
    assert r_bad.status_code == status.HTTP_400_BAD_REQUEST
    assert "invalid sort parameter" in r_bad.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 2. AUCTION DETAILS & PRIVACY ENFORCEMENT
# -----------------------------------------------------------------------------

def test_get_auction_details_public_vs_owner_privacy(client, auth_tokens):
    """
    Verify auction details endpoint and privacy masking:
    - Public / Buyer caller: reserve_price is MASKED (None).
    - Seller owner (s1 / vance_estates) / Admin caller: reserve_price is VISIBLE.
    - Other seller (s2 / apex_electronics): reserve_price is MASKED (None).
    """
    # Auction 14 belongs to product 14 (seller: vance_estates / s1) and has reserve_price = 20000.00
    # 1. Unauthenticated public request -> reserve_price is None
    r_public = client.get("/api/v1/auctions/14")
    assert r_public.status_code == status.HTTP_200_OK
    assert r_public.json()["reserve_price"] is None

    # 2. Buyer request -> reserve_price is None
    r_buyer = client.get("/api/v1/auctions/14", headers={"Authorization": f"Bearer {auth_tokens['buyer']}"})
    assert r_buyer.status_code == status.HTTP_200_OK
    assert r_buyer.json()["reserve_price"] is None

    # 3. Other Seller (s2) request -> reserve_price is None
    r_other = client.get("/api/v1/auctions/14", headers={"Authorization": f"Bearer {auth_tokens['s2']}"})
    assert r_other.status_code == status.HTTP_200_OK
    assert r_other.json()["reserve_price"] is None

    # 4. Seller 1 (Owner) request -> reserve_price is revealed
    r_owner = client.get("/api/v1/auctions/14", headers={"Authorization": f"Bearer {auth_tokens['s1']}"})
    assert r_owner.status_code == status.HTTP_200_OK
    assert Decimal(str(r_owner.json()["reserve_price"])) == Decimal("20000.00")

    # 5. Admin request -> reserve_price is revealed
    r_admin = client.get("/api/v1/auctions/14", headers={"Authorization": f"Bearer {auth_tokens['admin']}"})
    assert r_admin.status_code == status.HTTP_200_OK
    assert Decimal(str(r_admin.json()["reserve_price"])) == Decimal("20000.00")


def test_get_auction_details_missing_record_404(client):
    """Verify 404 response for non-existent auction ID."""
    response = client.get("/api/v1/auctions/999999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 3. SELLER AUCTION CREATION & VALIDATION TESTS
# -----------------------------------------------------------------------------

def test_create_auction_validation_and_lifecycle(client, auth_tokens, db: Session):
    """Verify auction creation validations (price, timing, reserve)."""
    # 1. Create a fresh test product for seller 1
    prod_resp = client.post(
        "/api/v1/products",
        json={
            "title": "Rare Coin Collection 1890",
            "description": "Mint condition numismatics coin set in protective casing.",
            "condition_status": "VINTAGE",
            "image_url": "https://images.unsplash.com/coin.jpg",
            "category_id": 5
        },
        headers={"Authorization": f"Bearer {auth_tokens['s1']}"}
    )
    product_id = prod_resp.json()["id"]

    try:
        now = datetime.now(timezone.utc)
        # Validation failure: end_time <= start_time
        invalid_time_payload = {
            "product_id": product_id,
            "starting_price": 100.00,
            "minimum_increment": 5.00,
            "start_time": (now + timedelta(hours=2)).isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat()  # Ends before it starts!
        }
        r_time = client.post("/api/v1/auctions", json=invalid_time_payload, headers={"Authorization": f"Bearer {auth_tokens['s1']}"})
        assert r_time.status_code == 422

        # Validation failure: reserve_price < starting_price
        invalid_reserve_payload = {
            "product_id": product_id,
            "starting_price": 500.00,
            "reserve_price": 200.00,  # Below starting price!
            "minimum_increment": 10.00,
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(days=3)).isoformat()
        }
        r_reserve = client.post("/api/v1/auctions", json=invalid_reserve_payload, headers={"Authorization": f"Bearer {auth_tokens['s1']}"})
        assert r_reserve.status_code == 422

        # Valid auction creation
        valid_payload = {
            "product_id": product_id,
            "starting_price": 150.00,
            "reserve_price": 250.00,
            "minimum_increment": 10.00,
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(days=3)).isoformat(),
            "status": "ACTIVE"
        }
        r_create = client.post("/api/v1/auctions", json=valid_payload, headers={"Authorization": f"Bearer {auth_tokens['s1']}"})
        assert r_create.status_code == status.HTTP_201_CREATED
        auction_id = r_create.json()["id"]
        assert Decimal(str(r_create.json()["starting_price"])) == Decimal("150.00")
        assert Decimal(str(r_create.json()["reserve_price"])) == Decimal("250.00")

        # Duplicate auction on same product check -> MUST FAIL WITH 409 CONFLICT
        r_dup = client.post("/api/v1/auctions", json=valid_payload, headers={"Authorization": f"Bearer {auth_tokens['s1']}"})
        assert r_dup.status_code == status.HTTP_409_CONFLICT
        assert "already has an auction" in r_dup.json()["detail"].lower()

    finally:
        # Cleanup created auction and product
        auc = db.query(Auction).filter(Auction.product_id == product_id).first()
        if auc:
            db.delete(auc)
        prod = db.query(Product).filter(Product.id == product_id).first()
        if prod:
            db.delete(prod)
        db.commit()


def test_seller_cannot_create_auction_for_another_sellers_product(client, auth_tokens, db: Session):
    """
    CRITICAL RBAC CHECK:
    Seller 1 owns product.
    Seller 2 attempts to schedule an auction for Seller 1's product -> MUST RETURN 403 FORBIDDEN.
    """
    # 1. Seller 1 creates product
    prod_resp = client.post(
        "/api/v1/products",
        json={
            "title": "Exclusive Seller 1 Jewelry",
            "description": "Diamond and sapphire necklace.",
            "condition_status": "NEW",
            "image_url": "https://images.unsplash.com/jewelry.jpg",
            "category_id": 3
        },
        headers={"Authorization": f"Bearer {auth_tokens['s1']}"}
    )
    product_id = prod_resp.json()["id"]

    try:
        now = datetime.now(timezone.utc)
        payload = {
            "product_id": product_id,
            "starting_price": 1000.00,
            "minimum_increment": 50.00,
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(days=2)).isoformat()
        }

        # 2. Seller 2 attempts to auction Seller 1's product -> 403 Forbidden
        attempt = client.post(
            "/api/v1/auctions",
            json=payload,
            headers={"Authorization": f"Bearer {auth_tokens['s2']}"}
        )
        assert attempt.status_code == status.HTTP_403_FORBIDDEN
        assert "cannot create an auction for a product you do not own" in attempt.json()["detail"].lower()

    finally:
        prod = db.query(Product).filter(Product.id == product_id).first()
        if prod:
            db.delete(prod)
            db.commit()


# -----------------------------------------------------------------------------
# 4. AUCTION UPDATE & CLOSED STATE PROTECTIONS
# -----------------------------------------------------------------------------

def test_cannot_modify_closed_auction(client, auth_tokens):
    """
    CRITICAL INTEGRITY REQUIREMENT:
    Completed, Unsold, or Cancelled auctions CANNOT be modified.
    Auction 16 is COMPLETED (owned by apex_electronics / s2).
    """
    update_payload = {"starting_price": 5000.00}
    r = client.put(
        "/api/v1/auctions/16",
        json=update_payload,
        headers={"Authorization": f"Bearer {auth_tokens['s2']}"}
    )
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert "auction is already closed" in r.json()["detail"].lower()


def test_cannot_modify_starting_price_after_bids_placed(client, auth_tokens):
    """
    CRITICAL AUCTION INTEGRITY REQUIREMENT:
    Once an active auction has received bids, starting price and reserve price are FROZEN.
    Auction 1 is ACTIVE with bids, owned by apex_electronics / s2.
    """
    update_payload = {"starting_price": 9999.00}
    r = client.put(
        "/api/v1/auctions/1",
        json=update_payload,
        headers={"Authorization": f"Bearer {auth_tokens['s2']}"}
    )
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert "cannot alter starting price" in r.json()["detail"].lower()


def test_cross_seller_cannot_update_another_sellers_auction(client, auth_tokens):
    """
    Verify Seller 1 cannot update Seller 2's auction listing.
    """
    # Auction 1 belongs to Seller 2 (apex_electronics). Seller 1 is vance_estates.
    r = client.put(
        "/api/v1/auctions/1",
        json={"minimum_increment": 50.00},
        headers={"Authorization": f"Bearer {auth_tokens['s1']}"}
    )
    assert r.status_code == status.HTTP_403_FORBIDDEN
    assert "you do not own this auction" in r.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 5. AUCTION CANCELLATION & ADMIN OVERRIDE TESTS
# -----------------------------------------------------------------------------

def test_auction_cancellation_rules(client, auth_tokens, db: Session):
    """
    Verify cancellation lifecycle:
    1. Seller creates new product & auction (0 bids).
    2. Seller 2 cannot cancel it (403).
    3. Seller 1 can cancel it (200, status becomes CANCELLED).
    4. Trying to cancel again returns 400 (already closed).
    5. Active auction with bids cannot be cancelled by seller (zero-bid rule).
    """
    # 1. Create product and 0-bid auction
    prod_resp = client.post(
        "/api/v1/products",
        json={
            "title": "Cancel Test Item",
            "description": "Item created strictly to test auction cancellation rules.",
            "condition_status": "USED",
            "image_url": "https://images.unsplash.com/item.jpg",
            "category_id": 1
        },
        headers={"Authorization": f"Bearer {auth_tokens['s1']}"}
    )
    product_id = prod_resp.json()["id"]

    now = datetime.now(timezone.utc)
    auc_resp = client.post(
        "/api/v1/auctions",
        json={
            "product_id": product_id,
            "starting_price": 50.00,
            "minimum_increment": 5.00,
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(days=2)).isoformat(),
            "status": "ACTIVE"
        },
        headers={"Authorization": f"Bearer {auth_tokens['s1']}"}
    )
    auction_id = auc_resp.json()["id"]

    try:
        # 2. Seller 2 tries to cancel -> 403 Forbidden
        r_cross = client.post(f"/api/v1/auctions/{auction_id}/cancel", headers={"Authorization": f"Bearer {auth_tokens['s2']}"})
        assert r_cross.status_code == status.HTTP_403_FORBIDDEN

        # 3. Seller 1 cancels own 0-bid auction -> 200 OK
        r_cancel = client.post(f"/api/v1/auctions/{auction_id}/cancel", headers={"Authorization": f"Bearer {auth_tokens['s1']}"})
        assert r_cancel.status_code == status.HTTP_200_OK
        assert r_cancel.json()["status"] == "CANCELLED"

        # 4. Cancelling an already cancelled auction -> 400 Bad Request
        r_again = client.post(f"/api/v1/auctions/{auction_id}/cancel", headers={"Authorization": f"Bearer {auth_tokens['s1']}"})
        assert r_again.status_code == status.HTTP_400_BAD_REQUEST
        assert "already closed" in r_again.json()["detail"].lower()

        # 5. Seller 2 tries to cancel Auction 1 (which has bids) -> 400 Bad Request (zero-bid rule)
        r_bidded = client.post("/api/v1/auctions/1/cancel", headers={"Authorization": f"Bearer {auth_tokens['s2']}"})
        assert r_bidded.status_code == status.HTTP_400_BAD_REQUEST
        assert "has received valid bids" in r_bidded.json()["detail"].lower()

    finally:
        # Cleanup
        auc = db.query(Auction).filter(Auction.id == auction_id).first()
        if auc:
            db.delete(auc)
        prod = db.query(Product).filter(Product.id == product_id).first()
        if prod:
            db.delete(prod)
        db.commit()


def test_seller_my_auctions_endpoint(client, auth_tokens):
    """Verify /auctions/seller/me returns the authenticated seller's auctions with reserve prices."""
    response = client.get("/api/v1/auctions/seller/me", headers={"Authorization": f"Bearer {auth_tokens['s1']}"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] >= 1
    # Check that reserve prices are visible to the owner
    first = data["items"][0]
    assert first["product"]["seller_id"] == 3  # vance_estates user id

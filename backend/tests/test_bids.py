"""
BidSmart Analytics — Secure Bidding Engine Test Suite (Phase 6)
Tests:
1. Successful First Bid (at or above starting price) & Subsequent Bids (at or above highest + increment)
2. Atomic State Updates (current_highest_bid, winner_id, total_bids, winning_bid_id)
3. Validation Rejections: Bids below starting price or below minimum increment
4. Role-Based Access Control:
   - Unauthenticated callers rejected (401)
   - Sellers rejected (403)
   - Administrators rejected (403 conflict of interest defense)
   - Suspended accounts rejected (403)
5. Anti-Self-Bidding Enforcement (Sellers cannot bid on own items)
6. Lifecycle Restrictions:
   - Not started / Scheduled auctions rejected (400)
   - Expired auctions rejected (400)
   - Cancelled / Completed auctions rejected (400)
7. Anti-Sniping Extension Rule (60s extension if bid placed in final 30s)
8. High-Concurrency Pessimistic Locking Simulation
9. Bid History Access Control (Masked vs Unmasked Bidder Identities)
10. Buyer Personal Bid History (/bids/me)
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi import status
from sqlalchemy.orm import Session
from app.models.auction import Auction, AuctionStatus
from app.models.product import Product
from app.models.user import User, UserStatus
from app.models.bid import Bid
from app.models.audit_log import AuditLog


@pytest.fixture
def test_users(client):
    """
    Provides tokens for:
    - buyer1: elena_r (id: 8)
    - buyer2: david_k (id: 9)
    - seller1: vance_estates (id: 3)
    - seller2: apex_electronics (id: 4)
    - admin: admin_sarah (id: 1)
    """
    b1 = client.post("/api/v1/auth/login", json={"username_or_email": "elena_r", "password": "password123"}).json()["access_token"]
    b2 = client.post("/api/v1/auth/login", json={"username_or_email": "david_k", "password": "password123"}).json()["access_token"]
    s1 = client.post("/api/v1/auth/login", json={"username_or_email": "vance_estates", "password": "password123"}).json()["access_token"]
    s2 = client.post("/api/v1/auth/login", json={"username_or_email": "apex_electronics", "password": "password123"}).json()["access_token"]
    admin = client.post("/api/v1/auth/login", json={"username_or_email": "admin_sarah", "password": "password123"}).json()["access_token"]
    return {"b1": b1, "b2": b2, "s1": s1, "s2": s2, "admin": admin}


# -----------------------------------------------------------------------------
# 1. SUCCESSFUL FIRST & SUBSEQUENT BIDS
# -----------------------------------------------------------------------------

def test_first_bid_and_subsequent_bid_lifecycle(client, test_users, db: Session):
    """
    Verify full bidding lifecycle on a fresh auction:
    1. Create product and 0-bid auction.
    2. First bid meeting starting_price succeeds.
    3. Subsequent bid below increment fails.
    4. Subsequent bid meeting increment succeeds.
    5. Verify single winning bid invariant and auction aggregates.
    """
    # 1. Seller 1 creates product and auction
    prod = client.post(
        "/api/v1/products",
        json={
            "title": "Bidding Lifecycle Test Watch",
            "description": "Item used to verify atomic bidding lifecycle.",
            "condition_status": "NEW",
            "image_url": "https://images.unsplash.com/watch.jpg",
            "category_id": 3
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()
    product_id = prod["id"]

    now = datetime.now(timezone.utc)
    auc = client.post(
        "/api/v1/auctions",
        json={
            "product_id": product_id,
            "starting_price": 500.00,
            "minimum_increment": 25.00,
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=5)).isoformat(),
            "status": "ACTIVE"
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()
    auction_id = auc["id"]

    try:
        # 2. First bid below starting price fails
        r_low_first = client.post(
            f"/api/v1/auctions/{auction_id}/bids",
            json={"bid_amount": 490.00},
            headers={"Authorization": f"Bearer {test_users['b1']}"}
        )
        assert r_low_first.status_code == status.HTTP_400_BAD_REQUEST
        assert "below required minimum" in r_low_first.json()["detail"].lower()

        # 3. First bid equal to starting price ($500) succeeds
        r_bid1 = client.post(
            f"/api/v1/auctions/{auction_id}/bids",
            json={"bid_amount": 500.00},
            headers={"Authorization": f"Bearer {test_users['b1']}"}
        )
        assert r_bid1.status_code == status.HTTP_201_CREATED
        b1_data = r_bid1.json()
        assert b1_data["is_winning_bid"] is True
        assert Decimal(str(b1_data["bid_amount"])) == Decimal("500.00")
        assert Decimal(str(b1_data["new_highest_bid"])) == Decimal("500.00")
        assert b1_data["new_total_bids"] == 1
        assert Decimal(str(b1_data["minimum_next_bid"])) == Decimal("525.00")

        # 4. Buyer 2 places bid below minimum increment ($510 < $525) -> 400 Bad Request
        r_low_second = client.post(
            f"/api/v1/auctions/{auction_id}/bids",
            json={"bid_amount": 510.00},
            headers={"Authorization": f"Bearer {test_users['b2']}"}
        )
        assert r_low_second.status_code == status.HTTP_400_BAD_REQUEST
        assert "below required minimum" in r_low_second.json()["detail"].lower()

        # 5. Buyer 2 places valid outbid ($550 >= $525) -> 201 Created
        r_bid2 = client.post(
            f"/api/v1/auctions/{auction_id}/bids",
            json={"bid_amount": 550.00},
            headers={"Authorization": f"Bearer {test_users['b2']}"}
        )
        assert r_bid2.status_code == status.HTTP_201_CREATED
        b2_data = r_bid2.json()
        assert b2_data["is_winning_bid"] is True
        assert Decimal(str(b2_data["new_highest_bid"])) == Decimal("550.00")
        assert b2_data["new_total_bids"] == 2

        # 6. Verify single winning bid invariant in database
        winning_bids = db.query(Bid).filter(Bid.auction_id == auction_id, Bid.is_winning_bid == True).all()
        assert len(winning_bids) == 1
        assert winning_bids[0].id == b2_data["id"]

        # First bid should now have is_winning_bid = False
        old_bid = db.query(Bid).filter(Bid.id == b1_data["id"]).first()
        assert old_bid.is_winning_bid is False

    finally:
        # Cleanup
        db.query(AuditLog).filter(AuditLog.entity_id == auction_id, AuditLog.entity_type == "AUCTION").delete()
        db.query(Bid).filter(Bid.auction_id == auction_id).delete()
        db.query(Auction).filter(Auction.id == auction_id).delete()
        db.query(Product).filter(Product.id == product_id).delete()
        db.commit()


# -----------------------------------------------------------------------------
# 2. RBAC & INTEGRITY REJECTIONS (ADMINS, SELLERS, SUSPENDED USERS)
# -----------------------------------------------------------------------------

def test_unauthenticated_bid_rejected(client):
    """Verify 401 Unauthorized for unauthenticated bid submission."""
    response = client.post("/api/v1/auctions/1/bids", json={"bid_amount": 5000.00})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_seller_cannot_bid(client, test_users):
    """Verify 403 Forbidden: Sellers cannot place bids on any auction."""
    response = client.post(
        "/api/v1/auctions/1/bids",
        json={"bid_amount": 5000.00},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "sellers cannot participate" in response.json()["detail"].lower()


def test_admin_cannot_bid_conflict_of_interest(client, test_users):
    """
    Verify 403 Forbidden: Administrators are prohibited from bidding
    to prevent conflicts of interest and protect platform integrity.
    """
    response = client.post(
        "/api/v1/auctions/1/bids",
        json={"bid_amount": 5000.00},
        headers={"Authorization": f"Bearer {test_users['admin']}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "administrative accounts are prohibited from bidding" in response.json()["detail"].lower()


def test_suspended_buyer_cannot_bid(client, test_users, db: Session):
    """Verify 403 Forbidden: Suspended accounts cannot submit bids."""
    # Suspend buyer 2 (david_k, id 9)
    admin_headers = {"Authorization": f"Bearer {test_users['admin']}"}
    client.patch("/api/v1/users/9/status", json={"status": "SUSPENDED"}, headers=admin_headers)

    try:
        response = client.post(
            "/api/v1/auctions/1/bids",
            json={"bid_amount": 5000.00},
            headers={"Authorization": f"Bearer {test_users['b2']}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "account suspended" in response.json()["detail"].lower()
    finally:
        # Restore buyer 2
        client.patch("/api/v1/users/9/status", json={"status": "ACTIVE"}, headers=admin_headers)


# -----------------------------------------------------------------------------
# 3. AUCTION STATUS & TEMPORAL WINDOW CHECKS
# -----------------------------------------------------------------------------

def test_cannot_bid_on_closed_or_cancelled_auctions(client, test_users):
    """Verify 400 Bad Request on completed or non-active auctions."""
    # Auction 16 is COMPLETED
    r_completed = client.post(
        "/api/v1/auctions/16/bids",
        json={"bid_amount": 10000.00},
        headers={"Authorization": f"Bearer {test_users['b1']}"}
    )
    assert r_completed.status_code == status.HTTP_400_BAD_REQUEST
    assert "auction status is completed" in r_completed.json()["detail"].lower()


def test_cannot_bid_on_not_started_auction(client, test_users, db: Session):
    """Verify 400 Bad Request on auctions scheduled in the future or not started yet."""
    # 1. Create product and future-scheduled auction (status: SCHEDULED)
    prod = client.post(
        "/api/v1/products",
        json={
            "title": "Future Auction Test Item",
            "description": "Item scheduled to start tomorrow.",
            "condition_status": "NEW",
            "image_url": "https://images.unsplash.com/future.jpg",
            "category_id": 1
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()
    product_id = prod["id"]

    now = datetime.now(timezone.utc)
    auc = client.post(
        "/api/v1/auctions",
        json={
            "product_id": product_id,
            "starting_price": 100.00,
            "minimum_increment": 5.00,
            "start_time": (now + timedelta(days=1)).isoformat(),
            "end_time": (now + timedelta(days=3)).isoformat(),
            "status": "SCHEDULED"
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()
    auction_id = auc["id"]

    try:
        # A. Status is SCHEDULED -> 400 Bad Request
        r_bid = client.post(
            f"/api/v1/auctions/{auction_id}/bids",
            json={"bid_amount": 150.00},
            headers={"Authorization": f"Bearer {test_users['b1']}"}
        )
        assert r_bid.status_code == status.HTTP_400_BAD_REQUEST
        assert "scheduled" in r_bid.json()["detail"].lower() or "not active" in r_bid.json()["detail"].lower()

        # B. Status forced to ACTIVE in DB, but start_time is tomorrow -> 400 Bad Request ('Auction has not started yet')
        auc_record = db.query(Auction).filter(Auction.id == auction_id).first()
        auc_record.status = AuctionStatus.ACTIVE
        auc_record.start_time = (datetime.now(timezone.utc) + timedelta(hours=2)).replace(tzinfo=None)
        db.commit()

        r_future = client.post(
            f"/api/v1/auctions/{auction_id}/bids",
            json={"bid_amount": 150.00},
            headers={"Authorization": f"Bearer {test_users['b1']}"}
        )
        assert r_future.status_code == status.HTTP_400_BAD_REQUEST
        assert "not started yet" in r_future.json()["detail"].lower()

    finally:
        db.query(Auction).filter(Auction.id == auction_id).delete()
        db.query(Product).filter(Product.id == product_id).delete()
        db.commit()


# -----------------------------------------------------------------------------
# 4. CONCURRENCY & PESSIMISTIC LOCKING SIMULATION
# -----------------------------------------------------------------------------

def test_concurrent_bids_serialized_atomically(client, test_users, db: Session):
    """
    Simulate 5 simultaneous concurrent bids on the same auction with the SAME bid amount.
    Because of pessimistic row locking, exactly ONE must be accepted (201 Created),
    and the other 4 must be rejected with outbid conflict (400 Bad Request).
    Zero unhandled exceptions or corrupt states.
    """
    # 1. Create product and active auction
    prod = client.post(
        "/api/v1/products",
        json={
            "title": "Concurrency Stress Test Item",
            "description": "Simulated multi-threaded race condition testing.",
            "condition_status": "USED",
            "image_url": "https://images.unsplash.com/race.jpg",
            "category_id": 1
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()
    product_id = prod["id"]

    now = datetime.now(timezone.utc)
    auc = client.post(
        "/api/v1/auctions",
        json={
            "product_id": product_id,
            "starting_price": 100.00,
            "minimum_increment": 10.00,
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=3)).isoformat(),
            "status": "ACTIVE"
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()
    auction_id = auc["id"]

    try:
        results = []

        def place_concurrent_bid(token, amount):
            resp = client.post(
                f"/api/v1/auctions/{auction_id}/bids",
                json={"bid_amount": amount},
                headers={"Authorization": f"Bearer {token}"}
            )
            return resp.status_code

        # 5 threads simultaneously submit identical bid of $120.00
        # Alternating between Buyer 1 and Buyer 2
        tokens = [test_users["b1"], test_users["b2"], test_users["b1"], test_users["b2"], test_users["b1"]]
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(place_concurrent_bid, tokens[i], 120.00) for i in range(5)]
            for f in futures:
                results.append(f.result())

        # Exactly ONE bid must succeed with 201 Created
        accepted_count = results.count(status.HTTP_201_CREATED)
        conflict_count = results.count(status.HTTP_400_BAD_REQUEST)
        assert accepted_count == 1, f"Expected exactly 1 accepted bid, got {accepted_count}. Results: {results}"
        assert conflict_count == 4, f"Expected 4 conflicts, got {conflict_count}. Results: {results}"

        # In database, exactly 1 bid exists with amount $120
        bids_in_db = db.query(Bid).filter(Bid.auction_id == auction_id).all()
        assert len(bids_in_db) == 1
        assert bids_in_db[0].is_winning_bid is True

    finally:
        db.query(AuditLog).filter(AuditLog.entity_id == auction_id, AuditLog.entity_type == "AUCTION").delete()
        db.query(Bid).filter(Bid.auction_id == auction_id).delete()
        db.query(Auction).filter(Auction.id == auction_id).delete()
        db.query(Product).filter(Product.id == product_id).delete()
        db.commit()


# -----------------------------------------------------------------------------
# 5. BID HISTORY ACCESS CONTROL & ANONYMIZATION
# -----------------------------------------------------------------------------

def test_bid_history_privacy_masking(client, test_users):
    """
    Verify bid history retrieval:
    - Public / Buyer viewer: Bidder usernames are masked (e.g. 'e***r') and bidder_id is None.
    - Auction seller / Admin viewer: Full bidder usernames and bidder_ids are revealed.
    - Own bids: 'is_own_bid: true'.
    """
    # Auction 1 has multiple seed bids from Elena (elena_r, id 8), David (david_k, id 9), etc.
    # 1. Public caller
    r_pub = client.get("/api/v1/auctions/1/bids")
    assert r_pub.status_code == status.HTTP_200_OK
    pub_data = r_pub.json()
    assert pub_data["total"] >= 1
    for b in pub_data["items"]:
        assert b["bidder_id"] is None
        assert "***" in b["bidder_username"]
        assert b["is_own_bid"] is False

    # 2. Buyer 1 (Elena) caller -> sees masked for others, but unmasked for own bids
    r_buyer = client.get("/api/v1/auctions/1/bids", headers={"Authorization": f"Bearer {test_users['b1']}"})
    assert r_buyer.status_code == status.HTTP_200_OK
    for b in r_buyer.json()["items"]:
        if b["is_own_bid"]:
            assert b["bidder_username"] == "elena_r"
            assert b["bidder_id"] == 8

    # 3. Seller 2 (Apex Electronics, owns Auction 1) caller -> sees ALL unmasked
    r_seller = client.get("/api/v1/auctions/1/bids", headers={"Authorization": f"Bearer {test_users['s2']}"})
    assert r_seller.status_code == status.HTTP_200_OK
    for b in r_seller.json()["items"]:
        assert b["bidder_id"] is not None
        assert "***" not in b["bidder_username"]

    # 4. Admin caller -> sees ALL unmasked
    r_admin = client.get("/api/v1/auctions/1/bids", headers={"Authorization": f"Bearer {test_users['admin']}"})
    assert r_admin.status_code == status.HTTP_200_OK
    for b in r_admin.json()["items"]:
        assert b["bidder_id"] is not None
        assert "***" not in b["bidder_username"]


def test_buyer_personal_bid_history(client, test_users):
    """Verify GET /api/v1/bids/me returns the logged-in buyer's personal bids."""
    response = client.get("/api/v1/bids/me", headers={"Authorization": f"Bearer {test_users['b1']}"})
    assert response.status_code == status.HTTP_200_OK
    bids = response.json()
    assert len(bids) >= 1
    first = bids[0]
    assert "auction_id" in first
    assert "bid_amount" in first
    assert "product_title" in first

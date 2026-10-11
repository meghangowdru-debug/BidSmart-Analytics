"""
BidSmart Analytics — Auction Closing, Winner Settlement & Notifications Test Suite (Phase 7)
Tests:
1. Zero-Bid Auction Resolution (UNSOLD, no winner, seller notification, audit log)
2. Reserve-Met Settlement (COMPLETED, winner declared, demo transaction created, notifications to winner/seller/outbid)
3. Reserve-Not-Met Settlement (RESERVE_NOT_MET, no winner, no transaction created, demote bids, notification)
4. Idempotency & Repeated Closing (Duplicate settlements and transactions strictly prevented)
5. Premature Close Protection & Admin Force-Close Privilege
6. Batch Expired Auction Closing (/api/v1/auctions/close-expired)
7. Concurrent Closing Pessimistic Row-Locking Simulation
8. Outbid In-App Notification Triggering During Real-Time Bidding
9. In-App Notification Management Lifecycle (list, unread-count, mark-read, mark-all-read, user isolation)
10. Strict RBAC & Ownership Enforcement on Closing Endpoints
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi import status
from sqlalchemy.orm import Session
from app.models.auction import Auction, AuctionStatus
from app.models.product import Product
from app.models.user import User
from app.models.bid import Bid
from app.models.transaction import Transaction, PaymentStatus
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.db.session import SessionLocal
from app.services.auction_closing import close_single_auction


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
# 1. ZERO-BID AUCTION RESOLUTION (UNSOLD) & IDEMPOTENCY
# -----------------------------------------------------------------------------

def test_zero_bid_auction_closing_unsold(client, test_users, db: Session):
    """
    Verify that an expired auction with 0 bids transitions to UNSOLD:
    - winner_id is None
    - final_price is None
    - Seller receives an AUCTION_ENDED notification
    - Repeated closing returns already_closed=True with no side-effects
    """
    # 1. Create product and auction
    prod = client.post(
        "/api/v1/products",
        json={
            "title": "Phase 7 Zero-Bid Vintage Vase",
            "description": "Vase destined to receive no bids for testing unsold status.",
            "condition_status": "VINTAGE",
            "image_url": "https://images.unsplash.com/vase.jpg",
            "category_id": 3
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()

    now = datetime.now(timezone.utc)
    auc = client.post(
        "/api/v1/auctions",
        json={
            "product_id": prod["id"],
            "starting_price": 300.00,
            "minimum_increment": 20.00,
            "start_time": (now - timedelta(hours=3)).isoformat(),
            "end_time": (now - timedelta(minutes=10)).isoformat(),  # Already expired
            "status": "ACTIVE"
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()
    auction_id = auc["id"]

    # 2. Seller closes auction
    close_res = client.post(
        f"/api/v1/auctions/{auction_id}/close",
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    )
    assert close_res.status_code == status.HTTP_200_OK, close_res.text
    data = close_res.json()
    assert data["auction_id"] == auction_id
    assert data["status"] == "UNSOLD"
    assert data["winner_id"] is None
    assert data["final_price"] is None
    assert data["already_closed"] is False
    assert data["transaction_id"] is None
    assert "zero bids received" in data["message"].lower()

    # 3. DB Verifications
    db_auc = db.query(Auction).filter(Auction.id == auction_id).first()
    assert db_auc.status == AuctionStatus.UNSOLD
    assert db_auc.winner_id is None

    # Seller notification verification
    seller_notif = db.query(Notification).filter(
        Notification.user_id == 3,
        Notification.type == "AUCTION_ENDED",
        Notification.title.like("%Unsold%")
    ).order_by(Notification.id.desc()).first()
    assert seller_notif is not None
    assert "without any bids" in seller_notif.message

    # Audit log verification
    audit = db.query(AuditLog).filter(
        AuditLog.entity_type == "AUCTION",
        AuditLog.entity_id == auction_id,
        AuditLog.action == "AUCTION_CLOSED_UNSOLD"
    ).first()
    assert audit is not None

    # 4. Idempotency verification: calling close again
    repeat_res = client.post(
        f"/api/v1/auctions/{auction_id}/close",
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    )
    assert repeat_res.status_code == status.HTTP_200_OK
    repeat_data = repeat_res.json()
    assert repeat_data["already_closed"] is True
    assert repeat_data["status"] == "UNSOLD"

    # Verify no second audit log was created
    audit_count = db.query(AuditLog).filter(
        AuditLog.entity_type == "AUCTION",
        AuditLog.entity_id == auction_id,
        AuditLog.action == "AUCTION_CLOSED_UNSOLD"
    ).count()
    assert audit_count == 1


# -----------------------------------------------------------------------------
# 2. RESERVE MET SETTLEMENT (COMPLETED) & DEMO TRANSACTION
# -----------------------------------------------------------------------------

def test_reserve_met_auction_closing_completed(client, test_users, db: Session):
    """
    Verify settlement when reserve price is met:
    - Status transitions to COMPLETED
    - winner_id and final_price set to highest bidder and bid amount
    - Winning bid marked WON, losing bid marked LOST
    - Simulated demo Transaction record inserted
    - In-app notifications dispatched to winner (AUCTION_WON), seller (AUCTION_ENDED), and outbid loser
    - Idempotent repeated closing strictly prevents duplicate transactions
    """
    # 1. Seller 1 creates product and auction with reserve_price
    prod = client.post(
        "/api/v1/products",
        json={
            "title": "Phase 7 Reserve Met Gold Coin",
            "description": "Rare gold coin with met reserve price.",
            "condition_status": "LIKE_NEW",
            "image_url": "https://images.unsplash.com/coin.jpg",
            "category_id": 3
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()

    now = datetime.now(timezone.utc)
    auc = client.post(
        "/api/v1/auctions",
        json={
            "product_id": prod["id"],
            "starting_price": 100.00,
            "reserve_price": 200.00,
            "minimum_increment": 10.00,
            "start_time": (now - timedelta(hours=2)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "status": "ACTIVE"
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()
    auction_id = auc["id"]

    # 2. Buyer 1 (elena_r, id: 8) bids 150.00
    b1_res = client.post(
        f"/api/v1/auctions/{auction_id}/bids",
        json={"bid_amount": 150.00},
        headers={"Authorization": f"Bearer {test_users['b1']}"}
    )
    assert b1_res.status_code == status.HTTP_201_CREATED

    # 3. Buyer 2 (david_k, id: 9) bids 220.00 (meets reserve)
    b2_res = client.post(
        f"/api/v1/auctions/{auction_id}/bids",
        json={"bid_amount": 220.00},
        headers={"Authorization": f"Bearer {test_users['b2']}"}
    )
    assert b2_res.status_code == status.HTTP_201_CREATED
    winning_bid_id = b2_res.json()["id"]

    # 4. Fast-forward auction end_time to the past
    db_auc = db.query(Auction).filter(Auction.id == auction_id).first()
    db_auc.end_time = now - timedelta(minutes=5)
    db.commit()

    # 5. Seller closes the auction
    close_res = client.post(
        f"/api/v1/auctions/{auction_id}/close",
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    )
    assert close_res.status_code == status.HTTP_200_OK, close_res.text
    data = close_res.json()
    assert data["status"] == "COMPLETED"
    assert data["winner_id"] == 9  # david_k
    assert float(data["final_price"]) == 220.00
    assert data["already_closed"] is False
    assert data["transaction_id"] is not None
    assert "successfully closed" in data["message"] or "settled successfully" in data["message"]

    # 6. Verify Database State
    db.refresh(db_auc)
    assert db_auc.status == AuctionStatus.COMPLETED
    assert db_auc.winner_id == 9
    assert float(db_auc.current_highest_bid) == 220.00

    # Verify Bids status
    bids = db.query(Bid).filter(Bid.auction_id == auction_id).order_by(Bid.id.asc()).all()
    assert len(bids) == 2
    assert bids[0].is_winning_bid is False
    assert bids[1].is_winning_bid is True
    assert bids[1].id == winning_bid_id

    # Verify Demo Transaction Record
    tx = db.query(Transaction).filter(Transaction.auction_id == auction_id).first()
    assert tx is not None
    assert tx.id == data["transaction_id"]
    assert tx.buyer_id == 9
    assert tx.seller_id == 3
    assert float(tx.amount) == 220.00
    assert tx.settlement_type.value == "SIMULATED_DEMO"
    assert tx.payment_status.value == "SETTLEMENT_PENDING_DEMO"
    assert tx.payment_reference.startswith(f"TX-DEMO-{auction_id}-")

    # Verify Notifications
    # Winner notification (david_k, id 9)
    winner_notif = db.query(Notification).filter(
        Notification.user_id == 9,
        Notification.type == "AUCTION_WON"
    ).order_by(Notification.id.desc()).first()
    assert winner_notif is not None
    assert "You won" in winner_notif.message

    # Seller notification (vance_estates, id 3)
    seller_notif = db.query(Notification).filter(
        Notification.user_id == 3,
        Notification.type == "AUCTION_ENDED"
    ).order_by(Notification.id.desc()).first()
    assert seller_notif is not None
    assert "$220.00" in seller_notif.message

    # Outbid / Lost notification for Elena (id 8)
    elena_notif = db.query(Notification).filter(
        Notification.user_id == 8,
        Notification.type == "OUTBID"
    ).order_by(Notification.id.desc()).first()
    assert elena_notif is not None

    # 7. Idempotency Check: Calling close again must not create another transaction
    repeat_res = client.post(
        f"/api/v1/auctions/{auction_id}/close",
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    )
    assert repeat_res.status_code == status.HTTP_200_OK
    repeat_data = repeat_res.json()
    assert repeat_data["already_closed"] is True
    assert repeat_data["transaction_id"] == tx.id

    # Confirm exactly ONE transaction exists in DB
    tx_count = db.query(Transaction).filter(Transaction.auction_id == auction_id).count()
    assert tx_count == 1


# -----------------------------------------------------------------------------
# 3. RESERVE NOT MET RESOLUTION
# -----------------------------------------------------------------------------

def test_reserve_not_met_auction_closing(client, test_users, db: Session):
    """
    Verify that an auction with bids failing to reach reserve_price transitions to RESERVE_NOT_MET:
    - Status transitions to RESERVE_NOT_MET
    - winner_id is None, final_price is None
    - All bids transitioned to LOST
    - No Transaction record is created
    - RESERVE_NOT_MET notifications sent to seller and bidders
    """
    # 1. Create product and auction with reserve_price = 1000.00
    prod = client.post(
        "/api/v1/products",
        json={
            "title": "Phase 7 Reserve Not Met Artwork",
            "description": "High reserve painting that won't reach reserve threshold.",
            "condition_status": "NEW",
            "image_url": "https://images.unsplash.com/art.jpg",
            "category_id": 3
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()

    now = datetime.now(timezone.utc)
    auc = client.post(
        "/api/v1/auctions",
        json={
            "product_id": prod["id"],
            "starting_price": 200.00,
            "reserve_price": 1000.00,
            "minimum_increment": 50.00,
            "start_time": (now - timedelta(hours=2)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "status": "ACTIVE"
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()
    auction_id = auc["id"]

    # 2. Place bid of 300.00 (below reserve of 1000.00)
    b_res = client.post(
        f"/api/v1/auctions/{auction_id}/bids",
        json={"bid_amount": 300.00},
        headers={"Authorization": f"Bearer {test_users['b1']}"}
    )
    assert b_res.status_code == status.HTTP_201_CREATED

    # 3. Fast-forward auction to expired
    db_auc = db.query(Auction).filter(Auction.id == auction_id).first()
    db_auc.end_time = now - timedelta(minutes=5)
    db.commit()

    # 4. Close auction
    close_res = client.post(
        f"/api/v1/auctions/{auction_id}/close",
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    )
    assert close_res.status_code == status.HTTP_200_OK
    data = close_res.json()
    assert data["status"] == "RESERVE_NOT_MET"
    assert data["winner_id"] is None
    assert data["final_price"] is None
    assert data["already_closed"] is False
    assert data["transaction_id"] is None
    assert "reserve" in data["message"].lower()

    # 5. Database assertions
    db.refresh(db_auc)
    assert db_auc.status == AuctionStatus.RESERVE_NOT_MET
    assert db_auc.winner_id is None

    # Bid marked not winning
    bid = db.query(Bid).filter(Bid.auction_id == auction_id).first()
    assert bid.is_winning_bid is False

    # Zero transactions created
    tx = db.query(Transaction).filter(Transaction.auction_id == auction_id).first()
    assert tx is None

    # Seller notification
    seller_notif = db.query(Notification).filter(
        Notification.user_id == 3,
        Notification.type == "AUCTION_ENDED",
        Notification.title.like("%Reserve%")
    ).order_by(Notification.id.desc()).first()
    assert seller_notif is not None
    assert "reserve price of $1000.00" in seller_notif.message


# -----------------------------------------------------------------------------
# 4. PREMATURE CLOSE PROTECTION & ADMIN FORCE-CLOSE PRIVILEGE
# -----------------------------------------------------------------------------

def test_premature_closing_and_admin_force(client, test_users, db: Session):
    """
    Verify:
    1. Calling close on an ongoing auction before deadline returns 400 Bad Request.
    2. Non-admin seller cannot use force=true (403 Forbidden).
    3. Admin caller CAN force close before deadline.
    """
    # 1. Create auction ending 4 hours in the future
    prod = client.post(
        "/api/v1/products",
        json={
            "title": "Phase 7 Premature Close Item",
            "description": "Item still actively running.",
            "condition_status": "NEW",
            "image_url": "https://images.unsplash.com/future.jpg",
            "category_id": 3
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()

    now = datetime.now(timezone.utc)
    auc = client.post(
        "/api/v1/auctions",
        json={
            "product_id": prod["id"],
            "starting_price": 50.00,
            "minimum_increment": 5.00,
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=4)).isoformat(),
            "status": "ACTIVE"
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()
    auction_id = auc["id"]

    # 2. Seller attempts normal close before deadline -> 400
    res_seller = client.post(
        f"/api/v1/auctions/{auction_id}/close",
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    )
    assert res_seller.status_code == status.HTTP_400_BAD_REQUEST
    assert "Auction deadline has not passed yet" in res_seller.text

    # 3. Seller attempts force close -> 403 Forbidden
    res_seller_force = client.post(
        f"/api/v1/auctions/{auction_id}/close?force=true",
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    )
    assert res_seller_force.status_code == status.HTTP_403_FORBIDDEN
    assert "Only administrators can force close" in res_seller_force.text

    # 4. Admin force closes -> 200 OK
    res_admin_force = client.post(
        f"/api/v1/auctions/{auction_id}/close?force=true",
        headers={"Authorization": f"Bearer {test_users['admin']}"}
    )
    assert res_admin_force.status_code == status.HTTP_200_OK
    assert res_admin_force.json()["status"] == "UNSOLD"
    assert res_admin_force.json()["already_closed"] is False


# -----------------------------------------------------------------------------
# 5. BATCH EXPIRED AUCTIONS CLOSING (/close-expired)
# -----------------------------------------------------------------------------

def test_batch_close_expired_auctions(client, test_users, db: Session):
    """
    Verify batch closing endpoint sweeps all expired auctions:
    - Identifies auctions with end_time <= now and status == ACTIVE
    - Settles them correctly (UNSOLD, COMPLETED, RESERVE_NOT_MET)
    - Ignores future auctions and already closed auctions
    - Returns comprehensive summary statistics
    """
    now = datetime.now(timezone.utc)

    # 1. Create Auction A (Expired, 0 bids -> UNSOLD)
    prod_a = client.post(
        "/api/v1/products",
        json={"title": "Batch Test Item A", "description": "Detailed description for batch item A.", "condition_status": "NEW", "image_url": "https://images.unsplash.com/item_a.jpg", "category_id": 3},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()
    auc_a = client.post(
        "/api/v1/auctions",
        json={"product_id": prod_a["id"], "starting_price": 50.00, "start_time": (now - timedelta(hours=3)).isoformat(), "end_time": (now - timedelta(minutes=10)).isoformat(), "status": "ACTIVE"},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()["id"]

    # 2. Create Auction B (Expired, Met Reserve -> COMPLETED)
    prod_b = client.post(
        "/api/v1/products",
        json={"title": "Batch Test Item B", "description": "Detailed description for batch item B.", "condition_status": "NEW", "image_url": "https://images.unsplash.com/item_b.jpg", "category_id": 3},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()
    auc_b = client.post(
        "/api/v1/auctions",
        json={"product_id": prod_b["id"], "starting_price": 50.00, "reserve_price": 80.00, "start_time": (now - timedelta(hours=3)).isoformat(), "end_time": (now + timedelta(hours=1)).isoformat(), "status": "ACTIVE"},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()["id"]
    # Place bid
    client.post(f"/api/v1/auctions/{auc_b}/bids", json={"bid_amount": 100.00}, headers={"Authorization": f"Bearer {test_users['b1']}"})
    # Fast forward to past
    db_auc_b = db.query(Auction).filter(Auction.id == auc_b).first()
    db_auc_b.end_time = now - timedelta(minutes=5)
    db.commit()

    # 3. Create Auction C (Active in future -> Must NOT be closed)
    prod_c = client.post(
        "/api/v1/products",
        json={"title": "Batch Test Item C Future", "description": "Detailed description for batch item C.", "condition_status": "NEW", "image_url": "https://images.unsplash.com/item_c.jpg", "category_id": 3},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()
    auc_c = client.post(
        "/api/v1/auctions",
        json={"product_id": prod_c["id"], "starting_price": 50.00, "start_time": (now - timedelta(hours=1)).isoformat(), "end_time": (now + timedelta(hours=5)).isoformat(), "status": "ACTIVE"},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()["id"]

    # 4. Run batch close endpoint
    batch_res = client.post(
        "/api/v1/auctions/close-expired",
        headers={"Authorization": f"Bearer {test_users['admin']}"}
    )
    assert batch_res.status_code == status.HTTP_200_OK
    batch_data = batch_res.json()
    assert batch_data["processed_count"] >= 2
    assert batch_data["completed_count"] >= 1
    assert batch_data["unsold_count"] >= 1

    # Verify Auction C remains ACTIVE
    db_auc_c = db.query(Auction).filter(Auction.id == auc_c).first()
    assert db_auc_c.status == AuctionStatus.ACTIVE


# -----------------------------------------------------------------------------
# 6. CONCURRENT CLOSING PESSIMISTIC ROW-LOCKING
# -----------------------------------------------------------------------------

def test_concurrent_auction_closing(client, test_users, db: Session):
    """
    Test concurrency safety:
    Spawn multiple threads that simultaneously attempt to close the same expired auction.
    Because of pessimistic row-locking (`SELECT ... FOR UPDATE`), exactly ONE thread
    performs the state transition and creates the transaction.
    All subsequent threads detect `already_closed == True`.
    """
    now = datetime.now(timezone.utc)
    prod = client.post(
        "/api/v1/products",
        json={"title": "Concurrent Closing Test Item", "description": "Pessimistic lock race test", "condition_status": "NEW", "image_url": "https://images.unsplash.com/item_concurrent.jpg", "category_id": 3},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()

    auc = client.post(
        "/api/v1/auctions",
        json={"product_id": prod["id"], "starting_price": 50.00, "start_time": (now - timedelta(hours=2)).isoformat(), "end_time": (now + timedelta(hours=1)).isoformat(), "status": "ACTIVE"},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()["id"]

    # Place bid to make it eligible for completion
    client.post(f"/api/v1/auctions/{auc}/bids", json={"bid_amount": 75.00}, headers={"Authorization": f"Bearer {test_users['b1']}"})

    # Fast forward to expired
    db_auc = db.query(Auction).filter(Auction.id == auc).first()
    db_auc.end_time = now - timedelta(minutes=5)
    db.commit()

    results = []

    def run_close():
        thread_db = SessionLocal()
        try:
            res = close_single_auction(db=thread_db, auction_id=auc, closing_user_id=1, force_close=False)
            results.append(res)
        finally:
            thread_db.close()

    # Launch 6 concurrent threads
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(run_close) for _ in range(6)]
        for f in futures:
            f.result()

    # Verification:
    # Exactly one result must have already_closed == False
    newly_closed = [r for r in results if not r.already_closed]
    already_closed = [r for r in results if r.already_closed]

    assert len(newly_closed) == 1, f"Expected 1 newly closed, got {len(newly_closed)}"
    assert len(already_closed) == 5, f"Expected 5 already closed, got {len(already_closed)}"

    # Exactly one transaction in database
    tx_count = db.query(Transaction).filter(Transaction.auction_id == auc).count()
    assert tx_count == 1


# -----------------------------------------------------------------------------
# 7. OUTBID NOTIFICATION TRIGGERING DURING REAL-TIME BIDDING
# -----------------------------------------------------------------------------

def test_outbid_notification_dispatch(client, test_users, db: Session):
    """
    Verify that placing a higher bid triggers an OUTBID in-app notification to the displaced winning bidder.
    """
    now = datetime.now(timezone.utc)
    prod = client.post(
        "/api/v1/products",
        json={"title": "Outbid Test Camera", "description": "Outbid alert verification", "condition_status": "NEW", "image_url": "https://images.unsplash.com/item_camera.jpg", "category_id": 3},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()

    auc = client.post(
        "/api/v1/auctions",
        json={"product_id": prod["id"], "starting_price": 100.00, "minimum_increment": 10.00, "start_time": (now - timedelta(hours=1)).isoformat(), "end_time": (now + timedelta(hours=2)).isoformat(), "status": "ACTIVE"},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()["id"]

    # 1. Buyer 1 (elena_r, id: 8) bids 100.00
    b1_res = client.post(
        f"/api/v1/auctions/{auc}/bids",
        json={"bid_amount": 100.00},
        headers={"Authorization": f"Bearer {test_users['b1']}"}
    )
    assert b1_res.status_code == status.HTTP_201_CREATED

    # Clear prior notifications for clean check
    db.query(Notification).filter(Notification.user_id == 8).delete()
    db.commit()

    # 2. Buyer 2 (david_k, id: 9) outbids with 120.00
    b2_res = client.post(
        f"/api/v1/auctions/{auc}/bids",
        json={"bid_amount": 120.00},
        headers={"Authorization": f"Bearer {test_users['b2']}"}
    )
    assert b2_res.status_code == status.HTTP_201_CREATED

    # 3. Check Buyer 1's notifications
    notif = db.query(Notification).filter(
        Notification.user_id == 8,
        Notification.type == "OUTBID"
    ).order_by(Notification.id.desc()).first()

    assert notif is not None
    assert "Outbid" in notif.title
    assert "$120.00" in notif.message
    assert f"/auctions/{auc}" in notif.link_url


# -----------------------------------------------------------------------------
# 8. NOTIFICATION MANAGEMENT LIFECYCLE (LIST, UNREAD-COUNT, MARK READ)
# -----------------------------------------------------------------------------

def test_notification_management_lifecycle(client, test_users, db: Session):
    """
    Verify:
    1. GET /api/v1/notifications lists current user's notifications.
    2. GET /api/v1/notifications/unread-count returns correct count.
    3. PATCH /api/v1/notifications/{id}/read marks individual notification read.
    4. POST /api/v1/notifications/read-all marks all notifications read.
    5. User isolation: Buyer 2 cannot read or modify Buyer 1's notifications.
    """
    # 1. Inject test notifications for Buyer 1 (id: 8)
    n1 = Notification(user_id=8, type="SYSTEM", title="Welcome 1", message="Welcome to BidSmart 1", is_read=False)
    n2 = Notification(user_id=8, type="OUTBID", title="Outbid 2", message="You were outbid 2", is_read=False)
    n3 = Notification(user_id=9, type="SYSTEM", title="David's Notif", message="Private to David", is_read=False)
    db.add_all([n1, n2, n3])
    db.commit()
    db.refresh(n1)
    db.refresh(n2)
    db.refresh(n3)

    # 2. Unread count for Buyer 1
    count_res = client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {test_users['b1']}"}
    )
    assert count_res.status_code == status.HTTP_200_OK
    initial_unread = count_res.json()["unread_count"]
    assert initial_unread >= 2

    # 3. List notifications for Buyer 1
    list_res = client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {test_users['b1']}"}
    )
    assert list_res.status_code == status.HTTP_200_OK
    items = list_res.json()["items"]
    # Check that David's notification is not in Elena's list
    for item in items:
        assert item["title"] != "David's Notif"

    # 4. Mark single notification (n1) as read
    read_res = client.patch(
        f"/api/v1/notifications/{n1.id}/read",
        headers={"Authorization": f"Bearer {test_users['b1']}"}
    )
    assert read_res.status_code == status.HTTP_200_OK
    assert read_res.json()["is_read"] is True

    # Verify unread count decreased by 1
    count_res2 = client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {test_users['b1']}"}
    )
    assert count_res2.json()["unread_count"] == initial_unread - 1

    # 5. User isolation: Buyer 1 attempts to mark David's notification (n3) as read -> 404
    iso_res = client.patch(
        f"/api/v1/notifications/{n3.id}/read",
        headers={"Authorization": f"Bearer {test_users['b1']}"}
    )
    assert iso_res.status_code == status.HTTP_404_NOT_FOUND

    # 6. Mark all as read for Buyer 1
    mark_all_res = client.post(
        "/api/v1/notifications/read-all",
        headers={"Authorization": f"Bearer {test_users['b1']}"}
    )
    assert mark_all_res.status_code == status.HTTP_200_OK
    assert mark_all_res.json()["count"] >= 1

    # Verify unread count is now 0 for Buyer 1
    count_res3 = client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {test_users['b1']}"}
    )
    assert count_res3.json()["unread_count"] == 0

    # Verify David's notification remains unread
    db.refresh(n3)
    assert n3.is_read is False


# -----------------------------------------------------------------------------
# 9. CLOSING RBAC & OWNERSHIP ENFORCEMENT
# -----------------------------------------------------------------------------

def test_closing_rbac_and_ownership(client, test_users, db: Session):
    """
    Verify closing endpoint permissions:
    1. Unauthenticated request -> 401 Unauthorized
    2. Buyer request -> 403 Forbidden
    3. Other Seller (not owner) -> 403 Forbidden
    4. Admin on any seller's auction -> Permitted (200 OK)
    """
    now = datetime.now(timezone.utc)
    # Seller 1 creates auction
    prod = client.post(
        "/api/v1/products",
        json={"title": "RBAC Closing Test Item", "description": "Item for testing ownership on close", "condition_status": "NEW", "image_url": "https://images.unsplash.com/item_rbac.jpg", "category_id": 3},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()

    auc = client.post(
        "/api/v1/auctions",
        json={"product_id": prod["id"], "starting_price": 50.00, "start_time": (now - timedelta(hours=2)).isoformat(), "end_time": (now - timedelta(minutes=5)).isoformat(), "status": "ACTIVE"},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()["id"]

    # 1. Unauthenticated -> 401
    res_unauth = client.post(f"/api/v1/auctions/{auc}/close")
    assert res_unauth.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Buyer (b1) -> 403 Forbidden
    res_buyer = client.post(
        f"/api/v1/auctions/{auc}/close",
        headers={"Authorization": f"Bearer {test_users['b1']}"}
    )
    assert res_buyer.status_code == status.HTTP_403_FORBIDDEN

    # 3. Different Seller (s2: apex_electronics) -> 403 Forbidden
    res_s2 = client.post(
        f"/api/v1/auctions/{auc}/close",
        headers={"Authorization": f"Bearer {test_users['s2']}"}
    )
    assert res_s2.status_code == status.HTTP_403_FORBIDDEN
    assert "You do not own this auction listing" in res_s2.text

    # 4. Admin (admin_sarah) -> 200 OK
    res_admin = client.post(
        f"/api/v1/auctions/{auc}/close",
        headers={"Authorization": f"Bearer {test_users['admin']}"}
    )
    assert res_admin.status_code == status.HTTP_200_OK
    assert res_admin.json()["status"] == "UNSOLD"


# -----------------------------------------------------------------------------
# 10. CROSS-SELLER BATCH ISOLATION & RESERVE PRICE PRIVACY VERIFICATION
# -----------------------------------------------------------------------------

def test_seller_batch_close_strictly_scoped_to_own_inventory(client, test_users, db: Session):
    """
    Verify:
    1. Seller 1 calling POST /api/v1/auctions/close-expired ONLY closes Seller 1's auctions.
    2. Seller 2's expired auctions remain ACTIVE and untouched.
    3. Seller 1 attempting to pass ?seller_id=4 (Seller 2) is rejected with 403 Forbidden.
    4. Admin calling close-expired closes all remaining expired auctions.
    """
    now = datetime.now(timezone.utc)

    # 1. Seller 1 (vance_estates, id 3) creates an expired auction
    p1 = client.post(
        "/api/v1/products",
        json={"title": "Seller 1 Batch Scoping Item", "description": "Item belonging strictly to seller 1.", "condition_status": "NEW", "image_url": "https://images.unsplash.com/s1.jpg", "category_id": 3},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()
    auc1 = client.post(
        "/api/v1/auctions",
        json={"product_id": p1["id"], "starting_price": 50.00, "start_time": (now - timedelta(hours=3)).isoformat(), "end_time": (now - timedelta(minutes=10)).isoformat(), "status": "ACTIVE"},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()["id"]

    # 2. Seller 2 (apex_electronics, id 4) creates an expired auction
    p2 = client.post(
        "/api/v1/products",
        json={"title": "Seller 2 Batch Scoping Item", "description": "Item belonging strictly to seller 2.", "condition_status": "NEW", "image_url": "https://images.unsplash.com/s2.jpg", "category_id": 1},
        headers={"Authorization": f"Bearer {test_users['s2']}"}
    ).json()
    auc2 = client.post(
        "/api/v1/auctions",
        json={"product_id": p2["id"], "starting_price": 100.00, "start_time": (now - timedelta(hours=3)).isoformat(), "end_time": (now - timedelta(minutes=10)).isoformat(), "status": "ACTIVE"},
        headers={"Authorization": f"Bearer {test_users['s2']}"}
    ).json()["id"]

    # 3. Seller 1 attempts to pass ?seller_id=4 -> 403 Forbidden
    cross_res = client.post(
        "/api/v1/auctions/close-expired?seller_id=4",
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    )
    assert cross_res.status_code == status.HTTP_403_FORBIDDEN
    assert "Sellers cannot close other sellers' auctions" in cross_res.text

    # 4. Seller 1 runs standard batch close-expired
    s1_batch_res = client.post(
        "/api/v1/auctions/close-expired",
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    )
    assert s1_batch_res.status_code == status.HTTP_200_OK
    s1_data = s1_batch_res.json()

    # Verify that Seller 1's auction was closed
    db_auc1 = db.query(Auction).filter(Auction.id == auc1).first()
    assert db_auc1.status == AuctionStatus.UNSOLD

    # CRITICAL VERIFICATION: Seller 2's auction MUST REMAIN ACTIVE!
    db_auc2 = db.query(Auction).filter(Auction.id == auc2).first()
    assert db_auc2.status == AuctionStatus.ACTIVE

    # Verify Seller 2's auction is NOT in Seller 1's results
    result_ids = [r["auction_id"] for r in s1_data["results"]]
    assert auc1 in result_ids
    assert auc2 not in result_ids

    # 5. Now Admin closes Seller 2's auction
    admin_batch_res = client.post(
        f"/api/v1/auctions/close-expired?seller_id=4",
        headers={"Authorization": f"Bearer {test_users['admin']}"}
    )
    assert admin_batch_res.status_code == status.HTTP_200_OK

    db.commit()  # Reset transaction snapshot to read latest committed data
    db_auc2 = db.query(Auction).filter(Auction.id == auc2).first()
    assert db_auc2.status == AuctionStatus.UNSOLD


def test_reserve_price_privacy_unauthorized_masking(client, test_users, db: Session):
    """
    Comprehensive verification of reserve price privacy:
    1. GET /api/v1/auctions/{id}:
       - Unauthenticated public: reserve_price is None, reserve_met is None.
       - Buyer (elena_r): reserve_price is None, reserve_met is None.
       - Other Seller (apex_electronics): reserve_price is None, reserve_met is None.
       - Owning Seller (vance_estates): reserve_price is 750.00.
       - Admin (admin_sarah): reserve_price is 750.00.
    2. Notifications:
       - Bidder receives notification when auction ends RESERVE_NOT_MET:
         Verifies private reserve price amount is NOT revealed in bidder's notification.
       - Seller receives notification: contains their own reserve price.
    """
    now = datetime.now(timezone.utc)
    # 1. Seller 1 creates item with secret reserve_price = 750.00
    p = client.post(
        "/api/v1/products",
        json={"title": "Reserve Privacy Test Antique", "description": "High value antique with secret reserve.", "condition_status": "VINTAGE", "image_url": "https://images.unsplash.com/antique.jpg", "category_id": 3},
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()

    auc = client.post(
        "/api/v1/auctions",
        json={
            "product_id": p["id"],
            "starting_price": 200.00,
            "reserve_price": 750.00,
            "minimum_increment": 25.00,
            "start_time": (now - timedelta(hours=2)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "status": "ACTIVE"
        },
        headers={"Authorization": f"Bearer {test_users['s1']}"}
    ).json()["id"]

    # Buyer places bid of 300.00 (below reserve of 750.00)
    client.post(f"/api/v1/auctions/{auc}/bids", json={"bid_amount": 300.00}, headers={"Authorization": f"Bearer {test_users['b1']}"})

    # --- Verification of Auction API Privacy Masking ---
    # Public
    r_pub = client.get(f"/api/v1/auctions/{auc}").json()
    assert r_pub["reserve_price"] is None
    assert r_pub["reserve_met"] is None

    # Buyer
    r_buy = client.get(f"/api/v1/auctions/{auc}", headers={"Authorization": f"Bearer {test_users['b1']}"}).json()
    assert r_buy["reserve_price"] is None
    assert r_buy["reserve_met"] is None

    # Other Seller (s2)
    r_s2 = client.get(f"/api/v1/auctions/{auc}", headers={"Authorization": f"Bearer {test_users['s2']}"}).json()
    assert r_s2["reserve_price"] is None
    assert r_s2["reserve_met"] is None

    # Owning Seller (s1)
    r_s1 = client.get(f"/api/v1/auctions/{auc}", headers={"Authorization": f"Bearer {test_users['s1']}"}).json()
    assert float(r_s1["reserve_price"]) == 750.00
    assert r_s1["reserve_met"] is False

    # Admin
    r_adm = client.get(f"/api/v1/auctions/{auc}", headers={"Authorization": f"Bearer {test_users['admin']}"}).json()
    assert float(r_adm["reserve_price"]) == 750.00
    assert r_adm["reserve_met"] is False

    # --- Close Auction and Verify Notifications Privacy ---
    db_auc = db.query(Auction).filter(Auction.id == auc).first()
    db_auc.end_time = now - timedelta(minutes=5)
    db.commit()

    close_res = client.post(f"/api/v1/auctions/{auc}/close", headers={"Authorization": f"Bearer {test_users['s1']}"})
    assert close_res.status_code == status.HTTP_200_OK
    assert float(close_res.json()["reserve_price"]) == 750.00
    assert close_res.json()["reserve_met"] is False

    # Check that close_single_auction called without privileged user masks reserve_price
    thread_db = SessionLocal()
    try:
        unprivileged_res = close_single_auction(db=thread_db, auction_id=auc, closing_user_id=None)
        assert unprivileged_res.reserve_price is None
        assert unprivileged_res.reserve_met is None
    finally:
        thread_db.close()

    # Check Bidder notification: MUST NOT contain "750" or "$750"
    bidder_notif = db.query(Notification).filter(
        Notification.user_id == 8,  # Elena
        Notification.type == "AUCTION_ENDED"
    ).order_by(Notification.id.desc()).first()

    assert bidder_notif is not None
    assert "750" not in bidder_notif.message
    assert "$750" not in bidder_notif.message
    assert "seller's reserve price was not met" in bidder_notif.message

    # Check Seller notification: CAN contain their own reserve price
    seller_notif = db.query(Notification).filter(
        Notification.user_id == 3,  # Vance Estates
        Notification.type == "AUCTION_ENDED"
    ).order_by(Notification.id.desc()).first()

    assert seller_notif is not None
    assert "$750.00" in seller_notif.message


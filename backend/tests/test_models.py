"""
Integration Tests for SQLAlchemy ORM Models & Schema Mapping (Phase 3)
Verifies models map to existing Phase 2 database without schema mutations.
"""

from sqlalchemy import text
from app.models import (
    Role, User, Category, Product, Auction, Bid, 
    Transaction, Watchlist, Notification, AuditLog
)


def test_seed_data_counts(db):
    """Verify all 10 tables are mapped and contain the expected seed data counts."""
    # Clean up ephemeral test artifacts created by other test suites
    db.execute(text('DELETE FROM transactions WHERE auction_id > 40 OR id > 18'))
    db.execute(text('DELETE FROM bids WHERE auction_id > 40'))
    db.execute(text('DELETE FROM watchlist WHERE auction_id > 40'))
    db.execute(text('DELETE FROM audit_logs WHERE entity_type = "AUCTION" AND entity_id > 40'))
    db.execute(text('DELETE FROM auctions WHERE id > 40'))
    db.execute(text('DELETE FROM products WHERE id > 40'))
    db.commit()

    assert db.query(Role).count() == 3
    assert db.query(User).count() == 32
    assert db.query(Category).count() == 6
    assert db.query(Product).count() == 40
    assert db.query(Auction).count() == 40
    assert db.query(Bid).count() >= 350
    assert db.query(Transaction).count() == 18
    assert db.query(Watchlist).count() >= 35
    assert db.query(Notification).count() >= 13
    assert db.query(AuditLog).count() >= 8


def test_user_role_relationship(db):
    """Verify User -> Role relationship traversal."""
    admin_user = db.query(User).filter(User.username == "admin_sarah").first()
    assert admin_user is not None
    assert admin_user.role is not None
    assert admin_user.role.name == "ADMIN"

    seller_user = db.query(User).filter(User.username == "vance_estates").first()
    assert seller_user is not None
    assert seller_user.role.name == "SELLER"


def test_auction_product_category_relationship(db):
    """Verify Auction -> Product -> Category relationship traversal."""
    auction = db.query(Auction).filter(Auction.id == 1).first()
    assert auction is not None
    assert auction.product is not None
    assert "Macintosh" in auction.product.title
    assert auction.product.category.name == "Electronics & Computing"
    assert auction.product.seller.username == "apex_electronics"


def test_bid_auction_relationship(db):
    """Verify Bid -> Auction and Bid -> Bidder relationships."""
    first_bid = db.query(Bid).filter(Bid.auction_id == 1).first()
    assert first_bid is not None
    assert first_bid.auction.id == 1
    assert first_bid.bidder is not None
    assert first_bid.bid_amount > 0


def test_completed_auction_transactions(db):
    """Verify completed auctions have matching simulated demo transactions."""
    completed_auctions = db.query(Auction).filter(
        Auction.id <= 40,
        Auction.status == "COMPLETED"
    ).all()
    assert len(completed_auctions) == 18

    for auc in completed_auctions:
        assert auc.transaction is not None
        assert auc.transaction.settlement_type.value == "SIMULATED_DEMO"
        assert auc.transaction.amount == auc.current_highest_bid
        assert auc.transaction.buyer_id == auc.winner_id


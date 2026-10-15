from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.api.deps import get_current_user
from app.api.v1.endpoints import analytics, payments, seller_payment_setup
from app.models.auction import Auction, AuctionStatus
from app.models.bid import Bid
from app.models.product import Product
from app.models.transaction import PaymentAttempt, PaymentAttemptStatus, Transaction
from app.models.user import User, UserStatus
from app.services.auction_closing import close_single_auction


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_seller_with_bid_cannot_move_auction_to_draft_or_change_price(
    client, auth_tokens
):
    seller_headers = _auth(auth_tokens["s2"])

    draft_response = client.put(
        "/api/v1/auctions/1",
        json={"status": "DRAFT"},
        headers=seller_headers,
    )
    assert draft_response.status_code == 400

    price_response = client.put(
        "/api/v1/auctions/1",
        json={"starting_price": "600.00"},
        headers=seller_headers,
    )
    assert price_response.status_code == 400


def test_cancelled_auction_with_bids_cannot_be_deleted_with_product(
    client, auth_tokens, db
):
    auction = db.query(Auction).filter(Auction.id == 1).one()
    auction.status = AuctionStatus.CANCELLED
    db.commit()

    response = client.delete(
        "/api/v1/products/1",
        headers=_auth(auth_tokens["s2"]),
    )

    assert response.status_code == 400
    assert db.get(Product, 1) is not None
    assert db.get(Auction, 1) is not None
    assert db.query(Bid).filter(Bid.auction_id == 1).count() > 0


def test_seller_cannot_force_close_owned_auction_through_service(db):
    with pytest.raises(HTTPException) as exc_info:
        close_single_auction(
            db=db,
            auction_id=15,
            closing_user_id=4,
            force_close=True,
        )

    assert exc_info.value.status_code == 403
    assert db.get(Auction, 15).status == AuctionStatus.SCHEDULED


def test_base_authentication_rejects_suspended_user(db, auth_tokens):
    user = db.get(User, 3)
    user.status = UserStatus.SUSPENDED
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=db, token=auth_tokens["s1"])

    assert exc_info.value.status_code == 403


def test_suspended_owner_is_anonymous_on_public_auction_detail(
    client, auth_tokens, db
):
    user = db.get(User, 3)
    user.status = UserStatus.SUSPENDED
    db.commit()

    response = client.get(
        "/api/v1/auctions/14",
        headers=_auth(auth_tokens["s1"]),
    )

    assert response.status_code == 200
    assert response.json()["reserve_price"] is None


@pytest.mark.parametrize("inconsistency", ["wrong_buyer", "auction_not_completed"])
def test_seller_summary_excludes_inconsistent_completed_payment(
    client, auth_tokens, db, inconsistency
):
    transaction = db.query(Transaction).filter(Transaction.auction_id == 16).one()
    auction = db.query(Auction).filter(Auction.id == 16).one()
    if inconsistency == "wrong_buyer":
        transaction.buyer_id = 8
    else:
        auction.status = AuctionStatus.ACTIVE
    db.add(
        PaymentAttempt(
            transaction_id=transaction.id,
            provider_order_id=f"release-order-{inconsistency}",
            provider_payment_id=f"release-payment-{inconsistency}",
            amount_minor=int(transaction.amount * 100),
            currency="USD",
            status=PaymentAttemptStatus.PAYMENT_COMPLETED,
        )
    )
    db.commit()

    response = client.get(
        "/api/v1/payments/me/seller-transactions",
        headers=_auth(auth_tokens["s2"]),
    )

    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["verified_payment_total"] == "0.00"
    assert summary["completed_settlements"] == "0.00"
    assert summary["total_sales"] == "0.00"


def test_setup_disabled_allows_new_seller_listing_without_profile(
    client, auth_tokens, db, monkeypatch
):
    from app.core.config import settings
    from app.models.seller_payment_profile import SellerPaymentProfile

    monkeypatch.setattr(settings, "ENABLE_SELLER_PAYMENT_SETUP", False)
    monkeypatch.setattr(
        seller_payment_setup.setup_service,
        "require_setup_table",
        lambda _db: pytest.fail("disabled setup must not inspect its database table"),
    )
    db.query(SellerPaymentProfile).filter(
        SellerPaymentProfile.seller_id == 4
    ).delete()
    db.commit()
    headers = _auth(auth_tokens["s2"])

    setup_status = client.get(
        "/api/v1/sellers/me/payment-setup",
        headers=headers,
    )
    assert setup_status.status_code == 200
    assert setup_status.json()["status"] == "DISABLED"
    assert setup_status.json()["required"] is False
    assert setup_status.json()["can_list"] is True

    product_response = client.post(
        "/api/v1/products",
        json={
            "title": "Rollout-disabled seller product",
            "description": "Verifies opt-in seller setup rollout.",
            "category_id": 1,
            "condition_status": "NEW",
            "image_url": "https://example.test/rollout-disabled.jpg",
        },
        headers=headers,
    )
    assert product_response.status_code in {200, 201}
    product_id = product_response.json()["id"]

    start_time = datetime.now(timezone.utc) + timedelta(minutes=1)
    auction_response = client.post(
        "/api/v1/auctions",
        json={
            "product_id": product_id,
            "starting_price": "10.00",
            "minimum_increment": "1.00",
            "start_time": start_time.isoformat(),
            "end_time": (start_time + timedelta(days=2)).isoformat(),
        },
        headers=headers,
    )
    assert auction_response.status_code in {200, 201}

    completion_response = client.post(
        "/api/v1/sellers/me/payment-setup/demo",
        json={"acknowledge_simulated": True},
        headers=headers,
    )
    assert completion_response.status_code == 200
    assert completion_response.json()["status"] == "DISABLED"
    assert db.query(SellerPaymentProfile).filter(
        SellerPaymentProfile.seller_id == 4
    ).count() == 0


def test_payment_schema_availability_check_detects_missing_transactions_table(
    db, monkeypatch
):
    class MissingTransactionsInspector:
        def has_table(self, table_name):
            return table_name == "payment_attempts"

        def get_columns(self, table_name):
            raise AssertionError("must not inspect columns for a missing table")

    monkeypatch.setattr(
        analytics,
        "sqlalchemy_inspect",
        lambda _bind: MissingTransactionsInspector(),
    )

    assert analytics._payment_attempts_available(db) is False


def test_payment_endpoint_returns_503_when_transactions_table_is_missing(
    client, auth_tokens, monkeypatch
):
    class MissingTransactionsInspector:
        def has_table(self, table_name):
            return table_name == "payment_attempts"

        def get_columns(self, table_name):
            raise AssertionError("must not inspect columns for a missing table")

    monkeypatch.setattr(
        payments,
        "sqlalchemy_inspect",
        lambda _bind: MissingTransactionsInspector(),
    )

    response = client.get(
        "/api/v1/payments/me/won-auctions",
        headers=_auth(auth_tokens["b1"]),
    )

    assert response.status_code == 503
    assert "database schema is missing" in response.json()["detail"]

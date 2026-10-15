"""Seller payment setup: status tracking and server-side listing authorization."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.core.config import settings
from app.models.product import Product
from app.models.seller_payment_profile import (
    SellerPaymentProfile,
    SellerPaymentSetupMode,
    SellerPaymentSetupStatus,
)

PRODUCT = {
    "title": "Setup gated product",
    "description": "Created to verify seller payment setup enforcement.",
    "category_id": 1,
    "condition_status": "NEW",
    "image_url": "https://example.test/p.jpg",
}


def _headers(client, username):
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username, "password": "password123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(autouse=True)
def enable_seller_payment_setup():
    previous = settings.ENABLE_SELLER_PAYMENT_SETUP
    settings.ENABLE_SELLER_PAYMENT_SETUP = True
    yield
    settings.ENABLE_SELLER_PAYMENT_SETUP = previous


@pytest.fixture(autouse=True)
def restore_shared_state(db):
    """The test database is shared for the whole session; undo this module's changes."""
    yield
    db.rollback()
    db.info.clear()
    SellerPaymentProfile.__table__.create(bind=db.get_bind(), checkfirst=True)
    db.query(Product).filter(Product.title == PRODUCT["title"]).delete()
    for seller_id in (3, 4):
        if not db.query(SellerPaymentProfile).filter_by(seller_id=seller_id).first():
            db.add(SellerPaymentProfile(
                seller_id=seller_id,
                setup_mode=SellerPaymentSetupMode.DEMO_SIMULATED,
                status=SellerPaymentSetupStatus.DEMO_COMPLETED,
                completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            ))
    db.commit()


@pytest.fixture
def unsetup_seller(client, db):
    """Seller 4 (apex_electronics) with the existing-account state: no profile row."""
    db.query(SellerPaymentProfile).filter(SellerPaymentProfile.seller_id == 4).delete()
    db.commit()
    return _headers(client, "apex_electronics")


def test_status_not_started_for_seller_without_profile(client, unsetup_seller):
    response = client.get("/api/v1/sellers/me/payment-setup", headers=unsetup_seller)

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "NOT_STARTED"
    assert body["required"] is True and body["can_list"] is False
    assert body["simulated"] is True
    assert body["payouts_enabled"] is False
    assert body["provider_onboarding_available"] is False
    assert "simulated" in body["message"].lower()


def test_unsetup_seller_cannot_create_product_or_auction(client, unsetup_seller):
    product = client.post("/api/v1/products", json=PRODUCT, headers=unsetup_seller)
    auction = client.post(
        "/api/v1/auctions",
        json={
            "product_id": 2,
            "starting_price": "10.00",
            "minimum_increment": "1.00",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        },
        headers=unsetup_seller,
    )

    assert product.status_code == 403
    assert "payment setup" in product.json()["detail"].lower()
    assert auction.status_code == 403


def test_completing_demo_setup_unlocks_listing_and_is_idempotent(client, db, unsetup_seller):
    rejected = client.post(
        "/api/v1/sellers/me/payment-setup/demo",
        json={"acknowledge_simulated": False},
        headers=unsetup_seller,
    )
    assert rejected.status_code == 422
    assert db.query(SellerPaymentProfile).filter_by(seller_id=4).count() == 0

    first = client.post(
        "/api/v1/sellers/me/payment-setup/demo",
        json={"acknowledge_simulated": True},
        headers=unsetup_seller,
    )
    second = client.post(
        "/api/v1/sellers/me/payment-setup/demo",
        json={"acknowledge_simulated": True},
        headers=unsetup_seller,
    )

    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == "DEMO_COMPLETED"
    assert first.json()["can_list"] is True
    assert first.json()["payouts_enabled"] is False
    assert db.query(SellerPaymentProfile).filter_by(seller_id=4).count() == 1
    assert client.post("/api/v1/products", json=PRODUCT, headers=unsetup_seller).status_code == 201


def test_integrity_error_during_setup_is_not_reported_as_success(
    client, db, unsetup_seller, monkeypatch
):
    from app.services import seller_payment_setup as setup_service

    def fail_demo_completion(*_args, **_kwargs):
        raise IntegrityError("INSERT", {}, Exception("simulated integrity failure"))

    monkeypatch.setattr(setup_service, "mark_demo_complete", fail_demo_completion)

    with pytest.raises(IntegrityError, match="simulated integrity failure"):
        client.post(
            "/api/v1/sellers/me/payment-setup/demo",
            json={"acknowledge_simulated": True},
            headers=unsetup_seller,
        )

    assert db.query(SellerPaymentProfile).filter_by(seller_id=4).count() == 0


def test_setup_is_per_seller_and_cannot_be_completed_for_another_account(client, db, unsetup_seller):
    client.post(
        "/api/v1/sellers/me/payment-setup/demo",
        json={"acknowledge_simulated": True},
        headers=unsetup_seller,
    )
    db.query(SellerPaymentProfile).filter(SellerPaymentProfile.seller_id == 3).delete()
    db.commit()

    other = _headers(client, "vance_estates")
    assert client.get("/api/v1/sellers/me/payment-setup", headers=other).json()["status"] == "NOT_STARTED"
    assert client.post("/api/v1/products", json=PRODUCT, headers=other).status_code == 403


def test_buyers_and_anonymous_users_cannot_use_setup_endpoints(client):
    buyer = _headers(client, "elena_r")

    assert client.get("/api/v1/sellers/me/payment-setup").status_code == 401
    assert client.get("/api/v1/sellers/me/payment-setup", headers=buyer).status_code == 403
    assert client.post(
        "/api/v1/sellers/me/payment-setup/demo",
        json={"acknowledge_simulated": True},
        headers=buyer,
    ).status_code == 403


def test_admin_is_not_required_to_complete_seller_setup(client):
    admin = _headers(client, "admin_sarah")

    status_body = client.get("/api/v1/sellers/me/payment-setup", headers=admin).json()

    assert status_body["status"] == "NOT_REQUIRED"
    assert status_body["can_list"] is True
    assert client.post("/api/v1/products", json=PRODUCT, headers=admin).status_code == 201


def test_missing_profile_table_fails_closed_with_503_and_login_still_works(client, db):
    db.execute(text("DROP TABLE seller_payment_profiles"))
    db.commit()
    db.info.clear()

    headers = _headers(client, "vance_estates")
    status_response = client.get("/api/v1/sellers/me/payment-setup", headers=headers)
    product = client.post("/api/v1/products", json=PRODUCT, headers=headers)

    assert status_response.status_code == 503
    assert product.status_code == 503
    assert "database schema is missing" in product.json()["detail"]
    assert client.get("/api/v1/products", headers=headers).status_code == 200


def test_existing_seller_data_is_unaffected_by_setup_state(client, unsetup_seller):
    response = client.get("/api/v1/products/seller/me", headers=unsetup_seller)

    assert response.status_code == 200

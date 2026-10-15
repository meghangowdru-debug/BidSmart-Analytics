"""Seller payment setup rules shared by the setup endpoints and listing authorization."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.orm import Session

from app.models.seller_payment_profile import (
    SellerPaymentProfile,
    SellerPaymentSetupMode,
    SellerPaymentSetupStatus,
)
from app.models.user import User

SETUP_REQUIRED_DETAIL = (
    "Seller payment setup is required before you can list products or create "
    "auctions. Complete Payment Setup in your Seller Console."
)
SCHEMA_MISSING_DETAIL = (
    "Seller payment setup is temporarily unavailable because required database "
    "schema is missing. Contact the platform administrator."
)


def _role_name(user: User) -> str:
    return user.role.name.upper() if user.role else ""


def setup_table_available(db: Session) -> bool:
    cached = db.info.get("seller_payment_profiles_available")
    if cached is None:
        cached = sqlalchemy_inspect(db.get_bind()).has_table("seller_payment_profiles")
        db.info["seller_payment_profiles_available"] = cached
    return cached


def require_setup_table(db: Session) -> None:
    if not setup_table_available(db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=SCHEMA_MISSING_DETAIL
        )


def get_profile(db: Session, seller_id: int) -> Optional[SellerPaymentProfile]:
    return (
        db.query(SellerPaymentProfile)
        .filter(SellerPaymentProfile.seller_id == seller_id)
        .first()
    )


def is_setup_complete(db: Session, user: User) -> bool:
    """Administrators are exempt; sellers need a completed profile row."""
    if _role_name(user) != "SELLER":
        return True
    require_setup_table(db)
    profile = get_profile(db, user.id)
    return bool(profile and profile.status == SellerPaymentSetupStatus.DEMO_COMPLETED)


def require_setup_complete(db: Session, user: User) -> None:
    if not is_setup_complete(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SETUP_REQUIRED_DETAIL)


def mark_demo_complete(db: Session, user: User) -> SellerPaymentProfile:
    profile = get_profile(db, user.id)
    if profile is None:
        profile = SellerPaymentProfile(
            seller_id=user.id, setup_mode=SellerPaymentSetupMode.DEMO_SIMULATED
        )
        db.add(profile)
    if profile.status != SellerPaymentSetupStatus.DEMO_COMPLETED:
        profile.status = SellerPaymentSetupStatus.DEMO_COMPLETED
        profile.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    return profile

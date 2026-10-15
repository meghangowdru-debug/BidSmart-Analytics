"""
BidSmart Analytics — Seller payment setup endpoints.

- GET  /api/v1/sellers/me/payment-setup       current setup status
- POST /api/v1/sellers/me/payment-setup/demo  complete the simulated demo setup

Demo setup is an acknowledgement only. It collects no bank details and does not
enable payouts. Verified payment-provider onboarding is not implemented.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_seller
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.seller_payment_setup import SellerPaymentSetupDemoIn, SellerPaymentSetupOut
from app.services import seller_payment_setup as setup_service
from app.models.seller_payment_profile import SellerPaymentSetupStatus

router = APIRouter()

DEMO_NOTICE = (
    "Simulated demo setup. No real bank details are collected and no real payouts are enabled."
)


def _status_out(db: Session, user: User) -> SellerPaymentSetupOut:
    if user.role is None or user.role.name.upper() != "SELLER":
        return SellerPaymentSetupOut(
            status="NOT_REQUIRED",
            required=False,
            can_list=True,
            message="Payment setup applies to seller accounts only.",
        )
    setup_service.require_setup_table(db)
    profile = setup_service.get_profile(db, user.id)
    if profile is None:
        return SellerPaymentSetupOut(
            status="NOT_STARTED",
            required=True,
            can_list=False,
            message=f"Complete Payment Setup to list products and create auctions. {DEMO_NOTICE}",
        )
    completed = profile.status == SellerPaymentSetupStatus.DEMO_COMPLETED
    return SellerPaymentSetupOut(
        status=profile.status.value,
        required=True,
        can_list=completed,
        completed_at=profile.completed_at,
        message=(
            f"Demo payment setup is complete. {DEMO_NOTICE}"
            if completed
            else f"Payment setup is not finished. {DEMO_NOTICE}"
        ),
    )


@router.get("", response_model=SellerPaymentSetupOut, summary="[Seller] Get payment setup status")
def get_payment_setup(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_seller),
):
    return _status_out(db, current_user)


@router.post(
    "/demo",
    response_model=SellerPaymentSetupOut,
    summary="[Seller] Complete the simulated demo payment setup",
)
def complete_demo_payment_setup(
    payload: SellerPaymentSetupDemoIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_seller),
):
    if current_user.role is None or current_user.role.name.upper() != "SELLER":
        return _status_out(db, current_user)
    if not payload.acknowledge_simulated:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must acknowledge that this is a simulated demo setup with no real payouts.",
        )
    setup_service.require_setup_table(db)
    already_complete = setup_service.is_setup_complete(db, current_user)
    try:
        setup_service.mark_demo_complete(db, current_user)
        if not already_complete:
            db.add(AuditLog(
                user_id=current_user.id,
                action="SELLER_PAYMENT_SETUP_DEMO_COMPLETED",
                entity_type="USER",
                entity_id=current_user.id,
                new_values={"mode": "DEMO_SIMULATED"},
            ))
        db.commit()
    except IntegrityError:
        db.rollback()
    return _status_out(db, current_user)

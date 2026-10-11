"""
BidSmart Analytics — User Management & RBAC Endpoints
Protected user profile, administrative governance, and role-gated route endpoints.
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db,
    get_current_active_user,
    require_admin,
    require_seller,
    require_buyer
)
from app.core.security import verify_password, get_password_hash
from app.models.user import User, UserStatus
from app.models.role import Role
from app.models.audit_log import AuditLog
from app.schemas.user import (
    UserOut,
    UserUpdate,
    UserRoleUpdate,
    UserStatusUpdate
)

router = APIRouter()


def _format_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role.name if user.role else "BUYER",
        role_id=user.role_id,
        status=user.status.value if hasattr(user.status, "value") else str(user.status),
        created_at=user.created_at,
        updated_at=user.updated_at
    )


# -----------------------------------------------------------------------------
# CURRENT AUTHENTICATED USER ENDPOINTS
# -----------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user profile"
)
def get_user_me(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Returns the profile of the currently authenticated active user."""
    return _format_user_out(current_user)


@router.put(
    "/me",
    response_model=UserOut,
    summary="Update current user profile"
)
def update_user_me(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Updates current user's profile information and allows password changes with verification."""
    if user_in.full_name is not None:
        current_user.full_name = user_in.full_name
    if user_in.phone is not None:
        current_user.phone = user_in.phone

    if user_in.new_password is not None:
        if not user_in.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to set a new password."
            )
        if not verify_password(user_in.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password provided."
            )
        current_user.password_hash = get_password_hash(user_in.new_password)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return _format_user_out(current_user)


# -----------------------------------------------------------------------------
# ROLE-BASED ACCESS CONTROL (RBAC) PORTAL TEST ENDPOINTS
# Demonstrates 401 Unauthorized and 403 Forbidden enforcement
# -----------------------------------------------------------------------------

@router.get(
    "/portal/buyer-only",
    summary="Buyer Portal Route (BUYER or ADMIN only)"
)
def buyer_portal_check(
    current_user: User = Depends(require_buyer)
) -> Any:
    """Accessible by BUYER and ADMIN accounts. Returns 403 for SELLER, 401 for unauthenticated."""
    return {
        "access": "granted",
        "portal": "Buyer Workspace",
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.name
    }


@router.get(
    "/portal/seller-only",
    summary="Seller Portal Route (SELLER or ADMIN only)"
)
def seller_portal_check(
    current_user: User = Depends(require_seller)
) -> Any:
    """Accessible by SELLER and ADMIN accounts. Returns 403 for BUYER, 401 for unauthenticated."""
    return {
        "access": "granted",
        "portal": "Seller Inventory Console",
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.name
    }


@router.get(
    "/portal/admin-only",
    summary="Admin Portal Route (ADMIN only)"
)
def admin_portal_check(
    current_user: User = Depends(require_admin)
) -> Any:
    """Accessible ONLY by ADMIN accounts. Returns 403 for BUYER/SELLER, 401 for unauthenticated."""
    return {
        "access": "granted",
        "portal": "System Administration & Compliance",
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.name
    }


# -----------------------------------------------------------------------------
# ADMINISTRATIVE USER MANAGEMENT ENDPOINTS (ADMIN ONLY)
# -----------------------------------------------------------------------------

@router.get(
    "",
    response_model=List[UserOut],
    summary="[Admin] List all registered users"
)
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> Any:
    """Lists registered users with pagination and filtering (Admin restricted)."""
    query = db.query(User)
    if role:
        query = query.join(Role).filter(Role.name == role.upper())
    if status_filter:
        query = query.filter(User.status == status_filter.upper())

    users = query.offset(skip).limit(limit).all()
    return [_format_user_out(u) for u in users]


@router.get(
    "/{user_id}",
    response_model=UserOut,
    summary="[Admin/Self] Get user by ID"
)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Returns a specific user by ID. Permitted if caller is ADMIN or querying self."""
    if current_user.role.name != "ADMIN" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to inspect other user profiles."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return _format_user_out(user)


@router.patch(
    "/{user_id}/role",
    response_model=UserOut,
    summary="[Admin] Update user role"
)
def update_user_role(
    user_id: int,
    role_in: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> Any:
    """Promotes or alters a user's role (Admin restricted)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    target_role = db.query(Role).filter(Role.name == role_in.role.upper()).first()
    if not target_role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role '{role_in.role}' not found.")

    old_role = user.role.name if user.role else "UNKNOWN"
    user.role_id = target_role.id

    # Audit log
    audit_entry = AuditLog(
        user_id=admin_user.id,
        action="USER_ROLE_UPDATED",
        entity_type="USER",
        entity_id=user.id,
        old_values={"role": old_role},
        new_values={"role": target_role.name}
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(user)

    return _format_user_out(user)


@router.patch(
    "/{user_id}/status",
    response_model=UserOut,
    summary="[Admin] Suspend or activate user"
)
def update_user_status(
    user_id: int,
    status_in: UserStatusUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
) -> Any:
    """Freezes or restores user account status (Admin restricted)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    old_status = str(user.status)
    user.status = UserStatus(status_in.status.upper())

    # Audit log
    audit_entry = AuditLog(
        user_id=admin_user.id,
        action="USER_STATUS_UPDATED",
        entity_type="USER",
        entity_id=user.id,
        old_values={"status": old_status},
        new_values={"status": user.status.value}
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(user)

    return _format_user_out(user)

"""
BidSmart Analytics — Authentication & Role-Based Access Control (RBAC) Dependencies
"""

from typing import Generator, List, Callable, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserStatus
from app.models.role import Role

# OAuth2 Bearer token extraction (mandatory)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/oauth",
    auto_error=True
)

# OAuth2 Bearer token extraction (optional for public endpoints that have personalized perks)
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/oauth",
    auto_error=False
)


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Decodes the Bearer JWT access token and queries the active User from the database.
    Raises:
        HTTP 401 Unauthorized if the token is invalid, expired, or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id_str: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id_str is None or token_type != "access":
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user


def get_optional_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme_optional)
) -> Optional[User]:
    """
    Optional token extraction. If a valid token is supplied, returns the User; otherwise None.
    Does not raise HTTP 401 if token is absent.
    """
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id_str: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id_str is None or token_type != "access":
            return None
        user_id = int(user_id_str)
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verifies that the authenticated user account is in 'ACTIVE' state.
    Raises:
        HTTP 403 Forbidden if the user account is suspended or pending verification.
    """
    if current_user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended: Access denied. Please contact platform administration."
        )
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account inactive: Current status is '{current_user.status}'."
        )
    return current_user


class RoleChecker:
    """
    Role-Based Access Control (RBAC) dependency factory.
    Enforces that the authenticated user holds one of the specified allowed roles.
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [r.upper() for r in allowed_roles]

    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        user_role_name = current_user.role.name.upper() if current_user.role else "NONE"
        if user_role_name not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Forbidden: Insufficient privileges. Required role in "
                    f"{self.allowed_roles}, but current user has role '{user_role_name}'."
                )
            )
        return current_user


def require_active_buyer(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Enforces that only active BUYER accounts are permitted to place bids.
    Marketplace Integrity Rules:
    - Administrators are explicitly prohibited to prevent conflicts of interest.
    - Sellers are explicitly prohibited to prevent shill bidding and self-inflation.
    """
    user_role_name = current_user.role.name.upper() if current_user.role else "NONE"
    if user_role_name != "BUYER":
        if user_role_name == "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Administrative accounts are prohibited from bidding to prevent conflicts of interest and preserve auction integrity."
            )
        elif user_role_name == "SELLER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Only accounts with the BUYER role are permitted to place bids. Sellers cannot participate in auction bidding."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Insufficient privileges. Required role 'BUYER', but current user has role '{user_role_name}'."
            )
    return current_user


# Role dependency shortcuts
require_admin = RoleChecker(["ADMIN"])
require_seller = RoleChecker(["SELLER", "ADMIN"])
require_buyer = RoleChecker(["BUYER", "ADMIN"])
require_buyer_only = RoleChecker(["BUYER"])
require_seller_only = RoleChecker(["SELLER"])

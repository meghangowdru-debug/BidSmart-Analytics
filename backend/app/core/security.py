"""
BidSmart Analytics — Cryptographic Security & JWT Token Management
Handles secure password hashing using bcrypt and JWT token issuance / verification.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import bcrypt
from jose import jwt, JWTError
from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored bcrypt hash.
    Safely handles string and bytes inputs and truncates at bcrypt's 72-byte limit.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        p_bytes = plain_password.encode("utf-8") if isinstance(plain_password, str) else plain_password
        h_bytes = hashed_password.encode("utf-8") if isinstance(hashed_password, str) else hashed_password
        return bcrypt.checkpw(p_bytes[:72], h_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Generates a secure cryptographic bcrypt hash with an automatic salt (rounds=12).
    """
    p_bytes = password.encode("utf-8") if isinstance(password, str) else password
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(p_bytes[:72], salt).decode("utf-8")


def create_access_token(
    subject: Union[str, int],
    username: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Creates a signed JWT access token.
    Claims:
        - sub: User ID (string)
        - username: User account username
        - role: RBAC role name ('ADMIN', 'SELLER', 'BUYER')
        - exp: Expiration timestamp (UTC)
        - type: 'access'
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "username": username,
        "role": role,
        "exp": expire,
        "type": "access",
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Creates a long-lived JWT refresh token for renewing access tokens.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodes and cryptographically validates a JWT token using the configured SECRET_KEY.
    Raises:
        JWTError if signature is invalid or token has expired.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

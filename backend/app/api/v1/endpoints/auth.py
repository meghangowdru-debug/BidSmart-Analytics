"""
BidSmart Analytics — Authentication Router
Endpoints:
- POST /api/v1/auth/register (User registration with validation & password hashing)
- POST /api/v1/auth/login (JSON Login with JWT token issuance)
- POST /api/v1/auth/login/oauth (OAuth2 Password Request Form for Swagger UI)
- POST /api/v1/auth/refresh (JWT access token renewal)
"""

from typing import Any
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.db.session import get_db
from app.models.user import User, UserStatus
from app.models.role import Role
from app.models.audit_log import AuditLog
from app.schemas.user import UserRegister, UserLogin, UserOut
from app.schemas.token import Token, RefreshTokenRequest

router = APIRouter()


def _format_user_out(user: User) -> UserOut:
    """Helper to convert User model with role relation into UserOut schema."""
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


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account"
)
def register(
    user_in: UserRegister,
    db: Session = Depends(get_db)
) -> Any:
    """
    Registers a new buyer or seller account with strict validation:
    - Unique username check (3–50 alphanumeric characters)
    - Unique email format check
    - Password complexity (8+ chars, upper, lower, numeric)
    - Bcrypt cryptographic password hashing (never plaintext)
    - Prevents self-assignment of administrative roles
    """
    # 1. Duplicate Username Check
    existing_username = db.query(User).filter(User.username == user_in.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{user_in.username}' is already registered."
        )

    # 2. Duplicate Email Check
    existing_email = db.query(User).filter(User.email == user_in.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email address '{user_in.email}' is already registered."
        )

    # 3. Lookup target role ID
    target_role_name = (user_in.role or "BUYER").upper()
    role_obj = db.query(Role).filter(Role.name == target_role_name).first()
    if not role_obj:
        role_obj = db.query(Role).filter(Role.name == "BUYER").first()

    # 4. Hash password with bcrypt
    hashed_password = get_password_hash(user_in.password)

    # 5. Create user record
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hashed_password,
        full_name=user_in.full_name,
        phone=user_in.phone,
        role_id=role_obj.id,
        status=UserStatus.ACTIVE
    )
    db.add(new_user)
    db.flush()

    # 6. Audit log entry
    audit_entry = AuditLog(
        user_id=new_user.id,
        action="USER_REGISTERED",
        entity_type="USER",
        entity_id=new_user.id,
        new_values={"username": new_user.username, "email": new_user.email, "role": role_obj.name}
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(new_user)

    return _format_user_out(new_user)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User login with JWT access token"
)
def login(
    login_in: UserLogin,
    db: Session = Depends(get_db)
) -> Any:
    """
    Authenticates a user via username or email and returns a signed JWT access token.
    """
    # Find user by username or email
    user = db.query(User).filter(
        (User.username == login_in.username_or_email) | (User.email == login_in.username_or_email)
    ).first()

    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended: Access denied. Please contact platform administration."
        )

    role_name = user.role.name if user.role else "BUYER"
    access_token = create_access_token(
        subject=user.id,
        username=user.username,
        role=role_name
    )
    refresh_token = create_refresh_token(subject=user.id)

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
        user=_format_user_out(user)
    )


@router.post(
    "/login/oauth",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="OAuth2 form-compatible login (Swagger UI)"
)
def login_oauth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    OAuth2 standard password flow endpoint for interactive Swagger UI authentication.
    """
    return login(UserLogin(username_or_email=form_data.username, password=form_data.password), db=db)


@router.post(
    "/refresh",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Renew expired JWT access token"
)
def refresh_token(
    refresh_in: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Issues a fresh access token using a valid, non-expired refresh token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(refresh_in.refresh_token)
        user_id_str: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id_str is None or token_type != "refresh":
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.status == UserStatus.SUSPENDED:
        raise credentials_exception

    role_name = user.role.name if user.role else "BUYER"
    new_access_token = create_access_token(
        subject=user.id,
        username=user.username,
        role=role_name
    )

    return Token(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_in.refresh_token,
        user=_format_user_out(user)
    )

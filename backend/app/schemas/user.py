"""
BidSmart Analytics — User Authentication & Profile Schemas
Defines request validation and sanitized response models (zero password exposure).
"""

import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique account username")
    email: EmailStr = Field(..., description="Valid unique email address")
    password: str = Field(..., min_length=8, max_length=72, description="Secure account password")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full legal or display name")
    phone: Optional[str] = Field(None, max_length=20, description="Optional contact telephone number")
    role: Optional[str] = Field("BUYER", description="Target role: 'BUYER' or 'SELLER'")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9_]{3,50}$", v):
            raise ValueError("Username must be between 3 and 50 characters and contain only letters, numbers, and underscores.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one numerical digit.")
        return v

    @field_validator("role")
    @classmethod
    def validate_role_assignment(cls, v: Optional[str]) -> str:
        role_upper = (v or "BUYER").upper().strip()
        if role_upper == "ADMIN":
            raise ValueError("Direct self-registration as ADMIN is forbidden. Administrative roles must be assigned by system governance.")
        if role_upper not in ["BUYER", "SELLER"]:
            raise ValueError("Registration role must be either 'BUYER' or 'SELLER'.")
        return role_upper


class UserLogin(BaseModel):
    username_or_email: str = Field(..., description="Username or email address")
    password: str = Field(..., min_length=1, description="Account password")


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str = Field(..., description="User role name ('ADMIN', 'SELLER', 'BUYER')")
    role_id: int
    status: str = Field(..., description="Account status ('ACTIVE', 'SUSPENDED')")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    current_password: Optional[str] = None
    new_password: Optional[str] = None

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if len(v) < 8:
                raise ValueError("New password must be at least 8 characters long.")
            if not re.search(r"[a-z]", v) or not re.search(r"[A-Z]", v) or not re.search(r"[0-9]", v):
                raise ValueError("New password must contain uppercase, lowercase, and numeric characters.")
        return v


class UserRoleUpdate(BaseModel):
    role: str = Field(..., description="New role name: 'BUYER', 'SELLER', or 'ADMIN'")

    @field_validator("role")
    @classmethod
    def validate_role_name(cls, v: str) -> str:
        role_upper = v.upper().strip()
        if role_upper not in ["BUYER", "SELLER", "ADMIN"]:
            raise ValueError("Role must be one of: 'BUYER', 'SELLER', 'ADMIN'")
        return role_upper


class UserStatusUpdate(BaseModel):
    status: str = Field(..., description="New status: 'ACTIVE' or 'SUSPENDED'")

    @field_validator("status")
    @classmethod
    def validate_status_name(cls, v: str) -> str:
        status_upper = v.upper().strip()
        if status_upper not in ["ACTIVE", "SUSPENDED", "PENDING_VERIFICATION"]:
            raise ValueError("Status must be one of: 'ACTIVE', 'SUSPENDED', 'PENDING_VERIFICATION'")
        return status_upper

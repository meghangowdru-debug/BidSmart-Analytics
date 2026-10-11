"""
BidSmart Analytics — Authentication Token Schemas
"""

from typing import Optional, Any
from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str = Field(..., description="Signed JWT Bearer access token")
    token_type: str = Field("bearer", description="Token type (Bearer)")
    expires_in: int = Field(..., description="Access token expiration window in seconds")
    refresh_token: Optional[str] = Field(None, description="Optional long-lived refresh token")
    user: Optional[Any] = Field(None, description="Authenticated user summary profile")


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Valid JWT refresh token")

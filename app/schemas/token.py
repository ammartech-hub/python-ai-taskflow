"""Pydantic schemas for JWT tokens and decoded payloads."""

from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.user import UserResponse


class Token(BaseModel):
    """JWT response returned upon successful authentication."""
    access_token: str = Field(..., description="Encoded JWT Bearer access token")
    token_type: str = Field(default="bearer", description="Token type descriptor")
    expires_in: int = Field(..., description="Token validity in seconds")
    user: UserResponse = Field(..., description="Authenticated user safe profile")


class TokenPayload(BaseModel):
    """Decoded JWT payload containing subject, claims, and lifecycle timestamps."""
    sub: str = Field(..., description="Subject claim containing user ID")
    role: str = Field(..., description="Authorization role claim")
    exp: int = Field(..., description="Expiration timestamp (epoch seconds)")
    iat: Optional[int] = Field(default=None, description="Issued at timestamp (epoch seconds)")

"""Pydantic schemas for user registration, authentication, and safe serialization."""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.user import UserRole


class UserRegisterRequest(BaseModel):
    """Schema for public user registration.

    Enforces that public registration can never assign administrative roles.
    """
    name: str = Field(
        ...,
        min_length=2,
        max_length=120,
        description="Full name of the user",
        examples=["Jane Developer"],
    )
    email: EmailStr = Field(
        ...,
        description="Unique user email address",
        examples=["jane@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Secure password (minimum 8 characters)",
        examples=["SecurePass123!"],
    )


class UserLoginRequest(BaseModel):
    """Schema for user credentials login."""
    email: EmailStr = Field(..., description="Registered account email", examples=["jane@example.com"])
    password: str = Field(..., min_length=1, description="Account password", examples=["SecurePass123!"])


class UserResponse(BaseModel):
    """Safe public user profile representation excluding credential hashes."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique user identifier")
    name: str = Field(..., description="User full name")
    email: EmailStr = Field(..., description="User email address")
    role: UserRole = Field(..., description="System authorization role")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last account update timestamp")


class UserRoleUpdateRequest(BaseModel):
    """Schema for admin-managed user role modifications."""
    role: UserRole = Field(..., description="Target system role")

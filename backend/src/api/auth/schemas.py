"""
Authentication Pydantic schemas.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token expiration time in seconds")


class AdminUserResponse(BaseModel):
    """Admin user response schema."""
    id: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUserCreate(BaseModel):
    """Admin user creation schema (internal use)."""
    email: EmailStr
    password: str = Field(..., min_length=8)

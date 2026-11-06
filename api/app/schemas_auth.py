"""Pydantic schemas for auth endpoints.

Note: we say "word" (not "headword") in all user-facing text.
The DB column is still `headword` for historical reasons, but
the API and UI use "word" everywhere.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ═══════════════════════════════════════════════════════════════
# Request schemas
# ═══════════════════════════════════════════════════════════════


class RegisterRequest(BaseModel):
    """Email + password registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = Field(None, max_length=50)


class LoginRequest(BaseModel):
    """Email + password login."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Exchange a refresh token for a new access token."""

    refresh_token: str


class GoogleOAuthRequest(BaseModel):
    """Receive a Google ID token from the frontend.

    The backend verifies the token with Google and either:
    - finds an existing user with that oauth_subject, or
    - creates a new user with oauth_provider='google'.
    """

    id_token: str


# ═══════════════════════════════════════════════════════════════
# Response schemas
# ═══════════════════════════════════════════════════════════════


class TokenResponse(BaseModel):
    """JWT pair returned after login/register/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access_token expires


class UserResponse(BaseModel):
    """Public user info — returned by /me and other endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str | None = None
    role: str
    created_at: datetime
    last_seen_at: datetime | None = None
    oauth_provider: str | None = None

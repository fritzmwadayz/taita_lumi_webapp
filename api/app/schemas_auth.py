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


# ── Password reset ────────────────────────────────────────────────


class PasswordResetRequest(BaseModel):
    """Request a password reset link.

    The endpoint always returns 200 (even if the email doesn't exist) to
    prevent email enumeration. The rate limit is 3 requests per email per hour.
    """

    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """Set a new password using a reset token.

    The token is the JWT issued by /password-reset/request, with type='reset'
    and a 1-hour expiry. The new password must be at least 8 chars (same
    constraint as registration).
    """

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ── Profile management ────────────────────────────────────────────


class ChangeEmailRequest(BaseModel):
    """Change the current user's email address.

    Requires the current password (verified server-side). The new email
    is lowercased before storage and uniqueness-checked against existing users.
    """

    new_email: EmailStr
    current_password: str


class DeleteAccountRequest(BaseModel):
    """Soft-delete (anonymize) the current user's account.

    Requires the current password. Anonymizes personal data but keeps the
    user's community contributions (suggestions, words) visible.
    """

    password: str


class ConnectedAccountsResponse(BaseModel):
    """Which auth methods are linked to the current user's account.

    The frontend uses this to show "Connected with Google" badges and to
    hide/show the password change form appropriately.
    """

    google: bool
    has_password: bool


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

"""Security utilities: password hashing and JWT creation/verification.

Uses passlib with bcrypt for password hashing (industry standard).
Uses python-jose with HS256 for JWT (symmetric, simple, fine for v1).

Token shape:
  Access token (short-lived, 30 min):
    { "sub": user_id, "email": "...", "role": "...", "type": "access", "exp": ... }
  Refresh token (long-lived, 30 days):
    { "sub": user_id, "type": "refresh", "exp": ... }
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

# ── Password hashing ──────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a stored hash."""
    return pwd_context.verify(plain, hashed)


# ── JWT creation ──────────────────────────────────────────────


def create_access_token(
    user_id: UUID,
    email: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived access token (default 30 min).

    The access token is sent on every authenticated request via
    Authorization: Bearer <token>.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    user_id: UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a long-lived refresh token (default 30 days).

    The refresh token is used only to obtain a new access token.
    It carries minimal info — just the user ID and type.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.refresh_token_expire_days)
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ── Password reset token ────────────────────────────────────────


# Password reset tokens expire after 1 hour (per the backend API contract).
PASSWORD_RESET_TOKEN_EXPIRE_SECONDS = 3600


def create_password_reset_token(
    user_id: UUID,
    email: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a single-use password reset token.

    The token carries the user ID and the user's email at issue time, so
    the confirm endpoint can invalidate it if the email has since changed
    (e.g. user changed email after requesting a reset).

    Signed with the same JWT_SECRET as access/refresh tokens, HS256.
    Expiry: 1 hour (PASSWORD_RESET_TOKEN_EXPIRE_SECONDS).
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(seconds=PASSWORD_RESET_TOKEN_EXPIRE_SECONDS)
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "type": "reset",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ── JWT verification ──────────────────────────────────────────


class TokenError(Exception):
    """Raised when a token is invalid, expired, or has the wrong type."""


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """Decode and verify a JWT.

    Raises TokenError if:
      - the signature is invalid
      - the token has expired
      - the type doesn't match expected_type
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as e:
        raise TokenError(f"Invalid token: {e}") from e

    if payload.get("type") != expected_type:
        raise TokenError(
            f"Wrong token type: expected {expected_type}, got {payload.get('type')}"
        )

    return payload

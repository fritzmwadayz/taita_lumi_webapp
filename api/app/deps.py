"""Shared FastAPI dependencies.

Auth dependencies use JWT (access token in Authorization: Bearer header).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User
from app.security import TokenError, decode_token

# Bearer token extractor — auto_error=False so we can return 401
# ourselves with a cleaner message than the default.
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode the JWT from the Authorization header and fetch the user.

    Raises 401 if:
      - no credentials provided
      - token is invalid or expired
      - user doesn't exist (deleted)
      - user is blocked
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── Decode + verify token ─────────────────────────────────
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # ── Fetch user ────────────────────────────────────────────
    user_id = UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )

    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been blocked",
        )

    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Like get_current_user, but returns None when no token is provided.

    Used by endpoints that accept both authed and anon users
    (e.g. POST /api/suggestions — contributors post as themselves,
    anon users post via session cookie).

    If a token IS provided but is invalid/expired, this still raises 401
    — that way the frontend's auto-refresh interceptor can kick in and
    retry with a fresh token. Only the "no token at all" case returns None.
    """
    if credentials is None:
        return None

    # ── Decode + verify token (raise 401 if invalid) ─────────
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # ── Fetch user ────────────────────────────────────────────
    user_id = UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Token points to a deleted user — treat as no auth
        return None

    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been blocked",
        )

    return user


async def require_user(user: User = Depends(get_current_user)) -> User:
    """Require an authenticated user (any registered user — user, reviewer, or admin)."""
    return user


async def require_reviewer(user: User = Depends(get_current_user)) -> User:
    """Require a reviewer or admin (can add words directly)."""
    if user.role not in ("reviewer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer access required.",
        )
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require an admin user."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only",
        )
    return user

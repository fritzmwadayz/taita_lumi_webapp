"""Auth endpoints: register, login, refresh, me, logout, Google OAuth.

Note: user-facing text says "word" (not "headword"). The DB column
stays `headword` for historical reasons.

Endpoints:
  POST /api/auth/register     — email + password signup
  POST /api/auth/login        — email + password login
  POST /api/auth/refresh      — exchange refresh token for new access token
  GET  /api/auth/me           — get current user (requires auth)
  POST /api/auth/logout       — invalidate (client-side; JWT is stateless)
  POST /api/auth/oauth/google — exchange Google ID token for our JWT
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import Suggestion, User, Vote, Word
from app.schemas_auth import (
    GoogleOAuthRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter()
settings = get_settings()


# ═══════════════════════════════════════════════════════════════
# POST /api/auth/register
# ═══════════════════════════════════════════════════════════════


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user with email + password.

    Returns a JWT pair immediately (no email verification in v1).
    New users default to role='contributor'.
    """
    # ── Check for existing email ──────────────────────────────
    existing = await db.execute(select(User).where(User.email == req.email.lower()))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    # ── Create user ───────────────────────────────────────────
    user = User(
        email=req.email.lower(),
        password_hash=hash_password(req.password),
        display_name=req.display_name,
        role="user",
        last_seen_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # ── Issue tokens ──────────────────────────────────────────
    access = create_access_token(user.id, user.email, user.role)
    refresh = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ═══════════════════════════════════════════════════════════════
# POST /api/auth/login
# ═══════════════════════════════════════════════════════════════


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login with email + password. Returns a JWT pair."""
    # ── Find user ─────────────────────────────────────────────
    result = await db.execute(
        select(User).where(User.email == req.email.lower())
    )
    user = result.scalar_one_or_none()

    # ── Verify password (constant-time via passlib) ──────────
    if user is None or not user.password_hash:
        # Same error for "no such user" and "wrong password" — don't leak which.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been blocked.",
        )

    # ── Update last_seen_at ──────────────────────────────────
    user.last_seen_at = datetime.now(timezone.utc)
    await db.commit()

    # ── Issue tokens ──────────────────────────────────────────
    access = create_access_token(user.id, user.email, user.role)
    refresh = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ═══════════════════════════════════════════════════════════════
# POST /api/auth/refresh
# ═══════════════════════════════════════════════════════════════


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a refresh token for a new access token.

    The refresh token's `sub` (user ID) is used to look up the user.
    If the user has been blocked or deleted, refresh fails.
    """
    try:
        payload = decode_token(req.refresh_token, expected_type="refresh")
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {e}",
        ) from e

    user_id = UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer available.",
        )

    # ── Issue new tokens (rotate refresh too) ────────────────
    access = create_access_token(user.id, user.email, user.role)
    new_refresh = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ═══════════════════════════════════════════════════════════════
# GET /api/auth/me
# ═══════════════════════════════════════════════════════════════


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get the current user's profile.

    Requires Authorization: Bearer <access_token>.
    """
    # ── Update last_seen_at (cheap write, no commit needed if
    #    we're okay with it being best-effort) ────────────────
    return UserResponse.model_validate(current_user)


# ═══════════════════════════════════════════════════════════════
# PATCH /api/auth/me — update profile (display name)
# ═══════════════════════════════════════════════════════════════


class UpdateProfileRequest(BaseModel):
    """Update the current user's profile."""

    display_name: str | None = Field(None, max_length=50)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    req: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the current user's display name.

    Only display_name is editable in v1. Email and password changes
    come later.
    """
    if req.display_name is not None:
        current_user.display_name = req.display_name.strip() or None

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


# ═══════════════════════════════════════════════════════════════
# PATCH /api/auth/me/password — change password
# ═══════════════════════════════════════════════════════════════


class ChangePasswordRequest(BaseModel):
    """Change the current user's password."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


@router.patch("/me/password")
async def change_password(
    req: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change the current user's password.

    Requires the current password. OAuth-only users (no password_hash)
    cannot use this endpoint — they should use Google sign-in.
    """
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses Google sign-in and has no password set.",
        )

    if not verify_password(req.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    current_user.password_hash = hash_password(req.new_password)
    await db.commit()

    return {"status": "ok", "message": "Password changed."}


# ═══════════════════════════════════════════════════════════════
# GET /api/auth/me/stats — contribution stats
# ═══════════════════════════════════════════════════════════════


class UserStatsResponse(BaseModel):
    """Contribution stats for the current user."""

    words_added: int = 0
    suggestions_submitted: int = 0
    suggestions_accepted: int = 0
    suggestions_open: int = 0
    suggestions_rejected: int = 0
    votes_cast: int = 0


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_my_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get contribution stats for the current user."""
    from sqlalchemy import func as sa_func

    # Words created by this user (source='user', created_by_user_id)
    words_added = await db.scalar(
        select(sa_func.count())
        .select_from(User)
        .join(Word, Word.created_by_user_id == current_user.id)
        .where(Word.source == "user", Word.status == "live")
    ) or 0

    # Suggestions
    sugg_total = await db.scalar(
        select(sa_func.count())
        .select_from(Suggestion)
        .where(Suggestion.created_by_user_id == current_user.id)
    ) or 0

    sugg_accepted = await db.scalar(
        select(sa_func.count())
        .select_from(Suggestion)
        .where(
            Suggestion.created_by_user_id == current_user.id,
            Suggestion.status == "accepted",
        )
    ) or 0

    sugg_open = await db.scalar(
        select(sa_func.count())
        .select_from(Suggestion)
        .where(
            Suggestion.created_by_user_id == current_user.id,
            Suggestion.status == "open",
        )
    ) or 0

    sugg_rejected = await db.scalar(
        select(sa_func.count())
        .select_from(Suggestion)
        .where(
            Suggestion.created_by_user_id == current_user.id,
            Suggestion.status == "rejected",
        )
    ) or 0

    # Votes cast
    votes_cast = await db.scalar(
        select(sa_func.count())
        .select_from(Vote)
        .where(Vote.user_id == current_user.id)
    ) or 0

    return UserStatsResponse(
        words_added=words_added,
        suggestions_submitted=sugg_total,
        suggestions_accepted=sugg_accepted,
        suggestions_open=sugg_open,
        suggestions_rejected=sugg_rejected,
        votes_cast=votes_cast,
    )


# ═══════════════════════════════════════════════════════════════
# POST /api/auth/logout
# ═══════════════════════════════════════════════════════════════


@router.post("/logout", status_code=204)
async def logout():
    """Logout.

    JWT is stateless, so there's no server-side invalidation in v1.
    The client simply discards its tokens. (A token blacklist could
    be added later if needed — not worth it for v1.)

    Returns 204 No Content.
    """
    return None


# ═══════════════════════════════════════════════════════════════
# POST /api/auth/oauth/google
# ═══════════════════════════════════════════════════════════════


async def _verify_google_id_token(id_token_str: str) -> dict:
    """Verify a Google ID token and return the payload.

    Verifies signature, audience (our client ID), and expiry.
    Returns the decoded token payload containing:
      - sub: Google user ID (stable per user)
      - email: user's Google email
      - email_verified: boolean
      - name: user's full name (optional)
      - picture: avatar URL (optional)

    Raises HTTPException 401 if the token is invalid.
    """
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    if not settings.google_oauth_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured on the server.",
        )

    try:
        payload = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.google_oauth_client_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {e}",
        ) from e

    return payload


@router.post("/oauth/google", response_model=TokenResponse)
async def login_with_google(
    req: GoogleOAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login or register with a Google ID token.

    The frontend obtains a Google ID token (via Google Identity Services)
    and posts it here. We verify it, then either:
    - find an existing user with oauth_provider='google' + oauth_subject=sub, or
    - find an existing user with the same email (and link the Google account), or
    - create a new user.

    Returns a JWT pair (same as register/login).
    """
    # ── Verify the Google token ───────────────────────────────
    payload = await _verify_google_id_token(req.id_token)

    google_sub = payload["sub"]
    email = payload["email"].lower()
    email_verified = payload.get("email_verified", False)
    display_name = payload.get("name") or None

    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google email is not verified. Verify your email with Google first.",
        )

    # ── Find or create user ───────────────────────────────────
    # 1. Look up by oauth_provider + oauth_subject (most reliable)
    result = await db.execute(
        select(User).where(
            User.oauth_provider == "google",
            User.oauth_subject == google_sub,
        )
    )
    user = result.scalar_one_or_none()

    # 2. Not found by Google subject — try by email (link existing account)
    if user is None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is not None:
            # Link Google to this existing email account
            user.oauth_provider = "google"
            user.oauth_subject = google_sub

    # 3. Still not found — create a new user
    if user is None:
        user = User(
            email=email,
            password_hash=None,  # OAuth-only users have no password
            oauth_provider="google",
            oauth_subject=google_sub,
            display_name=display_name,
            role="user",
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(user)
    else:
        # Update last_seen + maybe refresh display_name if user hasn't set one
        user.last_seen_at = datetime.now(timezone.utc)
        if not user.display_name and display_name:
            user.display_name = display_name

    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been blocked.",
        )

    await db.commit()
    await db.refresh(user)

    # ── Issue tokens ──────────────────────────────────────────
    access = create_access_token(user.id, user.email, user.role)
    refresh = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )

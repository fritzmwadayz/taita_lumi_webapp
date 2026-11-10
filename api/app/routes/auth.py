"""Auth endpoints: register, login, refresh, me, logout, Google OAuth,
password reset, profile management.

Note: user-facing text says "word" (not "headword"). The DB column
stays `headword` for historical reasons.

Endpoints:
  POST   /api/auth/register                          — email + password signup
  POST   /api/auth/login                             — email + password login
  POST   /api/auth/refresh                           — exchange refresh token for new access token
  GET    /api/auth/me                                — get current user (requires auth)
  PATCH  /api/auth/me                                — update display name
  PATCH  /api/auth/me/password                       — change password
  GET    /api/auth/me/stats                          — contribution stats
  POST   /api/auth/logout                            — invalidate (client-side; JWT is stateless)
  POST   /api/auth/oauth/google                      — exchange Google ID token for our JWT
  POST   /api/auth/password-reset/request            — request reset email (always 200)
  POST   /api/auth/password-reset/confirm            — set new password with reset token
  PATCH  /api/auth/me/email                          — change email (password verified)
  DELETE /api/auth/me                                — soft-delete / anonymize account
  GET    /api/auth/me/connected-accounts              — show linked OAuth + has_password
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.anon import check_password_reset_rate_limit
from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.email import send_email
from app.models import EditLog, Suggestion, User, Vote, Word
from app.schemas_auth import (
    ChangeEmailRequest,
    ConnectedAccountsResponse,
    DeleteAccountRequest,
    GoogleOAuthRequest,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.security import (
    TokenError,
    create_access_token,
    create_password_reset_token,
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current user's profile.

    Requires Authorization: Bearer <access_token>.
    """
    # ── Update last_seen_at (best-effort; not critical if it fails) ──
    current_user.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(current_user)

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


# ═══════════════════════════════════════════════════════════════
# POST /api/auth/password-reset/request
# ═══════════════════════════════════════════════════════════════


# ── Email templates ──────────────────────────────────────────────
_PASSWORD_RESET_SUBJECT = "Lumi — Password reset"


def _password_reset_email_body(reset_link: str) -> str:
    """Plain-text body of the password-reset email."""
    return (
        "You requested a password reset for your Lumi dictionary account.\n\n"
        "Click this link to set a new password:\n"
        f"{reset_link}\n\n"
        "This link expires in 1 hour. If you didn't request this, you can "
        "safely ignore this email.\n\n"
        "— The Lumi team"
    )


def _password_reset_email_html(reset_link: str) -> str:
    """Optional HTML body for the password-reset email."""
    return (
        "<p>You requested a password reset for your Lumi dictionary account.</p>"
        "<p>Click this link to set a new password:</p>"
        f'<p><a href="{reset_link}">{reset_link}</a></p>'
        "<p>This link expires in 1 hour. If you didn't request this, "
        "you can safely ignore this email.</p>"
        "<p>— The Lumi team</p>"
    )


def _build_reset_link(token: str) -> str:
    """Build the frontend reset link from the configured FRONTEND_URL + token."""
    base = (settings.frontend_url or "").rstrip("/")
    return f"{base}/reset-password?token={token}"


@router.post("/password-reset/request")
async def request_password_reset(
    req: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset link.

    Always returns 200 — even if the email doesn't exist — to prevent email
    enumeration. Behavior:

    1. Rate limit: max 3 requests per email per hour (429 if exceeded).
    2. Look up the user (case-insensitive — emails are lowercased on storage).
    3. If found AND not blocked AND has a password_hash (not OAuth-only):
       - Generate a 1-hour reset JWT (type=reset, sub=user_id, email=user.email)
       - Send a reset email to the user containing the frontend reset link
       - Write an EditLog row: action='user.password_reset_request'
    4. If not found, blocked, or OAuth-only: do nothing (but still return 200).

    Note: EditLog.entity_id is NOT NULL in the schema, so the audit row is
    only written when we actually have a user_id (i.e. the user was found).
    """
    email = req.email.lower()

    # ── Rate limit (per email, 3/hour) ────────────────────────
    # Applied before the lookup so the 429 is returned even for unknown
    # emails (otherwise the endpoint could be probed to enumerate emails
    # by observing which calls trigger rate-limiting).
    check_password_reset_rate_limit(email)

    # ── Look up user (case-insensitive) ────────────────────────
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if (
        user is not None
        and not user.is_blocked
        and user.password_hash  # OAuth-only users can't reset a password
    ):
        # ── Generate reset token ───────────────────────────────
        token = create_password_reset_token(user.id, user.email)

        # ── Send email (dev mode logs to stdout; never raises) ──
        reset_link = _build_reset_link(token)
        await send_email(
            to=user.email,
            subject=_PASSWORD_RESET_SUBJECT,
            body=_password_reset_email_body(reset_link),
            html=_password_reset_email_html(reset_link),
        )

        # ── Audit log (entity_id is NOT NULL, so only when we have a user) ──
        db.add(
            EditLog(
                actor_user_id=user.id,
                action="user.password_reset_request",
                entity_type="user",
                entity_id=user.id,
                after={"email": user.email},
            )
        )
        await db.commit()

    # Always return 200 with the same message
    return {
        "status": "ok",
        "message": "If an account exists for that email, a reset link has been sent.",
    }


# ═══════════════════════════════════════════════════════════════
# POST /api/auth/password-reset/confirm
# ═══════════════════════════════════════════════════════════════


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    req: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify a reset token and set a new password.

    Behavior:
    1. Decode the JWT, verify signature + expiry + type='reset'.
    2. Look up the user by sub (user_id).
    3. Verify the user still exists, is not blocked, and the email in the
       token matches the user's current email (invalidates the token if the
       email was changed after the reset was requested).
    4. Hash the new password with bcrypt, update user.password_hash.
    5. Write an EditLog row: action='user.password_reset'.

    Note: the JWT is stateless, so we can't truly invalidate it server-side
    after use. The 1-hour expiry + email-match check are the safety nets.
    """
    # ── Decode + verify token ────────────────────────────────
    try:
        payload = decode_token(req.token, expected_type="reset")
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        ) from e

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        ) from e

    token_email = payload.get("email")

    # ── Look up the user ──────────────────────────────────────
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Don't reveal whether the user exists — same message as invalid token
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        )

    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been blocked.",
        )

    # Email-mismatch check (e.g. user changed email after requesting reset)
    if not token_email or token_email.lower() != (user.email or "").lower():
        # Same message — don't reveal the specific reason
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        )

    # ── Set new password ─────────────────────────────────────
    user.password_hash = hash_password(req.new_password)

    # ── Audit log ─────────────────────────────────────────────
    db.add(
        EditLog(
            actor_user_id=user.id,
            action="user.password_reset",
            entity_type="user",
            entity_id=user.id,
        )
    )
    await db.commit()

    return {
        "status": "ok",
        "message": "Your password has been reset. Please log in.",
    }


# ═══════════════════════════════════════════════════════════════
# PATCH /api/auth/me/email — change email address
# ═══════════════════════════════════════════════════════════════


@router.patch("/me/email", response_model=UserResponse)
async def change_email(
    req: ChangeEmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change the current user's email address.

    Separate from PATCH /api/auth/me (display name only) to require password
    verification. OAuth-only accounts (no password_hash) cannot use this
    endpoint — they should use Google sign-in.

    Behavior:
    1. Verify current_password against user.password_hash (401 if wrong).
    2. If OAuth-only: return 400 'This account uses Google sign-in.'
    3. Lowercase the new email.
    4. Check for duplicates (409 if another user already has this email).
    5. Update user.email.
    6. Write EditLog: action='user.email_change', before/after the email swap.
    """
    # ── OAuth-only accounts can't change email this way ────────
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses Google sign-in.",
        )

    # ── Verify current password ───────────────────────────────
    if not verify_password(req.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    new_email = req.new_email.lower()

    # ── No-op if the email is unchanged ────────────────────────
    if new_email == (current_user.email or "").lower():
        # Still return the (unchanged) user — idempotent
        await db.refresh(current_user)
        return UserResponse.model_validate(current_user)

    # ── Duplicate check ───────────────────────────────────────
    existing = await db.execute(
        select(User).where(User.email == new_email).where(User.id != current_user.id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    # ── Apply + audit ─────────────────────────────────────────
    old_email = current_user.email
    current_user.email = new_email

    db.add(
        EditLog(
            actor_user_id=current_user.id,
            action="user.email_change",
            entity_type="user",
            entity_id=current_user.id,
            before={"email": old_email},
            after={"email": new_email},
        )
    )
    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


# ═══════════════════════════════════════════════════════════════
# DELETE /api/auth/me — soft-delete / anonymize account
# ═══════════════════════════════════════════════════════════════


@router.delete("/me", status_code=204)
async def delete_account(
    req: DeleteAccountRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete the current user's account.

    Anonymizes personal data but keeps the user's community contributions
    (suggestions, words) visible — `created_by_user_id` still points to the
    anonymized user, and `display_name` becomes "deleted user".

    Behavior:
    1. Verify password (401 if wrong).
    2. If OAuth-only: return 400 'This account uses Google sign-in and has no password.'
    3. Anonymize:
       - email → unique placeholder 'deleted+<uuid>@anon.lumi'
         (the DB column is nullable=False, unique=True, and the contract
          says no migrations needed — so we can't NULL it; we use a unique
          placeholder instead. The real email is discarded.)
       - display_name → 'deleted user'
       - password_hash → None
       - oauth_provider → None
       - oauth_subject → None
       - is_blocked → True (prevents any future auth via the same row)
    4. Keep Suggestion rows (community content).
    5. Keep Word rows where created_by_user_id = user_id (community content).
    6. Write EditLog: action='user.delete'.
    7. Return 204.

    Note: the user's existing JWTs will continue to work until expiry (the
    JWT is stateless). The next /refresh or /me call will fail because
    is_blocked is now True — that's the soft-delete enforcement mechanism.
    """
    # ── OAuth-only accounts have no password to verify ────────
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses Google sign-in and has no password.",
        )

    # ── Verify password ───────────────────────────────────────
    if not verify_password(req.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password is incorrect.",
        )

    # ── Anonymize personal data ───────────────────────────────
    # `email` is nullable=False + unique in the schema and the contract says
    # no migrations needed, so we replace it with a unique placeholder rather
    # than NULL. The placeholder is deterministic per user_id and clearly
    # anonymized, so it can't be confused with a real email and won't collide.
    current_user.email = f"deleted+{current_user.id}@anon.lumi"
    current_user.display_name = "deleted user"
    current_user.password_hash = None
    current_user.oauth_provider = None
    current_user.oauth_subject = None
    current_user.is_blocked = True  # prevents any future auth via this row

    # ── Audit log ─────────────────────────────────────────────
    db.add(
        EditLog(
            actor_user_id=current_user.id,
            action="user.delete",
            entity_type="user",
            entity_id=current_user.id,
            after={"anonymized": True},
        )
    )
    await db.commit()

    # 204 No Content — FastAPI returns an empty body automatically.
    return None


# ═══════════════════════════════════════════════════════════════
# GET /api/auth/me/connected-accounts — show linked OAuth + has_password
# ═══════════════════════════════════════════════════════════════


@router.get("/me/connected-accounts", response_model=ConnectedAccountsResponse)
async def get_connected_accounts(
    current_user: User = Depends(get_current_user),
):
    """Return which auth methods are linked to the current user's account.

    The frontend uses this to show 'Connected with Google' badges and to
    hide/show the password change form appropriately.
    """
    return ConnectedAccountsResponse(
        google=(current_user.oauth_provider == "google"),
        has_password=bool(current_user.password_hash),
    )

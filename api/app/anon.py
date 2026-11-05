"""Anonymous session handling.

Anon visitors are tracked via a cookie (random UUID generated client-side,
stored in localStorage). The backend hashes it, looks up or creates an
anonymous_sessions row, and uses it for rate limiting.

Rate limiting is in-memory for v1 (simple, no Redis dependency).
Per-session: 5 suggestions per hour.
Per-IP: 10 suggestions per hour.

The in-memory store is a dict keyed by session_id, with a sliding window
of timestamps. For production with multiple workers, this should be
upgraded to Redis — but for v1 (single Render free instance) it's fine.
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from uuid import UUID

from fastapi import Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnonymousSession

# ── Rate limit config ─────────────────────────────────────────
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds
RATE_LIMIT_PER_ANON_SESSION = 5  # max 5 suggestions per hour per anon session
RATE_LIMIT_PER_ANON_IP = 10  # max 10 suggestions per hour per IP
RATE_LIMIT_PER_REGISTERED_USER = 15  # max 15 suggestions per hour per registered non-reviewer

# ── In-memory rate limit store ────────────────────────────────
# Keyed by session_id (UUID) or user_id (UUID) or IP hash
# Value is list of timestamps
_session_attempts: dict[UUID, list[float]] = defaultdict(list)
_ip_attempts: dict[str, list[float]] = defaultdict(list)
_user_attempts: dict[UUID, list[float]] = defaultdict(list)


def _prune_old(attempts: list[float], window: int = RATE_LIMIT_WINDOW) -> list[float]:
    """Remove timestamps older than the window."""
    cutoff = time.time() - window
    return [t for t in attempts if t > cutoff]


def check_rate_limit(session_id: UUID, ip_hash: str) -> None:
    """Check if the anon session has exceeded the rate limit.

    Raises 429 if exceeded.
    """
    now = time.time()

    # ── Per-session check ─────────────────────────────────────
    _session_attempts[session_id] = _prune_old(_session_attempts[session_id])
    if len(_session_attempts[session_id]) >= RATE_LIMIT_PER_ANON_SESSION:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded: max {RATE_LIMIT_PER_ANON_SESSION} suggestions per hour. "
                "Sign in for a higher limit."
            ),
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    # ── Per-IP check ──────────────────────────────────────────
    _ip_attempts[ip_hash] = _prune_old(_ip_attempts[ip_hash])
    if len(_ip_attempts[ip_hash]) >= RATE_LIMIT_PER_ANON_IP:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for this IP address.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    # ── Record the attempt ────────────────────────────────────
    _session_attempts[session_id].append(now)
    _ip_attempts[ip_hash].append(now)


def check_registered_user_rate_limit(user_id: UUID) -> None:
    """Check if a registered non-reviewer user has exceeded the rate limit.

    Raises 429 if exceeded. Reviewers and admins are unlimited.
    """
    now = time.time()

    _user_attempts[user_id] = _prune_old(_user_attempts[user_id])
    if len(_user_attempts[user_id]) >= RATE_LIMIT_PER_REGISTERED_USER:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded: max {RATE_LIMIT_PER_REGISTERED_USER} suggestions per hour. "
                "Become a reviewer for unlimited suggestions."
            ),
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    _user_attempts[user_id].append(now)


def _hash_cookie(cookie_value: str) -> str:
    """Hash an anon cookie value for storage/lookup."""
    return hashlib.sha256(cookie_value.encode()).hexdigest()


def _hash_ip(ip: str) -> str:
    """Hash an IP for storage/lookup (we don't store raw IPs)."""
    return hashlib.sha256(ip.encode()).hexdigest()


async def get_or_create_anon_session(
    db: AsyncSession,
    cookie_value: str | None,
    ip: str,
) -> tuple[AnonymousSession, str]:
    """Get or create an anonymous session.

    Returns (session, ip_hash). The ip_hash is returned so callers
    can use it for rate limiting without re-hashing.

    If cookie_value is None, a new session is created (first visit).
    """
    ip_hash = _hash_ip(ip)

    if cookie_value:
        cookie_hash = _hash_cookie(cookie_value)
        result = await db.execute(
            select(AnonymousSession).where(
                AnonymousSession.cookie_hash == cookie_hash
            )
        )
        session = result.scalar_one_or_none()
        if session is not None:
            # Check if blocked
            if session.is_blocked:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This session has been blocked.",
                )
            return session, ip_hash

    # Create new session
    session = AnonymousSession(
        cookie_hash=_hash_cookie(cookie_value or str(UUID(int=0))),
        ip_hash=ip_hash,
    )
    db.add(session)
    await db.flush()
    return session, ip_hash


async def get_anon_actor(
    request: Request,
    db: AsyncSession,
    x_session_cookie: str | None = Header(None, alias="X-Session-Cookie"),
) -> tuple[AnonymousSession | None, str | None, UUID | None]:
    """FastAPI dependency: resolve the anon session from the request.

    Returns (session, ip_hash, session_id).
    If no cookie is provided, returns (None, ip_hash, None) — caller
    can decide whether to require a session or create one.

    The X-Session-Cookie header is set by the frontend (a random UUID
    stored in localStorage on first visit).
    """
    ip = request.client.host if request.client else "0.0.0.0"
    ip_hash = _hash_ip(ip)

    if not x_session_cookie:
        return None, ip_hash, None

    cookie_hash = _hash_cookie(x_session_cookie)
    result = await db.execute(
        select(AnonymousSession).where(
            AnonymousSession.cookie_hash == cookie_hash
        )
    )
    session = result.scalar_one_or_none()

    if session and session.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This session has been blocked.",
        )

    return session, ip_hash, session.id if session else None

"""Suggestion endpoints: create, list, detail.

Phase 3 supports:
  POST /api/suggestions          — create a suggestion (anon or contributor)
  GET  /api/suggestions          — list suggestions (public read)
  GET  /api/suggestions/{id}     — get a single suggestion (public read)

Voting (POST /api/suggestions/{id}/vote) comes in Phase 4.
Admin accept/reject (POST /api/suggestions/{id}/decide) comes in Phase 6.

Anon users are identified by the X-Session-Cookie header (a random UUID
the frontend generates and stores in localStorage). Anon suggestions
are rate-limited: 5 per hour per session, 10 per hour per IP.

Contributors are authenticated via JWT. Their suggestions have
created_by_user_id set; rate limiting does not apply.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.anon import check_rate_limit, get_or_create_anon_session
from app.db import get_db
from app.deps import get_optional_user
from app.models import AnonymousSession, Suggestion, User, Vote
from app.schemas_suggestion import (
    CreateSuggestionRequest,
    SuggestionListItem,
    SuggestionListResponse,
    SuggestionResponse,
)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


VALID_TARGET_TYPES = {"new_word", "word", "gloss", "example", "relation"}


def _validate_suggestion(req: CreateSuggestionRequest) -> None:
    """Validate the suggestion request based on target_type."""
    if req.target_type not in VALID_TARGET_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid target_type. Must be one of: {VALID_TARGET_TYPES}",
        )

    if req.target_type == "new_word":
        # proposed_value must contain at least a headword
        if not req.proposed_value.get("headword"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="new_word suggestions must include 'headword' in proposed_value",
            )

    elif req.target_type == "word":
        # Must have a target_id and field_path
        if not req.target_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="word corrections must include target_id (the word UUID)",
            )
        if not req.field_path:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="word corrections must include field_path (e.g. 'headword')",
            )


async def _get_vote_counts(
    db: AsyncSession, suggestion_ids: list[UUID]
) -> dict[UUID, dict[str, int]]:
    """Batch-fetch vote counts for a list of suggestions.

    Returns {suggestion_id: {"up": N, "down": N}}.
    """
    if not suggestion_ids:
        return {}

    stmt = (
        select(
            Vote.suggestion_id,
            Vote.vote,
            func.count().label("count"),
        )
        .where(Vote.suggestion_id.in_(suggestion_ids))
        .group_by(Vote.suggestion_id, Vote.vote)
    )
    result = await db.execute(stmt)

    counts: dict[UUID, dict[str, int]] = {
        sid: {"up": 0, "down": 0} for sid in suggestion_ids
    }
    for row in result.all():
        sid, vote, count = row
        if sid in counts and vote in ("up", "down"):
            counts[sid][vote] = count

    return counts


def _author_display(
    user_id: UUID | None,
    session_id: UUID | None,
    user: User | None = None,
) -> str | None:
    """Generate a display string for the suggestion author."""
    if user_id is not None:
        if user and user.display_name:
            return f"@{user.display_name}"
        return "registered user"
    if session_id is not None:
        return "anonymous"
    return None


# ═══════════════════════════════════════════════════════════════
# POST /api/suggestions — create a suggestion
# ═══════════════════════════════════════════════════════════════


@router.post("/suggestions", response_model=SuggestionResponse, status_code=201)
async def create_suggestion(
    req: CreateSuggestionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    x_session_cookie: str | None = None,
):
    """Create a new suggestion.

    Authenticated contributors: suggestion is created with created_by_user_id.
    Anonymous visitors: suggestion is created with created_by_session_id,
    and rate limiting applies (5/hour per session, 10/hour per IP).

    The X-Session-Cookie header is read from the request directly
    (the frontend sets it as a custom header).
    """
    _validate_suggestion(req)

    # ── Honeypot check (Phase 3c will add this; stub for now) ─
    # If proposed_value contains a 'website' field, it's a bot.
    if req.proposed_value.get("website"):
        # Silently accept but don't actually save — looks like success to the bot.
        # For now, just reject.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid submission.",
        )

    # ── Resolve the actor ─────────────────────────────────────
    if current_user is not None:
        # Authenticated contributor — no rate limit
        created_by_user_id = current_user.id
        created_by_session_id = None
    else:
        # Anonymous — need session cookie, create if missing
        x_session_cookie = request.headers.get("X-Session-Cookie")
        ip = request.client.host if request.client else "0.0.0.0"

        session, ip_hash = await get_or_create_anon_session(
            db, x_session_cookie, ip
        )

        # Rate limit check
        check_rate_limit(session.id, ip_hash)

        created_by_user_id = None
        created_by_session_id = session.id

    # ── Create the suggestion ────────────────────────────────
    suggestion = Suggestion(
        target_type=req.target_type,
        target_id=req.target_id,
        field_path=req.field_path,
        proposed_value=req.proposed_value,
        rationale=req.rationale,
        status="open",
        created_by_user_id=created_by_user_id,
        created_by_session_id=created_by_session_id,
    )
    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)

    return SuggestionResponse(
        id=suggestion.id,
        target_type=suggestion.target_type,
        target_id=suggestion.target_id,
        field_path=suggestion.field_path,
        proposed_value=suggestion.proposed_value,
        rationale=suggestion.rationale,
        status=suggestion.status,
        created_by_user_id=suggestion.created_by_user_id,
        created_by_session_id=suggestion.created_by_session_id,
        created_at=suggestion.created_at,
        decided_at=suggestion.decided_at,
        decided_by_user_id=suggestion.decided_by_user_id,
        applied_at=suggestion.applied_at,
        author_display=_author_display(
            created_by_user_id, created_by_session_id, current_user
        ),
        upvotes=0,
        downvotes=0,
    )


# ═══════════════════════════════════════════════════════════════
# GET /api/suggestions — list suggestions
# ═══════════════════════════════════════════════════════════════


@router.get("/suggestions", response_model=SuggestionListResponse)
async def list_suggestions(
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    target_type: str | None = Query(None, description="Filter by target type"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List suggestions with optional filters and pagination.

    Public read — no auth required.
    Default: open suggestions, sorted by most recent.
    """
    stmt = select(Suggestion)

    if status_filter:
        stmt = stmt.where(Suggestion.status == status_filter)
    else:
        # Default to open
        stmt = stmt.where(Suggestion.status == "open")

    if target_type:
        stmt = stmt.where(Suggestion.target_type == target_type)

    # ── Count total ───────────────────────────────────────────
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    # ── Paginate (most recent first) ──────────────────────────
    offset = (page - 1) * size
    stmt = stmt.order_by(Suggestion.created_at.desc()).offset(offset).limit(size)
    result = await db.execute(stmt)
    suggestions = result.scalars().all()

    # ── Batch-fetch vote counts ───────────────────────────────
    vote_counts = await _get_vote_counts(db, [s.id for s in suggestions])

    # ── Build response ────────────────────────────────────────
    items = [
        SuggestionListItem(
            id=s.id,
            target_type=s.target_type,
            target_id=s.target_id,
            field_path=s.field_path,
            proposed_value=s.proposed_value,
            rationale=s.rationale,
            status=s.status,
            created_at=s.created_at,
            author_display=_author_display(
                s.created_by_user_id, s.created_by_session_id
            ),
            upvotes=vote_counts.get(s.id, {}).get("up", 0),
            downvotes=vote_counts.get(s.id, {}).get("down", 0),
        )
        for s in suggestions
    ]

    return SuggestionListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        has_next=(offset + size) < total,
    )


# ═══════════════════════════════════════════════════════════════
# GET /api/suggestions/{id} — get a single suggestion
# ═══════════════════════════════════════════════════════════════


@router.get("/suggestions/{suggestion_id}", response_model=SuggestionResponse)
async def get_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single suggestion by ID. Public read."""
    result = await db.execute(
        select(Suggestion).where(Suggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()

    if suggestion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found",
        )

    # ── Fetch vote counts for this suggestion ─────────────────
    vote_counts = await _get_vote_counts(db, [suggestion.id])

    return SuggestionResponse(
        id=suggestion.id,
        target_type=suggestion.target_type,
        target_id=suggestion.target_id,
        field_path=suggestion.field_path,
        proposed_value=suggestion.proposed_value,
        rationale=suggestion.rationale,
        status=suggestion.status,
        created_by_user_id=suggestion.created_by_user_id,
        created_by_session_id=suggestion.created_by_session_id,
        created_at=suggestion.created_at,
        decided_at=suggestion.decided_at,
        decided_by_user_id=suggestion.decided_by_user_id,
        applied_at=suggestion.applied_at,
        author_display=_author_display(
            suggestion.created_by_user_id, suggestion.created_by_session_id
        ),
        upvotes=vote_counts.get(suggestion.id, {}).get("up", 0),
        downvotes=vote_counts.get(suggestion.id, {}).get("down", 0),
    )

"""Suggestion endpoints: create, list, detail, decide.

Supported target types:
  POST /api/suggestions          — create a suggestion (anon or contributor)
  GET  /api/suggestions          — list suggestions (public read)
  GET  /api/suggestions/{id}     — get a single suggestion (public read)
  POST /api/suggestions/{id}/decide — reviewer/admin accept or reject

Anon users are identified by the X-Session-Cookie header (a random UUID
the frontend generates and stores in localStorage). Anon suggestions
are rate-limited: 5 per hour per session, 10 per hour per IP.

Contributors are authenticated via JWT. Their suggestions have
created_by_user_id set; rate limiting applies only to role='user'
(reviewer/admin are unlimited).
"""

from __future__ import annotations

import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.anon import check_rate_limit, check_registered_user_rate_limit, get_or_create_anon_session
from app.db import get_db
from app.deps import get_optional_user, require_reviewer
from app.models import Example, Suggestion, User, Vote, Word
from app.promote import _apply_example, _apply_gloss, _apply_new_word, _apply_relation, _apply_word_correction
from app.schemas_suggestion import (
    CreateSuggestionRequest,
    SuggestionListItem,
    SuggestionListResponse,
    SuggestionResponse,
)
from pydantic import BaseModel

router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


VALID_TARGET_TYPES = {"new_word", "word", "gloss", "example", "relation"}


def _normalize_form(text: str) -> str:
    """Lowercase + strip non-alpha (keep apostrophes). Mirrors export script."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _validate_suggestion(req: CreateSuggestionRequest) -> None:
    """Validate the suggestion request based on target_type."""
    if req.target_type not in VALID_TARGET_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid target_type. Must be one of: {VALID_TARGET_TYPES}",
        )

    if req.target_type == "new_word":
        if not req.proposed_value.get("headword"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="new_word suggestions must include 'headword' in proposed_value",
            )

    elif req.target_type == "word":
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

    elif req.target_type == "gloss":
        # Adding a missing translation to an existing word
        # proposed_value must contain language ('sw' or 'en') and text
        if not req.target_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="gloss suggestions must include target_id (the word UUID)",
            )
        lang = req.proposed_value.get("language")
        if lang not in ("sw", "en"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="gloss suggestions must include 'language' ('sw' or 'en') in proposed_value",
            )
        if not req.proposed_value.get("text"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="gloss suggestions must include 'text' (the translation) in proposed_value",
            )

    elif req.target_type == "example":
        # Suggesting a translation for an existing example
        # target_id is the EXAMPLE UUID (not the word UUID)
        # proposed_value: { language: 'sw'|'en', text: '...' }
        if not req.target_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="example suggestions must include target_id (the EXAMPLE UUID)",
            )
        lang = req.proposed_value.get("language")
        if lang not in ("sw", "en"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="example suggestions must include 'language' ('sw' or 'en') in proposed_value",
            )
        if not req.proposed_value.get("text"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="example suggestions must include 'text' (the translation) in proposed_value",
            )

    elif req.target_type == "relation":
        # Linking this word to another word (variation, see_also, etc.)
        # proposed_value must contain related_word (headword or ID) and relation_type
        if not req.target_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="relation suggestions must include target_id (the word UUID)",
            )
        if not req.proposed_value.get("related_word"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="relation suggestions must include 'related_word' (headword or ID) in proposed_value",
            )
        if not req.proposed_value.get("relation_type"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="relation suggestions must include 'relation_type' in proposed_value",
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


async def _get_user_votes(
    db: AsyncSession, suggestion_ids: list[UUID], user_id: UUID | None
) -> dict[UUID, str | None]:
    """Batch-fetch the current user's vote on each suggestion.

    Returns {suggestion_id: 'up' | 'down' | None}.
    If user_id is None, returns all-None.
    """
    if not suggestion_ids or user_id is None:
        return {sid: None for sid in suggestion_ids}

    stmt = select(Vote).where(
        Vote.suggestion_id.in_(suggestion_ids),
        Vote.user_id == user_id,
    )
    result = await db.execute(stmt)
    votes: dict[UUID, str | None] = {sid: None for sid in suggestion_ids}
    for vote in result.scalars().all():
        votes[vote.suggestion_id] = vote.vote
    return votes


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
):
    """Create a new suggestion.

    Authenticated contributors: suggestion is created with created_by_user_id.
    Anonymous visitors: suggestion is created with created_by_session_id,
    and rate limiting applies (5/hour per session, 10/hour per IP).

    The X-Session-Cookie header is read from the request directly
    (the frontend sets it as a custom header).
    """
    _validate_suggestion(req)

    # ── Honeypot check ────────────────────────────────────────
    if req.proposed_value.get("website"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid submission.",
        )

    # ── Duplicate check for new_word suggestions ─────────────
    if req.target_type == "new_word":
        headword = (req.proposed_value.get("headword") or "").strip()
        normalized = _normalize_form(headword)
        if normalized:
            result = await db.execute(
                select(Word).where(
                    Word.normalized_form == normalized,
                    Word.status == "live",
                )
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "This word already exists in the dictionary.",
                        "existing_word_id": str(existing.id),
                        "existing_headword": existing.headword,
                        "existing_slug": existing.slug,
                    },
                )

    # ── Validate target_id existence for example/gloss/relation/word ──
    if req.target_type == "example":
        ex_result = await db.execute(
            select(Example).where(Example.id == req.target_id)
        )
        if ex_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Example not found",
            )
    elif req.target_type in ("gloss", "relation", "word"):
        w_result = await db.execute(
            select(Word).where(Word.id == req.target_id, Word.status == "live")
        )
        if w_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Word not found",
            )

    # ── Resolve the actor + apply rate limiting ──────────────
    if current_user is not None:
        # Authenticated user — rate limit depends on role
        created_by_user_id = current_user.id
        created_by_session_id = None

        # Only rate-limit non-reviewer registered users
        if current_user.role == "user":
            check_registered_user_rate_limit(current_user.id)
    else:
        # Anonymous — need session cookie, create if missing
        x_session_cookie = request.headers.get("X-Session-Cookie")
        ip = request.client.host if request.client else "0.0.0.0"

        session, ip_hash = await get_or_create_anon_session(
            db, x_session_cookie, ip
        )

        # Rate limit check (5/hr per session, 10/hr per IP)
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
        created_at=suggestion.created_at,
        decided_at=suggestion.decided_at,
        decided_by_user_id=suggestion.decided_by_user_id,
        applied_at=suggestion.applied_at,
        author_display=_author_display(
            created_by_user_id, created_by_session_id, current_user
        ),
        upvotes=0,
        downvotes=0,
        user_vote=None,
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
    current_user: User | None = Depends(get_optional_user),
):
    """List suggestions with optional filters and pagination.

    Public read — no auth required. If the caller is authenticated,
    `user_vote` is populated on each item with their vote ('up'|'down'|None).
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

    # ── Batch-fetch vote counts + current user's votes ────────
    sugg_ids = [s.id for s in suggestions]
    vote_counts = await _get_vote_counts(db, sugg_ids)
    user_votes = await _get_user_votes(db, sugg_ids, current_user.id if current_user else None)

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
            created_by_user_id=s.created_by_user_id,
            author_display=_author_display(
                s.created_by_user_id, s.created_by_session_id
            ),
            upvotes=vote_counts.get(s.id, {}).get("up", 0),
            downvotes=vote_counts.get(s.id, {}).get("down", 0),
            user_vote=user_votes.get(s.id),
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
    current_user: User | None = Depends(get_optional_user),
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

    # ── Fetch vote counts + current user's vote ───────────────
    vote_counts = await _get_vote_counts(db, [suggestion.id])
    user_votes = await _get_user_votes(
        db, [suggestion.id], current_user.id if current_user else None
    )

    return SuggestionResponse(
        id=suggestion.id,
        target_type=suggestion.target_type,
        target_id=suggestion.target_id,
        field_path=suggestion.field_path,
        proposed_value=suggestion.proposed_value,
        rationale=suggestion.rationale,
        status=suggestion.status,
        created_by_user_id=suggestion.created_by_user_id,
        created_at=suggestion.created_at,
        decided_at=suggestion.decided_at,
        decided_by_user_id=suggestion.decided_by_user_id,
        applied_at=suggestion.applied_at,
        author_display=_author_display(
            suggestion.created_by_user_id, suggestion.created_by_session_id
        ),
        upvotes=vote_counts.get(suggestion.id, {}).get("up", 0),
        downvotes=vote_counts.get(suggestion.id, {}).get("down", 0),
        user_vote=user_votes.get(suggestion.id),
    )


# ═══════════════════════════════════════════════════════════════
# POST /api/suggestions/{id}/decide — reviewer/admin accept or reject
# ═══════════════════════════════════════════════════════════════


class DecideRequest(BaseModel):
    """Reviewer accepts or rejects a suggestion manually."""

    decision: str  # 'accept' or 'reject'


@router.post("/suggestions/{suggestion_id}/decide")
async def decide_suggestion(
    suggestion_id: UUID,
    req: DecideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_reviewer),
):
    """Reviewer or admin manually accepts or rejects a suggestion.

    Accepting applies the suggestion to the word graph immediately
    (same as auto-promote, but without the voting threshold).
    Rejecting closes it without applying.

    An audit-log entry is written for the decision itself
    (action='suggestion.accept' or 'suggestion.reject').
    """
    if req.decision not in ("accept", "reject"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Decision must be 'accept' or 'reject'",
        )

    result = await db.execute(
        select(Suggestion).where(Suggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    if suggestion.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Suggestion is already {suggestion.status}",
        )

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    if req.decision == "accept":
        # ── Apply the suggestion ──────────────────────────────
        if suggestion.target_type == "new_word":
            await _apply_new_word(db, suggestion, actor_id=current_user.id)
        elif suggestion.target_type == "word":
            await _apply_word_correction(db, suggestion, actor_id=current_user.id)
        elif suggestion.target_type == "gloss":
            await _apply_gloss(db, suggestion, actor_id=current_user.id)
        elif suggestion.target_type == "example":
            await _apply_example(db, suggestion, actor_id=current_user.id)
        elif suggestion.target_type == "relation":
            await _apply_relation(db, suggestion, actor_id=current_user.id)

        suggestion.status = "accepted"
        suggestion.applied_at = now
    else:
        suggestion.status = "rejected"

    suggestion.decided_at = now
    suggestion.decided_by_user_id = current_user.id

    # ── Audit log: the decision itself (separate from the
    #    applied-change log that _apply_* writes) ──────────────
    from app.models import EditLog

    db.add(
        EditLog(
            actor_user_id=current_user.id,
            action="suggestion.accept" if req.decision == "accept" else "suggestion.reject",
            entity_type="suggestion",
            entity_id=suggestion.id,
            after={
                "decision": req.decision,
                "target_type": suggestion.target_type,
                "target_id": str(suggestion.target_id) if suggestion.target_id else None,
                "decided_by": str(current_user.id),
                "decided_by_email": current_user.email,
            },
        )
    )

    await db.commit()

    return {
        "id": str(suggestion.id),
        "status": suggestion.status,
        "decided_at": suggestion.decided_at.isoformat(),
        "decided_by": str(current_user.id),
    }

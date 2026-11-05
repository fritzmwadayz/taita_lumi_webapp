"""Vote endpoints: cast, change, remove vote on a suggestion.

  POST   /api/suggestions/{id}/vote  — cast or change vote (up/down)
  DELETE /api/suggestions/{id}/vote  — remove own vote

Rules:
  - Only authenticated contributors can vote (anon cannot vote — too easy to game)
  - One vote per user per suggestion
  - Voting on your own suggestion is not allowed
  - Repeating the same vote removes it (toggle behavior)
  - After each vote, the auto-promote check runs — if the suggestion
    meets the threshold, it's accepted and applied to the word graph

Auto-promote threshold (checked after each vote):
  - status = 'open'
  - age >= 7 days
  - net_votes (up - down) >= 3
  - at least 2 distinct non-anon upvotes
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models import Suggestion, User, Vote
from app.promote import check_and_promote

router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════


class VoteRequest(BaseModel):
    """Cast or change a vote. vote='up' or 'down'."""

    vote: str = Field(..., description="'up' or 'down'")


class VoteResponse(BaseModel):
    """Response after voting. Includes new counts + the user's current vote."""

    suggestion_id: UUID
    upvotes: int
    downvotes: int
    user_vote: str | None = None  # 'up', 'down', or None if no vote
    promoted: bool = False  # true if this vote triggered auto-promotion


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


async def _get_vote_counts(db: AsyncSession, suggestion_id: UUID) -> dict[str, int]:
    """Get up/down counts for a single suggestion."""
    result = await db.execute(
        select(Vote.vote, func.count().label("count"))
        .where(Vote.suggestion_id == suggestion_id)
        .group_by(Vote.vote)
    )
    counts = {"up": 0, "down": 0}
    for row in result.all():
        if row.vote in counts:
            counts[row.vote] = row.count
    return counts


async def _get_user_vote(
    db: AsyncSession, suggestion_id: UUID, user_id: UUID
) -> str | None:
    """Get the current user's vote on a suggestion, or None."""
    result = await db.execute(
        select(Vote).where(
            Vote.suggestion_id == suggestion_id,
            Vote.user_id == user_id,
        )
    )
    vote = result.scalar_one_or_none()
    return vote.vote if vote else None


# ═══════════════════════════════════════════════════════════════
# POST /api/suggestions/{id}/vote
# ═══════════════════════════════════════════════════════════════


@router.post("/suggestions/{suggestion_id}/vote", response_model=VoteResponse)
async def cast_vote(
    suggestion_id: UUID,
    req: VoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cast or change a vote on a suggestion.

    - Requires authentication (anon cannot vote)
    - Cannot vote on own suggestion
    - Repeating the same vote removes it (toggle)
    - Changing from up→down or down→up updates the existing vote
    - After voting, checks auto-promote threshold
    """
    if req.vote not in ("up", "down"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="vote must be 'up' or 'down'",
        )

    # ── Fetch the suggestion ──────────────────────────────────
    result = await db.execute(
        select(Suggestion).where(Suggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()
    if suggestion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found",
        )

    if suggestion.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot vote on a suggestion with status '{suggestion.status}'",
        )

    # ── Check: cannot vote on own suggestion ─────────────────
    if suggestion.created_by_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot vote on your own suggestion",
        )

    # ── Find existing vote ────────────────────────────────────
    result = await db.execute(
        select(Vote).where(
            Vote.suggestion_id == suggestion_id,
            Vote.user_id == current_user.id,
        )
    )
    existing_vote = result.scalar_one_or_none()

    user_vote: str | None

    if existing_vote is None:
        # No existing vote — create one
        vote = Vote(
            suggestion_id=suggestion_id,
            user_id=current_user.id,
            session_id=None,
            vote=req.vote,
        )
        db.add(vote)
        user_vote = req.vote

    elif existing_vote.vote == req.vote:
        # Same vote repeated — toggle off (remove)
        await db.delete(existing_vote)
        user_vote = None

    else:
        # Different vote — update
        existing_vote.vote = req.vote
        user_vote = req.vote

    await db.flush()

    # ── Get updated counts ────────────────────────────────────
    counts = await _get_vote_counts(db, suggestion_id)

    # ── Auto-promote check ────────────────────────────────────
    promoted = False
    if user_vote is not None:
        promoted = await check_and_promote(db, suggestion)

    await db.commit()

    return VoteResponse(
        suggestion_id=suggestion_id,
        upvotes=counts["up"],
        downvotes=counts["down"],
        user_vote=user_vote,
        promoted=promoted,
    )


# ═══════════════════════════════════════════════════════════════
# DELETE /api/suggestions/{id}/vote
# ═══════════════════════════════════════════════════════════════


@router.delete("/suggestions/{suggestion_id}/vote", response_model=VoteResponse)
async def remove_vote(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove the current user's vote on a suggestion."""
    # ── Find existing vote ────────────────────────────────────
    result = await db.execute(
        select(Vote).where(
            Vote.suggestion_id == suggestion_id,
            Vote.user_id == current_user.id,
        )
    )
    existing_vote = result.scalar_one_or_none()

    if existing_vote is not None:
        await db.delete(existing_vote)
        await db.flush()

    counts = await _get_vote_counts(db, suggestion_id)

    await db.commit()

    return VoteResponse(
        suggestion_id=suggestion_id,
        upvotes=counts["up"],
        downvotes=counts["down"],
        user_vote=None,
        promoted=False,
    )

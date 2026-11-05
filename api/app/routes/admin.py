"""Admin endpoints: user management, suggestion decide, word edit/hide/merge,
audit log, dashboard stats.

All endpoints require admin role (via require_admin dependency).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.deps import require_admin
from app.models import (
    EditLog,
    Gloss,
    Suggestion,
    User,
    Vote,
    Word,
    WordRelation,
)
from app.promote import _apply_new_word, _apply_word_correction
from app.schemas_admin import (
    AdminUserListResponse,
    AdminUserResponse,
    AuditLogEntry,
    AuditLogResponse,
    DashboardStats,
    DecideSuggestionRequest,
    EditWordRequest,
    MergeWordsRequest,
    UpdateUserRequest,
)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _normalize_form(text: str) -> str:
    """Lowercase + strip non-alpha (keep apostrophes)."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ═══════════════════════════════════════════════════════════════
# GET /api/admin/stats — dashboard
# ═══════════════════════════════════════════════════════════════


@router.get("/admin/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get dashboard stats. Admin only."""
    total_words = await db.scalar(
        select(func.count()).where(Word.status == "live")
    ) or 0

    total_users = await db.scalar(select(func.count()).select_from(User)) or 0

    total_suggestions = await db.scalar(
        select(func.count()).select_from(Suggestion)
    ) or 0

    open_suggestions = await db.scalar(
        select(func.count()).where(Suggestion.status == "open")
    ) or 0

    accepted_suggestions = await db.scalar(
        select(func.count()).where(Suggestion.status == "accepted")
    ) or 0

    rejected_suggestions = await db.scalar(
        select(func.count()).where(Suggestion.status == "rejected")
    ) or 0

    total_votes = await db.scalar(select(func.count()).select_from(Vote)) or 0

    # Recent words (last 5)
    recent_words_result = await db.execute(
        select(Word)
        .where(Word.status == "live")
        .order_by(Word.created_at.desc())
        .limit(5)
        .options(selectinload(Word.glosses))
    )
    recent_words = []
    for w in recent_words_result.scalars().unique().all():
        sw_gloss = next((g.text for g in w.glosses if g.language == "sw"), None)
        recent_words.append({
            "id": str(w.id),
            "headword": w.headword,
            "swahili_gloss": sw_gloss,
            "created_at": w.created_at.isoformat(),
        })

    # Recent suggestions (last 5)
    recent_sugg_result = await db.execute(
        select(Suggestion)
        .order_by(Suggestion.created_at.desc())
        .limit(5)
    )
    recent_suggestions = []
    for s in recent_sugg_result.scalars().all():
        recent_suggestions.append({
            "id": str(s.id),
            "target_type": s.target_type,
            "status": s.status,
            "headword": s.proposed_value.get("headword") if isinstance(s.proposed_value, dict) else None,
            "created_at": s.created_at.isoformat(),
        })

    return DashboardStats(
        total_words=total_words,
        total_users=total_users,
        total_suggestions=total_suggestions,
        open_suggestions=open_suggestions,
        accepted_suggestions=accepted_suggestions,
        rejected_suggestions=rejected_suggestions,
        total_votes=total_votes,
        recent_words=recent_words,
        recent_suggestions=recent_suggestions,
    )


# ═══════════════════════════════════════════════════════════════
# GET /api/admin/users — list users
# ═══════════════════════════════════════════════════════════════


@router.get("/admin/users", response_model=AdminUserListResponse)
async def list_users(
    q: str | None = Query(None, description="Search by email or display name"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List all users. Admin only."""
    stmt = select(User)

    if q:
        search = f"%{q.lower()}%"
        stmt = stmt.where(
            (User.email.ilike(search)) | (User.display_name.ilike(search))
        )

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    # Paginate
    offset = (page - 1) * size
    stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(size)
    result = await db.execute(stmt)
    users = result.scalars().all()

    items = [
        AdminUserResponse(
            id=u.id,
            email=u.email,
            display_name=u.display_name,
            role=u.role,
            is_blocked=u.is_blocked,
            created_at=u.created_at,
            last_seen_at=u.last_seen_at,
        )
        for u in users
    ]

    return AdminUserListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        has_next=(offset + size) < total,
    )


# ═══════════════════════════════════════════════════════════════
# PATCH /api/admin/users/{id} — update role / blocked
# ═══════════════════════════════════════════════════════════════


@router.patch("/admin/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: UUID,
    req: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update a user's role or blocked status. Admin only.

    Cannot block or demote yourself.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # ── Safety: can't modify yourself ─────────────────────────
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot modify your own account.",
        )

    if req.role is not None:
        if req.role not in ("contributor", "admin"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Role must be 'contributor' or 'admin'",
            )
        user.role = req.role

    if req.is_blocked is not None:
        user.is_blocked = req.is_blocked

    await db.commit()
    await db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_blocked=user.is_blocked,
        created_at=user.created_at,
        last_seen_at=user.last_seen_at,
    )


# ═══════════════════════════════════════════════════════════════
# POST /api/admin/suggestions/{id}/decide — accept/reject
# ═══════════════════════════════════════════════════════════════


@router.post("/admin/suggestions/{suggestion_id}/decide")
async def decide_suggestion(
    suggestion_id: UUID,
    req: DecideSuggestionRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin manually accepts or rejects a suggestion.

    Accepting applies the suggestion to the word graph (same as auto-promote).
    Rejecting closes it without applying.
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

    now = datetime.now(timezone.utc)

    if req.decision == "accept":
        # ── Apply the suggestion ──────────────────────────────
        if suggestion.target_type == "new_word":
            await _apply_new_word(db, suggestion, actor_id=admin.id)
        elif suggestion.target_type == "word":
            await _apply_word_correction(db, suggestion, actor_id=admin.id)

        suggestion.status = "accepted"
        suggestion.applied_at = now
    else:
        suggestion.status = "rejected"

    suggestion.decided_at = now
    suggestion.decided_by_user_id = admin.id

    await db.commit()

    return {
        "id": str(suggestion.id),
        "status": suggestion.status,
        "decided_at": suggestion.decided_at.isoformat(),
        "decided_by": str(admin.id),
    }


# ═══════════════════════════════════════════════════════════════
# PATCH /api/admin/words/{id} — edit a word
# ═══════════════════════════════════════════════════════════════


@router.patch("/admin/words/{word_id}")
async def edit_word(
    word_id: UUID,
    req: EditWordRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin edits a word's fields. Only provided fields are updated.

    Gloss fields (swahili_gloss, english_gloss) update the corresponding
    Gloss rows — creates them if they don't exist.
    """
    result = await db.execute(
        select(Word)
        .where(Word.id == word_id)
        .options(selectinload(Word.glosses))
    )
    word = result.scalar_one_or_none()
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")

    before = {}
    after = {}

    # ── Scalar fields ─────────────────────────────────────────
    if req.headword is not None:
        before["headword"] = word.headword
        word.headword = req.headword.strip()
        word.normalized_form = _normalize_form(req.headword)
        after["headword"] = word.headword

    if req.part_of_speech is not None:
        before["part_of_speech"] = word.part_of_speech
        word.part_of_speech = req.part_of_speech or None
        after["part_of_speech"] = word.part_of_speech

    if req.noun_class is not None:
        before["noun_class"] = word.noun_class
        word.noun_class = req.noun_class or None
        after["noun_class"] = word.noun_class

    if req.dialect is not None:
        before["dialect"] = word.dialect
        word.dialect = req.dialect or None
        after["dialect"] = word.dialect

    if req.literal_translation is not None:
        before["literal_translation"] = word.literal_translation
        word.literal_translation = req.literal_translation or None
        after["literal_translation"] = word.literal_translation

    if req.morphology_notes is not None:
        before["morphology_notes"] = word.morphology_notes
        word.morphology_notes = req.morphology_notes or None
        after["morphology_notes"] = word.morphology_notes

    # ── Gloss fields ──────────────────────────────────────────
    if req.swahili_gloss is not None:
        sw_gloss = next((g for g in word.glosses if g.language == "sw"), None)
        if sw_gloss:
            before["swahili_gloss"] = sw_gloss.text
            sw_gloss.text = req.swahili_gloss.strip()
        else:
            sw_gloss = Gloss(word_id=word.id, language="sw", text=req.swahili_gloss.strip())
            db.add(sw_gloss)
        after["swahili_gloss"] = req.swahili_gloss.strip()

    if req.english_gloss is not None:
        en_gloss = next((g for g in word.glosses if g.language == "en"), None)
        if en_gloss:
            before["english_gloss"] = en_gloss.text
            en_gloss.text = req.english_gloss.strip()
        else:
            en_gloss = Gloss(word_id=word.id, language="en", text=req.english_gloss.strip())
            db.add(en_gloss)
        after["english_gloss"] = req.english_gloss.strip()

    # ── Audit log ─────────────────────────────────────────────
    if before or after:
        word.reviewed_at = datetime.now(timezone.utc)
        word.reviewed_by_user_id = admin.id
        db.add(
            EditLog(
                actor_user_id=admin.id,
                action="update",
                entity_type="word",
                entity_id=word.id,
                before=before or None,
                after={**after, "source": "admin_edit"},
            )
        )

    await db.commit()

    return {"id": str(word.id), "updated_fields": list(after.keys())}


# ═══════════════════════════════════════════════════════════════
# POST /api/admin/words/{id}/hide — soft-delete a word
# ═══════════════════════════════════════════════════════════════


@router.post("/admin/words/{word_id}/hide")
async def hide_word(
    word_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Soft-delete a word (set status='hidden'). Admin only."""
    result = await db.execute(select(Word).where(Word.id == word_id))
    word = result.scalar_one_or_none()
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")

    before = {"status": word.status}
    word.status = "hidden"

    db.add(
        EditLog(
            actor_user_id=admin.id,
            action="delete",
            entity_type="word",
            entity_id=word.id,
            before=before,
            after={"status": "hidden", "source": "admin_hide"},
        )
    )

    await db.commit()

    return {"id": str(word.id), "status": "hidden"}


# ═══════════════════════════════════════════════════════════════
# POST /api/admin/words/merge — merge two words
# ═══════════════════════════════════════════════════════════════


@router.post("/admin/words/merge")
async def merge_words(
    req: MergeWordsRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Merge source word into target word. Source is soft-deleted (status='merged').

    - Source word's relations are re-pointed to the target
    - Source word's glosses and examples are moved to the target (if not duplicates)
    - Source word is set to status='merged'
    - Audit log entry written
    """
    if req.source_id == req.target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot merge a word into itself.",
        )

    # ── Fetch both words ──────────────────────────────────────
    source_result = await db.execute(
        select(Word)
        .where(Word.id == req.source_id)
        .options(selectinload(Word.glosses), selectinload(Word.examples))
    )
    source = source_result.scalar_one_or_none()

    target_result = await db.execute(
        select(Word)
        .where(Word.id == req.target_id)
        .options(selectinload(Word.glosses), selectinload(Word.examples))
    )
    target = target_result.scalar_one_or_none()

    if source is None:
        raise HTTPException(status_code=404, detail="Source word not found")
    if target is None:
        raise HTTPException(status_code=404, detail="Target word not found")

    # ── Re-point relations from source → target ───────────────
    # Outgoing: source.from_word_id → change to target
    out_result = await db.execute(
        select(WordRelation).where(WordRelation.from_word_id == source.id)
    )
    for rel in out_result.scalars().all():
        if rel.to_word_id != target.id:  # don't create self-relation
            rel.from_word_id = target.id

    # Incoming: source.to_word_id → change to target
    in_result = await db.execute(
        select(WordRelation).where(WordRelation.to_word_id == source.id)
    )
    for rel in in_result.scalars().all():
        if rel.from_word_id != target.id:
            rel.to_word_id = target.id

    # ── Move glosses (skip duplicates) ────────────────────────
    target_langs = {g.language for g in target.glosses}
    for g in source.glosses:
        if g.language not in target_langs:
            g.word_id = target.id
            target_langs.add(g.language)

    # ── Move examples ─────────────────────────────────────────
    for ex in source.examples:
        ex.word_id = target.id

    # ── Soft-delete source ────────────────────────────────────
    source.status = "merged"

    # ── Audit log ─────────────────────────────────────────────
    db.add(
        EditLog(
            actor_user_id=admin.id,
            action="merge",
            entity_type="word",
            entity_id=target.id,
            before={"merged_from": str(source.id), "source_headword": source.headword},
            after={"target_headword": target.headword, "source": "admin_merge"},
        )
    )

    await db.commit()

    return {
        "merged_into": str(target.id),
        "hidden": str(source.id),
        "target_headword": target.headword,
    }


# ═══════════════════════════════════════════════════════════════
# GET /api/admin/audit-log — query audit trail
# ═══════════════════════════════════════════════════════════════


@router.get("/admin/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),
    action: str | None = Query(None, description="Filter by action"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Query the audit log. Admin only."""
    stmt = select(EditLog)

    if entity_type:
        stmt = stmt.where(EditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(EditLog.entity_id == entity_id)
    if action:
        stmt = stmt.where(EditLog.action == action)

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    # Paginate
    offset = (page - 1) * size
    stmt = stmt.order_by(EditLog.created_at.desc()).offset(offset).limit(size)
    result = await db.execute(stmt)
    entries = result.scalars().all()

    items = [
        AuditLogEntry(
            id=e.id,
            actor_user_id=e.actor_user_id,
            actor_session_id=e.actor_session_id,
            action=e.action,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            before=e.before,
            after=e.after,
            created_at=e.created_at,
        )
        for e in entries
    ]

    return AuditLogResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        has_next=(offset + size) < total,
    )

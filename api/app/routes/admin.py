"""Admin endpoints: user management, suggestion decide, word edit/hide/merge,
audit log, dashboard stats.

All endpoints require admin role (via require_admin dependency).

Audit log shape mapping (DB → API):
  The DB table `edit_log` has columns:
    actor_user_id, actor_session_id, action, entity_type, entity_id, before, after

  The public API shape (integration doc 4.8) is:
    actor_id, actor_email, actor_role, action, target_type, target_id, details

  The mapping is done at the route layer:
    - actor_user_id    → actor_id
    - JOIN users       → actor_email, actor_role
    - action           → mapped via _map_action() to dotted namespace
    - entity_type      → target_type
    - entity_id        → target_id
    - before + after   → merged into a single `details` JSON

  Action namespace (public):
    word.create, word.update, word.hide, word.merge, word.import
    translation.create
    example.update
    relation.create
    suggestion.accept, suggestion.reject
    user.role.change, user.block, user.unblock
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
    Example,
    Translation,
    Suggestion,
    User,
    Vote,
    Word,
    WordRelationship,
    WordVariation,
)
from app.promote import _apply_example, _apply_new_example, _apply_new_word, _apply_relation, _apply_relationship, _apply_translation, _apply_variation, _apply_word_correction
from app.schemas import WordListItem
from app.schemas_admin import (
    AdminUserListResponse,
    AdminUserResponse,
    AuditLogEntry,
    AuditLogResponse,
    DashboardStats,
    DecideSuggestionRequest,
    EditWordRequest,
    MergeWordsRequest,
    RecentSuggestionItem,
    UpdateUserRequest,
)
from app.slugs import generate_unique_slug

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


def _map_action(db_action: str, entity_type: str, after: dict | None) -> str:
    """Map an internal edit_log action to the public dotted namespace.

    Internal actions stored in the DB are bare verbs: 'create', 'update',
    'delete', 'import', 'merge', 'suggestion.accept', 'suggestion.reject',
    'user.role.change', 'user.block', 'user.unblock'.

    For the bare-verb cases, we qualify them with the entity_type to get
    the public dotted form (e.g. 'create' on a 'word' → 'word.create').

    The qualified forms (suggestion.accept, user.role.change, etc.) are
    written directly by the routes that produce them and pass through
    unchanged.

    Special case: 'delete' on a word is rendered as 'word.hide' (since
    soft-delete is the only delete path), or 'word.merge' if the after
    payload indicates a merge.
    """
    # Already-qualified actions pass through
    if "." in db_action:
        return db_action

    if db_action == "delete":
        if entity_type == "word":
            return "word.hide"
        return f"{entity_type}.delete"

    if db_action == "merge":
        return "word.merge"

    # Bare verbs qualified with entity_type
    return f"{entity_type}.{db_action}"


def _build_audit_entry(
    e: EditLog,
    actor_email: str | None,
    actor_role: str | None,
) -> AuditLogEntry:
    """Convert an EditLog row to the public AuditLogEntry shape."""
    # Merge before + after into a single `details` payload.
    # If both are None, details is None. If only one is present, details
    # is just that dict. If both, details = {before: ..., after: ...}.
    if e.before is None and e.after is None:
        details = None
    elif e.before is None:
        details = e.after
    elif e.after is None:
        details = e.before
    else:
        details = {"before": e.before, "after": e.after}

    return AuditLogEntry(
        id=e.id,
        created_at=e.created_at,
        actor_id=e.actor_user_id,
        actor_email=actor_email,
        actor_role=actor_role,
        action=_map_action(e.action, e.entity_type, e.after),
        target_type=e.entity_type,
        target_id=e.entity_id,
        details=details,
    )


async def _resolve_actor_emails(
    db: AsyncSession, entries: list[EditLog]
) -> dict[UUID, tuple[str | None, str | None]]:
    """Batch-fetch email + role for all distinct actors in the entries.

    Returns {actor_user_id: (email, role)}.
    """
    actor_ids = {e.actor_user_id for e in entries if e.actor_user_id is not None}
    if not actor_ids:
        return {}

    result = await db.execute(
        select(User.id, User.email, User.role).where(User.id.in_(actor_ids))
    )
    return {row.id: (row.email, row.role) for row in result.all()}


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

    # Recent words (last 5) — full WordListItem shape
    recent_words_result = await db.execute(
        select(Word)
        .where(Word.status == "live")
        .order_by(Word.created_at.desc())
        .limit(5)
        .options(selectinload(Word.translations))
    )
    recent_word_rows = recent_words_result.scalars().unique().all()

    # Batch-check which recent words have variations or relationships
    recent_word_ids = [w.id for w in recent_word_rows]
    if recent_word_ids:
        recent_with_relations: set[UUID] = set()

        # Variations: bidirectional, check both sides
        var_out = (
            select(WordVariation.word_id.label("wid"))
            .where(WordVariation.word_id.in_(recent_word_ids))
        )
        var_in = (
            select(WordVariation.other_word_id.label("wid"))
            .where(WordVariation.other_word_id.in_(recent_word_ids))
        )
        # Union the two variation queries (2-way check)
        var_combined = var_out.union(var_in)
        var_result = await db.execute(var_combined)
        for row in var_result.all():
            recent_with_relations.add(row[0])

        # Relationships: same — both directions
        rel_out = (
            select(WordRelationship.word_id.label("wid"))
            .where(WordRelationship.word_id.in_(recent_word_ids))
        )
        rel_in = (
            select(WordRelationship.other_word_id.label("wid"))
            .where(WordRelationship.other_word_id.in_(recent_word_ids))
        )
        rel_combined = rel_out.union(rel_in)
        rel_result = await db.execute(rel_combined)
        for row in rel_result.all():
            recent_with_relations.add(row[0])
    else:
        recent_with_relations = set()

    recent_words: list[WordListItem] = []
    for w in recent_word_rows:
        sw_translation = next((g.text for g in w.translations if g.language == "sw"), None)
        en_translation = next((g.text for g in w.translations if g.language == "en"), None)
        recent_words.append(WordListItem(
            id=w.id,
            slug=w.slug,
            headword=w.headword,
            part_of_speech=w.part_of_speech,
            noun_class=w.noun_class,
            dialect=w.dialect,
            swahili_translation=sw_translation,
            english_translation=en_translation,
            has_relations=w.id in recent_with_relations,
        ))

    # Recent suggestions (last 5)
    recent_sugg_result = await db.execute(
        select(Suggestion)
        .order_by(Suggestion.created_at.desc())
        .limit(5)
    )
    recent_suggestions: list[RecentSuggestionItem] = []
    for s in recent_sugg_result.scalars().all():
        headword = None
        if isinstance(s.proposed_value, dict):
            headword = s.proposed_value.get("headword")
        recent_suggestions.append(RecentSuggestionItem(
            id=s.id,
            headword=headword,
            target_type=s.target_type,
            status=s.status,
            created_at=s.created_at,
        ))

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

    Cannot block or demote yourself. Writes an audit-log entry for
    every role or blocked-status change.
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

    before = {}
    after = {}

    if req.role is not None:
        if req.role not in ("user", "reviewer", "admin"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Role must be 'user', 'reviewer', or 'admin'",
            )
        if user.role != req.role:
            before["role"] = user.role
            user.role = req.role
            after["role"] = req.role

    if req.is_blocked is not None:
        if user.is_blocked != req.is_blocked:
            before["is_blocked"] = user.is_blocked
            user.is_blocked = req.is_blocked
            after["is_blocked"] = req.is_blocked

    # ── Audit log for role change / block / unblock ───────────
    if before or after:
        # Decide on the dotted action name
        if "role" in after and "is_blocked" not in after:
            action = "user.role.change"
        elif "is_blocked" in after and after["is_blocked"] is True:
            action = "user.block"
        elif "is_blocked" in after and after["is_blocked"] is False:
            action = "user.unblock"
        else:
            # Both changed — log as role.change (the more material change)
            action = "user.role.change"

        db.add(
            EditLog(
                actor_user_id=admin.id,
                action=action,
                entity_type="user",
                entity_id=user.id,
                before=before or None,
                after={**after, "by_admin": admin.email},
            )
        )

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

    now = datetime.now(timezone.utc)

    if req.decision == "accept":
        # ── Apply the suggestion ──────────────────────────────
        if suggestion.target_type == "new_word":
            await _apply_new_word(db, suggestion, actor_id=admin.id)
        elif suggestion.target_type == "word":
            await _apply_word_correction(db, suggestion, actor_id=admin.id)
        elif suggestion.target_type in ("translation", "gloss"):
            await _apply_translation(db, suggestion, actor_id=admin.id)
        elif suggestion.target_type == "example":
            await _apply_example(db, suggestion, actor_id=admin.id)
        elif suggestion.target_type == "new_example":
            await _apply_new_example(db, suggestion, actor_id=admin.id)
        elif suggestion.target_type == "relation":
            await _apply_relation(db, suggestion, actor_id=admin.id)
        elif suggestion.target_type == "variation":
            await _apply_variation(db, suggestion, actor_id=admin.id)
        elif suggestion.target_type == "relationship":
            await _apply_relationship(db, suggestion, actor_id=admin.id)

        suggestion.status = "accepted"
        suggestion.applied_at = now
    else:
        suggestion.status = "rejected"

    suggestion.decided_at = now
    suggestion.decided_by_user_id = admin.id

    # ── Audit log: the decision itself ────────────────────────
    db.add(
        EditLog(
            actor_user_id=admin.id,
            action="suggestion.accept" if req.decision == "accept" else "suggestion.reject",
            entity_type="suggestion",
            entity_id=suggestion.id,
            after={
                "decision": req.decision,
                "target_type": suggestion.target_type,
                "target_id": str(suggestion.target_id) if suggestion.target_id else None,
                "decided_by": str(admin.id),
                "decided_by_email": admin.email,
            },
        )
    )

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

    Translation fields (swahili_translation, english_translation) update the corresponding
    Translation rows — creates them if they don't exist.

    If `examples` is provided, it REPLACES the word's example set: existing
    examples not in the list are deleted, examples with a matching `id` are
    updated, examples without an `id` are created.

    Returns {id, slug, updated_fields}.
    """
    result = await db.execute(
        select(Word)
        .where(Word.id == word_id)
        .options(selectinload(Word.translations), selectinload(Word.examples))
    )
    word = result.scalar_one_or_none()
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")

    before = {}
    after = {}

    # ── Scalar fields ─────────────────────────────────────────
    if req.headword is not None:
        before["headword"] = word.headword
        before["slug"] = word.slug
        word.headword = req.headword.strip()
        word.normalized_form = _normalize_form(req.headword)
        word.slug = await generate_unique_slug(
            db, req.headword, exclude_word_id=word.id
        )
        after["headword"] = word.headword
        after["slug"] = word.slug

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

    # ── Translation fields ──────────────────────────────────────────
    if req.swahili_translation is not None:
        sw_translation = next((g for g in word.translations if g.language == "sw"), None)
        if sw_translation:
            before["swahili_translation"] = sw_translation.text
            sw_translation.text = req.swahili_translation.strip()
        else:
            sw_translation = Translation(word_id=word.id, language="sw", text=req.swahili_translation.strip())
            db.add(sw_translation)
        after["swahili_translation"] = req.swahili_translation.strip()

    if req.english_translation is not None:
        en_translation = next((g for g in word.translations if g.language == "en"), None)
        if en_translation:
            before["english_translation"] = en_translation.text
            en_translation.text = req.english_translation.strip()
        else:
            en_translation = Translation(word_id=word.id, language="en", text=req.english_translation.strip())
            db.add(en_translation)
        after["english_translation"] = req.english_translation.strip()

    # ── Examples (replace strategy) ───────────────────────────
    if req.examples is not None:
        existing_by_id = {e.id: e for e in word.examples}
        kept_ids = {ex.id for ex in req.examples if ex.id is not None}

        # Delete examples not in the new set
        for ex_id, ex_obj in existing_by_id.items():
            if ex_id not in kept_ids:
                await db.delete(ex_obj)

        before["examples"] = [
            {"id": str(e.id), "taita_text": e.taita_text} for e in word.examples
        ]
        after["examples"] = []

        for ex in req.examples:
            if ex.id is not None and ex.id in existing_by_id:
                ex_obj = existing_by_id[ex.id]
                ex_obj.taita_text = ex.taita_text.strip()
                ex_obj.swahili_text = ex.swahili_text.strip() if ex.swahili_text else None
                ex_obj.english_text = ex.english_text.strip() if ex.english_text else None
                ex_obj.source_ref = ex.source_ref
            else:
                new_ex = Example(
                    word_id=word.id,
                    taita_text=ex.taita_text.strip(),
                    swahili_text=ex.swahili_text.strip() if ex.swahili_text else None,
                    english_text=ex.english_text.strip() if ex.english_text else None,
                    source_ref=ex.source_ref,
                )
                db.add(new_ex)
            after["examples"].append({
                "id": str(ex.id) if ex.id else None,
                "taita_text": ex.taita_text,
                "swahili_text": ex.swahili_text,
                "english_text": ex.english_text,
            })

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
                after={**after, "source": "admin_edit", "by_admin": admin.email},
            )
        )

    await db.commit()

    return {"id": str(word.id), "slug": word.slug, "updated_fields": list(after.keys())}


# ═══════════════════════════════════════════════════════════════
# POST /api/admin/words/{id}/hide — soft-delete a word
# ═══════════════════════════════════════════════════════════════


@router.post("/admin/words/{word_id}/hide")
async def hide_word(
    word_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Soft-delete a word (set status='hidden'). Admin only.

    Audit-logged as action='word.hide'.
    """
    result = await db.execute(select(Word).where(Word.id == word_id))
    word = result.scalar_one_or_none()
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")

    before = {"status": word.status}
    word.status = "hidden"

    db.add(
        EditLog(
            actor_user_id=admin.id,
            action="delete",  # _map_action() will surface this as 'word.hide'
            entity_type="word",
            entity_id=word.id,
            before=before,
            after={"status": "hidden", "source": "admin_hide", "by_admin": admin.email},
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
    - Source word's translations and examples are moved to the target (if not duplicates)
    - Source word is set to status='merged'
    - Audit log entry written (action='word.merge')
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
        .options(selectinload(Word.translations), selectinload(Word.examples))
    )
    source = source_result.scalar_one_or_none()

    target_result = await db.execute(
        select(Word)
        .where(Word.id == req.target_id)
        .options(selectinload(Word.translations), selectinload(Word.examples))
    )
    target = target_result.scalar_one_or_none()

    if source is None:
        raise HTTPException(status_code=404, detail="Source word not found")
    if target is None:
        raise HTTPException(status_code=404, detail="Target word not found")

    # ── Re-point variations from source → target ──────────────
    # Variations are bidirectional; check both word_id and other_word_id sides.
    var_out_result = await db.execute(
        select(WordVariation).where(WordVariation.word_id == source.id)
    )
    for var in var_out_result.scalars().all():
        if var.other_word_id != target.id:  # don't create self-variation
            var.word_id = target.id

    var_in_result = await db.execute(
        select(WordVariation).where(WordVariation.other_word_id == source.id)
    )
    for var in var_in_result.scalars().all():
        if var.word_id != target.id:
            var.other_word_id = target.id

    # ── Re-point relationships from source → target ───────────
    rel_out_result = await db.execute(
        select(WordRelationship).where(WordRelationship.word_id == source.id)
    )
    for rel in rel_out_result.scalars().all():
        if rel.other_word_id != target.id:
            rel.word_id = target.id

    rel_in_result = await db.execute(
        select(WordRelationship).where(WordRelationship.other_word_id == source.id)
    )
    for rel in rel_in_result.scalars().all():
        if rel.word_id != target.id:
            rel.other_word_id = target.id

    # ── Move translations (skip duplicates) ────────────────────────
    target_langs = {g.language for g in target.translations}
    for g in source.translations:
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
            action="merge",  # _map_action() will surface this as 'word.merge'
            entity_type="word",
            entity_id=target.id,
            before={"merged_from": str(source.id), "source_headword": source.headword},
            after={"target_headword": target.headword, "source": "admin_merge", "by_admin": admin.email},
        )
    )

    await db.commit()

    return {
        "merged_into": str(target.id),
        "merged_into_slug": target.slug,
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
    """Query the audit log. Admin only.

    Returns entries in the public API shape (4.8):
      {id, created_at, actor_id, actor_email, actor_role,
       action, target_type, target_id, details}

    The `action` filter accepts either the internal DB form ('create',
    'update', 'delete', 'merge', 'import') or the public dotted form
    ('word.create', 'word.hide', 'user.role.change', etc.).
    """
    stmt = select(EditLog)

    if entity_type:
        stmt = stmt.where(EditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(EditLog.entity_id == entity_id)
    if action:
        # Accept both bare and dotted forms: 'word.create' or 'create'
        if "." in action:
            # Dotted — strip the entity prefix and match the bare verb
            # (the dotted form is computed by _map_action at read time)
            bare = action.split(".", 1)[1]
            stmt = stmt.where(EditLog.action == bare)
        else:
            stmt = stmt.where(EditLog.action == action)

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    # Paginate
    offset = (page - 1) * size
    stmt = stmt.order_by(EditLog.created_at.desc()).offset(offset).limit(size)
    result = await db.execute(stmt)
    entries = result.scalars().all()

    # ── Batch-resolve actor email + role ──────────────────────
    actor_map = await _resolve_actor_emails(db, entries)

    items = [
        _build_audit_entry(
            e,
            actor_email=actor_map.get(e.actor_user_id, (None, None))[0] if e.actor_user_id else None,
            actor_role=actor_map.get(e.actor_user_id, (None, None))[1] if e.actor_user_id else None,
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

"""Word endpoints: list, detail, search, create, edit.

  GET   /api/words                 — paginated list with optional filters
  GET   /api/words/{slug_or_id}    — full word detail (accepts slug OR uuid)
  GET   /api/search?q=             — fuzzy search using pg_trgm
  POST  /api/words                 — reviewer+ creates a live word directly
  PATCH /api/words/{id}            — reviewer+ edits a word's fields
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.deps import require_reviewer
from app.models import EditLog, Example, Gloss, Suggestion, User, Word, WordRelation
from app.schemas import (
    ExampleOut,
    GlossOut,
    RelationOut,
    SearchResponse,
    SearchResultItem,
    WordDetail,
    WordListItem,
    WordListResponse,
)
from app.slugs import generate_unique_slug
from pydantic import BaseModel, Field

router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# Create / edit word request schemas
# ═══════════════════════════════════════════════════════════════


class ExampleInput(BaseModel):
    """An example provided when creating or editing a word.

    If `id` is provided on edit, the existing example is updated; otherwise
    a new example is created. Translations are paired: taita_text is
    required, swahili_text and english_text are optional (the frontend will
    offer readers a non-confrontational option to suggest missing ones via
    POST /api/suggestions with target_type='example').
    """

    id: UUID | None = None
    taita_text: str = Field(..., min_length=1)
    swahili_text: str | None = None
    english_text: str | None = None
    source_ref: str | None = None


class CreateWordRequest(BaseModel):
    """Request body for POST /api/words — reviewer adds a live word."""

    headword: str = Field(..., min_length=1, max_length=200)
    part_of_speech: str | None = None
    noun_class: str | None = None
    dialect: str | None = None
    literal_translation: str | None = None
    morphology_notes: str | None = None
    swahili_gloss: str | None = None
    english_gloss: str | None = None
    examples: list[ExampleInput] | None = None


class EditWordRequest(BaseModel):
    """Edit a word's fields. All fields optional — only provided fields are updated.

    `examples` (if provided) REPLACES the word's example set: existing examples
    not in the list are deleted, examples with a matching `id` are updated,
    examples without an `id` are created.
    """

    headword: str | None = None
    part_of_speech: str | None = None
    noun_class: str | None = None
    dialect: str | None = None
    literal_translation: str | None = None
    morphology_notes: str | None = None
    swahili_gloss: str | None = None
    english_gloss: str | None = None
    examples: list[ExampleInput] | None = None


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _gloss_text(glosses: list[Gloss], language: str) -> str | None:
    """Extract the text of the first gloss matching a language, or None."""
    for g in glosses:
        if g.language == language:
            return g.text
    return None


async def _batch_has_relations(
    session: AsyncSession, word_ids: list[UUID]
) -> set[UUID]:
    """Check which words have any relations (incoming or outgoing).

    Returns a set of word IDs that have at least one relation.
    Uses a single query instead of N+1.
    """
    if not word_ids:
        return set()

    # Union outgoing and incoming relation targets, then distinct
    out_subq = (
        select(WordRelation.from_word_id.label("word_id"))
        .where(WordRelation.from_word_id.in_(word_ids))
    )
    in_subq = (
        select(WordRelation.to_word_id.label("word_id"))
        .where(WordRelation.to_word_id.in_(word_ids))
    )
    stmt = select(out_subq.union(in_subq).subquery().c.word_id)
    result = await session.execute(stmt)
    return {row[0] for row in result.all()}


def _normalize_form(text: str) -> str:
    """Lowercase + strip non-alpha (keep apostrophes). Mirrors export script."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_uuid(s: str) -> bool:
    """Return True if `s` looks like a UUID (with or without dashes)."""
    try:
        UUID(s)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


async def _fetch_word_relations(
    db: AsyncSession, word_id: UUID
) -> list[RelationOut]:
    """Fetch all relations for a word (both directions) as RelationOut list.

    Each relation includes the other word's slug so the frontend can build
    /words/{slug} links without an extra lookup.
    """
    # Outgoing: this word → other
    out_stmt = (
        select(WordRelation, Word.headword, Word.slug)
        .join(Word, WordRelation.to_word_id == Word.id)
        .where(WordRelation.from_word_id == word_id)
    )
    # Incoming: other → this word
    in_stmt = (
        select(WordRelation, Word.headword, Word.slug)
        .join(Word, WordRelation.from_word_id == Word.id)
        .where(WordRelation.to_word_id == word_id)
    )

    relations: list[RelationOut] = []

    out_result = await db.execute(out_stmt)
    for rel, other_headword, other_slug in out_result.all():
        relations.append(
            RelationOut(
                other_word_id=rel.to_word_id,
                other_headword=other_headword,
                other_slug=other_slug,
                relation_type=rel.relation_type,
                direction="outgoing",
            )
        )

    in_result = await db.execute(in_stmt)
    for rel, other_headword, other_slug in in_result.all():
        relations.append(
            RelationOut(
                other_word_id=rel.from_word_id,
                other_headword=other_headword,
                other_slug=other_slug,
                relation_type=rel.relation_type,
                direction="incoming",
            )
        )

    return relations


def _build_word_detail(word: Word) -> WordDetail:
    """Build a WordDetail response from a Word ORM object (with glosses,
    examples, and relations already loaded/computed)."""
    return WordDetail(
        id=word.id,
        slug=word.slug,
        headword=word.headword,
        part_of_speech=word.part_of_speech,
        noun_class=word.noun_class,
        dialect=word.dialect,
        literal_translation=word.literal_translation,
        morphology_notes=word.morphology_notes,
        status=word.status,
        created_at=word.created_at,
        glosses=[GlossOut(language=g.language, text=g.text) for g in word.glosses],
        examples=[
            ExampleOut(
                id=e.id,
                taita_text=e.taita_text,
                swahili_text=e.swahili_text,
                english_text=e.english_text,
                source_ref=e.source_ref,
            )
            for e in word.examples
        ],
        relations=[],  # populated by caller if needed
    )


# ═══════════════════════════════════════════════════════════════
# GET /api/words — paginated list with filters
# ═══════════════════════════════════════════════════════════════


@router.get("/words", response_model=WordListResponse)
async def list_words(
    q: str | None = Query(None, description="Optional fuzzy search query"),
    pos: str | None = Query(None, description="Filter by part of speech"),
    dialect: str | None = Query(None, description="Filter by dialect"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
    db: AsyncSession = Depends(get_db),
):
    """List words with optional filters and pagination.

    If `q` is provided, results are ranked by trigram similarity to the query.
    Otherwise, results are ordered by frequency (desc) then headword (asc).
    """
    # ── Build base query ──────────────────────────────────────
    stmt = select(Word).where(Word.status == "live")

    if pos:
        stmt = stmt.where(Word.part_of_speech == pos)
    if dialect:
        stmt = stmt.where(Word.dialect == dialect)

    # ── Apply search if q is provided ─────────────────────────
    if q:
        normalized_q = q.lower().strip()
        # Use trigram similarity operator (%) for fuzzy match,
        # plus ILIKE for prefix matches that trigram might miss.
        stmt = stmt.where(
            or_(
                Word.normalized_form.op("%")(normalized_q),
                Word.headword.ilike(f"%{normalized_q}%"),
                Word.slug.ilike(f"%{normalized_q}%"),
            )
        )
        # Rank by similarity
        stmt = stmt.order_by(
            func.similarity(Word.normalized_form, normalized_q).desc(),
            Word.headword.asc(),
        )
    else:
        stmt = stmt.order_by(Word.created_at.desc(), Word.headword.asc())

    # ── Count total (before pagination) ───────────────────────
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    # ── Paginate ──────────────────────────────────────────────
    offset = (page - 1) * size
    stmt = stmt.offset(offset).limit(size).options(selectinload(Word.glosses))
    result = await db.execute(stmt)
    words = result.scalars().unique().all()

    # ── Batch-check which words have relations (1 query, not N) ─
    word_ids = [w.id for w in words]
    words_with_relations = await _batch_has_relations(db, word_ids)

    # ── Build response items ──────────────────────────────────
    items: list[WordListItem] = []
    for w in words:
        items.append(
            WordListItem(
                id=w.id,
                slug=w.slug,
                headword=w.headword,
                part_of_speech=w.part_of_speech,
                noun_class=w.noun_class,
                dialect=w.dialect,
                swahili_gloss=_gloss_text(w.glosses, "sw"),
                english_gloss=_gloss_text(w.glosses, "en"),
                has_relations=w.id in words_with_relations,
            )
        )

    return WordListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        has_next=(offset + size) < total,
    )


# ═══════════════════════════════════════════════════════════════
# GET /api/words/{slug_or_id} — full word detail
# ═══════════════════════════════════════════════════════════════


@router.get("/words/{slug_or_id}", response_model=WordDetail)
async def get_word(
    slug_or_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full detail for a single word.

    Accepts either the slug (e.g. 'mlima') or the UUID — for backward
    compatibility with old /words/{uuid} URLs.

    Returns 404 if the word doesn't exist or is hidden/merged.
    """
    # ── Build the lookup condition (slug OR uuid) ─────────────
    if _is_uuid(slug_or_id):
        condition = Word.id == UUID(slug_or_id)
    else:
        condition = Word.slug == slug_or_id

    # ── Fetch the word with glosses and examples eager-loaded ─
    stmt = (
        select(Word)
        .where(condition, Word.status == "live")
        .options(
            selectinload(Word.glosses),
            selectinload(Word.examples),
        )
    )
    result = await db.execute(stmt)
    word = result.scalar_one_or_none()

    if word is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Word '{slug_or_id}' not found",
        )

    relations = await _fetch_word_relations(db, word.id)
    detail = _build_word_detail(word)
    detail.relations = relations
    return detail


# ═══════════════════════════════════════════════════════════════
# GET /api/search — fuzzy search using pg_trgm
# ═══════════════════════════════════════════════════════════════


@router.get("/search", response_model=SearchResponse)
async def search_words(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Max results (default 20)"),
    db: AsyncSession = Depends(get_db),
):
    """Fuzzy search across Taita headwords using pg_trgm.

    Returns results ranked by trigram similarity to the query.
    Also includes prefix matches via ILIKE as a fallback.
    """
    normalized_q = q.lower().strip()

    # ── Build the search query ────────────────────────────────
    # The `%` operator uses the GIN trigram index for fast fuzzy matching.
    # We also OR with ILIKE to catch prefix matches that trigram might miss
    # (e.g. searching "ml" should match "mlima" even if similarity is low).
    stmt = (
        select(
            Word,
            func.similarity(Word.normalized_form, normalized_q).label("sim"),
        )
        .where(
            Word.status == "live",
            or_(
                Word.normalized_form.op("%")(normalized_q),
                Word.headword.ilike(f"{normalized_q}%"),
                Word.slug.ilike(f"{normalized_q}%"),
            ),
        )
        .order_by(text("sim DESC"), Word.headword.asc())
        .limit(limit)
        .options(selectinload(Word.glosses))
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Batch-check relations (1 query, not N)
    word_ids = [word.id for word, _ in rows]
    words_with_relations = await _batch_has_relations(db, word_ids)

    items: list[SearchResultItem] = []
    for word, sim in rows:
        items.append(
            SearchResultItem(
                id=word.id,
                slug=word.slug,
                headword=word.headword,
                part_of_speech=word.part_of_speech,
                noun_class=word.noun_class,
                dialect=word.dialect,
                swahili_gloss=_gloss_text(word.glosses, "sw"),
                english_gloss=_gloss_text(word.glosses, "en"),
                has_relations=word.id in words_with_relations,
                similarity=round(float(sim), 3) if sim is not None else None,
            )
        )

    return SearchResponse(query=q, items=items, total=len(items))


# ═══════════════════════════════════════════════════════════════
# POST /api/words — reviewer creates a live word directly
# ═══════════════════════════════════════════════════════════════


@router.post("/words", response_model=WordDetail, status_code=201)
async def create_word(
    req: CreateWordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_reviewer),
):
    """Create a new word that goes live immediately.

    Requires reviewer or admin role. The word is created
    with status='live' and source='user', so it appears in the dictionary
    instantly.

    For traceability, we also:
    - Write an edit_log entry (action='create')
    - Create an 'accepted' suggestion record (so the word has a provenance
      trail — it came from a user, not an import)

    If a word with the same normalized_form already exists, returns 409.
    """
    headword = req.headword.strip()
    normalized = _normalize_form(headword)

    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Word must contain at least one letter.",
        )

    # ── Check for duplicate ───────────────────────────────────
    existing_result = await db.execute(
        select(Word).where(
            Word.normalized_form == normalized,
            Word.status == "live",
        )
    )
    existing = existing_result.scalar_one_or_none()
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

    # ── Generate slug ─────────────────────────────────────────
    slug = await generate_unique_slug(db, headword)

    # ── Create the Word ───────────────────────────────────────
    word = Word(
        headword=headword,
        normalized_form=normalized,
        slug=slug,
        part_of_speech=req.part_of_speech,
        noun_class=req.noun_class,
        dialect=req.dialect,
        literal_translation=req.literal_translation,
        morphology_notes=req.morphology_notes,
        status="live",
        source="user",
        created_by_user_id=current_user.id,
    )
    db.add(word)
    await db.flush()  # populate word.id

    # ── Glosses (Swahili + English) ───────────────────────────
    if req.swahili_gloss:
        db.add(Gloss(word_id=word.id, language="sw", text=req.swahili_gloss.strip()))
    if req.english_gloss:
        db.add(Gloss(word_id=word.id, language="en", text=req.english_gloss.strip()))

    # ── Examples ──────────────────────────────────────────────
    for ex in req.examples or []:
        db.add(Example(
            word_id=word.id,
            taita_text=ex.taita_text.strip(),
            swahili_text=ex.swahili_text.strip() if ex.swahili_text else None,
            english_text=ex.english_text.strip() if ex.english_text else None,
            source_ref=ex.source_ref,
        ))

    # ── Audit log ─────────────────────────────────────────────
    db.add(
        EditLog(
            actor_user_id=current_user.id,
            action="create",
            entity_type="word",
            entity_id=word.id,
            after={
                "headword": word.headword,
                "slug": word.slug,
                "source": "direct_add",
                "by_user": current_user.email,
            },
        )
    )

    # ── Provenance: create an accepted suggestion record ──────
    suggestion = Suggestion(
        target_type="new_word",
        target_id=word.id,
        proposed_value={
            "headword": headword,
            "part_of_speech": req.part_of_speech,
            "noun_class": req.noun_class,
            "dialect": req.dialect,
            "literal_translation": req.literal_translation,
            "morphology_notes": req.morphology_notes,
            "swahili_gloss": req.swahili_gloss,
            "english_gloss": req.english_gloss,
            "examples": [ex.model_dump(mode="json") for ex in req.examples] if req.examples else None,
        },
        rationale=None,
        status="accepted",
        created_by_user_id=current_user.id,
        decided_at=datetime.now(timezone.utc),
        decided_by_user_id=current_user.id,
        applied_at=datetime.now(timezone.utc),
    )
    db.add(suggestion)

    await db.commit()

    # ── Return the full word detail ───────────────────────────
    result = await db.execute(
        select(Word)
        .where(Word.id == word.id)
        .options(
            selectinload(Word.glosses),
            selectinload(Word.examples),
        )
    )
    word = result.scalar_one()

    detail = _build_word_detail(word)
    detail.relations = await _fetch_word_relations(db, word.id)
    return detail


# ═══════════════════════════════════════════════════════════════
# PATCH /api/words/{id} — reviewer/admin edits a word
# ═══════════════════════════════════════════════════════════════


@router.patch("/words/{word_id}", response_model=WordDetail)
async def edit_word(
    word_id: UUID,
    req: EditWordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_reviewer),
):
    """Edit a word's fields. Requires reviewer or admin role.

    Only provided fields are updated. Gloss fields (swahili_gloss, english_gloss)
    update the corresponding Gloss rows — creates them if they don't exist.

    If `examples` is provided, it REPLACES the word's example set: existing
    examples not in the list are deleted, examples with a matching `id` are
    updated, examples without an `id` are created.
    """
    result = await db.execute(
        select(Word)
        .where(Word.id == word_id)
        .options(selectinload(Word.glosses), selectinload(Word.examples))
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

    # ── Examples (replace strategy) ───────────────────────────
    if req.examples is not None:
        # Track existing examples by id
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

        # Update or create
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

    # ── Audit log + mark reviewed ─────────────────────────────
    if before or after:
        word.reviewed_at = datetime.now(timezone.utc)
        word.reviewed_by_user_id = current_user.id
        db.add(
            EditLog(
                actor_user_id=current_user.id,
                action="update",
                entity_type="word",
                entity_id=word.id,
                before=before or None,
                after={**after, "source": "reviewer_edit", "by_user": current_user.email},
            )
        )

    await db.commit()

    # ── Return updated word ───────────────────────────────────
    result = await db.execute(
        select(Word)
        .where(Word.id == word_id)
        .options(selectinload(Word.glosses), selectinload(Word.examples))
    )
    word = result.scalar_one()

    detail = _build_word_detail(word)
    detail.relations = await _fetch_word_relations(db, word.id)
    return detail

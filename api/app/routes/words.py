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
from app.models import EditLog, Example, Sense, Suggestion, Translation, User, Word, WordRelationship, WordVariation
from app.schemas import (
    ExampleOut,
    TranslationOut,
    RelationOut,
    RelationshipOut,
    SearchResponse,
    SearchResultItem,
    SenseOut,
    VariationOut,
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


class CreateExampleRequest(BaseModel):
    """Request body for POST /api/words/:id/examples — append a single example.

    Reviewer+ shortcut that mirrors the target_type='new_example' suggestion
    flow but skips the vote. taita_text is required; the translations are
    optional — readers can suggest them later via target_type='example' on
    the new example.

    sense_id is optional: scopes the example to a specific sense. If not
    provided, the word's default sense (order_index=1) is used.
    """

    taita_text: str = Field(..., min_length=1, max_length=2000)
    swahili_text: str | None = Field(None, max_length=2000)
    english_text: str | None = Field(None, max_length=2000)
    source_ref: str | None = Field(None, max_length=500)
    sense_id: UUID | None = None


class CreateWordRequest(BaseModel):
    """Request body for POST /api/words — reviewer adds a live word."""

    headword: str = Field(..., min_length=1, max_length=200)
    part_of_speech: str | None = None
    noun_class: str | None = None
    dialect: str | None = None
    literal_translation: str | None = None
    morphology_notes: str | None = None
    swahili_translation: str | None = None
    english_translation: str | None = None
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
    swahili_translation: str | None = None
    english_translation: str | None = None
    examples: list[ExampleInput] | None = None


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _translation_text(translations: list[Translation], language: str) -> str | None:
    """Extract the text of the first translation matching a language, or None."""
    for t in translations:
        if t.language == language:
            return t.text
    return None


async def _batch_has_relations(
    session: AsyncSession, word_ids: list[UUID]
) -> set[UUID]:
    """Check which words have any variations or relationships (incoming or outgoing).

    Returns a set of word IDs that have at least one variation or relationship.
    Uses a single query per table instead of N+1.
    """
    if not word_ids:
        return set()

    found: set[UUID] = set()

    # Variations: bidirectional, so check both word_id and other_word_id
    var_subq = (
        select(WordVariation.word_id.label("wid"))
        .where(WordVariation.word_id.in_(word_ids))
        .union(
            select(WordVariation.other_word_id.label("wid"))
            .where(WordVariation.other_word_id.in_(word_ids))
        )
    )
    result = await session.execute(var_subq)
    for row in result.all():
        found.add(row[0])

    # Relationships: same — both directions
    rel_subq = (
        select(WordRelationship.word_id.label("wid"))
        .where(WordRelationship.word_id.in_(word_ids))
        .union(
            select(WordRelationship.other_word_id.label("wid"))
            .where(WordRelationship.other_word_id.in_(word_ids))
        )
    )
    result = await session.execute(rel_subq)
    for row in result.all():
        found.add(row[0])

    return found


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


async def _fetch_word_variations_and_relationships(
    db: AsyncSession, word_id: UUID
) -> tuple[list[VariationOut], list[RelationshipOut], list[RelationOut]]:
    """Fetch all variations and relationships for a word.

    Returns (variations, relationships, legacy_relations):
      - variations: list[VariationOut] — bidirectional, definitional links
      - relationships: list[RelationshipOut] — typed, may be directional
      - legacy_relations: list[RelationOut] — backward-compat with v1.1 frontend

    For each table we look in both directions (word_id and other_word_id)
    because variations are always symmetric and bidirectional relationships
    need to surface on both ends.
    """
    # ── Variations (bidirectional) ────────────────────────────
    # Variations are stored as (word_id, other_word_id, type) but are symmetric.
    # We fetch rows where this word is on either side and normalize so the
    # "other" word is always the one that's NOT word_id.
    var_stmt = (
        select(WordVariation, Word.headword, Word.slug)
        .join(Word, WordVariation.other_word_id == Word.id)
        .where(WordVariation.word_id == word_id)
    )
    var_reverse = (
        select(WordVariation, Word.headword, Word.slug)
        .join(Word, WordVariation.word_id == Word.id)
        .where(WordVariation.other_word_id == word_id)
    )

    variations: list[VariationOut] = []
    legacy_relations: list[RelationOut] = []

    var_out_result = await db.execute(var_stmt)
    for var, other_headword, other_slug in var_out_result.all():
        variations.append(VariationOut(
            other_word_id=var.other_word_id,
            other_headword=other_headword,
            other_slug=other_slug,
            variation_type=var.variation_type,
        ))
        # Legacy: variations show as 'outgoing'
        legacy_relations.append(RelationOut(
            other_word_id=var.other_word_id,
            other_headword=other_headword,
            other_slug=other_slug,
            relation_type=var.variation_type,
            direction="outgoing",
        ))

    var_in_result = await db.execute(var_reverse)
    for var, other_headword, other_slug in var_in_result.all():
        # The "other" word here is var.word_id (since var.other_word_id IS word_id)
        variations.append(VariationOut(
            other_word_id=var.word_id,
            other_headword=other_headword,
            other_slug=other_slug,
            variation_type=var.variation_type,
        ))
        legacy_relations.append(RelationOut(
            other_word_id=var.word_id,
            other_headword=other_headword,
            other_slug=other_slug,
            relation_type=var.variation_type,
            direction="incoming",
        ))

    # ── Relationships (typed, may be directional) ────────────
    rel_out_stmt = (
        select(WordRelationship, Word.headword, Word.slug)
        .join(Word, WordRelationship.other_word_id == Word.id)
        .where(WordRelationship.word_id == word_id)
    )
    rel_in_stmt = (
        select(WordRelationship, Word.headword, Word.slug)
        .join(Word, WordRelationship.word_id == Word.id)
        .where(WordRelationship.other_word_id == word_id)
    )

    relationships: list[RelationshipOut] = []

    rel_out_result = await db.execute(rel_out_stmt)
    for rel, other_headword, other_slug in rel_out_result.all():
        # This word is the source (word_id side)
        # For 'bidirectional' direction, surface as 'bidirectional' (symmetric)
        # For 'forward' direction, surface as 'forward' (this word derives FROM other)
        # For 'reverse' direction, surface as 'reverse' (this word is the source of
        #   someone else's forward relationship — unusual, but supported)
        rel_dir = rel.direction if rel.direction != "bidirectional" else "bidirectional"
        relationships.append(RelationshipOut(
            other_word_id=rel.other_word_id,
            other_headword=other_headword,
            other_slug=other_slug,
            relationship_type=rel.relationship_type,
            direction=rel_dir,
            note=rel.note,
        ))
        # Legacy: bidirectional and forward surface as 'outgoing'
        legacy_relations.append(RelationOut(
            other_word_id=rel.other_word_id,
            other_headword=other_headword,
            other_slug=other_slug,
            relation_type=rel.relationship_type,
            direction="outgoing",
        ))

    rel_in_result = await db.execute(rel_in_stmt)
    for rel, other_headword, other_slug in rel_in_result.all():
        # This word is the target (other_word_id side)
        # For 'bidirectional' direction, we already added it from the outgoing pass
        #   (because it's symmetric — both sides should see it).
        #   But to be safe and avoid duplication in the legacy field, we skip
        #   bidirectional incoming entries from the legacy_relations list.
        # For 'forward' direction from the other word's perspective, this word
        #   is the source — surface as 'reverse'.
        if rel.direction == "bidirectional":
            # Already surfaced from the outgoing pass (since bidirectional is symmetric)
            # — but only if this row also exists in the outgoing set, which it does
            # for true bidirectional entries. Skip to avoid duplicates.
            continue
        # Forward (the other word derives from this one) → this word sees 'reverse'
        # Reverse (this word is the source of someone else's reverse) → 'forward' from this side
        reversed_dir = "reverse" if rel.direction == "forward" else "forward"
        relationships.append(RelationshipOut(
            other_word_id=rel.word_id,
            other_headword=other_headword,
            other_slug=other_slug,
            relationship_type=rel.relationship_type,
            direction=reversed_dir,
            note=rel.note,
        ))
        legacy_relations.append(RelationOut(
            other_word_id=rel.word_id,
            other_headword=other_headword,
            other_slug=other_slug,
            relation_type=rel.relationship_type,
            direction="incoming",
        ))

    return variations, relationships, legacy_relations


def _build_word_detail(word: Word, senses: list[Sense] | None = None) -> WordDetail:
    """Build a WordDetail response from a Word ORM object (with translations,
    examples, and relations already loaded/computed).

    `senses` is an optional list of Sense ORM objects with their translations
    and examples eager-loaded. If provided, the senses field is populated
    with each sense.s translations/examples. If None, senses is left empty
    (legacy mode for callers that haven't been updated).
    """
    sense_outs: list[SenseOut] = []
    if senses:
        for s in senses:
            sense_translations = [
                TranslationOut(language=g.language, text=g.text)
                for g in getattr(s, "translations", []) or []
            ]
            sense_examples = [
                ExampleOut(
                    id=e.id,
                    sense_id=e.sense_id,
                    taita_text=e.taita_text,
                    swahili_text=e.swahili_text,
                    english_text=e.english_text,
                    source_ref=e.source_ref,
                )
                for e in getattr(s, "examples", []) or []
            ]
            sense_outs.append(SenseOut(
                id=s.id,
                order_index=s.order_index,
                part_of_speech=s.part_of_speech,
                definition=s.definition,
                notes=s.notes,
                translations=sense_translations,
                examples=sense_examples,
            ))

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
        translations=[TranslationOut(language=g.language, text=g.text) for g in word.translations],
        examples=[
            ExampleOut(
                id=e.id,
                sense_id=e.sense_id,
                taita_text=e.taita_text,
                swahili_text=e.swahili_text,
                english_text=e.english_text,
                source_ref=e.source_ref,
            )
            for e in word.examples
        ],
        variations=[],
        relationships=[],
        senses=sense_outs,
        relations=[],
    )


async def _populate_relations(db: AsyncSession, detail: WordDetail, word_id: UUID) -> WordDetail:
    """Populate the variations, relationships, and legacy relations fields
    on a WordDetail using the new split tables. Also fetches and populates
    senses (with their translations/examples)."""
    variations, relationships, legacy = await _fetch_word_variations_and_relationships(db, word_id)
    detail.variations = variations
    detail.relationships = relationships
    detail.relations = legacy
    detail.senses = [
        SenseOut(
            id=s.id,
            order_index=s.order_index,
            part_of_speech=s.part_of_speech,
            definition=s.definition,
            notes=s.notes,
            translations=[TranslationOut(language=g.language, text=g.text) for g in getattr(s, "translations", []) or []],
            examples=[
                ExampleOut(
                    id=e.id,
                    sense_id=e.sense_id,
                    taita_text=e.taita_text,
                    swahili_text=e.swahili_text,
                    english_text=e.english_text,
                    source_ref=e.source_ref,
                )
                for e in getattr(s, "examples", []) or []
            ],
        )
        for s in await _fetch_senses_for_word(db, word_id)
    ]
    return detail


async def _fetch_senses_for_word(db: AsyncSession, word_id: UUID) -> list[Sense]:
    """Fetch all senses for a word with their translations and examples eager-loaded.

    Returns the senses ordered by order_index (1, 2, 3, ...).

    Sense doesn't have a relationship to translations/examples (they reference
    sense_id directly via FK), so we batch-fetch them separately and attach.
    """
    result = await db.execute(
        select(Sense).where(Sense.word_id == word_id).order_by(Sense.order_index)
    )
    senses = result.scalars().all()
    if not senses:
        return []

    sense_ids = [s.id for s in senses]

    # Batch-fetch translations for all senses
    translation_result = await db.execute(
        select(Translation).where(Translation.sense_id.in_(sense_ids))
    )
    translations_by_sense: dict[UUID, list[Translation]] = {sid: [] for sid in sense_ids}
    for g in translation_result.scalars().all():
        if g.sense_id and g.sense_id in translations_by_sense:
            translations_by_sense[g.sense_id].append(g)

    # Batch-fetch examples for all senses
    ex_result = await db.execute(
        select(Example).where(Example.sense_id.in_(sense_ids))
    )
    examples_by_sense: dict[UUID, list[Example]] = {sid: [] for sid in sense_ids}
    for e in ex_result.scalars().all():
        if e.sense_id and e.sense_id in examples_by_sense:
            examples_by_sense[e.sense_id].append(e)

    # Attach to sense objects (using setattr to avoid type-check issues)
    for s in senses:
        s.translations = translations_by_sense.get(s.id, [])  # type: ignore[attr-defined]
        s.examples = examples_by_sense.get(s.id, [])  # type: ignore[attr-defined]

    return senses


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
    stmt = stmt.offset(offset).limit(size).options(selectinload(Word.translations))
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
                swahili_translation=_translation_text(w.translations, "sw"),
                english_translation=_translation_text(w.translations, "en"),
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

    # ── Fetch the word with translations and examples eager-loaded ─
    stmt = (
        select(Word)
        .where(condition, Word.status == "live")
        .options(
            selectinload(Word.translations),
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

    detail = _build_word_detail(word)
    detail = await _populate_relations(db, detail, word.id)
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
        .options(selectinload(Word.translations))
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
                swahili_translation=_translation_text(word.translations, "sw"),
                english_translation=_translation_text(word.translations, "en"),
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

    # ── Translations (Swahili + English) ───────────────────────────
    # Create a default sense (order_index=1) and scope the translations + examples to it
    default_sense = Sense(
        word_id=word.id,
        order_index=1,
        definition=None,
        notes=None,
        created_by_user_id=current_user.id,
    )
    db.add(default_sense)
    await db.flush()  # populate default_sense.id

    if req.swahili_translation:
        db.add(Translation(word_id=word.id, sense_id=default_sense.id, language="sw", text=req.swahili_translation.strip()))
    if req.english_translation:
        db.add(Translation(word_id=word.id, sense_id=default_sense.id, language="en", text=req.english_translation.strip()))

    # ── Examples (scoped to the default sense) ────────────────
    for ex in req.examples or []:
        db.add(Example(
            word_id=word.id,
            sense_id=default_sense.id,
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
            "swahili_translation": req.swahili_translation,
            "english_translation": req.english_translation,
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
            selectinload(Word.translations),
            selectinload(Word.examples),
        )
    )
    word = result.scalar_one()

    detail = _build_word_detail(word)
    detail = await _populate_relations(db, detail, word.id)
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

    Only provided fields are updated. Translation fields (swahili_translation, english_translation)
    update the corresponding Translation rows — creates them if they don't exist.

    If `examples` is provided, it REPLACES the word's example set: existing
    examples not in the list are deleted, examples with a matching `id` are
    updated, examples without an `id` are created.
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
        .options(selectinload(Word.translations), selectinload(Word.examples))
    )
    word = result.scalar_one()

    detail = _build_word_detail(word)
    detail = await _populate_relations(db, detail, word.id)
    return detail


# ═══════════════════════════════════════════════════════════════
# POST /api/words/{id}/examples — reviewer+ appends a single example
# ═══════════════════════════════════════════════════════════════


@router.post("/words/{word_id}/examples", response_model=WordDetail, status_code=201)
async def add_example_to_word(
    word_id: UUID,
    req: CreateExampleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_reviewer),
):
    """Append a single example to a word. Reviewer+ only.

    This is the direct-add shortcut that mirrors the
    target_type='new_example' suggestion flow but skips the vote. Useful
    for reviewers who want to add an example without going through the
    suggestion queue.

    taita_text is required. swahili_text and english_text are optional —
    readers can suggest them later via target_type='example' on the new
    example.

    sense_id is optional: scopes the example to a specific sense. If not
    provided, the word's default sense (order_index=1) is used. If the
    word has no senses, a default one is created.

    Returns the full updated word detail.
    """
    # ── Fetch the word ────────────────────────────────────────
    result = await db.execute(
        select(Word).where(Word.id == word_id, Word.status == "live")
    )
    word = result.scalar_one_or_none()
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")

    # ── Resolve the sense to scope this example to ────────────
    sense_id = req.sense_id
    if sense_id is None:
        # Use the word's default sense (order_index=1); create if missing
        sense_result = await db.execute(
            select(Sense).where(Sense.word_id == word.id, Sense.order_index == 1)
        )
        default_sense = sense_result.scalar_one_or_none()
        if default_sense is None:
            default_sense = Sense(word_id=word.id, order_index=1)
            db.add(default_sense)
            await db.flush()
        sense_id = default_sense.id

    # ── Create the example ────────────────────────────────────
    example = Example(
        word_id=word.id,
        sense_id=sense_id,
        taita_text=req.taita_text.strip(),
        swahili_text=req.swahili_text.strip() if req.swahili_text else None,
        english_text=req.english_text.strip() if req.english_text else None,
        source_ref=req.source_ref,
    )
    db.add(example)

    # ── Audit log ─────────────────────────────────────────────
    db.add(
        EditLog(
            actor_user_id=current_user.id,
            action="create",
            entity_type="example",
            entity_id=word.id,
            after={
                "taita_text": example.taita_text,
                "swahili_text": example.swahili_text,
                "english_text": example.english_text,
                "source_ref": example.source_ref,
                "sense_id": str(sense_id),
                "source": "direct_add",
                "by_user": current_user.email,
            },
        )
    )

    await db.commit()

    # ── Return the full updated word detail ───────────────────
    result = await db.execute(
        select(Word)
        .where(Word.id == word_id)
        .options(
            selectinload(Word.translations),
            selectinload(Word.examples),
        )
    )
    word = result.scalar_one()

    detail = _build_word_detail(word)
    detail = await _populate_relations(db, detail, word.id)
    return detail


# ═══════════════════════════════════════════════════════════════
# POST /api/words/{id}/senses — reviewer+ adds a new sense
# ═══════════════════════════════════════════════════════════════


class CreateSenseRequest(BaseModel):
    """Request body for POST /api/words/:id/senses — add a new sense.

    A sense is a distinct meaning of a word. The new sense gets the next
    available order_index (e.g. if the word has senses 1 and 2, the new
    one becomes 3).
    """

    part_of_speech: str | None = None
    definition: str | None = Field(None, max_length=500)
    notes: str | None = Field(None, max_length=2000)


@router.post("/words/{word_id}/senses", response_model=WordDetail, status_code=201)
async def add_sense_to_word(
    word_id: UUID,
    req: CreateSenseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_reviewer),
):
    """Add a new sense to a word. Reviewer+ only.

    The new sense gets the next available order_index. Translations and examples
    for the new sense can be added via PATCH /api/words/:id (with sense-scoped
    examples in the body) or via the suggestion flow (target_type='translation'
    or 'new_example' with sense_id in proposed_value).

    Returns the full updated word detail.
    """
    # ── Fetch the word ────────────────────────────────────────
    result = await db.execute(
        select(Word).where(Word.id == word_id, Word.status == "live")
    )
    word = result.scalar_one_or_none()
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")

    # ── Determine the next order_index ────────────────────────
    max_order_result = await db.execute(
        select(func.max(Sense.order_index)).where(Sense.word_id == word.id)
    )
    max_order = max_order_result.scalar() or 0
    next_order = max_order + 1

    # ── Create the sense ──────────────────────────────────────
    sense = Sense(
        word_id=word.id,
        order_index=next_order,
        part_of_speech=req.part_of_speech,
        definition=req.definition,
        notes=req.notes,
        created_by_user_id=current_user.id,
    )
    db.add(sense)

    # ── Audit log ─────────────────────────────────────────────
    db.add(
        EditLog(
            actor_user_id=current_user.id,
            action="create",
            entity_type="sense",
            entity_id=word.id,
            after={
                "order_index": next_order,
                "part_of_speech": req.part_of_speech,
                "definition": req.definition,
                "notes": req.notes,
                "source": "direct_add",
                "by_user": current_user.email,
            },
        )
    )

    await db.commit()

    # ── Return the full updated word detail ───────────────────
    result = await db.execute(
        select(Word)
        .where(Word.id == word_id)
        .options(
            selectinload(Word.translations),
            selectinload(Word.examples),
        )
    )
    word = result.scalar_one()

    detail = _build_word_detail(word)
    detail = await _populate_relations(db, detail, word.id)
    return detail


# ═══════════════════════════════════════════════════════════════
# PATCH /api/senses/{id} — reviewer+ edits a sense
# ═══════════════════════════════════════════════════════════════


class EditSenseRequest(BaseModel):
    """Edit a sense's fields. All fields optional — only provided fields are updated."""

    order_index: int | None = Field(None, ge=1)
    part_of_speech: str | None = None
    definition: str | None = Field(None, max_length=500)
    notes: str | None = Field(None, max_length=2000)


@router.patch("/senses/{sense_id}", response_model=WordDetail)
async def edit_sense(
    sense_id: UUID,
    req: EditSenseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_reviewer),
):
    """Edit a sense's fields. Reviewer+ only.

    Only provided fields are updated. Returns the full updated word detail
    (the sense's parent word).
    """
    result = await db.execute(select(Sense).where(Sense.id == sense_id))
    sense = result.scalar_one_or_none()
    if sense is None:
        raise HTTPException(status_code=404, detail="Sense not found")

    before = {}
    after = {}

    if req.order_index is not None and req.order_index != sense.order_index:
        before["order_index"] = sense.order_index
        sense.order_index = req.order_index
        after["order_index"] = req.order_index

    if req.part_of_speech is not None and (req.part_of_speech or None) != sense.part_of_speech:
        before["part_of_speech"] = sense.part_of_speech
        sense.part_of_speech = req.part_of_speech or None
        after["part_of_speech"] = sense.part_of_speech

    if req.definition is not None and (req.definition or None) != sense.definition:
        before["definition"] = sense.definition
        sense.definition = req.definition or None
        after["definition"] = sense.definition

    if req.notes is not None and (req.notes or None) != sense.notes:
        before["notes"] = sense.notes
        sense.notes = req.notes or None
        after["notes"] = sense.notes

    if before or after:
        sense.reviewed_at = datetime.now(timezone.utc)
        sense.reviewed_by_user_id = current_user.id
        db.add(
            EditLog(
                actor_user_id=current_user.id,
                action="update",
                entity_type="sense",
                entity_id=sense.id,
                before=before or None,
                after={**after, "source": "reviewer_edit", "by_user": current_user.email},
            )
        )

    await db.commit()

    # ── Return the full updated word detail ───────────────────
    result = await db.execute(
        select(Word)
        .where(Word.id == sense.word_id)
        .options(
            selectinload(Word.translations),
            selectinload(Word.examples),
        )
    )
    word = result.scalar_one()

    detail = _build_word_detail(word)
    detail = await _populate_relations(db, detail, word.id)
    return detail

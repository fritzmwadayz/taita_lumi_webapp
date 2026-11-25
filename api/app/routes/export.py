"""GET /api/export/dictionary — full static snapshot of the dictionary.

Returns every live word as a complete WordDetail (the same shape the word
detail page renders), plus a compact list index used by the static frontend.

Why this endpoint exists: the frontend snapshots the dictionary into static
JSON at deploy time (see scripts/export-dictionary.mjs in the Nuxt repo) so
that anonymous traffic never touches the API or the database. This endpoint
is the single bulk query behind that snapshot — 6 queries total for the whole
dictionary, instead of N × 3 queries for N words via the per-word endpoint.

Assembly mirrors the per-word logic exactly (senses, sense-scoped
translations/examples, variations, relationships, legacy relations,
has_relations) so a static word page is byte-for-byte the same data the live
API would return. The only additions are two envelope fields:
  - exported_at: when the snapshot was taken
  - total: number of words included

No pagination by design: the point is one complete dump. If the dictionary
outgrows a single response we chunk by headword prefix, not pages.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import (
    Example,
    Sense,
    Translation,
    Word,
    WordRelationship,
    WordVariation,
)
from app.routes.words import _batch_has_relations
from app.schemas import (
    _STATUS_MAP,
    ExampleOut,
    RelationOut,
    RelationshipOut,
    SenseOut,
    TranslationOut,
    VariationOut,
    WordDetail,
    WordListItem,
)

router = APIRouter()


@router.get("/export/dictionary")
async def export_dictionary(db: AsyncSession = Depends(get_db)):
    """One bulk dump of every live word, ready for static export.

    Public and unauthenticated: it exposes nothing that isn't already public
    on the word detail/list endpoints, and it is only ever called by the
    frontend's deploy script. Render it unreachable in dev if you like —
    it's read-only either way.
    """
    # ── 1. All live words (translations + examples eager-loaded) ──────
    # Same eager-loading as GET /api/words/{slug_or_id} so WordDetail's
    # word-level translations/examples match the per-word endpoint exactly.
    words_result = await db.execute(
        select(Word)
        .where(Word.status == "live")
        .options(selectinload(Word.translations), selectinload(Word.examples))
        .order_by(Word.created_at.desc(), Word.headword.asc())
    )
    words = words_result.scalars().unique().all()

    if not words:
        return {
            "exported_at": _now_iso(),
            "total": 0,
            "words": [],
            "list": [],
        }

    word_ids = [w.id for w in words]

    # ── 2. Senses for every word (one query) ───────────────────────────
    senses_result = await db.execute(
        select(Sense)
        .where(Sense.word_id.in_(word_ids))
        .order_by(Sense.word_id, Sense.order_index)
    )
    senses = senses_result.scalars().all()
    senses_by_word: dict = {}
    for s in senses:
        senses_by_word.setdefault(s.word_id, []).append(s)

    # ── 3. Sense-scoped translations + examples (one query each) ──────
    # Word.translations/examples eager loads include sense-scoped rows too
    # (no primaryjoin filter on sense_id IS NULL), so the word-level lists
    # here mirror the per-word endpoint. These queries are for the SENSE
    # lists, which the per-word endpoint assembles the same way.
    sense_ids = [s.id for s in senses]

    sense_translations: dict = {}
    if sense_ids:
        tr_result = await db.execute(
            select(Translation).where(Translation.sense_id.in_(sense_ids))
        )
        for g in tr_result.scalars().all():
            sense_translations.setdefault(g.sense_id, []).append(g)

    sense_examples: dict = {}
    if sense_ids:
        ex_result = await db.execute(
            select(Example).where(Example.sense_id.in_(sense_ids))
        )
        for e in ex_result.scalars().all():
            sense_examples.setdefault(e.sense_id, []).append(e)

    # ── 4. Variations + relationships, both directions (one per table) ─
    var_rows = (await db.execute(select(WordVariation))).scalars().all()
    rel_rows = (await db.execute(select(WordRelationship))).scalars().all()

    # Headword/slug for every referenced word — all live words are already
    # in `words`, so build an id → (headword, slug) lookup from them.
    # (A variation pointing at a hidden word still points at a real word;
    # the per-word endpoint surfaces those links the same way — the join
    # there targets the Word table regardless of status.)
    word_info: dict = {w.id: (w.headword, w.slug) for w in words}
    missing_ids = {
        wid
        for row in (list(var_rows) + list(rel_rows))
        for wid in (row.word_id, row.other_word_id)
        if wid not in word_info
    }
    if missing_ids:
        # Resolve non-live words referenced by relations (hidden/merged
        # words still show as links on the word page).
        extra = await db.execute(
            select(Word.id, Word.headword, Word.slug).where(Word.id.in_(missing_ids))
        )
        for wid, headword, slug in extra.all():
            word_info[wid] = (headword, slug)

    # ── 5. Assemble per-word detail (mirrors _populate_relations) ──────
    variations_by_word: dict = {}
    relationships_by_word: dict = {}
    legacy_by_word: dict = {}

    for var in var_rows:
        other_id = var.other_word_id
        a_side, b_side = var.word_id, other_id
        if b_side not in word_info:
            continue  # dangling FK guard — shouldn't happen

        # Forward direction: word A lists B as a variation
        headword_b, slug_b = word_info[other_id]
        variations_by_word.setdefault(a_side, []).append(
            VariationOut(
                other_word_id=other_id,
                other_headword=headword_b,
                other_slug=slug_b,
                variation_type=var.variation_type,
            )
        )
        legacy_by_word.setdefault(a_side, []).append(
            RelationOut(
                other_word_id=other_id,
                other_headword=headword_b,
                other_slug=slug_b,
                relation_type=var.variation_type,
                direction="outgoing",
            )
        )

        # Reverse direction: word B lists A as a variation (variations are
        # symmetric — same two queries the per-word endpoint runs, batched).
        headword_a, slug_a = word_info[a_side]
        variations_by_word.setdefault(b_side, []).append(
            VariationOut(
                other_word_id=a_side,
                other_headword=headword_a,
                other_slug=slug_a,
                variation_type=var.variation_type,
            )
        )
        legacy_by_word.setdefault(b_side, []).append(
            RelationOut(
                other_word_id=a_side,
                other_headword=headword_a,
                other_slug=slug_a,
                relation_type=var.variation_type,
                direction="incoming",
            )
        )

    for rel in rel_rows:
        other_id = rel.other_word_id
        a_side, b_side = rel.word_id, other_id
        if other_id not in word_info:
            continue

        # Forward: A → B
        headword_b, slug_b = word_info[other_id]
        relationships_by_word.setdefault(a_side, []).append(
            RelationshipOut(
                other_word_id=other_id,
                other_headword=headword_b,
                other_slug=slug_b,
                relationship_type=rel.relationship_type,
                direction=rel.direction,
                note=rel.note,
            )
        )
        if rel.direction != "bidirectional":
            # bidirectional already surfaces on both sides via the forward
            # pass (symmetric) — same skip the per-word endpoint applies.
            legacy_by_word.setdefault(a_side, []).append(
                RelationOut(
                    other_word_id=other_id,
                    other_headword=headword_b,
                    other_slug=slug_b,
                    relation_type=rel.relationship_type,
                    direction="outgoing",
                )
            )

        # Reverse: B sees A (with flipped direction labels)
        headword_a, slug_a = word_info[a_side]
        if rel.direction == "bidirectional":
            relationships_by_word.setdefault(b_side, []).append(
                RelationshipOut(
                    other_word_id=a_side,
                    other_headword=headword_a,
                    other_slug=slug_a,
                    relationship_type=rel.relationship_type,
                    direction="bidirectional",
                    note=rel.note,
                )
            )
        else:
            reversed_dir = "reverse" if rel.direction == "forward" else "forward"
            relationships_by_word.setdefault(b_side, []).append(
                RelationshipOut(
                    other_word_id=a_side,
                    other_headword=headword_a,
                    other_slug=slug_a,
                    relationship_type=rel.relationship_type,
                    direction=reversed_dir,
                    note=rel.note,
                )
            )
            legacy_by_word.setdefault(b_side, []).append(
                RelationOut(
                    other_word_id=a_side,
                    other_headword=headword_a,
                    other_slug=slug_a,
                    relation_type=rel.relationship_type,
                    direction="incoming",
                )
            )

    # has_relations for the list index — same batch helper the list/search
    # endpoints use.
    words_with_relations = await _batch_has_relations(db, word_ids)

    # ── 6. Build the response ──────────────────────────────────────────
    details: list[WordDetail] = []
    list_items: list[WordListItem] = []

    for w in words:
        sw = _translation_text_local(w.translations, "sw")
        en = _translation_text_local(w.translations, "en")

        sense_outs = []
        for s in senses_by_word.get(w.id, []):
            sense_outs.append(
                SenseOut(
                    id=s.id,
                    order_index=s.order_index,
                    part_of_speech=s.part_of_speech,
                    definition=s.definition,
                    notes=s.notes,
                    translations=[
                        TranslationOut(language=g.language, text=g.text)
                        for g in sense_translations.get(s.id, [])
                    ],
                    examples=[
                        ExampleOut(
                            id=e.id,
                            sense_id=e.sense_id,
                            taita_text=e.taita_text,
                            swahili_text=e.swahili_text,
                            english_text=e.english_text,
                            source_ref=e.source_ref,
                        )
                        for e in sense_examples.get(s.id, [])
                    ],
                )
            )

        detail = WordDetail(
            id=w.id,
            slug=w.slug,
            headword=w.headword,
            part_of_speech=w.part_of_speech,
            noun_class=w.noun_class,
            dialect=w.dialect,
            literal_translation=w.literal_translation,
            morphology_notes=w.morphology_notes,
            status=_STATUS_MAP.get(w.status, w.status),
            created_at=w.created_at,
            translations=[
                TranslationOut(language=g.language, text=g.text)
                for g in w.translations
            ],
            examples=[
                ExampleOut(
                    id=e.id,
                    sense_id=e.sense_id,
                    taita_text=e.taita_text,
                    swahili_text=e.swahili_text,
                    english_text=e.english_text,
                    source_ref=e.source_ref,
                )
                for e in w.examples
            ],
            variations=variations_by_word.get(w.id, []),
            relationships=relationships_by_word.get(w.id, []),
            senses=sense_outs,
            relations=legacy_by_word.get(w.id, []),
        )
        details.append(detail)

        list_items.append(
            WordListItem(
                id=w.id,
                slug=w.slug,
                headword=w.headword,
                part_of_speech=w.part_of_speech,
                noun_class=w.noun_class,
                dialect=w.dialect,
                swahili_translation=sw,
                english_translation=en,
                has_relations=w.id in words_with_relations,
            )
        )

    return {
        "exported_at": _now_iso(),
        "total": len(details),
        "words": details,
        "list": list_items,
    }


def _translation_text_local(translations: list[Translation], language: str) -> str | None:
    """Word-level translation summary — mirrors _translation_text in words.py
    (first translation for the language wins, regardless of sense scope)."""
    for g in translations:
        if g.language == language:
            return g.text
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

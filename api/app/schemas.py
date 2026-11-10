"""Pydantic response schemas for the Lumi API.

These define the shape of API responses, used for:
  - Auto-generated OpenAPI docs at /docs
  - Typed responses the Vue frontend can rely on
  - Validation that DB rows serialize correctly

Status mapping: the DB stores 'live' | 'hidden' | 'merged', but the API
contract exposes 'active' | 'hidden' to the frontend. 'merged' is internal
(merged words are excluded from public queries). The mapping is done by
the @field_validator on WordDetail.status.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


# ═══════════════════════════════════════════════════════════════
# Translations, Examples & Relations (nested in WordDetail)
# ═══════════════════════════════════════════════════════════════


class TranslationOut(BaseModel):
    """A single translation of a word in a specific language.

    (Renamed from GlossOut in v1.3 — "translation" is more intuitive
    than "gloss" for non-lexicographers.)
    """

    model_config = ConfigDict(from_attributes=True)

    language: str  # 'sw' or 'en'
    text: str


class ExampleOut(BaseModel):
    """A usage example with parallel text in Taita / Swahili / English.

    The frontend pairs these as parallel translations. If a translation
    is missing (e.g. swahili_text is None), the frontend offers the reader
    a non-confrontational option to suggest one via POST /api/suggestions
    with target_type='example'.

    Strictly scoped to a single sense (sense_id) once senses are in use.
    Pre-senses examples were backfilled to a default sense per word.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sense_id: UUID | None = None
    taita_text: str
    swahili_text: str | None = None
    english_text: str | None = None
    source_ref: str | None = None


class SenseOut(BaseModel):
    """A distinct meaning of a word.

    Each sense has its own translations and examples (strict scoping). The
    frontend should render a word's senses as separate numbered sections:
      ┌────────────────────────────────────────────┐
      │ 1. Mountain, large hill                    │
      │   SW: mlima    EN: mountain, hill          │
      │   Examples:                                │
      │   • Mlima u mrefu. (Mlima ni mrefu.)       │
      │     The mountain is tall.                  │
      ├────────────────────────────────────────────┤
      │ 2. Pile, heap (e.g. of harvest)            │
      │   SW: mlima    EN: pile, heap              │
      │   (no examples yet — [suggest one])        │
      └────────────────────────────────────────────┘

    `definition` is an optional short inline header for the sense
    (e.g. "Mountain, large hill"). `notes` carries usage notes
    (e.g. "archaic", "Dawida dialect").
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_index: int
    part_of_speech: str | None = None
    definition: str | None = None
    notes: str | None = None
    translations: list[TranslationOut] = []
    examples: list[ExampleOut] = []


class VariationOut(BaseModel):
    """A bidirectional variation link between this word and another word.

    Examples: mlima ↔ milima (singular ↔ plural), kuja ↔ anakuja (lemma ↔ conjugation).
    Variations are always symmetric — display them on both words' detail pages.

    variation_type ∈ {'variant', 'plural', 'singular', 'conjugation',
                       'diminutive', 'augmentative'}
    """

    other_word_id: UUID
    other_headword: str
    other_slug: str
    variation_type: str


class RelationshipOut(BaseModel):
    """A typed link between this word and a DIFFERENT lemma.

    direction:
      - 'bidirectional' (antonym, synonym, see_also): symmetric — display on both
        words' pages.
      - 'forward' (derived, etymological): this word derives FROM other_word.
        Display on this word's page as outgoing.
      - 'reverse': stored for completeness — this word is the source of a
        forward relationship from another word. Display as incoming.
    """

    other_word_id: UUID
    other_headword: str
    other_slug: str
    relationship_type: str  # 'antonym' | 'synonym' | 'see_also' | 'derived' | 'etymological'
    direction: str  # 'bidirectional' | 'forward' | 'reverse'
    note: str | None = None


# Deprecated: kept for backward-compat with old WordDetail.relations field.
# New code should use WordDetail.variations + WordDetail.relationships instead.
class RelationOut(BaseModel):
    """DEPRECATED — use VariationOut / RelationshipOut instead.

    Kept for backward compatibility with the v1.1 frontend. Will be removed
    in v1.3 once the frontend migrates to the new split fields.
    """

    other_word_id: UUID
    other_headword: str
    other_slug: str | None = None
    relation_type: str  # 'variant' | 'plural' | 'singular' | 'see_also' | ...
    direction: str  # 'outgoing' | 'incoming'


# ═══════════════════════════════════════════════════════════════
# Word list / search item (lightweight card)
# ═══════════════════════════════════════════════════════════════


class WordListItem(BaseModel):
    """Lightweight word card for list and search results.

    Only includes the fields needed to render a list item.
    Use GET /api/words/{slug_or_id} for the full detail.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    headword: str
    part_of_speech: str | None = None
    noun_class: str | None = None
    dialect: str | None = None
    swahili_translation: str | None = None
    english_translation: str | None = None
    has_relations: bool = False


class WordListResponse(BaseModel):
    """Paginated list of words."""

    items: list[WordListItem]
    total: int
    page: int
    size: int
    has_next: bool


# ═══════════════════════════════════════════════════════════════
# Word detail (full)
# ═══════════════════════════════════════════════════════════════


# Map internal DB status to the public API status enum.
# 'live'   -> 'active'  (visible in the dictionary)
# 'hidden' -> 'hidden'  (soft-deleted)
# 'merged' -> 'hidden'  (was merged into another word; never exposed publicly)
_STATUS_MAP = {"live": "active", "hidden": "hidden", "merged": "hidden"}


class WordDetail(BaseModel):
    """Full word detail for the word detail page."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    headword: str
    part_of_speech: str | None = None
    noun_class: str | None = None
    dialect: str | None = None
    literal_translation: str | None = None
    morphology_notes: str | None = None
    status: str
    created_at: datetime

    translations: list[TranslationOut] = []
    examples: list[ExampleOut] = []
    variations: list[VariationOut] = []
    relationships: list[RelationshipOut] = []
    senses: list[SenseOut] = []
    # Deprecated: still populated by the API for backward compat with v1.1
    # frontend code. New frontend code should use `variations` + `relationships`.
    relations: list[RelationOut] = []

    @field_validator("status", mode="before")
    @classmethod
    def _map_status(cls, v: str | None) -> str:
        """Map internal DB status to the public API status enum."""
        if v is None:
            return "active"
        return _STATUS_MAP.get(v, v)


# ═══════════════════════════════════════════════════════════════
# Search (extends list response with similarity score)
# ═══════════════════════════════════════════════════════════════


class SearchResultItem(WordListItem):
    """A search result, with a similarity score for ranking display."""

    similarity: float | None = None


class SearchResponse(BaseModel):
    """Response from GET /api/search."""

    query: str
    items: list[SearchResultItem]
    total: int

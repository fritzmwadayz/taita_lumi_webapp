"""Pydantic response schemas for the TaitaLumi API.

These define the shape of API responses, used for:
  - Auto-generated OpenAPI docs at /docs
  - Typed responses the Vue frontend can rely on
  - Validation that DB rows serialize correctly
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ═══════════════════════════════════════════════════════════════
# Glosses & Relations (nested in WordDetail)
# ═══════════════════════════════════════════════════════════════


class GlossOut(BaseModel):
    """A single translation in a specific language."""

    model_config = ConfigDict(from_attributes=True)

    language: str  # 'sw' or 'en'
    text: str


class RelationOut(BaseModel):
    """A relation between this word and another word.

    'direction' is 'outgoing' if this word points to the other
    (e.g. this is the singular, other is the plural), or 'incoming'
    if the other word points to this one.
    """

    other_word_id: UUID
    other_headword: str
    relation_type: str  # 'plural' | 'singular' | 'variant' | 'see_also' | ...
    direction: str  # 'outgoing' | 'incoming'


class ExampleOut(BaseModel):
    """A usage example with parallel text. Empty for now (Phase 1 has no examples)."""

    model_config = ConfigDict(from_attributes=True)

    taita_text: str
    swahili_text: str | None = None
    english_text: str | None = None
    source_ref: str | None = None


# ═══════════════════════════════════════════════════════════════
# Word list / search item (lightweight card)
# ═══════════════════════════════════════════════════════════════


class WordListItem(BaseModel):
    """Lightweight word card for list and search results.

    Only includes the fields needed to render a list item.
    Use GET /api/words/{id} for the full detail.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    headword: str
    part_of_speech: str | None = None
    noun_class: str | None = None
    dialect: str | None = None
    swahili_gloss: str | None = None
    english_gloss: str | None = None
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


class WordDetail(BaseModel):
    """Full word detail for the word detail page."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    headword: str
    part_of_speech: str | None = None
    noun_class: str | None = None
    dialect: str | None = None
    literal_translation: str | None = None
    morphology_notes: str | None = None
    status: str
    created_at: datetime

    glosses: list[GlossOut] = []
    examples: list[ExampleOut] = []
    relations: list[RelationOut] = []


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

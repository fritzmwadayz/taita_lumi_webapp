"""Pydantic response schemas for the TaitaLumi API.

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
# Glosses, Examples & Relations (nested in WordDetail)
# ═══════════════════════════════════════════════════════════════


class GlossOut(BaseModel):
    """A single translation of a word in a specific language."""

    model_config = ConfigDict(from_attributes=True)

    language: str  # 'sw' or 'en'
    text: str


class ExampleOut(BaseModel):
    """A usage example with parallel text in Taita / Swahili / English.

    The frontend pairs these as parallel translations. If a translation
    is missing (e.g. swahili_text is None), the frontend offers the reader
    a non-confrontational option to suggest one via POST /api/suggestions
    with target_type='example'.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    taita_text: str
    swahili_text: str | None = None
    english_text: str | None = None
    source_ref: str | None = None


class RelationOut(BaseModel):
    """A relation between this word and another word.

    'direction' is 'outgoing' if this word points to the other
    (e.g. this is the singular, other is the plural), or 'incoming'
    if the other word points to this one.

    Variations (relation_type='variant') are treated as bidirectional for
    the 'see also' UX: the frontend's "See also" section surfaces all
    variant relations regardless of direction.
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

    glosses: list[GlossOut] = []
    examples: list[ExampleOut] = []
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

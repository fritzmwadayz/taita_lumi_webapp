"""Pydantic schemas for suggestion endpoints.

A suggestion is a proposal to add or correct a word (or related entity).
Phase 3 supports two target types:
  - 'new_word': propose a brand new word
  - 'word': propose a correction to an existing word's field

Other target types (gloss, example, relation) will be added in later phases.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════════
# Request schemas
# ═══════════════════════════════════════════════════════════════


class NewWordProposal(BaseModel):
    """Proposed data for a new word. Used when target_type='new_word'."""

    headword: str = Field(..., min_length=1, max_length=200)
    part_of_speech: str | None = None
    noun_class: str | None = None
    dialect: str | None = None
    literal_translation: str | None = None
    morphology_notes: str | None = None
    swahili_gloss: str | None = None
    english_gloss: str | None = None


class CreateSuggestionRequest(BaseModel):
    """Create a new suggestion.

    For target_type='new_word':
      - target_id and field_path are ignored
      - proposed_value should be a NewWordProposal dict

    For target_type='word':
      - target_id is the word UUID being corrected
      - field_path is the field name (e.g. 'headword', 'part_of_speech')
      - proposed_value is the new value for that field
    """

    target_type: str = Field(..., description="'new_word' or 'word'")
    target_id: UUID | None = None
    field_path: str | None = None
    proposed_value: dict = Field(..., description="The proposed new value or full entity")
    rationale: str | None = Field(None, max_length=2000)


# ═══════════════════════════════════════════════════════════════
# Response schemas
# ═══════════════════════════════════════════════════════════════


class SuggestionResponse(BaseModel):
    """A single suggestion, returned by GET /api/suggestions/{id}."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_type: str
    target_id: UUID | None = None
    field_path: str | None = None
    proposed_value: dict
    rationale: str | None = None
    status: str
    created_by_user_id: UUID | None = None
    created_by_session_id: UUID | None = None
    created_at: datetime
    decided_at: datetime | None = None
    decided_by_user_id: UUID | None = None
    applied_at: datetime | None = None

    # Derived fields (not in DB — computed for display)
    author_display: str | None = None  # "@username" or "anonymous"
    upvotes: int = 0
    downvotes: int = 0
    user_vote: str | None = None  # 'up', 'down', or None — current user's vote


class SuggestionListItem(BaseModel):
    """Lightweight suggestion card for list view."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_type: str
    target_id: UUID | None = None
    field_path: str | None = None
    proposed_value: dict
    rationale: str | None = None
    status: str
    created_at: datetime
    author_display: str | None = None
    upvotes: int = 0
    downvotes: int = 0
    user_vote: str | None = None  # current user's vote (None if anon/not voted)


class SuggestionListResponse(BaseModel):
    """Paginated list of suggestions."""

    items: list[SuggestionListItem]
    total: int
    page: int
    size: int
    has_next: bool

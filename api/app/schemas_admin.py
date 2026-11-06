"""Pydantic schemas for admin endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import WordListItem


# ═══════════════════════════════════════════════════════════════
# User management
# ═══════════════════════════════════════════════════════════════


class AdminUserResponse(BaseModel):
    """User as seen by admins — includes role + blocked status."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str | None = None
    role: str
    is_blocked: bool
    created_at: datetime
    last_seen_at: datetime | None = None


class AdminUserListResponse(BaseModel):
    """Paginated list of users."""

    items: list[AdminUserResponse]
    total: int
    page: int
    size: int
    has_next: bool


class UpdateUserRequest(BaseModel):
    """Update a user's role or blocked status."""

    role: str | None = Field(None, description="'user', 'reviewer', or 'admin'")
    is_blocked: bool | None = None


# ═══════════════════════════════════════════════════════════════
# Suggestion decide (admin accept/reject)
# ═══════════════════════════════════════════════════════════════


class DecideSuggestionRequest(BaseModel):
    """Admin accepts or rejects a suggestion manually."""

    decision: str = Field(..., description="'accept' or 'reject'")


# ═══════════════════════════════════════════════════════════════
# Word edit / hide / merge
# ═══════════════════════════════════════════════════════════════


class ExampleInput(BaseModel):
    """An example as provided in word create/edit requests.

    If `id` is provided on edit, the existing example is updated; otherwise
    a new example is created. Translations are paired: taita_text is
    required, swahili_text and english_text are optional (the frontend will
    offer readers a non-confrontational option to suggest missing ones via
    POST /api/suggestions with target_type='example').
    """

    id: UUID | None = None  # only set when editing an existing example
    taita_text: str = Field(..., min_length=1)
    swahili_text: str | None = None
    english_text: str | None = None
    source_ref: str | None = None


class EditWordRequest(BaseModel):
    """Admin edits a word's fields. All fields optional — only provided fields are updated.

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


class MergeWordsRequest(BaseModel):
    """Merge source word into target word. Source is soft-deleted."""

    source_id: UUID = Field(..., description="The word to merge FROM (will be hidden)")
    target_id: UUID = Field(..., description="The word to merge INTO (kept)")


# ═══════════════════════════════════════════════════════════════
# Audit log — public shape (matches frontend TypeScript interface)
# ═══════════════════════════════════════════════════════════════
#
# The DB table (edit_log) has different column names:
#   actor_user_id, actor_session_id, action, entity_type, entity_id, before, after
#
# The public API shape (4.8 in the integration doc) is:
#   actor_id, actor_email, actor_role, action, target_type, target_id, details
#
# The mapping happens at the route layer (admin.py), which JOINs users
# to populate actor_email/actor_role and merges before+after into a single
# `details` JSON object. The action namespace is also mapped at that layer:
#   'create'  → 'word.create' (etc.)  — see app.routes.admin._map_action()
#


class AuditLogEntry(BaseModel):
    """A single audit log entry, in the public API shape (4.8)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    actor_id: UUID | None = None
    actor_email: str | None = None
    actor_role: str | None = None
    action: str  # dotted: 'word.create', 'word.hide', 'user.role.change', 'suggestion.accept', ...
    target_type: str | None = None
    target_id: UUID | None = None
    details: dict | None = None  # {before: ..., after: ...} or just the change payload


class AuditLogResponse(BaseModel):
    """Paginated audit log."""

    items: list[AuditLogEntry]
    total: int
    page: int
    size: int
    has_next: bool


# ═══════════════════════════════════════════════════════════════
# Dashboard stats
# ═══════════════════════════════════════════════════════════════


class RecentSuggestionItem(BaseModel):
    """Recent suggestion card for the dashboard."""

    id: UUID
    headword: str | None = None
    target_type: str
    status: str
    created_at: datetime


class DashboardStats(BaseModel):
    """Stats for the admin dashboard.

    Note: `total_suggestions` is intentionally kept even though it's not in
    the integration doc's 4.6 — it powers the "sign up to contribute" CTA
    on the public site and is part of why we have user accounts.
    """

    total_words: int
    total_users: int
    total_suggestions: int
    open_suggestions: int
    accepted_suggestions: int
    rejected_suggestions: int
    total_votes: int
    recent_words: list[WordListItem] = []  # last 5 words added (full WordListItem shape)
    recent_suggestions: list[RecentSuggestionItem] = []  # last 5 suggestions

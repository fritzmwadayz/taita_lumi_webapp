"""Pydantic schemas for admin endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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

    role: str | None = Field(None, description="'contributor' or 'admin'")
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


class EditWordRequest(BaseModel):
    """Admin edits a word's fields. All fields optional — only provided fields are updated."""

    headword: str | None = None
    part_of_speech: str | None = None
    noun_class: str | None = None
    dialect: str | None = None
    literal_translation: str | None = None
    morphology_notes: str | None = None
    swahili_gloss: str | None = None
    english_gloss: str | None = None


class MergeWordsRequest(BaseModel):
    """Merge source word into target word. Source is soft-deleted."""

    source_id: UUID = Field(..., description="The word to merge FROM (will be hidden)")
    target_id: UUID = Field(..., description="The word to merge INTO (kept)")


# ═══════════════════════════════════════════════════════════════
# Audit log
# ═══════════════════════════════════════════════════════════════


class AuditLogEntry(BaseModel):
    """A single audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None = None
    actor_session_id: UUID | None = None
    action: str
    entity_type: str
    entity_id: UUID
    before: dict | None = None
    after: dict | None = None
    created_at: datetime


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


class DashboardStats(BaseModel):
    """Stats for the admin dashboard."""

    total_words: int
    total_users: int
    total_suggestions: int
    open_suggestions: int
    accepted_suggestions: int
    rejected_suggestions: int
    total_votes: int
    recent_words: list[dict] = []  # last 5 words added
    recent_suggestions: list[dict] = []  # last 5 suggestions

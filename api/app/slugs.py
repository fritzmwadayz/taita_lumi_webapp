"""Slug generation and collision handling for words.

A slug is a human-readable, URL-safe identifier derived from the headword:
  - lowercase
  - non-alpha characters (except apostrophes) replaced with spaces, then hyphens
  - collapsed consecutive hyphens
  - leading/trailing hyphens stripped

Slugs must be unique. On collision, append "-2", "-3", ... until free.

Examples:
  "Mlima"          -> "mlima"
  "Ki-dzonzi"      -> "ki-dzonzi"
  "Ng'ombe"        -> "ng-ombe"
  "Mlima" (dup)    -> "mlima-2"

Used by:
  - POST /api/words (word creation)
  - PATCH /api/words/{id} (headword change)
  - app.promote._apply_new_word (auto-promote / accept)
  - app.cli.import_data (bulk import)
"""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Word

# Match headword-to-slug: keep [a-z] and apostrophes, replace everything else with space,
# then collapse whitespace to a single hyphen.
_SLUG_STRIP = re.compile(r"[^a-z']+")
_SLUG_COLLAPSE = re.compile(r"\s+")


def make_slug(headword: str) -> str:
    """Convert a headword to a slug.

    Returns an empty string if the headword contains no slug-able characters.
    Caller must handle the empty case (word creation should reject it).
    """
    if not headword:
        return ""
    s = headword.lower().strip()
    s = _SLUG_STRIP.sub(" ", s)
    s = _SLUG_COLLAPSE.sub("-", s.strip())
    s = s.strip("-")
    return s


async def generate_unique_slug(
    db: AsyncSession,
    headword: str,
    *,
    exclude_word_id: UUID | None = None,
) -> str:
    """Generate a unique slug for the given headword.

    If `exclude_word_id` is provided, that word's current slug is not counted
    as a collision (used when regenerating a slug for an existing word whose
    headword is being edited — we don't want a self-collision).

    The function tries the base slug, then "base-2", "base-3", etc. up to 1000
    before raising RuntimeError (in practice, collisions are extremely rare
    because headwords are near-unique by normalized_form already).
    """
    base = make_slug(headword)
    if not base:
        raise ValueError("Cannot generate slug from empty headword")

    candidate = base
    suffix = 2
    while True:
        stmt = select(Word.id).where(Word.slug == candidate)
        if exclude_word_id is not None:
            stmt = stmt.where(Word.id != exclude_word_id)
        result = await db.execute(stmt)
        existing_id = result.scalar_one_or_none()
        if existing_id is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1
        if suffix > 1000:
            raise RuntimeError(
                f"Could not find a unique slug for {headword!r} after 1000 attempts"
            )

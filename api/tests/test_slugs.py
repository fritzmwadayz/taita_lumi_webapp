"""Tests for slug generation and collision handling (app.slugs)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.slugs import generate_unique_slug, make_slug


# ═══════════════════════════════════════════════════════════════
# make_slug — pure function, no DB
# ═══════════════════════════════════════════════════════════════


class TestMakeSlug:
    def test_simple_lowercase(self):
        assert make_slug("Mlima") == "mlima"

    def test_already_lowercase(self):
        assert make_slug("mlima") == "mlima"

    def test_with_apostrophe(self):
        # Apostrophes are preserved (Taita words use them)
        assert make_slug("ng'ombe") == "ng'ombe"

    def test_with_hyphen(self):
        # Hyphens become spaces then collapse to hyphens
        assert make_slug("Ki-dzonzi") == "ki-dzonzi"

    def test_with_spaces(self):
        assert make_slug("Mlima Mkuu") == "mlima-mkuu"

    def test_with_special_chars(self):
        assert make_slug("Mlima (kubwa)!") == "mlima-kubwa"

    def test_leading_trailing_whitespace(self):
        assert make_slug("  mlima  ") == "mlima"

    def test_multiple_spaces_collapsed(self):
        assert make_slug("a   b") == "a-b"

    def test_empty_string(self):
        assert make_slug("") == ""

    def test_only_special_chars(self):
        # All non-alpha → empty slug
        assert make_slug("!!!") == ""

    def test_none_input(self):
        assert make_slug(None) == ""  # type: ignore[arg-type]

    def test_numbers_stripped(self):
        assert make_slug("mlima123") == "mlima"

    def test_unicode_lowercased(self):
        # Latin extended should lowercase fine
        assert make_slug("Mlima") == "mlima"


# ═══════════════════════════════════════════════════════════════
# generate_unique_slug — async, uses DB session
# ═══════════════════════════════════════════════════════════════


class MockSlugResult:
    """Mock SQLAlchemy Result that returns a single scalar (the existing word id)."""

    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


@pytest.mark.asyncio
async def test_generate_unique_slug_no_collision():
    """If no word has the slug, return it as-is."""
    db = MagicMock()
    db.execute = AsyncMock(return_value=MockSlugResult(value=None))

    slug = await generate_unique_slug(db, "Mlima")
    assert slug == "mlima"


@pytest.mark.asyncio
async def test_generate_unique_slug_with_collision():
    """If 'mlima' is taken, return 'mlima-2'."""
    existing_id = uuid.uuid4()
    # First call (slug='mlima') returns existing → collision
    # Second call (slug='mlima-2') returns None → free
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[MockSlugResult(value=existing_id), MockSlugResult(value=None)]
    )

    slug = await generate_unique_slug(db, "Mlima")
    assert slug == "mlima-2"


@pytest.mark.asyncio
async def test_generate_unique_slug_with_multiple_collisions():
    """If 'mlima' and 'mlima-2' are taken, return 'mlima-3'."""
    existing_id_1 = uuid.uuid4()
    existing_id_2 = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            MockSlugResult(value=existing_id_1),  # mlima taken
            MockSlugResult(value=existing_id_2),  # mlima-2 taken
            MockSlugResult(value=None),           # mlima-3 free
        ]
    )

    slug = await generate_unique_slug(db, "Mlima")
    assert slug == "mlima-3"


@pytest.mark.asyncio
async def test_generate_unique_slug_excludes_self():
    """When regenerating a slug for an existing word, the word's own current
    slug is not counted as a collision (exclude_word_id)."""
    word_id = uuid.uuid4()
    # Only one call should be made (no collision because we exclude self)
    db = MagicMock()
    db.execute = AsyncMock(return_value=MockSlugResult(value=None))

    slug = await generate_unique_slug(db, "Mlima", exclude_word_id=word_id)
    assert slug == "mlima"


@pytest.mark.asyncio
async def test_generate_unique_slug_empty_headword_raises():
    """Empty headword should raise ValueError."""
    db = MagicMock()
    with pytest.raises(ValueError, match="empty headword"):
        await generate_unique_slug(db, "")

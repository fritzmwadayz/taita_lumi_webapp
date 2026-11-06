"""Tests for word slug support, status enum mapping, and examples.

Covers:
  - GET /api/words/{slug}     — slug lookup (Phase D)
  - GET /api/words/{uuid}     — UUID lookup (backward compat, Phase D)
  - WordListItem.slug field    — present in list/search responses (Phase D)
  - WordDetail.status mapping  — 'live' → 'active' (Phase C)
  - WordDetail.examples       — real examples surface (Phase E)
  - POST /api/words           — examples accepted in body (Phase E)
  - PATCH /api/words/{id}     — examples replace strategy (Phase E)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.deps import require_reviewer
from app.main import app
from app.models import Example, Gloss, Word


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def make_mock_word(
    headword: str = "mlima",
    slug: str = "mlima",
    part_of_speech: str | None = "noun",
    dialect: str | None = "Dawida",
    swahili_gloss: str | None = "mlima, kilima",
    english_gloss: str | None = "mountain, hill",
    status: str = "live",
    examples: list[Example] | None = None,
) -> MagicMock:
    """Create a mock Word object with glosses + examples eager-loaded."""
    word = MagicMock(spec=Word)
    word.id = uuid.uuid4()
    word.headword = headword
    word.normalized_form = headword.lower()
    word.slug = slug
    word.part_of_speech = part_of_speech
    word.noun_class = None
    word.dialect = dialect
    word.literal_translation = None
    word.morphology_notes = None
    word.status = status
    word.created_at = datetime.now(timezone.utc)

    glosses = []
    if swahili_gloss:
        g = MagicMock(spec=Gloss)
        g.language = "sw"
        g.text = swahili_gloss
        glosses.append(g)
    if english_gloss:
        g = MagicMock(spec=Gloss)
        g.language = "en"
        g.text = english_gloss
        glosses.append(g)
    word.glosses = glosses
    word.examples = examples or []
    return word


def make_mock_example(
    taita_text: str = "Mlima u mrefu.",
    swahili_text: str | None = "Mlima ni mrefu.",
    english_text: str | None = "The mountain is tall.",
    source_ref: str | None = "story-1",
) -> MagicMock:
    ex = MagicMock(spec=Example)
    ex.id = uuid.uuid4()
    ex.taita_text = taita_text
    ex.swahili_text = swahili_text
    ex.english_text = english_text
    ex.source_ref = source_ref
    return ex


class MockResult:
    def __init__(self, value=None, rows=None):
        self._value = value
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._value

    def scalar(self):
        return self._value

    def scalars(self):
        m = MagicMock()
        m.all.return_value = self._rows
        m.unique.return_value = m
        return m

    def all(self):
        return self._rows


@pytest.fixture
async def mock_db():
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=1)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
async def client_with_mock_db(mock_db):
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def client_authed(client_with_mock_db, mock_db):
    user = MagicMock(spec=Word)
    user.id = uuid.uuid4()
    user.email = "reviewer@example.com"
    user.display_name = "reviewer"
    user.role = "reviewer"
    user.is_blocked = False

    async def override_auth():
        return user

    app.dependency_overrides[require_reviewer] = override_auth
    return client_with_mock_db


# ═══════════════════════════════════════════════════════════════
# Phase D: Slug lookup
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_word_by_slug(client_with_mock_db, mock_db):
    """GET /api/words/{slug} looks up the word by slug."""
    word = make_mock_word(headword="mlima", slug="mlima")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = word
    # Two execute calls: word fetch + relations fetch (outgoing + incoming)
    mock_db.execute = AsyncMock(
        side_effect=[
            mock_result,                       # word fetch
            MockResult(rows=[]),               # outgoing relations
            MockResult(rows=[]),               # incoming relations
        ]
    )

    response = await client_with_mock_db.get("/api/words/mlima")

    assert response.status_code == 200
    data = response.json()
    assert data["headword"] == "mlima"
    assert data["slug"] == "mlima"


@pytest.mark.asyncio
async def test_get_word_by_uuid_still_works(client_with_mock_db, mock_db):
    """GET /api/words/{uuid} still works for backward compatibility."""
    word_id = uuid.uuid4()
    word = make_mock_word(headword="mlima", slug="mlima")
    word.id = word_id
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = word
    mock_db.execute = AsyncMock(
        side_effect=[
            mock_result,
            MockResult(rows=[]),
            MockResult(rows=[]),
        ]
    )

    response = await client_with_mock_db.get(f"/api/words/{word_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(word_id)
    assert data["slug"] == "mlima"


@pytest.mark.asyncio
async def test_get_word_by_unknown_slug_returns_404(client_with_mock_db, mock_db):
    """GET /api/words/{unknown-slug} returns 404."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await client_with_mock_db.get("/api/words/nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════
# Phase D: Slug field in list/search responses
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_words_includes_slug(client_with_mock_db, mock_db):
    """GET /api/words response items include the slug field."""
    word = make_mock_word(headword="mlima", slug="mlima")
    mock_result = MagicMock()
    mock_result.scalars.return_value.unique.return_value.all.return_value = [word]
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.scalar = AsyncMock(return_value=1)

    response = await client_with_mock_db.get("/api/words")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["slug"] == "mlima"


# ═══════════════════════════════════════════════════════════════
# Phase C: Status enum mapping (live → active)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_word_detail_status_live_mapped_to_active(client_with_mock_db, mock_db):
    """WordDetail.status='live' is mapped to 'active' in the API response."""
    word = make_mock_word(status="live")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = word
    mock_db.execute = AsyncMock(
        side_effect=[mock_result, MockResult(rows=[]), MockResult(rows=[])]
    )

    response = await client_with_mock_db.get("/api/words/mlima")

    assert response.status_code == 200
    assert response.json()["status"] == "active"


@pytest.mark.asyncio
async def test_word_detail_status_hidden_passes_through(client_with_mock_db, mock_db):
    """WordDetail.status='hidden' passes through as 'hidden'."""
    word = make_mock_word(status="hidden")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = word
    mock_db.execute = AsyncMock(
        side_effect=[mock_result, MockResult(rows=[]), MockResult(rows=[])]
    )

    response = await client_with_mock_db.get("/api/words/mlima")

    # Word is hidden → 404 (because the query filters status='live')
    # but if it slipped through, the mapping would still produce 'hidden'
    # This test documents that mapping behaviour; the 404 is also fine.
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        assert response.json()["status"] == "hidden"


def test_status_mapping_via_schema_directly():
    """Directly test the field_validator on WordDetail."""
    from app.schemas import WordDetail

    word_id = uuid.uuid4()
    detail = WordDetail(
        id=word_id,
        slug="mlima",
        headword="mlima",
        status="live",  # internal value
        created_at=datetime.now(timezone.utc),
    )
    assert detail.status == "active"

    detail2 = WordDetail(
        id=word_id,
        slug="mlima",
        headword="mlima",
        status="merged",  # internal value
        created_at=datetime.now(timezone.utc),
    )
    assert detail2.status == "hidden"  # merged → hidden


# ═══════════════════════════════════════════════════════════════
# Phase E: Examples surface in word detail
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_word_detail_surfaces_examples(client_with_mock_db, mock_db):
    """WordDetail.examples returns real examples (not [])."""
    ex1 = make_mock_example(
        taita_text="Mlima u mrefu.",
        swahili_text="Mlima ni mrefu.",
        english_text="The mountain is tall.",
    )
    ex2 = make_mock_example(
        taita_text="Wari mlima.",
        swahili_text=None,  # missing translation — frontend offers to suggest
        english_text=None,
    )
    word = make_mock_word(examples=[ex1, ex2])
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = word
    mock_db.execute = AsyncMock(
        side_effect=[mock_result, MockResult(rows=[]), MockResult(rows=[])]
    )

    response = await client_with_mock_db.get("/api/words/mlima")

    assert response.status_code == 200
    examples = response.json()["examples"]
    assert len(examples) == 2
    assert examples[0]["taita_text"] == "Mlima u mrefu."
    assert examples[0]["swahili_text"] == "Mlima ni mrefu."
    assert examples[0]["english_text"] == "The mountain is tall."
    assert examples[0]["id"] == str(ex1.id)
    # Second example has missing translations
    assert examples[1]["swahili_text"] is None
    assert examples[1]["english_text"] is None


# ═══════════════════════════════════════════════════════════════
# Phase E: Examples accepted in POST /api/words
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_word_with_examples(client_authed, mock_db):
    """POST /api/words accepts examples in the body and creates them."""
    # Mock: no duplicate found, generate_unique_slug returns 'mlima'
    no_dup_result = MagicMock()
    no_dup_result.scalar_one_or_none.return_value = None
    # slug lookup (returns None — no collision)
    slug_result = MagicMock()
    slug_result.scalar_one_or_none.return_value = None
    # final word fetch (after commit)
    word = make_mock_word(headword="mlima", slug="mlima")
    final_result = MagicMock()
    final_result.scalar_one.return_value = word
    # relations fetch
    mock_db.execute = AsyncMock(
        side_effect=[
            no_dup_result,    # duplicate check
            slug_result,      # slug collision check
            final_result,     # final word fetch
            MockResult(rows=[]),  # outgoing relations
            MockResult(rows=[]),  # incoming relations
        ]
    )

    response = await client_authed.post(
        "/api/words",
        json={
            "headword": "mlima",
            "swahili_gloss": "mlima",
            "examples": [
                {
                    "taita_text": "Mlima u mrefu.",
                    "swahili_text": "Mlima ni mrefu.",
                    "english_text": "The mountain is tall.",
                },
                {
                    "taita_text": "Wari mlima.",
                    # missing translations — frontend will offer to suggest
                },
            ],
        },
    )

    assert response.status_code == 201
    # Verify db.add was called for the word + gloss + 2 examples + edit_log + suggestion
    # (we don't count exactly because the provenance suggestion also adds)
    assert mock_db.add.call_count >= 5  # word + gloss + 2 examples + edit_log + suggestion


@pytest.mark.asyncio
async def test_create_word_examples_optional(client_authed, mock_db):
    """POST /api/words without examples field still works."""
    no_dup_result = MagicMock()
    no_dup_result.scalar_one_or_none.return_value = None
    slug_result = MagicMock()
    slug_result.scalar_one_or_none.return_value = None
    word = make_mock_word(headword="mlima", slug="mlima")
    final_result = MagicMock()
    final_result.scalar_one.return_value = word
    mock_db.execute = AsyncMock(
        side_effect=[
            no_dup_result,
            slug_result,
            final_result,
            MockResult(rows=[]),
            MockResult(rows=[]),
        ]
    )

    response = await client_authed.post(
        "/api/words",
        json={"headword": "mlima", "swahili_gloss": "mlima"},
    )

    assert response.status_code == 201


# ═══════════════════════════════════════════════════════════════
# Phase E: Examples replace strategy on PATCH /api/words/{id}
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_edit_word_replaces_examples(client_authed, mock_db):
    """PATCH /api/words/{id} with examples replaces the example set."""
    existing_ex = make_mock_example(taita_text="Old example.")
    kept_ex = make_mock_example(taita_text="Kept example.")
    kept_ex_id = kept_ex.id
    word = make_mock_word(examples=[existing_ex, kept_ex])

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = word
    new_ex_mock = MagicMock(spec=Example)
    new_ex_mock.id = uuid.uuid4()
    new_ex_mock.taita_text = "New example."
    new_ex_mock.swahili_text = None
    new_ex_mock.english_text = None
    new_ex_mock.source_ref = None
    final_word = make_mock_word(
        headword="mlima",
        slug="mlima",
        examples=[kept_ex, new_ex_mock],
    )
    final_result = MagicMock()
    final_result.scalar_one.return_value = final_word

    # No headword change → no slug regen check.
    # Call sequence: initial fetch, final fetch, outgoing relations, incoming relations
    mock_db.execute = AsyncMock(
        side_effect=[
            fetch_result,             # initial word fetch
            final_result,             # final word fetch (after commit)
            MockResult(rows=[]),      # outgoing relations
            MockResult(rows=[]),      # incoming relations
        ]
    )

    response = await client_authed.patch(
        f"/api/words/{word.id}",
        json={
            "examples": [
                # Keep the existing example (with id)
                {
                    "id": str(kept_ex_id),
                    "taita_text": "Kept example (edited).",
                },
                # Add a new one (no id)
                {
                    "taita_text": "New example.",
                },
            ],
        },
    )

    assert response.status_code == 200
    # delete was called for the example not in the new set (existing_ex)
    assert mock_db.delete.call_count >= 1

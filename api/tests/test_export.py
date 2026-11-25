"""Tests for GET /api/export/dictionary — the bulk static-snapshot endpoint.

Mock-DB style matches tests/test_words.py: dependency_overrides with a mocked
AsyncSession. These tests cover the assembly contract (envelope fields, list
index parity with WordListItem, detail parity with the per-word endpoint) and
the empty-dictionary edge case.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.main import app
from app.models import Example, Sense, Translation, Word


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


def make_mock_word(headword: str = "mlima") -> MagicMock:
    word = MagicMock(spec=Word)
    word.id = uuid.uuid4()
    word.headword = headword
    word.normalized_form = headword.lower()
    word.slug = headword.lower()
    word.part_of_speech = "noun"
    word.noun_class = "3/4"
    word.dialect = "Dawida"
    word.literal_translation = None
    word.morphology_notes = None
    word.status = "live"
    word.created_at = datetime.now(timezone.utc)

    translations = []
    for language, text in (("sw", "mlima, kilima"), ("en", "mountain, hill")):
        g = MagicMock(spec=Translation)
        g.language = language
        g.text = text
        g.sense_id = None
        translations.append(g)
    word.translations = translations
    word.examples = []
    return word


def make_mock_sense(word_id, order: int = 1) -> MagicMock:
    s = MagicMock(spec=Sense)
    s.id = uuid.uuid4()
    s.word_id = word_id
    s.order_index = order
    s.part_of_speech = "noun"
    s.definition = f"definition {order}"
    s.notes = None
    return s


@pytest.fixture
async def mock_db():
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=1)
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


def _result_of(rows):
    """Build a mock execute() result whose .scalars().all() returns rows."""
    result = MagicMock()
    result.scalars.return_value.unique.return_value.all.return_value = rows
    result.all.return_value = rows
    result.scalars.return_value.all.return_value = rows
    return result


# ═══════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_export_empty_dictionary(client_with_mock_db, mock_db):
    """Empty dictionary → 200 with a zero-word envelope."""
    mock_db.execute = AsyncMock(return_value=_result_of([]))
    response = await client_with_mock_db.get("/api/export/dictionary")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["words"] == []
    assert data["list"] == []
    assert data["exported_at"]


@pytest.mark.asyncio
async def test_export_envelope_and_list_parity(client_with_mock_db, mock_db):
    """Two live words → envelope fields, list index, and full details."""
    w1 = make_mock_word("mlima")
    w2 = make_mock_word("ngoma")

    # Query order in the endpoint is fixed: words → senses → sense
    # translations → sense examples → variations → relationships →
    # relation-missing-word resolve (skipped, both live) → has-relations
    # unions. Dispatch by call count — no brittle SQL-string matching.
    responses = [_result_of([w1, w2])] + [_result_of([]) for _ in range(6)]

    calls = {"n": 0}

    async def execute_side_effect(stmt, *a, **kw):
        result = responses[min(calls["n"], len(responses) - 1)]
        calls["n"] += 1
        return result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)

    response = await client_with_mock_db.get("/api/export/dictionary")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    assert len(data["words"]) == 2
    assert len(data["list"]) == 2

    # List item parity with WordListItem
    mlima_list = data["list"][0]
    assert mlima_list["slug"] == "mlima"
    assert mlima_list["headword"] == "mlima"
    assert mlima_list["part_of_speech"] == "noun"
    assert mlima_list["noun_class"] == "3/4"
    assert mlima_list["dialect"] == "Dawida"
    assert mlima_list["swahili_translation"] == "mlima, kilima"
    assert mlima_list["english_translation"] == "mountain, hill"
    assert mlima_list["has_relations"] is False

    # Detail parity with the per-word endpoint
    mlima = data["words"][0]
    assert mlima["slug"] == "mlima"
    assert mlima["status"] == "active"  # live → active mapping
    assert mlima["translations"] == [
        {"language": "sw", "text": "mlima, kilima"},
        {"language": "en", "text": "mountain, hill"},
    ]
    assert mlima["examples"] == []
    assert mlima["senses"] == []
    assert mlima["variations"] == []
    assert mlima["relationships"] == []
    assert mlima["relations"] == []


@pytest.mark.asyncio
async def test_export_senses_and_examples(client_with_mock_db, mock_db):
    """Sense-scoped translations and examples land on the right sense."""
    w1 = make_mock_word("mlima")
    sense = make_mock_sense(w1.id, order=1)

    g = MagicMock(spec=Translation)
    g.language = "sw"
    g.text = "mlima"
    g.sense_id = sense.id

    ex = MagicMock(spec=Example)
    ex.id = uuid.uuid4()
    ex.sense_id = sense.id
    ex.taita_text = "Mlima ni mrefu."
    ex.swahili_text = "Mlima ni mrefu."
    ex.english_text = "The mountain is tall."
    ex.source_ref = None

    # Query order: words → senses → sense translations → sense examples →
    # variations → relationships → (missing-words resolve) → has-relations.
    responses = [
        _result_of([w1]),     # 0: live words
        _result_of([sense]),  # 1: senses
        _result_of([g]),      # 2: sense translations
        _result_of([ex]),     # 3: sense examples
        _result_of([]),       # 4: variations
        _result_of([]),       # 5: relationships
    ]

    calls = {"n": 0}

    async def execute_side_effect(stmt, *a, **kw):
        result = responses[min(calls["n"], len(responses) - 1)]
        calls["n"] += 1
        return result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)

    response = await client_with_mock_db.get("/api/export/dictionary")
    assert response.status_code == 200
    data = response.json()

    mlima = data["words"][0]
    assert len(mlima["senses"]) == 1
    sense_out = mlima["senses"][0]
    assert sense_out["order_index"] == 1
    assert sense_out["definition"] == "definition 1"
    assert sense_out["translations"] == [{"language": "sw", "text": "mlima"}]
    assert len(sense_out["examples"]) == 1
    assert sense_out["examples"][0]["taita_text"] == "Mlima ni mrefu."

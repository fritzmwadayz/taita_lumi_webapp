"""Tests for Phase H: senses table with strict scoping.

Verifies:
  - Migration 0005 is syntactically valid (revision chain)
  - WordDetail.senses field exists
  - SenseOut schema has the right shape
  - ExampleOut includes sense_id (strict scoping)
  - TranslationOut/ExampleOut can be attached to a sense
  - POST /api/words/:id/senses reviewer endpoint
  - PATCH /api/senses/:id reviewer endpoint
"""

from __future__ import annotations

import importlib.util
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.deps import require_reviewer
from app.main import app
from app.models import Example, Translation, Sense, User, Word


# ═══════════════════════════════════════════════════════════════
# Migration chain validation
# ═══════════════════════════════════════════════════════════════


def test_migration_0005_exists_and_chains_correctly():
    """The 0005 migration file exists and chains from 0004."""
    migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "0005_senses.py"
    assert migration_path.exists(), "Migration 0005 file should exist"

    spec = importlib.util.spec_from_file_location("m0005", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0005"
    assert module.down_revision == "0004"
    assert callable(module.upgrade)
    assert callable(module.downgrade)


# ═══════════════════════════════════════════════════════════════
# Sense model + schema
# ═══════════════════════════════════════════════════════════════


def test_sense_model_has_required_fields():
    """Sense model has word_id, order_index, definition, notes, part_of_speech."""
    # Verify the columns exist on the model class
    assert hasattr(Sense, "word_id")
    assert hasattr(Sense, "order_index")
    assert hasattr(Sense, "definition")
    assert hasattr(Sense, "notes")
    assert hasattr(Sense, "part_of_speech")
    assert hasattr(Sense, "created_by_user_id")
    assert hasattr(Sense, "reviewed_at")
    assert hasattr(Sense, "reviewed_by_user_id")


def test_gloss_model_has_sense_id():
    """Translation model has sense_id column (strict scoping)."""
    assert hasattr(Translation, "sense_id")


def test_example_model_has_sense_id():
    """Example model has sense_id column (strict scoping)."""
    assert hasattr(Example, "sense_id")


def test_word_detail_schema_has_senses_field():
    """WordDetail includes a senses field."""
    from app.schemas import WordDetail

    word_id = uuid.uuid4()
    detail = WordDetail(
        id=word_id,
        slug="mlima",
        headword="mlima",
        status="live",
        created_at=datetime.now(timezone.utc),
    )
    assert hasattr(detail, "senses")
    assert detail.senses == []


def test_sense_out_schema_shape():
    """SenseOut has id, order_index, definition, notes, translations, examples."""
    from app.schemas import SenseOut

    fields = SenseOut.model_fields
    assert "id" in fields
    assert "order_index" in fields
    assert "part_of_speech" in fields
    assert "definition" in fields
    assert "notes" in fields
    assert "translations" in fields
    assert "examples" in fields


def test_example_out_includes_sense_id():
    """ExampleOut includes sense_id (strict scoping)."""
    from app.schemas import ExampleOut

    fields = ExampleOut.model_fields
    assert "sense_id" in fields


# ═══════════════════════════════════════════════════════════════
# Helpers for endpoint tests
# ═══════════════════════════════════════════════════════════════


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


def make_flexible_execute(*primary_results, default_result=None):
    default = default_result if default_result is not None else MockResult(rows=[])

    async def side_effect(*args, **kwargs):
        nonlocal call_index
        if call_index < len(primary_results):
            r = primary_results[call_index]
        else:
            r = default
        call_index += 1
        return r

    call_index = 0
    return AsyncMock(side_effect=side_effect)


def make_mock_word(headword="mlima", slug="mlima") -> MagicMock:
    word = MagicMock(spec=Word)
    word.id = uuid.uuid4()
    word.headword = headword
    word.normalized_form = headword.lower()
    word.slug = slug
    word.part_of_speech = "noun"
    word.noun_class = None
    word.dialect = "Dawida"
    word.literal_translation = None
    word.morphology_notes = None
    word.status = "live"
    word.created_at = datetime.now(timezone.utc)
    word.translations = []
    word.examples = []
    return word


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
async def client_reviewer(mock_db):
    """HTTP client with reviewer auth."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "reviewer@example.com"
    user.display_name = "reviewer"
    user.role = "reviewer"
    user.is_blocked = False

    async def override_auth():
        return user

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_reviewer] = override_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════
# POST /api/words/:id/senses — add a sense
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_add_sense_to_word_unknown_word_returns_404(client_reviewer, mock_db):
    """POST /api/words/:id/senses to a non-existent word returns 404."""
    mock_db.execute = make_flexible_execute(MockResult(value=None))

    response = await client_reviewer.post(
        f"/api/words/{uuid.uuid4()}/senses",
        json={"definition": "Mountain, large hill"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_sense_to_word_creates_sense(client_reviewer, mock_db):
    """POST /api/words/:id/senses with valid body creates a sense with the next order_index."""
    word = make_mock_word()
    word_fetch = MagicMock()
    word_fetch.scalar_one_or_none.return_value = word

    # max(order_index) returns 1 (word already has sense 1)
    max_order_result = MagicMock()
    max_order_result.scalar.return_value = 1

    final_word = make_mock_word()
    final_fetch = MagicMock()
    final_fetch.scalar_one.return_value = final_word

    mock_db.execute = make_flexible_execute(word_fetch, max_order_result, final_fetch)

    response = await client_reviewer.post(
        f"/api/words/{word.id}/senses",
        json={
            "definition": "Pile, heap (e.g. of harvest)",
            "notes": "Specific to Dawida dialect",
        },
    )

    assert response.status_code == 201
    # db.add was called for the Sense + EditLog
    assert mock_db.add.call_count >= 2
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_add_sense_first_sense_gets_order_index_1(client_reviewer, mock_db):
    """When a word has no senses, the new sense gets order_index=1."""
    word = make_mock_word()
    word_fetch = MagicMock()
    word_fetch.scalar_one_or_none.return_value = word

    # max(order_index) returns None (no existing senses)
    max_order_result = MagicMock()
    max_order_result.scalar.return_value = None

    final_word = make_mock_word()
    final_fetch = MagicMock()
    final_fetch.scalar_one.return_value = final_word

    mock_db.execute = make_flexible_execute(word_fetch, max_order_result, final_fetch)

    response = await client_reviewer.post(
        f"/api/words/{word.id}/senses",
        json={"definition": "First sense"},
    )

    assert response.status_code == 201
    # Verify the Sense was created with order_index=1
    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
    senses_added = [o for o in added_objects if isinstance(o, Sense)]
    assert len(senses_added) == 1
    assert senses_added[0].order_index == 1


# ═══════════════════════════════════════════════════════════════
# PATCH /api/senses/:id — edit a sense
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_edit_sense_unknown_sense_returns_404(client_reviewer, mock_db):
    """PATCH /api/senses/:id to a non-existent sense returns 404."""
    mock_db.execute = make_flexible_execute(MockResult(value=None))

    response = await client_reviewer.patch(
        f"/api/senses/{uuid.uuid4()}",
        json={"definition": "Updated definition"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_edit_sense_updates_fields(client_reviewer, mock_db):
    """PATCH /api/senses/:id updates only the provided fields."""
    sense = MagicMock(spec=Sense)
    sense.id = uuid.uuid4()
    sense.word_id = uuid.uuid4()
    sense.order_index = 1
    sense.part_of_speech = "noun"
    sense.definition = "Old definition"
    sense.notes = None
    sense.reviewed_at = None
    sense.reviewed_by_user_id = None

    sense_fetch = MagicMock()
    sense_fetch.scalar_one_or_none.return_value = sense

    final_word = make_mock_word()
    final_fetch = MagicMock()
    final_fetch.scalar_one.return_value = final_word

    mock_db.execute = make_flexible_execute(sense_fetch, final_fetch)

    response = await client_reviewer.patch(
        f"/api/senses/{sense.id}",
        json={
            "definition": "New definition",
            "notes": "Updated notes",
        },
    )

    assert response.status_code == 200
    # Verify the sense was updated
    assert sense.definition == "New definition"
    assert sense.notes == "Updated notes"
    # part_of_speech should be unchanged (not in the request)
    assert sense.part_of_speech == "noun"
    # Reviewed fields should be set
    assert sense.reviewed_at is not None


@pytest.mark.asyncio
async def test_edit_sense_no_change_no_audit(client_reviewer, mock_db):
    """PATCH /api/senses/:id with no actual changes doesn't write an audit entry."""
    from app.models import EditLog

    sense = MagicMock(spec=Sense)
    sense.id = uuid.uuid4()
    sense.word_id = uuid.uuid4()
    sense.order_index = 1
    sense.part_of_speech = "noun"
    sense.definition = "Same definition"
    sense.notes = None
    sense.reviewed_at = None
    sense.reviewed_by_user_id = None

    sense_fetch = MagicMock()
    sense_fetch.scalar_one_or_none.return_value = sense

    final_word = make_mock_word()
    final_fetch = MagicMock()
    final_fetch.scalar_one.return_value = final_word

    mock_db.execute = make_flexible_execute(sense_fetch, final_fetch)

    # Set definition to the same value it already has
    response = await client_reviewer.patch(
        f"/api/senses/{sense.id}",
        json={"definition": "Same definition"},
    )

    assert response.status_code == 200
    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
    audit_entries = [o for o in added_objects if isinstance(o, EditLog)]
    assert len(audit_entries) == 0

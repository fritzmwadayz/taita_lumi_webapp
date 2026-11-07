"""Tests for Phase F: target_type='new_example' suggestion flow
and the POST /api/words/:id/examples reviewer shortcut.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.deps import get_optional_user, require_reviewer
from app.main import app
from app.models import User, Word


# ═══════════════════════════════════════════════════════════════
# Helpers
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
    """Build an AsyncMock for db.execute that returns primary_results in order,
    then default_result (or an empty MockResult) for any extra calls."""
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


def make_mock_word(headword="mlima", slug="mlima", examples=None) -> MagicMock:
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
    word.examples = examples or []
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

    # commit + refresh need to populate server-default fields (id, created_at)
    async def fake_commit():
        pass

    async def fake_refresh(obj):
        if not getattr(obj, "id", None):
            obj.id = uuid.uuid4()
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(timezone.utc)

    session.commit = AsyncMock(side_effect=fake_commit)
    session.refresh = AsyncMock(side_effect=fake_refresh)
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


# ═══════════════════════════════════════════════════════════════
# Phase F: new_example suggestion validation
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_new_example_suggestion_validates_taita_text_required(client_with_mock_db, mock_db):
    """new_example suggestion without taita_text returns 422."""
    async def override_auth():
        return None
    app.dependency_overrides[get_optional_user] = override_auth

    # Mock: target word exists
    word = make_mock_word()
    mock_db.execute = AsyncMock(return_value=MockResult(value=word))

    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "new_example",
            "target_id": str(word.id),
            "proposed_value": {"swahili_text": "Mlima ni mrefu."},
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_new_example_suggestion_validates_target_id_required(client_with_mock_db, mock_db):
    """new_example suggestion without target_id returns 422."""
    async def override_auth():
        return None
    app.dependency_overrides[get_optional_user] = override_auth

    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "new_example",
            "proposed_value": {"taita_text": "Mlima u mrefu."},
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_new_example_suggestion_unknown_word_returns_404(client_with_mock_db, mock_db):
    """new_example suggestion to non-existent word returns 404."""
    async def override_auth():
        return None
    app.dependency_overrides[get_optional_user] = override_auth

    mock_db.execute = AsyncMock(return_value=MockResult(value=None))

    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "new_example",
            "target_id": str(uuid.uuid4()),
            "proposed_value": {"taita_text": "Mlima u mrefu."},
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_new_example_suggestion_creates_open_suggestion(client_with_mock_db, mock_db):
    """A valid new_example suggestion from an authed user creates an open suggestion."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "user@example.com"
    user.display_name = "user"
    user.role = "user"
    user.is_blocked = False

    async def override_auth():
        return user
    app.dependency_overrides[get_optional_user] = override_auth

    # Mock: target word exists
    word = make_mock_word()
    mock_db.execute = AsyncMock(return_value=MockResult(value=word))

    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "new_example",
            "target_id": str(word.id),
            "proposed_value": {
                "taita_text": "Mlima u mrefu.",
                "swahili_text": "Mlima ni mrefu.",
                "english_text": "The mountain is tall.",
            },
            "rationale": "Common usage.",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["target_type"] == "new_example"
    assert data["status"] == "open"
    assert data["target_id"] == str(word.id)
    # db.add was called for the Suggestion
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


# ═══════════════════════════════════════════════════════════════
# Phase F: POST /api/words/:id/examples reviewer shortcut
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
async def client_reviewer(client_with_mock_db, mock_db):
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "reviewer@example.com"
    user.display_name = "reviewer"
    user.role = "reviewer"
    user.is_blocked = False

    async def override_auth():
        return user
    app.dependency_overrides[require_reviewer] = override_auth
    return client_with_mock_db


@pytest.mark.asyncio
async def test_add_example_to_word_requires_reviewer(client_with_mock_db, mock_db):
    """POST /api/words/:id/examples without reviewer role returns 401."""
    from fastapi import HTTPException, status

    async def override_auth():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    app.dependency_overrides[require_reviewer] = override_auth

    response = await client_with_mock_db.post(
        f"/api/words/{uuid.uuid4()}/examples",
        json={"taita_text": "Mlima u mrefu."},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_add_example_to_word_unknown_word_returns_404(client_reviewer, mock_db):
    """POST /api/words/:id/examples to a non-existent word returns 404."""
    mock_db.execute = AsyncMock(return_value=MockResult(value=None))

    response = await client_reviewer.post(
        f"/api/words/{uuid.uuid4()}/examples",
        json={"taita_text": "Mlima u mrefu."},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_example_to_word_validates_taita_text_required(client_reviewer, mock_db):
    """POST /api/words/:id/examples without taita_text returns 422."""
    response = await client_reviewer.post(
        f"/api/words/{uuid.uuid4()}/examples",
        json={"swahili_text": "Mlima ni mrefu."},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_example_to_word_creates_example(client_reviewer, mock_db):
    """POST /api/words/:id/examples with valid body creates an example."""
    word = make_mock_word()
    word_fetch = MagicMock()
    word_fetch.scalar_one_or_none.return_value = word

    # sense lookup returns None (no default sense)
    sense_lookup = MagicMock()
    sense_lookup.scalar_one_or_none.return_value = None

    final_word = make_mock_word()
    final_fetch = MagicMock()
    final_fetch.scalar_one.return_value = final_word

    mock_db.execute = make_flexible_execute(word_fetch, sense_lookup, final_fetch)

    response = await client_reviewer.post(
        f"/api/words/{word.id}/examples",
        json={
            "taita_text": "Mlima u mrefu.",
            "swahili_text": "Mlima ni mrefu.",
            "english_text": "The mountain is tall.",
        },
    )

    assert response.status_code == 201
    # db.add was called for the Sense, Example, and EditLog
    assert mock_db.add.call_count >= 3
    assert mock_db.commit.called

"""Tests for suggestion endpoints.

Uses FastAPI dependency_overrides to mock the DB session.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.main import app
from app.models import Suggestion, User


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def make_mock_suggestion(
    target_type="new_word",
    status="open",
    user_id=None,
    session_id=None,
) -> MagicMock:
    """Create a mock Suggestion object."""
    s = MagicMock(spec=Suggestion)
    s.id = uuid.uuid4()
    s.target_type = target_type
    s.target_id = None
    s.field_path = None
    s.proposed_value = {"headword": "test"}
    s.rationale = "test rationale"
    s.status = status
    s.created_by_user_id = user_id
    s.created_by_session_id = session_id
    s.created_at = datetime.now(timezone.utc)
    s.decided_at = None
    s.decided_by_user_id = None
    s.applied_at = None
    return s


class MockResult:
    """Mock SQLAlchemy Result."""

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
    """Mock AsyncSession."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MockResult())
    session.scalar = AsyncMock(return_value=0)
    session.add = MagicMock()

    # commit + refresh need to populate server-default fields (id, created_at)
    async def fake_commit():
        pass

    async def fake_refresh(obj):
        # Populate fields that the DB would set via server defaults
        if not getattr(obj, "id", None):
            obj.id = uuid.uuid4()
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(timezone.utc)

    session.commit = AsyncMock(side_effect=fake_commit)
    session.flush = AsyncMock()
    session.refresh = AsyncMock(side_effect=fake_refresh)
    return session


@pytest.fixture
async def client_with_mock_db(mock_db):
    """HTTP client with DB dependency overridden."""

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
async def client_unauth(client_with_mock_db):
    """Client with no auth (get_optional_user returns None — anon user)."""
    from app.deps import get_optional_user

    async def override_auth():
        return None

    app.dependency_overrides[get_optional_user] = override_auth
    return client_with_mock_db


@pytest.fixture
async def client_authed(client_with_mock_db):
    """Client with a mock authenticated user."""
    from app.deps import get_optional_user

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.display_name = "testuser"
    user.role = "reviewer"
    user.is_blocked = False

    async def override_auth():
        return user

    app.dependency_overrides[get_optional_user] = override_auth
    return client_with_mock_db


# ═══════════════════════════════════════════════════════════════
# Tests: POST /api/suggestions
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_suggestion_new_word_authed(client_authed, mock_db):
    """Authenticated reviewer can create a new_word suggestion."""
    response = await client_authed.post(
        "/api/suggestions",
        json={
            "target_type": "new_word",
            "proposed_value": {
                "headword": "mlima",
                "swahili_gloss": "mlima",
            },
            "rationale": "Common word, should be in the dictionary.",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["target_type"] == "new_word"
    assert data["status"] == "open"
    assert data["author_display"] == "@testuser"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_suggestion_word_correction_authed(client_authed, mock_db):
    """Authenticated reviewer can suggest a word correction."""
    word_id = uuid.uuid4()
    response = await client_authed.post(
        "/api/suggestions",
        json={
            "target_type": "word",
            "target_id": str(word_id),
            "field_path": "headword",
            "proposed_value": {"value": "mlima_corrected"},
            "rationale": "Spelling fix.",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["target_type"] == "word"
    assert data["target_id"] == str(word_id)
    assert data["field_path"] == "headword"


@pytest.mark.asyncio
async def test_create_suggestion_invalid_target_type(client_authed, mock_db):
    """Invalid target_type returns 422."""
    response = await client_authed.post(
        "/api/suggestions",
        json={
            "target_type": "invalid_type",
            "proposed_value": {"headword": "test"},
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_suggestion_new_word_missing_headword(client_authed, mock_db):
    """new_word suggestion without headword in proposed_value returns 422."""
    response = await client_authed.post(
        "/api/suggestions",
        json={
            "target_type": "new_word",
            "proposed_value": {"swahili_gloss": "test"},
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_suggestion_word_missing_target_id(client_authed, mock_db):
    """word correction without target_id returns 422."""
    response = await client_authed.post(
        "/api/suggestions",
        json={
            "target_type": "word",
            "field_path": "headword",
            "proposed_value": {"value": "test"},
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_suggestion_honeypot_rejected(client_authed, mock_db):
    """Suggestion with honeypot 'website' field is rejected."""
    response = await client_authed.post(
        "/api/suggestions",
        json={
            "target_type": "new_word",
            "proposed_value": {
                "headword": "test",
                "website": "http://spam.example.com",
            },
        },
    )

    assert response.status_code == 400


# ═══════════════════════════════════════════════════════════════
# Tests: GET /api/suggestions
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_suggestions_returns_200(client_unauth, mock_db):
    """GET /api/suggestions returns 200 with paginated response."""
    mock_db.execute = AsyncMock(
        return_value=MockResult(rows=[], value=0)
    )
    mock_db.scalar = AsyncMock(return_value=0)

    response = await client_unauth.get("/api/suggestions")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "has_next" in data


@pytest.mark.asyncio
async def test_list_suggestions_with_status_filter(client_unauth, mock_db):
    """GET /api/suggestions?status=accepted returns 200."""
    mock_db.execute = AsyncMock(
        return_value=MockResult(rows=[], value=0)
    )
    mock_db.scalar = AsyncMock(return_value=0)

    response = await client_unauth.get("/api/suggestions?status=accepted")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_suggestions_pagination(client_unauth, mock_db):
    """GET /api/suggestions?page=2&size=10 returns requested params."""
    mock_db.execute = AsyncMock(
        return_value=MockResult(rows=[], value=0)
    )
    mock_db.scalar = AsyncMock(return_value=0)

    response = await client_unauth.get("/api/suggestions?page=2&size=10")

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["size"] == 10


# ═══════════════════════════════════════════════════════════════
# Tests: GET /api/suggestions/{id}
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_suggestion_returns_404_for_unknown_id(client_unauth, mock_db):
    """GET /api/suggestions/{id} returns 404 when not found."""
    mock_db.execute = AsyncMock(return_value=MockResult(value=None))

    random_id = uuid.uuid4()
    response = await client_unauth.get(f"/api/suggestions/{random_id}")

    assert response.status_code == 404

"""Tests for vote endpoints.

Uses FastAPI dependency_overrides to mock the DB session.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.deps import get_current_user
from app.main import app
from app.models import Suggestion, User, Vote


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def make_mock_user(user_id=None) -> MagicMock:
    """Create a mock User object."""
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.email = "voter@example.com"
    user.display_name = "voter"
    user.role = "contributor"
    user.is_blocked = False
    return user


def make_mock_suggestion(
    user_id=None,
    status="open",
    target_type="new_word",
) -> MagicMock:
    """Create a mock Suggestion object."""
    s = MagicMock(spec=Suggestion)
    s.id = uuid.uuid4()
    s.target_type = target_type
    s.target_id = None
    s.field_path = None
    s.proposed_value = {"headword": "test"}
    s.rationale = None
    s.status = status
    s.created_by_user_id = user_id or uuid.uuid4()  # different from voter
    s.created_by_session_id = None
    s.created_at = datetime.now(timezone.utc)
    s.decided_at = None
    s.decided_by_user_id = None
    s.applied_at = None
    return s


class MockResult:
    def __init__(self, value=None, rows=None):
        self._value = value
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._value

    def scalar(self):
        return self._value

    def all(self):
        return self._rows


@pytest.fixture
async def mock_db():
    """Mock AsyncSession."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MockResult())
    session.scalar = AsyncMock(return_value=0)
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
async def mock_user():
    """A mock authenticated user (the voter)."""
    return make_mock_user()


@pytest.fixture
async def client_with_auth(mock_db, mock_user):
    """HTTP client with mocked DB + authenticated user."""

    async def override_get_db():
        yield mock_db

    async def override_auth():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def client_no_auth(mock_db):
    """HTTP client with no auth (anon)."""

    async def override_get_db():
        yield mock_db

    async def override_auth():
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════
# Tests: POST /api/suggestions/{id}/vote
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_vote_requires_auth(client_no_auth, mock_db):
    """Anon users cannot vote — 401."""
    # Mock: suggestion exists
    suggestion = make_mock_suggestion()
    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(value=suggestion),  # suggestion lookup
            MockResult(value=None),  # existing vote lookup
            MockResult(rows=[]),  # vote counts (empty)
            MockResult(value=0),  # non-anon upvote count
        ]
    )

    response = await client_no_auth.post(
        f"/api/suggestions/{suggestion.id}/vote",
        json={"vote": "up"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_vote_up_success(client_with_auth, mock_db, mock_user):
    """Authenticated user can vote up."""
    suggestion = make_mock_suggestion(user_id=uuid.uuid4())  # different author

    # Mock row with .vote and .count attributes (like SQLAlchemy Row)
    vote_count_row = MagicMock()
    vote_count_row.vote = "up"
    vote_count_row.count = 1

    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(value=suggestion),  # suggestion lookup
            MockResult(value=None),  # existing vote lookup (none)
            MockResult(rows=[vote_count_row]),  # vote counts after flush
            MockResult(value=1),  # non-anon upvote count (for promote check)
        ]
    )

    response = await client_with_auth.post(
        f"/api/suggestions/{suggestion.id}/vote",
        json={"vote": "up"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_vote"] == "up"
    assert data["upvotes"] == 1
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_vote_invalid_value_returns_422(client_with_auth, mock_db):
    """Vote with invalid value returns 422."""
    suggestion = make_mock_suggestion()
    mock_db.execute = AsyncMock(return_value=MockResult(value=suggestion))

    response = await client_with_auth.post(
        f"/api/suggestions/{suggestion.id}/vote",
        json={"vote": "sideways"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_vote_on_nonexistent_suggestion_returns_404(client_with_auth, mock_db):
    """Vote on a suggestion that doesn't exist returns 404."""
    mock_db.execute = AsyncMock(return_value=MockResult(value=None))

    random_id = uuid.uuid4()
    response = await client_with_auth.post(
        f"/api/suggestions/{random_id}/vote",
        json={"vote": "up"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_vote_on_own_suggestion_returns_400(client_with_auth, mock_db, mock_user):
    """User cannot vote on their own suggestion."""
    suggestion = make_mock_suggestion(user_id=mock_user.id)  # same user

    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(value=suggestion),  # suggestion lookup
        ]
    )

    response = await client_with_auth.post(
        f"/api/suggestions/{suggestion.id}/vote",
        json={"vote": "up"},
    )

    assert response.status_code == 400
    assert "own suggestion" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_vote_on_closed_suggestion_returns_400(client_with_auth, mock_db):
    """Cannot vote on a suggestion that's not open."""
    suggestion = make_mock_suggestion(status="accepted")

    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(value=suggestion),  # suggestion lookup
        ]
    )

    response = await client_with_auth.post(
        f"/api/suggestions/{suggestion.id}/vote",
        json={"vote": "up"},
    )

    assert response.status_code == 400


# ═══════════════════════════════════════════════════════════════
# Tests: DELETE /api/suggestions/{id}/vote
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_remove_vote_success(client_with_auth, mock_db):
    """User can remove their vote."""
    suggestion = make_mock_suggestion()
    existing_vote = MagicMock(spec=Vote)
    existing_vote.vote = "up"

    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(value=existing_vote),  # existing vote lookup
            MockResult(rows=[]),  # vote counts after delete (empty)
        ]
    )

    response = await client_with_auth.delete(
        f"/api/suggestions/{suggestion.id}/vote",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_vote"] is None
    mock_db.delete.assert_called_once()


@pytest.mark.asyncio
async def test_remove_vote_when_none_exists(client_with_auth, mock_db):
    """Removing a vote when none exists returns 200 with 0 counts."""
    suggestion = make_mock_suggestion()
    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(value=None),  # no existing vote
            MockResult(rows=[]),  # vote counts (empty)
        ]
    )

    response = await client_with_auth.delete(
        f"/api/suggestions/{suggestion.id}/vote",
    )

    assert response.status_code == 200
    assert response.json()["user_vote"] is None

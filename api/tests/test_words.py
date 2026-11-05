"""Tests for word endpoints.

Uses FastAPI dependency_overrides to mock the database session,
so these tests run without a real Postgres connection.

For integration tests against the real DB, run the app locally
and hit the endpoints manually or via a separate integration test suite.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.main import app
from app.models import Gloss, Word


# ═══════════════════════════════════════════════════════════════
# Test fixtures
# ═══════════════════════════════════════════════════════════════


def make_mock_word(
    headword: str = "mlima",
    part_of_speech: str | None = "noun",
    dialect: str | None = "Dawida",
    swahili_gloss: str | None = "mlima, kilima",
    english_gloss: str | None = "mountain, hill",
) -> MagicMock:
    """Create a mock Word object with glosses eager-loaded."""
    word = MagicMock(spec=Word)
    word.id = uuid.uuid4()
    word.headword = headword
    word.normalized_form = headword.lower()
    word.part_of_speech = part_of_speech
    word.noun_class = None
    word.dialect = dialect
    word.literal_translation = None
    word.morphology_notes = None
    word.status = "live"
    word.created_at = datetime.now(timezone.utc)
    word.frequency = 42

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
    word.examples = []

    return word


@pytest.fixture
async def mock_db():
    """Mock AsyncSession that returns canned data."""
    session = AsyncMock()
    # Default: scalar() returns 1 (for count queries)
    session.scalar = AsyncMock(return_value=1)
    return session


@pytest.fixture
async def client_with_mock_db(mock_db):
    """HTTP client with the DB dependency overridden to use mock_db."""

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
# Tests: GET /api/words
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_words_returns_200(client_with_mock_db, mock_db):
    """GET /api/words returns 200 with a paginated response."""
    # Mock the execute() chain to return an empty list
    mock_result = MagicMock()
    mock_result.scalars.return_value.unique.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.scalar = AsyncMock(return_value=0)

    response = await client_with_mock_db.get("/api/words")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "has_next" in data
    assert data["page"] == 1
    assert data["size"] == 20


@pytest.mark.asyncio
async def test_list_words_with_pagination(client_with_mock_db, mock_db):
    """GET /api/words?page=2&size=10 returns the requested page params."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.unique.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.scalar = AsyncMock(return_value=0)

    response = await client_with_mock_db.get("/api/words?page=2&size=10")

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["size"] == 10


@pytest.mark.asyncio
async def test_list_words_invalid_page_returns_422(client_with_mock_db):
    """GET /api/words?page=0 returns 422 (page must be >= 1)."""
    response = await client_with_mock_db.get("/api/words?page=0")
    assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Tests: GET /api/words/{id}
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_word_returns_404_for_unknown_id(client_with_mock_db, mock_db):
    """GET /api/words/{id} returns 404 when the word doesn't exist."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    random_id = uuid.uuid4()
    response = await client_with_mock_db.get(f"/api/words/{random_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════
# Tests: GET /api/search
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_search_returns_200(client_with_mock_db, mock_db):
    """GET /api/search?q=mlima returns 200 with search results."""
    mock_result = MagicMock()
    mock_result.all.return_value = []  # no results
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.scalar = AsyncMock(return_value=0)

    response = await client_with_mock_db.get("/api/search?q=mlima")

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "mlima"
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_search_requires_query(client_with_mock_db):
    """GET /api/search without q returns 422."""
    response = await client_with_mock_db.get("/api/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_empty_query_returns_422(client_with_mock_db):
    """GET /api/search?q= returns 422 (min_length=1)."""
    response = await client_with_mock_db.get("/api/search?q=")
    assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Tests: POST /api/words — contributor creates a live word
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
async def client_authed(client_with_mock_db, mock_db):
    """HTTP client with a mock authenticated user."""
    from app.deps import require_user

    user = MagicMock(spec=Word)
    user.id = uuid.uuid4()
    user.email = "contributor@example.com"
    user.display_name = "contributor"
    user.role = "contributor"
    user.is_blocked = False

    async def override_auth():
        return user

    app.dependency_overrides[require_user] = override_auth
    return client_with_mock_db


@pytest.fixture
async def client_unauth_word(client_with_mock_db, mock_db):
    """HTTP client with no auth — POST /api/words should 401."""
    from app.deps import require_user
    from fastapi import HTTPException, status

    async def override_auth():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    app.dependency_overrides[require_user] = override_auth
    return client_with_mock_db


@pytest.mark.asyncio
async def test_create_word_requires_auth(client_unauth_word, mock_db):
    """POST /api/words without auth returns 401."""
    response = await client_unauth_word.post(
        "/api/words",
        json={"headword": "mlima", "swahili_gloss": "mlima"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_word_missing_headword(client_authed, mock_db):
    """POST /api/words without headword returns 422."""
    response = await client_authed.post(
        "/api/words",
        json={"swahili_gloss": "mlima"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_word_duplicate_returns_409(client_authed, mock_db):
    """POST /api/words with existing normalized_form returns 409."""
    # Mock: existing word found (execute returns a result with scalar_one_or_none → existing word)
    existing = MagicMock(spec=Word)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await client_authed.post(
        "/api/words",
        json={"headword": "mlima", "swahili_gloss": "mlima"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()

"""Tests for admin endpoints.

All endpoints require admin role. Tests mock the DB + auth.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.deps import require_admin
from app.main import app
from app.models import Suggestion, User, Word


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def make_mock_admin() -> MagicMock:
    """Create a mock admin user."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "admin@example.com"
    user.display_name = "admin"
    user.role = "admin"
    user.is_blocked = False
    return user


def make_mock_user(user_id=None, email="user@example.com", role="contributor") -> MagicMock:
    """Create a mock regular user."""
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.email = email
    user.display_name = "user"
    user.role = role
    user.is_blocked = False
    user.created_at = datetime.now(timezone.utc)
    user.last_seen_at = None
    return user


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
    session.execute = AsyncMock(return_value=MockResult())
    session.scalar = AsyncMock(return_value=0)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
async def client_admin(mock_db):
    """HTTP client with admin auth."""

    async def override_get_db():
        yield mock_db

    admin = make_mock_admin()

    async def override_admin():
        return admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_admin] = override_admin

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def client_non_admin(mock_db):
    """HTTP client where require_admin raises 403 (non-admin user)."""
    from fastapi import HTTPException, status

    async def override_get_db():
        yield mock_db

    async def override_admin():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_admin] = override_admin

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════
# Tests: GET /api/admin/stats
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_stats_requires_admin(client_non_admin):
    """Non-admin gets 403."""
    response = await client_non_admin.get("/api/admin/stats")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_stats_returns_200(client_admin, mock_db):
    """Admin can get dashboard stats."""
    mock_db.scalar = AsyncMock(return_value=0)
    mock_db.execute = AsyncMock(return_value=MockResult(rows=[]))

    response = await client_admin.get("/api/admin/stats")

    assert response.status_code == 200
    data = response.json()
    assert "total_words" in data
    assert "total_users" in data
    assert "open_suggestions" in data


# ═══════════════════════════════════════════════════════════════
# Tests: GET /api/admin/users
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_users_requires_admin(client_non_admin):
    """Non-admin gets 403."""
    response = await client_non_admin.get("/api/admin/users")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users_returns_200(client_admin, mock_db):
    """Admin can list users."""
    mock_db.scalar = AsyncMock(return_value=0)
    mock_db.execute = AsyncMock(return_value=MockResult(rows=[]))

    response = await client_admin.get("/api/admin/users")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


# ═══════════════════════════════════════════════════════════════
# Tests: PATCH /api/admin/users/{id}
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_update_user_not_found(client_admin, mock_db):
    """Updating a non-existent user returns 404."""
    mock_db.execute = AsyncMock(return_value=MockResult(value=None))

    random_id = uuid.uuid4()
    response = await client_admin.patch(
        f"/api/admin/users/{random_id}",
        json={"role": "admin"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_user_invalid_role(client_admin, mock_db):
    """Invalid role returns 422."""
    user = make_mock_user()
    mock_db.execute = AsyncMock(return_value=MockResult(value=user))

    response = await client_admin.patch(
        f"/api/admin/users/{user.id}",
        json={"role": "superadmin"},
    )

    assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Tests: POST /api/admin/suggestions/{id}/decide
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_decide_suggestion_not_found(client_admin, mock_db):
    """Deciding on non-existent suggestion returns 404."""
    mock_db.execute = AsyncMock(return_value=MockResult(value=None))

    random_id = uuid.uuid4()
    response = await client_admin.post(
        f"/api/admin/suggestions/{random_id}/decide",
        json={"decision": "accept"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_decide_suggestion_invalid_decision(client_admin, mock_db):
    """Invalid decision returns 422."""
    response = await client_admin.post(
        f"/api/admin/suggestions/{uuid.uuid4()}/decide",
        json={"decision": "maybe"},
    )

    assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Tests: PATCH /api/admin/words/{id} — edit word
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_edit_word_not_found(client_admin, mock_db):
    """Editing non-existent word returns 404."""
    mock_db.execute = AsyncMock(return_value=MockResult(value=None))

    random_id = uuid.uuid4()
    response = await client_admin.patch(
        f"/api/admin/words/{random_id}",
        json={"headword": "newvalue"},
    )

    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════
# Tests: POST /api/admin/words/{id}/hide
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_hide_word_not_found(client_admin, mock_db):
    """Hiding non-existent word returns 404."""
    mock_db.execute = AsyncMock(return_value=MockResult(value=None))

    random_id = uuid.uuid4()
    response = await client_admin.post(f"/api/admin/words/{random_id}/hide")

    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════
# Tests: POST /api/admin/words/merge
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_merge_same_word_returns_400(client_admin, mock_db):
    """Merging a word into itself returns 400."""
    word_id = uuid.uuid4()
    response = await client_admin.post(
        "/api/admin/words/merge",
        json={"source_id": str(word_id), "target_id": str(word_id)},
    )

    assert response.status_code == 400


# ═══════════════════════════════════════════════════════════════
# Tests: GET /api/admin/audit-log
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_audit_log_requires_admin(client_non_admin):
    """Non-admin gets 403."""
    response = await client_non_admin.get("/api/admin/audit-log")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_log_returns_200(client_admin, mock_db):
    """Admin can view audit log."""
    mock_db.scalar = AsyncMock(return_value=0)
    mock_db.execute = AsyncMock(return_value=MockResult(rows=[]))

    response = await client_admin.get("/api/admin/audit-log")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data

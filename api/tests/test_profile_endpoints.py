"""Tests for the profile-management endpoints (endpoints #3, #4, #5 of the
backend API additions contract).

  PATCH  /api/auth/me/email              — change email (password verified)
  DELETE /api/auth/me                     — soft-delete / anonymize
  GET    /api/auth/me/connected-accounts — show linked OAuth + has_password

Tests follow the same mock-based pattern as tests/test_auth.py and
tests/test_phase_b_audit_writes.py: the DB session is an AsyncMock, and
queries return canned values per test. Password hashing/verification is
real bcrypt. JWTs are real (so the auth dependency actually validates them).
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
from app.models import EditLog, User
from app.security import create_access_token, hash_password


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


def make_mock_user(
    email="alice@example.com",
    password="alicepassword123",
    is_blocked=False,
    oauth_provider=None,
    oauth_subject=None,
    display_name="Alice",
    role="user",
) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = email.lower()
    user.password_hash = hash_password(password) if password else None
    user.display_name = display_name
    user.role = role
    user.is_blocked = is_blocked
    user.oauth_provider = oauth_provider
    user.oauth_subject = oauth_subject
    user.created_at = datetime.now(timezone.utc)
    user.last_seen_at = None
    return user


@pytest.fixture
async def mock_db():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MockResult(None))
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
async def client(mock_db):
    """Authenticated HTTP client: get_current_user is overridden to return
    a fixed test user, so we don't need to mint real JWTs in tests.
    """
    current = make_mock_user(email="alice@example.com", password="alicepassword123")

    async def override_get_db():
        yield mock_db

    async def override_current_user():
        return current

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        ac.current_user = current  # type: ignore[attr-defined]
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def anon_client(mock_db):
    """Unauthenticated client — used to verify the connected-accounts endpoint
    rejects requests with no Bearer token.
    """

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    # NOTE: get_current_user NOT overridden → real auth path runs → 401

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════
# PATCH /api/auth/me/email — change email address
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_change_email_success(client, mock_db):
    """Correct password + new email → 200 with updated email + audit row."""
    # Duplicate check returns None (no existing user with the new email)
    mock_db.execute = AsyncMock(return_value=MockResult(None))

    response = await client.patch(
        "/api/auth/me/email",
        json={
            "new_email": "alice.new@example.com",
            "current_password": "alicepassword123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "alice.new@example.com"
    assert data["id"] == str(client.current_user.id)  # type: ignore[attr-defined]

    # ── User row updated in-memory ───────────────────────────
    assert client.current_user.email == "alice.new@example.com"  # type: ignore[attr-defined]

    # ── Audit row ────────────────────────────────────────────
    added = [c.args[0] for c in mock_db.add.call_args_list]
    audit_entries = [o for o in added if isinstance(o, EditLog)]
    assert len(audit_entries) == 1
    assert audit_entries[0].action == "user.email_change"
    assert audit_entries[0].entity_type == "user"
    assert audit_entries[0].entity_id == client.current_user.id  # type: ignore[attr-defined]
    assert audit_entries[0].before == {"email": "alice@example.com"}
    assert audit_entries[0].after == {"email": "alice.new@example.com"}


@pytest.mark.asyncio
async def test_change_email_lowercases_new_email(client, mock_db):
    """Mixed-case new email is lowercased before storage + duplicate check."""
    mock_db.execute = AsyncMock(return_value=MockResult(None))

    response = await client.patch(
        "/api/auth/me/email",
        json={
            "new_email": "Alice.NEW@example.com",
            "current_password": "alicepassword123",
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == "alice.new@example.com"


@pytest.mark.asyncio
async def test_change_email_wrong_password_returns_401(client, mock_db):
    """Wrong current password → 401."""
    mock_db.execute = AsyncMock(return_value=MockResult(None))

    response = await client.patch(
        "/api/auth/me/email",
        json={
            "new_email": "alice.new@example.com",
            "current_password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Current password is incorrect."
    # No audit row written
    added = [c.args[0] for c in mock_db.add.call_args_list]
    assert [o for o in added if isinstance(o, EditLog)] == []


@pytest.mark.asyncio
async def test_change_email_oauth_only_returns_400(client, mock_db):
    """An OAuth-only user (no password_hash) can't change email this way."""
    client.current_user.password_hash = None  # type: ignore[attr-defined]
    client.current_user.oauth_provider = "google"  # type: ignore[attr-defined]

    response = await client.patch(
        "/api/auth/me/email",
        json={
            "new_email": "alice.new@example.com",
            "current_password": "anything",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "This account uses Google sign-in."


@pytest.mark.asyncio
async def test_change_email_already_taken_returns_409(client, mock_db):
    """If another user already has the new email → 409."""
    other = make_mock_user(email="alice.new@example.com", password="otherpass123")
    mock_db.execute = AsyncMock(return_value=MockResult(other))

    response = await client.patch(
        "/api/auth/me/email",
        json={
            "new_email": "alice.new@example.com",
            "current_password": "alicepassword123",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "An account with this email already exists."


@pytest.mark.asyncio
async def test_change_email_same_email_is_idempotent(client, mock_db):
    """Setting the email to its current value is a no-op (200, no audit row)."""
    mock_db.execute = AsyncMock(return_value=MockResult(None))

    response = await client.patch(
        "/api/auth/me/email",
        json={
            "new_email": "alice@example.com",  # same as current
            "current_password": "alicepassword123",
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"
    # No duplicate-check query was issued, no audit row
    mock_db.execute.assert_not_called()
    added = [c.args[0] for c in mock_db.add.call_args_list]
    assert [o for o in added if isinstance(o, EditLog)] == []


@pytest.mark.asyncio
async def test_change_email_invalid_format_returns_422(client):
    """Pydantic EmailStr validation: invalid email → 422."""
    response = await client.patch(
        "/api/auth/me/email",
        json={
            "new_email": "not-an-email",
            "current_password": "alicepassword123",
        },
    )
    assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# DELETE /api/auth/me — soft-delete / anonymize
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_delete_account_success(client, mock_db):
    """Correct password → 204 + user anonymized + audit row."""
    original_email = client.current_user.email  # type: ignore[attr-defined]
    original_id = client.current_user.id  # type: ignore[attr-defined]

    response = await client.request(
        "DELETE",
        "/api/auth/me",
        json={"password": "alicepassword123"},
    )

    assert response.status_code == 204
    assert response.content == b""

    # ── Anonymized in-memory ─────────────────────────────────
    u = client.current_user  # type: ignore[attr-defined]
    assert u.email == f"deleted+{original_id}@anon.lumi"
    assert u.display_name == "deleted user"
    assert u.password_hash is None
    assert u.oauth_provider is None
    assert u.oauth_subject is None
    assert u.is_blocked is True

    # ── Audit row ────────────────────────────────────────────
    added = [c.args[0] for c in mock_db.add.call_args_list]
    audit_entries = [o for o in added if isinstance(o, EditLog)]
    assert len(audit_entries) == 1
    assert audit_entries[0].action == "user.delete"
    assert audit_entries[0].entity_type == "user"
    assert audit_entries[0].entity_id == original_id


@pytest.mark.asyncio
async def test_delete_account_wrong_password_returns_401(client):
    """Wrong password → 401, no anonymization."""
    response = await client.request(
        "DELETE",
        "/api/auth/me",
        json={"password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Password is incorrect."
    # User NOT anonymized
    assert client.current_user.email != ""  # type: ignore[attr-defined]
    assert client.current_user.is_blocked is False  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_delete_account_oauth_only_returns_400(client):
    """An OAuth-only user (no password_hash) can't self-delete this way."""
    client.current_user.password_hash = None  # type: ignore[attr-defined]
    client.current_user.oauth_provider = "google"  # type: ignore[attr-defined]

    response = await client.request(
        "DELETE",
        "/api/auth/me",
        json={"password": "anything"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "This account uses Google sign-in and has no password."
    )


@pytest.mark.asyncio
async def test_delete_account_email_placeholder_is_unique_per_user(client, mock_db):
    """Two users get different anonymized emails (per user_id)."""
    # First delete
    user_a_id = client.current_user.id  # type: ignore[attr-defined]
    await client.request(
        "DELETE",
        "/api/auth/me",
        json={"password": "alicepassword123"},
    )
    email_a = client.current_user.email  # type: ignore[attr-defined]

    # Set up a second user
    user_b = make_mock_user(email="bob@example.com", password="bobpassword123")
    user_b_id = user_b.id

    async def override_current_user():
        return user_b

    app.dependency_overrides[get_current_user] = override_current_user

    await client.request(
        "DELETE",
        "/api/auth/me",
        json={"password": "bobpassword123"},
    )
    email_b = user_b.email

    # Each placeholder contains the user's UUID → unique
    assert email_a != email_b
    assert str(user_a_id) in email_a
    assert str(user_b_id) in email_b


# ═══════════════════════════════════════════════════════════════
# GET /api/auth/me/connected-accounts
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_connected_accounts_password_only_user(client):
    """A user with a password and no OAuth → {google: false, has_password: true}."""
    response = await client.get("/api/auth/me/connected-accounts")
    assert response.status_code == 200
    assert response.json() == {"google": False, "has_password": True}


@pytest.mark.asyncio
async def test_connected_accounts_oauth_user(client):
    """A user with Google linked and a password → both true."""
    client.current_user.oauth_provider = "google"  # type: ignore[attr-defined]

    response = await client.get("/api/auth/me/connected-accounts")
    assert response.status_code == 200
    assert response.json() == {"google": True, "has_password": True}


@pytest.mark.asyncio
async def test_connected_accounts_oauth_only_user(client):
    """An OAuth-only user → {google: true, has_password: false}."""
    client.current_user.oauth_provider = "google"  # type: ignore[attr-defined]
    client.current_user.password_hash = None  # type: ignore[attr-defined]

    response = await client.get("/api/auth/me/connected-accounts")
    assert response.status_code == 200
    assert response.json() == {"google": True, "has_password": False}


@pytest.mark.asyncio
async def test_connected_accounts_requires_auth(anon_client):
    """Without a Bearer token, the endpoint returns 401."""
    response = await anon_client.get("/api/auth/me/connected-accounts")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_connected_accounts_with_real_token_works(mock_db):
    """End-to-end: a real JWT (minted with our secret) is accepted.

    This exercises the actual get_current_user dependency path so we don't
    only test it under the override.
    """
    user = make_mock_user(email="alice@example.com", password="alicepassword123")

    async def override_get_db():
        yield mock_db

    # The real get_current_user will call db.execute(select(User).where(...))
    mock_db.execute = AsyncMock(return_value=MockResult(user))

    app.dependency_overrides[get_db] = override_get_db
    # Do NOT override get_current_user — let it run for real

    token = create_access_token(user.id, user.email, user.role)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            response = await ac.get(
                "/api/auth/me/connected-accounts",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200
        assert response.json() == {"google": False, "has_password": True}
    finally:
        app.dependency_overrides.clear()

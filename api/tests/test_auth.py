"""Tests for auth endpoints.

Uses FastAPI dependency_overrides to mock the DB session, so tests
run without a real Postgres connection.

The tests cover:
  - Register: success, duplicate email, short password
  - Login: success, wrong password, unknown email
  - Me: success, no token, invalid token
  - Refresh: success, invalid token

Password hashing is real (bcrypt) — we want to verify that path works.
JWT creation/verification is real too — same reason.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.main import app
from app.models import User
from app.security import hash_password


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def make_mock_user(
    email="test@example.com",
    password="testpassword123",
    role="contributor",
    is_blocked=False,
) -> MagicMock:
    """Create a mock User object with a real hashed password."""
    user = MagicMock(spec=User)
    user.id = MagicMock()  # will be a UUID-like
    user.id.__str__ = lambda self: "00000000-0000-0000-0000-000000000001"
    user.email = email
    user.password_hash = hash_password(password)
    user.display_name = "Test User"
    user.role = role
    user.is_blocked = is_blocked
    return user


class MockResult:
    """Mock SQLAlchemy Result that returns a single scalar or None."""

    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


@pytest.fixture
async def mock_db():
    """Mock AsyncSession. Tests configure return values per-test."""
    session = AsyncMock()
    # Default: queries return None (no existing user)
    session.execute = AsyncMock(return_value=MockResult(None))
    return session


@pytest.fixture
async def client_with_mock_db(mock_db):
    """HTTP client with the DB dependency overridden."""

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
# Tests: POST /api/auth/register
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_register_success(client_with_mock_db, mock_db):
    """Register with valid email + password returns 201 + tokens."""
    # Mock: no existing user with this email
    mock_db.execute = AsyncMock(return_value=MockResult(None))

    response = await client_with_mock_db.post(
        "/api/auth/register",
        json={
            "email": "new@example.com",
            "password": "securepass123",
            "display_name": "New User",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    # db.add was called (user creation)
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client_with_mock_db, mock_db):
    """Register with an existing email returns 409."""
    # Mock: an existing user is found
    existing = make_mock_user(email="existing@example.com")
    mock_db.execute = AsyncMock(return_value=MockResult(existing))

    response = await client_with_mock_db.post(
        "/api/auth/register",
        json={"email": "existing@example.com", "password": "securepass123"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_short_password_returns_422(client_with_mock_db):
    """Register with password < 8 chars returns 422."""
    response = await client_with_mock_db.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "short"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email_returns_422(client_with_mock_db):
    """Register with invalid email returns 422."""
    response = await client_with_mock_db.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "securepass123"},
    )

    assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Tests: POST /api/auth/login
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_login_success(client_with_mock_db, mock_db):
    """Login with correct email + password returns tokens."""
    user = make_mock_user(email="test@example.com", password="testpassword123")
    mock_db.execute = AsyncMock(return_value=MockResult(user))

    response = await client_with_mock_db.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client_with_mock_db, mock_db):
    """Login with wrong password returns 401."""
    user = make_mock_user(email="test@example.com", password="testpassword123")
    mock_db.execute = AsyncMock(return_value=MockResult(user))

    response = await client_with_mock_db.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client_with_mock_db, mock_db):
    """Login with unknown email returns 401 (same error as wrong password)."""
    mock_db.execute = AsyncMock(return_value=MockResult(None))

    response = await client_with_mock_db.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "anypassword"},
    )

    assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════
# Tests: GET /api/auth/me
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_me_without_token_returns_401(client_with_mock_db):
    """GET /me without Authorization header returns 401."""
    response = await client_with_mock_db.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token_returns_401(client_with_mock_db):
    """GET /me with an invalid token returns 401."""
    response = await client_with_mock_db.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════
# Tests: POST /api/auth/refresh
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(client_with_mock_db):
    """Refresh with an invalid token returns 401."""
    response = await client_with_mock_db.post(
        "/api/auth/refresh",
        json={"refresh_token": "not-a-real-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_returns_204(client_with_mock_db):
    """Logout returns 204 No Content."""
    response = await client_with_mock_db.post("/api/auth/logout")
    assert response.status_code == 204


# ═══════════════════════════════════════════════════════════════
# Tests: POST /api/auth/oauth/google
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
async def mock_google_token(monkeypatch):
    """Patch the Google token verifier to return a canned payload.

    This lets us test the endpoint without a real Google ID token.
    """
    payload = {
        "sub": "google-user-123",
        "email": "googleuser@gmail.com",
        "email_verified": True,
        "name": "Google User",
        "picture": "https://lh3.googleusercontent.com/...",
    }

    async def fake_verify(id_token_str: str) -> dict:
        return payload

    # Patch in the module where it's defined
    from app.routes import auth as auth_module

    monkeypatch.setattr(auth_module, "_verify_google_id_token", fake_verify)
    return payload


@pytest.mark.asyncio
async def test_google_oauth_creates_new_user(client_with_mock_db, mock_db, mock_google_token):
    """Google OAuth with a new user creates an account and returns tokens."""
    # Mock: no existing user found (returns None for both lookups)
    mock_db.execute = AsyncMock(return_value=MockResult(None))

    response = await client_with_mock_db.post(
        "/api/auth/oauth/google",
        json={"id_token": "fake-google-id-token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # db.add was called (user creation)
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_google_oauth_links_existing_email(client_with_mock_db, mock_db, mock_google_token):
    """Google OAuth with an existing email account links the Google ID to it."""
    # Mock: existing user with same email but no oauth_provider
    existing = make_mock_user(email="googleuser@gmail.com", password="somepassword")
    existing.oauth_provider = None
    existing.oauth_subject = None

    # First execute() call (by oauth_provider+sub) returns None — no Google-linked user yet
    # Second execute() call (by email) returns the existing user
    mock_db.execute = AsyncMock(
        side_effect=[MockResult(None), MockResult(existing)]
    )

    response = await client_with_mock_db.post(
        "/api/auth/oauth/google",
        json={"id_token": "fake-google-id-token"},
    )

    assert response.status_code == 200
    # The existing user's oauth_provider should now be 'google'
    assert existing.oauth_provider == "google"
    assert existing.oauth_subject == "google-user-123"


@pytest.mark.asyncio
async def test_google_oauth_unverified_email_returns_400(
    client_with_mock_db, mock_db, monkeypatch
):
    """Google OAuth with an unverified email returns 400."""
    # Mock: payload with email_verified=False
    payload = {
        "sub": "google-user-456",
        "email": "unverified@gmail.com",
        "email_verified": False,
        "name": "Unverified User",
    }

    async def fake_verify(id_token_str: str) -> dict:
        return payload

    from app.routes import auth as auth_module

    monkeypatch.setattr(auth_module, "_verify_google_id_token", fake_verify)

    response = await client_with_mock_db.post(
        "/api/auth/oauth/google",
        json={"id_token": "fake-google-id-token"},
    )

    assert response.status_code == 400
    assert "not verified" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_google_oauth_unconfigured_returns_503(
    client_with_mock_db, mock_db, monkeypatch
):
    """Google OAuth returns 503 if GOOGLE_OAUTH_CLIENT_ID is not set."""
    # Mock: settings has empty client ID — _verify_google_id_token raises 503
    from app.routes import auth as auth_module
    from app.config import get_settings

    # Temporarily set client ID to empty
    original = get_settings().google_oauth_client_id
    get_settings().google_oauth_client_id = ""

    try:
        response = await client_with_mock_db.post(
            "/api/auth/oauth/google",
            json={"id_token": "fake-google-id-token"},
        )
        assert response.status_code == 503
    finally:
        get_settings().google_oauth_client_id = original

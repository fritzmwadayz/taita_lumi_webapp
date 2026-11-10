"""Tests for the password-reset workflow (endpoints #1 and #2 of the
backend API additions contract).

  POST /api/auth/password-reset/request — always returns 200, sends email
  POST /api/auth/password-reset/confirm — sets a new password with a token

Tests follow the same mock-based pattern as tests/test_auth.py and
tests/test_phase_b_audit_writes.py: the DB session is an AsyncMock, and
queries return canned values per test. JWT creation/verification is real
(we exercise the actual create_password_reset_token + decode_token path).
Password hashing is real bcrypt.

Rate limiting is reset between tests via reset_password_reset_rate_limit().
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.anon import reset_password_reset_rate_limit
from app.db import get_db
from app.email import send_email as real_send_email
from app.main import app
from app.models import EditLog, User
from app.security import create_password_reset_token, hash_password
from app.config import get_settings

settings = get_settings()


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
    password="oldpassword123",
    is_blocked=False,
    oauth_provider=None,
    oauth_subject=None,
) -> MagicMock:
    """Create a mock User with a real (bcrypt) password hash."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = email.lower()
    user.password_hash = hash_password(password)
    user.display_name = "Alice"
    user.role = "user"
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


@pytest.fixture(autouse=True)
def _isolate_rate_limit():
    """Clear the in-memory rate-limit window before every test."""
    reset_password_reset_rate_limit("alice@example.com")
    reset_password_reset_rate_limit("nobody@example.com")
    reset_password_reset_rate_limit("blocked@example.com")
    reset_password_reset_rate_limit("google@example.com")
    yield
    reset_password_reset_rate_limit("alice@example.com")
    reset_password_reset_rate_limit("nobody@example.com")
    reset_password_reset_rate_limit("blocked@example.com")
    reset_password_reset_rate_limit("google@example.com")


@pytest.fixture
async def client(mock_db, monkeypatch):
    """HTTP client with the DB dependency overridden + send_email mocked.

    send_email is mocked so tests can assert on its calls without anything
    actually being sent or printed.
    """
    send_calls: list[dict] = []

    async def fake_send_email(to, subject, body, html=None):
        send_calls.append({"to": to, "subject": subject, "body": body, "html": html})

    monkeypatch.setattr("app.routes.auth.send_email", fake_send_email)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        ac.send_calls = send_calls  # type: ignore[attr-defined]
        yield ac

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════
# POST /api/auth/password-reset/request
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_request_known_user_sends_email_and_writes_audit(client, mock_db):
    """A known, unblocked, password-having user receives an email and an audit row."""
    user = make_mock_user(email="alice@example.com", password="oldpassword123")
    mock_db.execute = AsyncMock(return_value=MockResult(user))

    response = await client.post(
        "/api/auth/password-reset/request",
        json={"email": "alice@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "message": "If an account exists for that email, a reset link has been sent.",
    }
    # ── Email was "sent" ────────────────────────────────────
    assert len(client.send_calls) == 1  # type: ignore[attr-defined]
    sent = client.send_calls[0]  # type: ignore[attr-defined]
    assert sent["to"] == "alice@example.com"
    assert "reset" in sent["subject"].lower()
    assert "/reset-password?token=" in sent["body"]
    # ── Audit row ───────────────────────────────────────────
    added = [c.args[0] for c in mock_db.add.call_args_list]
    audit_entries = [o for o in added if isinstance(o, EditLog)]
    assert len(audit_entries) == 1
    assert audit_entries[0].action == "user.password_reset_request"
    assert audit_entries[0].entity_type == "user"
    assert audit_entries[0].entity_id == user.id


@pytest.mark.asyncio
async def test_request_unknown_email_still_returns_200_no_audit(client, mock_db):
    """Unknown email → 200, no email sent, no audit row."""
    mock_db.execute = AsyncMock(return_value=MockResult(None))

    response = await client.post(
        "/api/auth/password-reset/request",
        json={"email": "nobody@example.com"},
    )

    assert response.status_code == 200
    assert "reset link has been sent" in response.json()["message"]
    # No email
    assert client.send_calls == []  # type: ignore[attr-defined]
    # No audit row
    added = [c.args[0] for c in mock_db.add.call_args_list]
    assert [o for o in added if isinstance(o, EditLog)] == []


@pytest.mark.asyncio
async def test_request_blocked_user_returns_200_no_email(client, mock_db):
    """A blocked user gets the same 200 — no email, no audit row."""
    user = make_mock_user(email="blocked@example.com", is_blocked=True)
    mock_db.execute = AsyncMock(return_value=MockResult(user))

    response = await client.post(
        "/api/auth/password-reset/request",
        json={"email": "blocked@example.com"},
    )

    assert response.status_code == 200
    assert client.send_calls == []  # type: ignore[attr-defined]
    added = [c.args[0] for c in mock_db.add.call_args_list]
    assert [o for o in added if isinstance(o, EditLog)] == []


@pytest.mark.asyncio
async def test_request_oauth_only_user_returns_200_no_email(client, mock_db):
    """An OAuth-only user (no password_hash) gets no reset email."""
    user = make_mock_user(email="google@example.com", password="ignored")
    user.password_hash = None
    user.oauth_provider = "google"
    user.oauth_subject = "google-sub-123"
    mock_db.execute = AsyncMock(return_value=MockResult(user))

    response = await client.post(
        "/api/auth/password-reset/request",
        json={"email": "google@example.com"},
    )

    assert response.status_code == 200
    assert client.send_calls == []  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_request_invalid_email_returns_422(client):
    """Pydantic validation: invalid email returns 422."""
    response = await client.post(
        "/api/auth/password-reset/request",
        json={"email": "not-an-email"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_request_rate_limit_returns_429(client, mock_db):
    """After 3 requests for the same email, the 4th returns 429."""
    mock_db.execute = AsyncMock(return_value=MockResult(None))

    for _ in range(3):
        r = await client.post(
            "/api/auth/password-reset/request",
            json={"email": "alice@example.com"},
        )
        assert r.status_code == 200

    r4 = await client.post(
        "/api/auth/password-reset/request",
        json={"email": "alice@example.com"},
    )
    assert r4.status_code == 429
    assert r4.headers.get("Retry-After") == "3600"


@pytest.mark.asyncio
async def test_request_rate_limit_isolated_per_email(client, mock_db):
    """Rate limit is per-email — different emails don't share the window."""
    mock_db.execute = AsyncMock(return_value=MockResult(None))

    for _ in range(3):
        await client.post(
            "/api/auth/password-reset/request",
            json={"email": "alice@example.com"},
        )
    # A different email is unaffected
    r = await client.post(
        "/api/auth/password-reset/request",
        json={"email": "bob@example.com"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_request_email_is_lowercased_before_lookup(client, mock_db):
    """Mixed-case email is lowercased before the DB lookup."""
    user = make_mock_user(email="alice@example.com", password="oldpassword123")
    mock_db.execute = AsyncMock(return_value=MockResult(user))

    response = await client.post(
        "/api/auth/password-reset/request",
        json={"email": "ALICE@example.com"},
    )

    assert response.status_code == 200
    assert len(client.send_calls) == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_request_reset_link_uses_frontend_url(client, mock_db, monkeypatch):
    """The reset link is built from settings.frontend_url."""
    user = make_mock_user(email="alice@example.com", password="oldpassword123")
    mock_db.execute = AsyncMock(return_value=MockResult(user))

    # Set a distinct frontend URL so we can verify it appears in the email body
    monkeypatch.setattr(settings, "frontend_url", "https://lumi.example.com")

    response = await client.post(
        "/api/auth/password-reset/request",
        json={"email": "alice@example.com"},
    )

    assert response.status_code == 200
    sent = client.send_calls[0]  # type: ignore[attr-defined]
    assert "https://lumi.example.com/reset-password?token=" in sent["body"]


# ═══════════════════════════════════════════════════════════════
# POST /api/auth/password-reset/confirm
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_confirm_with_valid_token_resets_password(client, mock_db):
    """A valid token + new password resets the password and writes an audit row."""
    user = make_mock_user(email="alice@example.com", password="oldpassword123")
    token = create_password_reset_token(user.id, user.email)

    mock_db.execute = AsyncMock(return_value=MockResult(user))

    response = await client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": "newpassword456"},
    )

    assert response.status_code == 200
    assert "reset" in response.json()["message"].lower()
    # password_hash was set
    assert user.password_hash is not None
    assert user.password_hash != hash_password("oldpassword123")
    # Audit row
    added = [c.args[0] for c in mock_db.add.call_args_list]
    audit_entries = [o for o in added if isinstance(o, EditLog)]
    assert len(audit_entries) == 1
    assert audit_entries[0].action == "user.password_reset"
    assert audit_entries[0].entity_type == "user"
    assert audit_entries[0].entity_id == user.id


@pytest.mark.asyncio
async def test_confirm_with_invalid_token_returns_400(client):
    """A garbage token returns 400 with the standard message."""
    response = await client.post(
        "/api/auth/password-reset/confirm",
        json={"token": "not-a-real-jwt", "new_password": "newpassword456"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired reset token."


@pytest.mark.asyncio
async def test_confirm_with_access_token_returns_400(client, mock_db):
    """An access-type JWT (wrong type) is rejected."""
    from app.security import create_access_token

    user = make_mock_user(email="alice@example.com")
    token = create_access_token(user.id, user.email, user.role)
    mock_db.execute = AsyncMock(return_value=MockResult(user))

    response = await client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": "newpassword456"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired reset token."


@pytest.mark.asyncio
async def test_confirm_with_expired_token_returns_400(client, mock_db):
    """An expired reset token returns 400."""
    from datetime import timedelta

    user = make_mock_user(email="alice@example.com")
    # Already-expired token (negative expiry)
    token = create_password_reset_token(
        user.id, user.email, expires_delta=timedelta(seconds=-10)
    )
    mock_db.execute = AsyncMock(return_value=MockResult(user))

    response = await client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": "newpassword456"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired reset token."


@pytest.mark.asyncio
async def test_confirm_with_unknown_user_returns_400(client, mock_db):
    """A token whose sub points to a deleted user returns 400 (not 404)."""
    user = make_mock_user(email="alice@example.com")
    token = create_password_reset_token(user.id, user.email)

    mock_db.execute = AsyncMock(return_value=MockResult(None))

    response = await client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": "newpassword456"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired reset token."


@pytest.mark.asyncio
async def test_confirm_with_blocked_user_returns_403(client, mock_db):
    """A blocked user can't reset their password."""
    user = make_mock_user(email="alice@example.com", is_blocked=True)
    token = create_password_reset_token(user.id, user.email)

    mock_db.execute = AsyncMock(return_value=MockResult(user))

    response = await client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": "newpassword456"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "This account has been blocked."


@pytest.mark.asyncio
async def test_confirm_with_email_mismatch_returns_400(client, mock_db):
    """If the user has changed their email since requesting the reset, the token is invalid."""
    user = make_mock_user(email="newalice@example.com")
    # Token was issued for the OLD email
    token = create_password_reset_token(user.id, "oldalice@example.com")

    mock_db.execute = AsyncMock(return_value=MockResult(user))

    response = await client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": "newpassword456"},
    )
    assert response.status_code == 400
    # Same message as invalid token — don't reveal the specific reason
    assert response.json()["detail"] == "Invalid or expired reset token."


@pytest.mark.asyncio
async def test_confirm_short_password_returns_422(client, mock_db):
    """A new password shorter than 8 chars fails Pydantic validation (422)."""
    user = make_mock_user(email="alice@example.com")
    token = create_password_reset_token(user.id, user.email)
    mock_db.execute = AsyncMock(return_value=MockResult(user))

    response = await client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_confirm_missing_token_returns_422(client):
    """Missing token field fails Pydantic validation."""
    response = await client.post(
        "/api/auth/password-reset/confirm",
        json={"new_password": "newpassword456"},
    )
    assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Cross-check: request → confirm end-to-end (mocked DB)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_request_then_confirm_full_flow(client, mock_db):
    """Full flow: request generates a token in the email; confirm uses it."""
    user = make_mock_user(email="alice@example.com", password="oldpassword123")
    mock_db.execute = AsyncMock(return_value=MockResult(user))

    # 1. Request — captures the token from the email body
    r1 = await client.post(
        "/api/auth/password-reset/request",
        json={"email": "alice@example.com"},
    )
    assert r1.status_code == 200
    body = client.send_calls[0]["body"]  # type: ignore[attr-defined]
    # Extract the token from the link
    token_marker = "/reset-password?token="
    idx = body.find(token_marker)
    assert idx != -1, "reset link missing from email body"
    token = body[idx + len(token_marker):].split("\n")[0].strip()

    # 2. Confirm — using that token, set a new password
    r2 = await client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": "brandnewpass789"},
    )
    assert r2.status_code == 200
    assert "reset" in r2.json()["message"].lower()
    # password_hash was updated
    assert user.password_hash is not None
    # Audit entries: 1 from request, 1 from confirm
    added = [c.args[0] for c in mock_db.add.call_args_list]
    audit = [o for o in added if isinstance(o, EditLog)]
    actions = sorted(a.action for a in audit)
    assert actions == ["user.password_reset", "user.password_reset_request"]

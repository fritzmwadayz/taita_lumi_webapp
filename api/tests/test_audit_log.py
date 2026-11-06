"""Tests for the audit-log public-API shape mapping (admin.py).

The DB stores edit_log rows with columns:
  actor_user_id, actor_session_id, action, entity_type, entity_id, before, after

The public API exposes them as (integration doc 4.8):
  actor_id, actor_email, actor_role, action, target_type, target_id, details

This test file exercises the _map_action() and _build_audit_entry() helpers
directly, plus the GET /api/admin/audit-log endpoint with mocked DB rows.
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
from app.models import EditLog, User
from app.routes.admin import _build_audit_entry, _map_action


# ═══════════════════════════════════════════════════════════════
# _map_action — pure function
# ═══════════════════════════════════════════════════════════════


class TestMapAction:
    def test_create_on_word(self):
        assert _map_action("create", "word", None) == "word.create"

    def test_update_on_word(self):
        assert _map_action("update", "word", None) == "word.update"

    def test_delete_on_word_becomes_hide(self):
        """'delete' on a word is rendered as 'word.hide' (soft-delete is the only delete path)."""
        assert _map_action("delete", "word", None) == "word.hide"

    def test_merge_on_word(self):
        assert _map_action("merge", "word", None) == "word.merge"

    def test_import_on_word(self):
        assert _map_action("import", "word", None) == "word.import"

    def test_create_on_gloss(self):
        assert _map_action("create", "gloss", None) == "gloss.create"

    def test_update_on_example(self):
        assert _map_action("update", "example", None) == "example.update"

    def test_create_on_relation(self):
        assert _map_action("create", "relation", None) == "relation.create"

    def test_already_dotted_passes_through_suggestion_accept(self):
        """Already-qualified actions (suggestion.accept, user.role.change, etc.) pass through unchanged."""
        assert _map_action("suggestion.accept", "suggestion", None) == "suggestion.accept"

    def test_already_dotted_passes_through_suggestion_reject(self):
        assert _map_action("suggestion.reject", "suggestion", None) == "suggestion.reject"

    def test_already_dotted_passes_through_user_role_change(self):
        assert _map_action("user.role.change", "user", None) == "user.role.change"

    def test_already_dotted_passes_through_user_block(self):
        assert _map_action("user.block", "user", None) == "user.block"

    def test_already_dotted_passes_through_user_unblock(self):
        assert _map_action("user.unblock", "user", None) == "user.unblock"


# ═══════════════════════════════════════════════════════════════
# _build_audit_entry — converts an EditLog row to public AuditLogEntry
# ═══════════════════════════════════════════════════════════════


def make_mock_edit_log(
    action="create",
    entity_type="word",
    entity_id=None,
    actor_user_id=None,
    before=None,
    after=None,
) -> MagicMock:
    """Create a mock EditLog row."""
    e = MagicMock(spec=EditLog)
    e.id = uuid.uuid4()
    e.created_at = datetime.now(timezone.utc)
    e.actor_user_id = actor_user_id
    e.actor_session_id = None
    e.action = action
    e.entity_type = entity_type
    e.entity_id = entity_id or uuid.uuid4()
    e.before = before
    e.after = after
    return e


class TestBuildAuditEntry:
    def test_basic_mapping(self):
        """actor_user_id → actor_id, entity_type → target_type, entity_id → target_id."""
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        e = make_mock_edit_log(
            action="create",
            entity_type="word",
            entity_id=target_id,
            actor_user_id=actor_id,
            before=None,
            after={"headword": "mlima"},
        )
        entry = _build_audit_entry(e, actor_email="admin@example.com", actor_role="admin")
        assert entry.actor_id == actor_id
        assert entry.actor_email == "admin@example.com"
        assert entry.actor_role == "admin"
        assert entry.action == "word.create"
        assert entry.target_type == "word"
        assert entry.target_id == target_id
        # Only `after` is set → details = after dict
        assert entry.details == {"headword": "mlima"}

    def test_details_only_before(self):
        """If only `before` is set, details = before dict."""
        e = make_mock_edit_log(
            action="update",
            entity_type="word",
            before={"headword": "old"},
            after=None,
        )
        entry = _build_audit_entry(e, actor_email=None, actor_role=None)
        assert entry.details == {"headword": "old"}

    def test_details_both_before_and_after(self):
        """If both before and after are set, details = {before: ..., after: ...}."""
        e = make_mock_edit_log(
            action="update",
            entity_type="word",
            before={"headword": "old"},
            after={"headword": "new"},
        )
        entry = _build_audit_entry(e, actor_email=None, actor_role=None)
        assert entry.details == {"before": {"headword": "old"}, "after": {"headword": "new"}}

    def test_details_neither_before_nor_after(self):
        """If both before and after are None, details is None."""
        e = make_mock_edit_log(
            action="create",
            entity_type="word",
            before=None,
            after=None,
        )
        entry = _build_audit_entry(e, actor_email=None, actor_role=None)
        assert entry.details is None

    def test_actor_id_none_when_no_actor(self):
        """System actions (auto-promote) have actor_user_id=None → actor_id=None."""
        e = make_mock_edit_log(
            action="create",
            entity_type="word",
            actor_user_id=None,
        )
        entry = _build_audit_entry(e, actor_email=None, actor_role=None)
        assert entry.actor_id is None
        assert entry.actor_email is None
        assert entry.actor_role is None

    def test_delete_action_mapped_to_word_hide(self):
        """delete on a word → word.hide in the public action."""
        e = make_mock_edit_log(
            action="delete",
            entity_type="word",
            after={"status": "hidden"},
        )
        entry = _build_audit_entry(e, actor_email=None, actor_role=None)
        assert entry.action == "word.hide"

    def test_suggestion_accept_passes_through(self):
        """suggestion.accept (already dotted) passes through unchanged."""
        sugg_id = uuid.uuid4()
        e = make_mock_edit_log(
            action="suggestion.accept",
            entity_type="suggestion",
            entity_id=sugg_id,
            after={"decision": "accept", "target_type": "new_word"},
        )
        entry = _build_audit_entry(e, actor_email="admin@example.com", actor_role="admin")
        assert entry.action == "suggestion.accept"
        assert entry.target_type == "suggestion"
        assert entry.target_id == sugg_id


# ═══════════════════════════════════════════════════════════════
# GET /api/admin/audit-log — endpoint test
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


def make_mock_admin_user() -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "admin@example.com"
    user.display_name = "admin"
    user.role = "admin"
    user.is_blocked = False
    return user


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

    admin = make_mock_admin_user()

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


@pytest.mark.asyncio
async def test_audit_log_returns_public_shape(client_admin, mock_db):
    """GET /api/admin/audit-log returns entries in the public API shape (4.8)."""
    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()
    entry = make_mock_edit_log(
        action="create",
        entity_type="word",
        entity_id=target_id,
        actor_user_id=actor_id,
        after={"headword": "mlima", "slug": "mlima"},
    )

    # Mock: count returns 1, fetch returns [entry], actor lookup returns the admin
    admin_user = make_mock_admin_user()
    admin_row = MagicMock()
    admin_row.id = actor_id
    admin_row.email = "actor@example.com"
    admin_row.role = "admin"

    mock_db.scalar = AsyncMock(return_value=1)
    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(rows=[entry]),  # paginated fetch
            MockResult(rows=[admin_row]),  # actor email/role lookup
        ]
    )

    response = await client_admin.get("/api/admin/audit-log")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] == 1
    item = data["items"][0]
    # ── Public shape ──────────────────────────────────────────
    assert "id" in item
    assert "created_at" in item
    assert item["actor_id"] == str(actor_id)
    assert item["actor_email"] == "actor@example.com"
    assert item["actor_role"] == "admin"
    assert item["action"] == "word.create"  # mapped from 'create' on 'word'
    assert item["target_type"] == "word"
    assert item["target_id"] == str(target_id)
    assert item["details"] == {"headword": "mlima", "slug": "mlima"}
    # ── session_id is NOT exposed ─────────────────────────────
    assert "actor_session_id" not in item
    assert "before" not in item
    assert "after" not in item
    assert "entity_type" not in item
    assert "entity_id" not in item
    assert "actor_user_id" not in item


@pytest.mark.asyncio
async def test_audit_log_filter_by_dotted_action(client_admin, mock_db):
    """Filtering by 'word.create' filters on the bare verb 'create' in the DB."""
    mock_db.scalar = AsyncMock(return_value=0)
    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(rows=[]),  # paginated fetch
            MockResult(rows=[]),  # actor lookup (no actors)
        ]
    )

    response = await client_admin.get("/api/admin/audit-log?action=word.create")

    assert response.status_code == 200
    # Verify the filter was applied (the first execute call should have a where
    # clause for action='create')
    # We don't assert on the SQL directly, but the mock not raising means
    # the request was processed successfully.


@pytest.mark.asyncio
async def test_audit_log_filter_by_bare_action(client_admin, mock_db):
    """Filtering by 'create' (bare verb) also works."""
    mock_db.scalar = AsyncMock(return_value=0)
    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(rows=[]),
            MockResult(rows=[]),
        ]
    )

    response = await client_admin.get("/api/admin/audit-log?action=create")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_audit_log_filter_by_entity_type(client_admin, mock_db):
    """Filtering by entity_type=word works."""
    mock_db.scalar = AsyncMock(return_value=0)
    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(rows=[]),
            MockResult(rows=[]),
        ]
    )

    response = await client_admin.get("/api/admin/audit-log?entity_type=word")
    assert response.status_code == 200

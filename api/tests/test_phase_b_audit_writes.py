"""Tests for Phase B audit-log writes:

  - PATCH /api/admin/users/{id} writes an audit entry on role change
  - PATCH /api/admin/users/{id} writes 'user.block' / 'user.unblock' on block toggle
  - POST /api/admin/suggestions/{id}/decide writes 'suggestion.accept' / 'suggestion.reject'
  - POST /api/admin/words/{id}/hide writes 'delete' (→ 'word.hide' via _map_action)
  - POST /api/admin/words/merge writes 'merge' (→ 'word.merge' via _map_action)
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
from app.models import EditLog, Suggestion, User, Word


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


def make_mock_admin() -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "admin@example.com"
    user.display_name = "admin"
    user.role = "admin"
    user.is_blocked = False
    return user


def make_mock_user(
    email="target@example.com",
    role="user",
    is_blocked=False,
) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = email
    user.display_name = "target"
    user.role = role
    user.is_blocked = is_blocked
    user.created_at = datetime.now(timezone.utc)
    user.last_seen_at = None
    return user


@pytest.fixture
async def mock_db():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MockResult())
    session.scalar = AsyncMock(return_value=0)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
async def client_admin(mock_db):
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
        # Attach the admin to the client so tests can reference it
        ac.admin = admin  # type: ignore[attr-defined]
        yield ac

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════
# PATCH /api/admin/users/{id} — role change audit
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_update_user_role_writes_audit_entry(client_admin, mock_db):
    """Changing a user's role writes an audit-log entry with action='user.role.change'."""
    target = make_mock_user(role="user")
    mock_db.execute = AsyncMock(return_value=MockResult(value=target))

    response = await client_admin.patch(
        f"/api/admin/users/{target.id}",
        json={"role": "reviewer"},
    )

    assert response.status_code == 200
    # Verify an EditLog was added with action='user.role.change'
    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
    audit_entries = [o for o in added_objects if isinstance(o, EditLog)]
    assert len(audit_entries) == 1
    assert audit_entries[0].action == "user.role.change"
    assert audit_entries[0].entity_type == "user"
    assert audit_entries[0].entity_id == target.id
    assert audit_entries[0].before == {"role": "user"}
    assert audit_entries[0].after == {"role": "reviewer", "by_admin": "admin@example.com"}


@pytest.mark.asyncio
async def test_update_user_block_writes_user_block_audit(client_admin, mock_db):
    """Blocking a user writes an audit-log entry with action='user.block'."""
    target = make_mock_user(is_blocked=False)
    mock_db.execute = AsyncMock(return_value=MockResult(value=target))

    response = await client_admin.patch(
        f"/api/admin/users/{target.id}",
        json={"is_blocked": True},
    )

    assert response.status_code == 200
    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
    audit_entries = [o for o in added_objects if isinstance(o, EditLog)]
    assert len(audit_entries) == 1
    assert audit_entries[0].action == "user.block"
    assert audit_entries[0].after == {"is_blocked": True, "by_admin": "admin@example.com"}


@pytest.mark.asyncio
async def test_update_user_unblock_writes_user_unblock_audit(client_admin, mock_db):
    """Unblocking a user writes an audit-log entry with action='user.unblock'."""
    target = make_mock_user(is_blocked=True)
    mock_db.execute = AsyncMock(return_value=MockResult(value=target))

    response = await client_admin.patch(
        f"/api/admin/users/{target.id}",
        json={"is_blocked": False},
    )

    assert response.status_code == 200
    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
    audit_entries = [o for o in added_objects if isinstance(o, EditLog)]
    assert len(audit_entries) == 1
    assert audit_entries[0].action == "user.unblock"


@pytest.mark.asyncio
async def test_update_user_no_change_no_audit(client_admin, mock_db):
    """If role and is_blocked are unchanged, no audit entry is written."""
    target = make_mock_user(role="user", is_blocked=False)
    mock_db.execute = AsyncMock(return_value=MockResult(value=target))

    # Set role to the same value it already has
    response = await client_admin.patch(
        f"/api/admin/users/{target.id}",
        json={"role": "user"},
    )

    assert response.status_code == 200
    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
    audit_entries = [o for o in added_objects if isinstance(o, EditLog)]
    assert len(audit_entries) == 0


@pytest.mark.asyncio
async def test_update_user_cannot_modify_self(client_admin, mock_db):
    """An admin cannot modify their own account."""
    # Use the admin that the client_admin fixture created
    admin = client_admin.admin  # type: ignore[attr-defined]
    mock_db.execute = AsyncMock(return_value=MockResult(value=admin))

    response = await client_admin.patch(
        f"/api/admin/users/{admin.id}",
        json={"role": "user"},
    )

    assert response.status_code == 400
    assert "your own account" in response.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════
# POST /api/admin/suggestions/{id}/decide — audit write
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_decide_accept_writes_audit(client_admin, mock_db):
    """Admin accepting a suggestion writes an audit entry with action='suggestion.accept'."""
    suggestion = MagicMock(spec=Suggestion)
    suggestion.id = uuid.uuid4()
    suggestion.target_type = "word"
    suggestion.target_id = uuid.uuid4()
    suggestion.field_path = "headword"
    suggestion.proposed_value = {"value": "mlima"}
    suggestion.status = "open"
    suggestion.created_by_user_id = None
    suggestion.created_by_session_id = uuid.uuid4()

    # First execute: suggestion lookup → found
    # _apply_word_correction will call execute to fetch the word (returns None → returns early)
    # so we provide multiple side effects
    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(value=suggestion),  # suggestion lookup
            MockResult(value=None),        # word lookup in _apply_word_correction
        ]
    )

    response = await client_admin.post(
        f"/api/admin/suggestions/{suggestion.id}/decide",
        json={"decision": "accept"},
    )

    assert response.status_code == 200
    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
    audit_entries = [o for o in added_objects if isinstance(o, EditLog)]
    # At least one audit entry should be the suggestion.accept entry
    accept_entries = [e for e in audit_entries if e.action == "suggestion.accept"]
    assert len(accept_entries) == 1
    assert accept_entries[0].entity_type == "suggestion"
    assert accept_entries[0].entity_id == suggestion.id


@pytest.mark.asyncio
async def test_admin_decide_reject_writes_audit(client_admin, mock_db):
    """Admin rejecting a suggestion writes an audit entry with action='suggestion.reject'."""
    suggestion = MagicMock(spec=Suggestion)
    suggestion.id = uuid.uuid4()
    suggestion.target_type = "new_word"
    suggestion.target_id = None
    suggestion.field_path = None
    suggestion.proposed_value = {"headword": "mlima"}
    suggestion.status = "open"
    suggestion.created_by_user_id = None
    suggestion.created_by_session_id = uuid.uuid4()

    mock_db.execute = AsyncMock(return_value=MockResult(value=suggestion))

    response = await client_admin.post(
        f"/api/admin/suggestions/{suggestion.id}/decide",
        json={"decision": "reject"},
    )

    assert response.status_code == 200
    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
    audit_entries = [o for o in added_objects if isinstance(o, EditLog)]
    reject_entries = [e for e in audit_entries if e.action == "suggestion.reject"]
    assert len(reject_entries) == 1


# ═══════════════════════════════════════════════════════════════
# POST /api/admin/words/{id}/hide — audit write
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_hide_word_writes_audit(client_admin, mock_db):
    """Hiding a word writes an audit entry with action='delete' (→ 'word.hide' via _map_action)."""
    word = MagicMock(spec=Word)
    word.id = uuid.uuid4()
    word.status = "live"
    word.headword = "mlima"
    word.slug = "mlima"

    mock_db.execute = AsyncMock(return_value=MockResult(value=word))

    response = await client_admin.post(f"/api/admin/words/{word.id}/hide")

    assert response.status_code == 200
    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
    audit_entries = [o for o in added_objects if isinstance(o, EditLog)]
    assert len(audit_entries) == 1
    # The DB stores the bare verb 'delete' — the dotted form 'word.hide'
    # is computed at read time by _map_action().
    assert audit_entries[0].action == "delete"
    assert audit_entries[0].entity_type == "word"
    assert audit_entries[0].before == {"status": "live"}
    assert audit_entries[0].after["status"] == "hidden"


# ═══════════════════════════════════════════════════════════════
# POST /api/admin/words/merge — audit write
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_merge_words_writes_audit(client_admin, mock_db):
    """Merging two words writes an audit entry with action='merge' (→ 'word.merge' via _map_action)."""
    source = MagicMock(spec=Word)
    source.id = uuid.uuid4()
    source.headword = "mlima"
    source.slug = "mlima"
    source.translations = []
    source.examples = []

    target = MagicMock(spec=Word)
    target.id = uuid.uuid4()
    target.headword = "mlima"
    target.slug = "mlima"
    target.translations = []
    target.examples = []

    # Call order in merge_words:
    #   1. source fetch (scalar_one_or_none → source)
    #   2. target fetch (scalar_one_or_none → target)
    #   3. variations outgoing for source (scalars → [])
    #   4. variations incoming for source (scalars → [])
    #   5. relationships outgoing for source (scalars → [])
    #   6. relationships incoming for source (scalars → [])
    mock_db.execute = make_flexible_execute(
        MockResult(value=source),  # source fetch
        MockResult(value=target),  # target fetch
    )

    response = await client_admin.post(
        "/api/admin/words/merge",
        json={"source_id": str(source.id), "target_id": str(target.id)},
    )

    assert response.status_code == 200
    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
    audit_entries = [o for o in added_objects if isinstance(o, EditLog)]
    assert len(audit_entries) == 1
    assert audit_entries[0].action == "merge"
    assert audit_entries[0].entity_type == "word"
    assert audit_entries[0].entity_id == target.id


# ═══════════════════════════════════════════════════════════════
# GET /api/admin/stats — recent_words uses full WordListItem shape
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_stats_recent_words_full_shape(client_admin, mock_db):
    """GET /api/admin/stats returns recent_words as full WordListItem objects (with slug)."""
    word = MagicMock(spec=Word)
    word.id = uuid.uuid4()
    word.headword = "mlima"
    word.slug = "mlima"
    word.part_of_speech = "noun"
    word.noun_class = None
    word.dialect = "Dawida"
    word.status = "live"
    word.translations = []

    # Call order in get_stats:
    #   1. recent words fetch (scalars → [word])
    #   2. variations + relationships batch check (4 subqueries unioned → [])
    #   3. recent suggestions fetch (scalars → [])
    mock_db.scalar = AsyncMock(return_value=0)
    mock_db.execute = make_flexible_execute(
        MockResult(rows=[word]),  # recent words fetch
    )

    response = await client_admin.get("/api/admin/stats")

    assert response.status_code == 200
    data = response.json()
    assert "recent_words" in data
    assert len(data["recent_words"]) == 1
    rw = data["recent_words"][0]
    # Full WordListItem shape
    assert "id" in rw
    assert "slug" in rw
    assert rw["slug"] == "mlima"
    assert "headword" in rw
    assert "part_of_speech" in rw
    assert "noun_class" in rw
    assert "dialect" in rw
    assert "swahili_translation" in rw
    assert "english_translation" in rw
    assert "has_relations" in rw
    # total_suggestions is intentionally kept (per user's confirmation)
    assert "total_suggestions" in data

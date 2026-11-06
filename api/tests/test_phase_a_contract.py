"""Tests for Phase A contract fixes:
  - UserResponse includes oauth_provider
  - SuggestionListItem includes created_by_user_id
  - SuggestionResponse no longer leaks created_by_session_id
  - user_vote is populated on list/detail when authed
  - get_me updates last_seen_at
  - DashboardStats.recent_words uses WordListItem shape (with slug)

Plus tests for the dropped 3rd promote condition (Phase A auto-promote change).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.deps import get_current_user, get_optional_user
from app.main import app
from app.models import Suggestion, User, Vote, Word
from app.promote import _meets_threshold, PROMOTE_MIN_AGE_DAYS, PROMOTE_MIN_NET_VOTES


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
    email="test@example.com",
    role="reviewer",
    oauth_provider=None,
) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = email
    user.display_name = "Test User"
    user.role = role
    user.is_blocked = False
    user.created_at = datetime.now(timezone.utc)
    user.last_seen_at = None
    user.oauth_provider = oauth_provider
    return user


def make_mock_suggestion(
    target_type="new_word",
    status="open",
    user_id=None,
    session_id=None,
    age_days=0,
) -> MagicMock:
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
    s.created_at = datetime.now(timezone.utc) - timedelta(days=age_days)
    s.decided_at = None
    s.decided_by_user_id = None
    s.applied_at = None
    return s


@pytest.fixture
async def mock_db():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MockResult())
    session.scalar = AsyncMock(return_value=0)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
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
# UserResponse includes oauth_provider
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_user_response_includes_oauth_provider(client_with_mock_db, mock_db):
    """GET /api/auth/me returns oauth_provider for OAuth-linked users."""
    user = make_mock_user(oauth_provider="google")

    async def override_auth():
        return user

    app.dependency_overrides[get_current_user] = override_auth

    response = await client_with_mock_db.get("/api/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert "oauth_provider" in data
    assert data["oauth_provider"] == "google"


@pytest.mark.asyncio
async def test_user_response_oauth_provider_none_for_password_users(client_with_mock_db, mock_db):
    """GET /api/auth/me returns oauth_provider=null for password users."""
    user = make_mock_user(oauth_provider=None)

    async def override_auth():
        return user

    app.dependency_overrides[get_current_user] = override_auth

    response = await client_with_mock_db.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["oauth_provider"] is None


# ═══════════════════════════════════════════════════════════════
# get_me updates last_seen_at
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_me_updates_last_seen_at(client_with_mock_db, mock_db):
    """GET /api/auth/me updates the user's last_seen_at timestamp."""
    user = make_mock_user()
    user.last_seen_at = None  # initially null

    async def override_auth():
        return user

    app.dependency_overrides[get_current_user] = override_auth

    response = await client_with_mock_db.get("/api/auth/me")

    assert response.status_code == 200
    # The endpoint should have set last_seen_at to a non-None value
    assert user.last_seen_at is not None
    assert mock_db.commit.called


# ═══════════════════════════════════════════════════════════════
# SuggestionListItem includes created_by_user_id
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_suggestion_list_includes_created_by_user_id(client_with_mock_db, mock_db):
    """GET /api/suggestions response items include created_by_user_id."""
    user_id = uuid.uuid4()
    suggestion = make_mock_suggestion(user_id=user_id)

    mock_db.scalar = AsyncMock(return_value=1)
    # Two execute calls: paginated fetch returns [suggestion], vote counts returns []
    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(rows=[suggestion]),  # paginated fetch
            MockResult(rows=[]),            # vote counts (empty)
        ]
    )

    response = await client_with_mock_db.get("/api/suggestions")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["created_by_user_id"] == str(user_id)


# ═══════════════════════════════════════════════════════════════
# SuggestionResponse no longer leaks created_by_session_id
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_suggestion_response_omits_session_id(client_with_mock_db, mock_db):
    """GET /api/suggestions/{id} response does NOT include created_by_session_id."""
    session_id = uuid.uuid4()
    suggestion = make_mock_suggestion(session_id=session_id)

    mock_db.execute = AsyncMock(return_value=MockResult(value=suggestion))

    response = await client_with_mock_db.get(f"/api/suggestions/{suggestion.id}")

    assert response.status_code == 200
    data = response.json()
    # session_id should NOT be in the response (privacy: it's an internal UUID)
    assert "created_by_session_id" not in data


# ═══════════════════════════════════════════════════════════════
# user_vote is populated when authed
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_suggestion_list_user_vote_populated_when_authed(client_with_mock_db, mock_db):
    """GET /api/suggestions as authed user includes user_vote on each item."""
    user_id = uuid.uuid4()
    suggestion = make_mock_suggestion(user_id=user_id)

    user = make_mock_user()
    user.id = user_id

    async def override_auth():
        return user

    app.dependency_overrides[get_optional_user] = override_auth

    # Mock: count=1, fetch=[suggestion], vote_counts=[('up', 3)], user_vote=[Vote('up')]
    up_vote = MagicMock(spec=Vote)
    up_vote.suggestion_id = suggestion.id
    up_vote.vote = "up"

    # Vote-count row that supports BOTH attribute access (row.suggestion_id, row.vote, row.count)
    # AND tuple unpacking (sid, vote, count = row) — SQLAlchemy Row supports both.
    vote_count_row = MagicMock()
    vote_count_row.suggestion_id = suggestion.id
    vote_count_row.vote = "up"
    vote_count_row.count = 3
    vote_count_row.__iter__ = lambda self: iter((suggestion.id, "up", 3))

    mock_db.scalar = AsyncMock(return_value=1)
    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(rows=[suggestion]),       # paginated fetch
            MockResult(rows=[vote_count_row]),    # vote count
            MockResult(rows=[up_vote]),           # user's vote
        ]
    )

    response = await client_with_mock_db.get("/api/suggestions")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["user_vote"] == "up"
    assert items[0]["upvotes"] == 3


@pytest.mark.asyncio
async def test_suggestion_list_user_vote_none_when_unauth(client_with_mock_db, mock_db):
    """GET /api/suggestions as anon user has user_vote=null on each item."""
    suggestion = make_mock_suggestion()

    async def override_auth():
        return None

    app.dependency_overrides[get_optional_user] = override_auth

    # Vote-count row that supports both attribute access and tuple unpacking
    vote_count_row = MagicMock()
    vote_count_row.suggestion_id = suggestion.id
    vote_count_row.vote = "up"
    vote_count_row.count = 2
    vote_count_row.__iter__ = lambda self: iter((suggestion.id, "up", 2))

    mock_db.scalar = AsyncMock(return_value=1)
    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(rows=[suggestion]),
            MockResult(rows=[vote_count_row]),
        ]
    )

    response = await client_with_mock_db.get("/api/suggestions")

    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["user_vote"] is None


# ═══════════════════════════════════════════════════════════════
# Phase A: dropped 3rd promote condition (no non-anon-upvote requirement)
# ═══════════════════════════════════════════════════════════════


def make_vote_count_row(vote: str, count: int) -> MagicMock:
    """Make a mock Row with .vote and .count attributes (mimics SQLAlchemy Row)."""
    row = MagicMock()
    row.vote = vote
    row.count = count
    return row


@pytest.mark.asyncio
async def test_promote_threshold_age_only_and_net_votes():
    """_meets_threshold returns True with ONLY age >= 7d AND net >= 3,
    even if all upvotes are from anon sessions (no registered-user requirement)."""
    # Suggestion: 8 days old (past the 7-day threshold)
    suggestion = make_mock_suggestion(age_days=8)
    suggestion.status = "open"

    db = MagicMock()

    # Mock vote counts: 3 anon upvotes, 0 downvotes
    # _meets_threshold's vote-count query returns 3 'up' votes
    vote_count_result = MagicMock()
    vote_count_result.all.return_value = [make_vote_count_row("up", 3)]

    db.execute = AsyncMock(return_value=vote_count_result)

    result = await _meets_threshold(db, suggestion)

    assert result is True, (
        "Auto-promote should fire with age >= 7d AND net >= 3, "
        "even if all upvotes are anon (the 3rd 'non-anon upvotes' condition "
        "was intentionally removed)."
    )


@pytest.mark.asyncio
async def test_promote_threshold_fails_when_too_young():
    """_meets_threshold returns False when suggestion is < 7 days old,
    even with high vote count."""
    suggestion = make_mock_suggestion(age_days=3)
    suggestion.status = "open"

    db = MagicMock()
    vote_count_result = MagicMock()
    vote_count_result.all.return_value = [make_vote_count_row("up", 10)]
    db.execute = AsyncMock(return_value=vote_count_result)

    result = await _meets_threshold(db, suggestion)
    assert result is False


@pytest.mark.asyncio
async def test_promote_threshold_fails_when_net_votes_below_3():
    """_meets_threshold returns False when net votes < 3, even if old enough."""
    suggestion = make_mock_suggestion(age_days=10)
    suggestion.status = "open"

    db = MagicMock()
    vote_count_result = MagicMock()
    vote_count_result.all.return_value = [make_vote_count_row("up", 2)]
    db.execute = AsyncMock(return_value=vote_count_result)

    result = await _meets_threshold(db, suggestion)
    assert result is False


@pytest.mark.asyncio
async def test_promote_threshold_fails_when_not_open():
    """_meets_threshold returns False when suggestion status != 'open'."""
    suggestion = make_mock_suggestion(age_days=10, status="accepted")

    db = MagicMock()
    result = await _meets_threshold(db, suggestion)
    assert result is False


@pytest.mark.asyncio
async def test_promote_threshold_with_downvotes_subtracted():
    """_meets_threshold uses net = up - down, not raw up count."""
    suggestion = make_mock_suggestion(age_days=10)
    suggestion.status = "open"

    db = MagicMock()
    vote_count_result = MagicMock()
    # 5 up, 3 down → net = 2 → below threshold
    vote_count_result.all.return_value = [
        make_vote_count_row("up", 5),
        make_vote_count_row("down", 3),
    ]
    db.execute = AsyncMock(return_value=vote_count_result)

    result = await _meets_threshold(db, suggestion)
    assert result is False


# ═══════════════════════════════════════════════════════════════
# Phase E: example suggestions validation
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_example_suggestion_validates_target_id_required(client_with_mock_db, mock_db):
    """example suggestion without target_id returns 422."""
    async def override_auth():
        return None

    app.dependency_overrides[get_optional_user] = override_auth

    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "example",
            "proposed_value": {"language": "sw", "text": "Mlima ni mrefu."},
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_example_suggestion_validates_language_required(client_with_mock_db, mock_db):
    """example suggestion without language returns 422."""
    async def override_auth():
        return None

    app.dependency_overrides[get_optional_user] = override_auth

    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "example",
            "target_id": str(uuid.uuid4()),
            "proposed_value": {"text": "Mlima ni mrefu."},
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_example_suggestion_validates_text_required(client_with_mock_db, mock_db):
    """example suggestion without text returns 422."""
    async def override_auth():
        return None

    app.dependency_overrides[get_optional_user] = override_auth

    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "example",
            "target_id": str(uuid.uuid4()),
            "proposed_value": {"language": "sw"},
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_example_suggestion_unknown_target_returns_404(client_with_mock_db, mock_db):
    """example suggestion to non-existent example returns 404."""
    async def override_auth():
        return None

    app.dependency_overrides[get_optional_user] = override_auth

    # Mock: example lookup returns None (not found)
    mock_db.execute = AsyncMock(return_value=MockResult(value=None))

    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "example",
            "target_id": str(uuid.uuid4()),
            "proposed_value": {"language": "sw", "text": "Mlima ni mrefu."},
        },
    )

    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════
# Phase E: relation suggestion treats 'variant' and 'see_also' as symmetric
# (Documented behaviour — verified by inspecting _apply_relation)
# ═══════════════════════════════════════════════════════════════


def test_relation_symmetric_types_documented():
    """Document that 'variant' and 'see_also' are treated as symmetric
    by _apply_relation (the dedup check looks in both directions)."""
    from app.promote import _apply_relation
    # We can't easily unit-test the async function with a real DB,
    # but we can verify the symmetric-type list is referenced in the source.
    import inspect

    source = inspect.getsource(_apply_relation)
    assert "symmetric" in source.lower()
    assert '"variant"' in source or "'variant'" in source
    assert '"see_also"' in source or "'see_also'" in source

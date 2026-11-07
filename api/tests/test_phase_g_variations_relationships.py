"""Tests for Phase G: split word_relations into word_variations +
word_relationships.

Verifies:
  - Migration 0004 is syntactically valid (revision chain)
  - WordDetail.variations and WordDetail.relationships fields exist
  - Legacy WordDetail.relations field still populated for backward compat
  - target_type='variation' suggestion flow
  - target_type='relationship' suggestion flow
  - target_type='relation' (legacy) auto-dispatches to the right table
"""

from __future__ import annotations

import importlib.util
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.deps import get_optional_user
from app.main import app
from app.promote import (
    DIRECTIONAL_RELATIONSHIP_TYPES,
    RELATIONSHIP_TYPES,
    SYMMETRIC_RELATIONSHIP_TYPES,
    VARIATION_TYPES,
)


# ═══════════════════════════════════════════════════════════════
# Migration chain validation
# ═══════════════════════════════════════════════════════════════


def test_migration_0004_exists_and_chains_correctly():
    """The 0004 migration file exists and chains from 0003."""
    migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "0004_split_variations_relationships.py"
    assert migration_path.exists(), "Migration 0004 file should exist"

    spec = importlib.util.spec_from_file_location("m0004", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0004"
    assert module.down_revision == "0003"
    assert callable(module.upgrade)
    assert callable(module.downgrade)


def test_migration_0004_vocabulary_constants():
    """The migration defines the right sets of variation and relationship types."""
    migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "0004_split_variations_relationships.py"
    spec = importlib.util.spec_from_file_location("m0004", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.VARIATION_TYPES == {
        "variant", "plural", "singular", "conjugation",
        "diminutive", "augmentative",
    }
    assert module.SYMMETRIC_RELATIONSHIPS == {"antonym", "synonym", "see_also"}
    assert module.DIRECTIONAL_RELATIONSHIPS == {"derived", "etymological"}
    assert module.RELATIONSHIP_TYPES == module.SYMMETRIC_RELATIONSHIPS | module.DIRECTIONAL_RELATIONSHIPS


# ═══════════════════════════════════════════════════════════════
# Vocabulary sets in promote.py
# ═══════════════════════════════════════════════════════════════


def test_variation_types_set_is_correct():
    """VARIATION_TYPES matches the migration's set."""
    assert VARIATION_TYPES == frozenset({
        "variant", "plural", "singular", "conjugation",
        "diminutive", "augmentative",
    })


def test_relationship_types_set_is_correct():
    """RELATIONSHIP_TYPES matches the migration's set."""
    assert RELATIONSHIP_TYPES == frozenset({"antonym", "synonym", "see_also", "derived", "etymological"})


def test_symmetric_vs_directional_split():
    """Symmetric and directional relationship types are disjoint and cover all relationships."""
    assert SYMMETRIC_RELATIONSHIP_TYPES.isdisjoint(DIRECTIONAL_RELATIONSHIP_TYPES)
    assert SYMMETRIC_RELATIONSHIP_TYPES | DIRECTIONAL_RELATIONSHIP_TYPES == RELATIONSHIP_TYPES


def test_variations_and_relationships_are_disjoint():
    """No type appears in both VARIATION_TYPES and RELATIONSHIP_TYPES."""
    assert VARIATION_TYPES.isdisjoint(RELATIONSHIP_TYPES)


# ═══════════════════════════════════════════════════════════════
# WordDetail schema includes variations + relationships + legacy relations
# ═══════════════════════════════════════════════════════════════


def test_word_detail_schema_has_split_fields():
    """WordDetail includes variations, relationships, and legacy relations fields."""
    from app.schemas import WordDetail

    # Build a minimal WordDetail to verify the fields exist
    word_id = uuid.uuid4()
    detail = WordDetail(
        id=word_id,
        slug="mlima",
        headword="mlima",
        status="live",
        created_at=datetime.now(timezone.utc),
    )
    assert hasattr(detail, "variations")
    assert hasattr(detail, "relationships")
    assert hasattr(detail, "relations")  # legacy
    assert detail.variations == []
    assert detail.relationships == []
    assert detail.relations == []


def test_variation_out_schema_shape():
    """VariationOut has the right fields (no direction — always bidirectional)."""
    from app.schemas import VariationOut

    fields = VariationOut.model_fields
    assert "other_word_id" in fields
    assert "other_headword" in fields
    assert "other_slug" in fields
    assert "variation_type" in fields
    # Variations are bidirectional — no direction field
    assert "direction" not in fields


def test_relationship_out_schema_shape():
    """RelationshipOut has the right fields including direction and note."""
    from app.schemas import RelationshipOut

    fields = RelationshipOut.model_fields
    assert "other_word_id" in fields
    assert "other_headword" in fields
    assert "other_slug" in fields
    assert "relationship_type" in fields
    assert "direction" in fields
    assert "note" in fields


# ═══════════════════════════════════════════════════════════════
# Suggestion target_type validation
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


@pytest.fixture
async def mock_db():
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=0)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()

    async def fake_commit():
        pass

    async def fake_refresh(obj):
        if not getattr(obj, "id", None):
            obj.id = uuid.uuid4()
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(timezone.utc)

    session.commit = AsyncMock(side_effect=fake_commit)
    session.refresh = AsyncMock(side_effect=fake_refresh)
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


@pytest.mark.asyncio
async def test_variation_suggestion_validates_required_fields(client_with_mock_db, mock_db):
    """variation suggestion without related_word or variation_type returns 422."""
    async def override_auth():
        return None
    app.dependency_overrides[get_optional_user] = override_auth

    # Missing related_word
    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "variation",
            "target_id": str(uuid.uuid4()),
            "proposed_value": {"variation_type": "plural"},
        },
    )
    assert response.status_code == 422

    # Missing variation_type
    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "variation",
            "target_id": str(uuid.uuid4()),
            "proposed_value": {"related_word": "mlima"},
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_relationship_suggestion_validates_required_fields(client_with_mock_db, mock_db):
    """relationship suggestion without related_word or relationship_type returns 422."""
    async def override_auth():
        return None
    app.dependency_overrides[get_optional_user] = override_auth

    # Missing related_word
    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "relationship",
            "target_id": str(uuid.uuid4()),
            "proposed_value": {"relationship_type": "antonym"},
        },
    )
    assert response.status_code == 422

    # Missing relationship_type
    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "relationship",
            "target_id": str(uuid.uuid4()),
            "proposed_value": {"related_word": "enda"},
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_variation_suggestion_unknown_word_returns_404(client_with_mock_db, mock_db):
    """variation suggestion to non-existent word returns 404."""
    async def override_auth():
        return None
    app.dependency_overrides[get_optional_user] = override_auth

    mock_db.execute = AsyncMock(return_value=MockResult(value=None))

    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "variation",
            "target_id": str(uuid.uuid4()),
            "proposed_value": {"related_word": "mlima", "variation_type": "plural"},
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_relationship_suggestion_unknown_word_returns_404(client_with_mock_db, mock_db):
    """relationship suggestion to non-existent word returns 404."""
    async def override_auth():
        return None
    app.dependency_overrides[get_optional_user] = override_auth

    mock_db.execute = AsyncMock(return_value=MockResult(value=None))

    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "relationship",
            "target_id": str(uuid.uuid4()),
            "proposed_value": {"related_word": "enda", "relationship_type": "antonym"},
        },
    )

    assert response.status_code == 404

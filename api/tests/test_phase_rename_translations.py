"""Tests for the v1.3 gloss → translation rename.

Verifies:
  - target_type='translation' works (the new name)
  - target_type='gloss' still works (legacy alias for in-flight suggestions)
  - NewWordProposal uses swahili_translation / english_translation
  - _apply_new_word accepts both new keys (swahili_translation) and legacy (swahili_gloss)
    so in-flight suggestions created before the rename still apply
  - WordListItem uses swahili_translation / english_translation
  - WordDetail.translations field exists (was glosses)
  - SenseOut.translations field exists (was glosses)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.deps import get_optional_user
from app.main import app
from app.models import Suggestion, Translation, Word


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


def make_mock_word(headword="mlima", slug="mlima") -> MagicMock:
    word = MagicMock(spec=Word)
    word.id = uuid.uuid4()
    word.headword = headword
    word.normalized_form = headword.lower()
    word.slug = slug
    word.part_of_speech = "noun"
    word.noun_class = None
    word.dialect = "Dawida"
    word.literal_translation = None
    word.morphology_notes = None
    word.status = "live"
    word.created_at = datetime.now(timezone.utc)
    word.translations = []
    word.examples = []
    return word


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


# ═══════════════════════════════════════════════════════════════
# Schema field renames
# ═══════════════════════════════════════════════════════════════


def test_word_list_item_uses_translation_field_names():
    """WordListItem has swahili_translation and english_translation (not gloss)."""
    from app.schemas import WordListItem

    fields = WordListItem.model_fields
    assert "swahili_translation" in fields
    assert "english_translation" in fields
    assert "swahili_gloss" not in fields
    assert "english_gloss" not in fields


def test_word_detail_uses_translations_field():
    """WordDetail has a translations field (not glosses)."""
    from app.schemas import WordDetail

    fields = WordDetail.model_fields
    assert "translations" in fields
    assert "glosses" not in fields


def test_sense_out_uses_translations_field():
    """SenseOut has a translations field (not glosses)."""
    from app.schemas import SenseOut

    fields = SenseOut.model_fields
    assert "translations" in fields
    assert "glosses" not in fields


def test_translation_out_replaces_gloss_out():
    """TranslationOut exists (GlossOut is gone)."""
    from app.schemas import TranslationOut

    fields = TranslationOut.model_fields
    assert "language" in fields
    assert "text" in fields

    # GlossOut should no longer be importable
    with pytest.raises(ImportError):
        from app.schemas import GlossOut  # noqa: F401


def test_new_word_proposal_uses_translation_field_names():
    """NewWordProposal has swahili_translation and english_translation."""
    from app.schemas_suggestion import NewWordProposal

    fields = NewWordProposal.model_fields
    assert "swahili_translation" in fields
    assert "english_translation" in fields
    assert "swahili_gloss" not in fields
    assert "english_gloss" not in fields


def test_translation_model_replaces_gloss():
    """The Translation model exists (Gloss is gone)."""
    from app.models import Translation

    assert Translation.__tablename__ == "translations"

    # Gloss should no longer be importable
    with pytest.raises(ImportError):
        from app.models import Gloss  # noqa: F401


# ═══════════════════════════════════════════════════════════════
# Suggestion target_type alias
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_translation_suggestion_accepted(client_with_mock_db, mock_db):
    """target_type='translation' is accepted (the new name)."""
    async def override_auth():
        return None
    app.dependency_overrides[get_optional_user] = override_auth

    word = make_mock_word()
    mock_db.execute = AsyncMock(return_value=MockResult(value=word))

    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "translation",
            "target_id": str(word.id),
            "proposed_value": {"language": "sw", "text": "mlima"},
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["target_type"] == "translation"
    assert data["status"] == "open"


@pytest.mark.asyncio
async def test_gloss_suggestion_still_accepted_as_legacy_alias(client_with_mock_db, mock_db):
    """target_type='gloss' still works as a legacy alias for in-flight suggestions."""
    async def override_auth():
        return None
    app.dependency_overrides[get_optional_user] = override_auth

    word = make_mock_word()
    mock_db.execute = AsyncMock(return_value=MockResult(value=word))

    response = await client_with_mock_db.post(
        "/api/suggestions",
        json={
            "target_type": "gloss",
            "target_id": str(word.id),
            "proposed_value": {"language": "sw", "text": "mlima"},
        },
    )

    assert response.status_code == 201
    data = response.json()
    # The target_type is stored as-is (whatever the client sent)
    assert data["target_type"] == "gloss"


# ═══════════════════════════════════════════════════════════════
# _apply_new_word accepts both new and legacy proposed_value keys
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_apply_new_word_reads_swahili_translation_key():
    """_apply_new_word reads proposed_value.swahili_translation (new key)."""
    from app.promote import _apply_new_word

    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    # generate_unique_slug calls db.execute — mock it to return None (no collision)
    slug_result = MagicMock()
    slug_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=slug_result)

    suggestion = MagicMock(spec=Suggestion)
    suggestion.id = uuid.uuid4()
    suggestion.created_by_user_id = uuid.uuid4()
    suggestion.created_by_session_id = None
    suggestion.proposed_value = {
        "headword": "mlima",
        "swahili_translation": "mlima, kilima",
        "english_translation": "mountain, hill",
    }

    await _apply_new_word(db, suggestion, actor_id=None)

    # Verify Translation objects were added (not Gloss)
    added = [call.args[0] for call in db.add.call_args_list]
    translations = [o for o in added if isinstance(o, Translation)]
    assert len(translations) >= 2  # at least sw + en

    # Verify the text matches the new key
    sw_translations = [t for t in translations if t.language == "sw"]
    assert len(sw_translations) == 1
    assert sw_translations[0].text == "mlima, kilima"


@pytest.mark.asyncio
async def test_apply_new_word_reads_legacy_swahili_gloss_key():
    """_apply_new_word still reads proposed_value.swahili_gloss (legacy key)
    so in-flight suggestions created before the v1.3 rename still apply."""
    from app.promote import _apply_new_word

    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    slug_result = MagicMock()
    slug_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=slug_result)

    suggestion = MagicMock(spec=Suggestion)
    suggestion.id = uuid.uuid4()
    suggestion.created_by_user_id = uuid.uuid4()
    suggestion.created_by_session_id = None
    suggestion.proposed_value = {
        "headword": "mlima",
        # Legacy keys (pre-v1.3 suggestion)
        "swahili_gloss": "mlima, kilima",
        "english_gloss": "mountain, hill",
    }

    await _apply_new_word(db, suggestion, actor_id=None)

    added = [call.args[0] for call in db.add.call_args_list]
    translations = [o for o in added if isinstance(o, Translation)]
    assert len(translations) >= 2

    sw_translations = [t for t in translations if t.language == "sw"]
    assert len(sw_translations) == 1
    assert sw_translations[0].text == "mlima, kilima"

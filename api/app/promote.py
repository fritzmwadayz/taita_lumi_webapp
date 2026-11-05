"""Auto-promote logic for suggestions.

When a suggestion meets the threshold, it's automatically accepted
and applied to the word graph:
  - status = 'open'
  - age >= 7 days
  - net_votes (up - down) >= 3
  - at least 2 distinct non-anon upvotes

Applying a suggestion:
  - target_type='new_word': create a Word row with glosses (sw + en)
  - target_type='word': update the Word row's field

After applying:
  - suggestion.status = 'accepted'
  - suggestion.applied_at = now()
  - edit_log row written for audit
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EditLog, Gloss, Suggestion, User, Vote, Word

# ── Threshold config ──────────────────────────────────────────
PROMOTE_MIN_AGE_DAYS = 7
PROMOTE_MIN_NET_VOTES = 3
PROMOTE_MIN_NON_ANON_UPVOTES = 2


def _normalize_form(text: str) -> str:
    """Lowercase + strip non-alpha (keep apostrophes). Mirrors export script."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def _meets_threshold(db: AsyncSession, suggestion: Suggestion) -> bool:
    """Check if a suggestion meets the auto-promote threshold."""
    if suggestion.status != "open":
        return False

    # ── Age check ─────────────────────────────────────────────
    age = datetime.now(timezone.utc) - suggestion.created_at
    if age < timedelta(days=PROMOTE_MIN_AGE_DAYS):
        return False

    # ── Vote stats ────────────────────────────────────────────
    result = await db.execute(
        select(Vote.vote, func.count().label("count"))
        .where(Vote.suggestion_id == suggestion.id)
        .group_by(Vote.vote)
    )
    counts = {"up": 0, "down": 0}
    for row in result.all():
        if row.vote in counts:
            counts[row.vote] = row.count

    net_votes = counts["up"] - counts["down"]
    if net_votes < PROMOTE_MIN_NET_VOTES:
        return False

    # ── Non-anon upvotes (votes where user_id is not NULL) ───
    result = await db.execute(
        select(func.count()).where(
            Vote.suggestion_id == suggestion.id,
            Vote.vote == "up",
            Vote.user_id.is_not(None),
        )
    )
    non_anon_upvotes = result.scalar() or 0
    if non_anon_upvotes < PROMOTE_MIN_NON_ANON_UPVOTES:
        return False

    return True


async def _apply_new_word(
    db: AsyncSession, suggestion: Suggestion, actor_id: UUID | None
) -> UUID:
    """Apply a new_word suggestion: create the Word + Glosses.

    Returns the new Word ID.
    """
    pv = suggestion.proposed_value
    headword = pv.get("headword", "").strip()
    normalized = _normalize_form(headword)

    word = Word(
        headword=headword,
        normalized_form=normalized,
        part_of_speech=pv.get("part_of_speech"),
        noun_class=pv.get("noun_class"),
        dialect=pv.get("dialect"),
        literal_translation=pv.get("literal_translation"),
        morphology_notes=pv.get("morphology_notes"),
        status="live",
        source="user" if suggestion.created_by_user_id else "anon",
        created_by_user_id=suggestion.created_by_user_id,
        created_by_session_id=suggestion.created_by_session_id,
    )
    db.add(word)
    await db.flush()  # populate word.id

    # ── Glosses ───────────────────────────────────────────────
    if pv.get("swahili_gloss"):
        db.add(Gloss(word_id=word.id, language="sw", text=pv["swahili_gloss"]))
    if pv.get("english_gloss"):
        db.add(Gloss(word_id=word.id, language="en", text=pv["english_gloss"]))

    # ── Audit log ─────────────────────────────────────────────
    db.add(
        EditLog(
            actor_user_id=actor_id,
            action="create",
            entity_type="word",
            entity_id=word.id,
            after={
                "headword": word.headword,
                "source": "auto-promote",
                "suggestion_id": str(suggestion.id),
            },
        )
    )

    return word.id


async def _apply_word_correction(
    db: AsyncSession, suggestion: Suggestion, actor_id: UUID | None
) -> None:
    """Apply a word correction: update the Word's field.

    For v1, we support correcting scalar fields on the Word itself
    (headword, part_of_speech, dialect, noun_class, literal_translation,
    morphology_notes). Gloss/example corrections come later.
    """
    if not suggestion.target_id:
        return

    # ── Fetch the word ────────────────────────────────────────
    result = await db.execute(select(Word).where(Word.id == suggestion.target_id))
    word = result.scalar_one_or_none()
    if word is None:
        return  # word was deleted; can't apply

    field = suggestion.field_path
    # proposed_value is a dict like {"value": "new_value"} or just the value
    pv = suggestion.proposed_value
    new_value = pv.get("value") if isinstance(pv, dict) else pv
    if new_value is None:
        return

    # ── Special handling for headword (also update normalized_form) ─
    before_value = getattr(word, field, None) if hasattr(word, field) else None

    if field == "headword":
        word.headword = str(new_value)
        word.normalized_form = _normalize_form(str(new_value))
    elif hasattr(word, field):
        setattr(word, field, new_value)
    else:
        return  # unknown field

    # ── Audit log ─────────────────────────────────────────────
    db.add(
        EditLog(
            actor_user_id=actor_id,
            action="update",
            entity_type="word",
            entity_id=word.id,
            before={field: before_value},
            after={field: new_value, "source": "auto-promote", "suggestion_id": str(suggestion.id)},
        )
    )


async def _apply_gloss(
    db: AsyncSession, suggestion: Suggestion, actor_id: UUID | None
) -> None:
    """Apply a gloss suggestion: add a translation to an existing word.

    proposed_value should contain:
      - language: 'sw' or 'en'
      - text: the translation text
    """
    if not suggestion.target_id:
        return

    pv = suggestion.proposed_value
    language = pv.get("language")
    text = pv.get("text", "").strip()

    if not language or not text:
        return

    # ── Check if the word exists ──────────────────────────────
    result = await db.execute(select(Word).where(Word.id == suggestion.target_id))
    word = result.scalar_one_or_none()
    if word is None:
        return

    # ── Check if a gloss for this language already exists ─────
    existing = await db.execute(
        select(Gloss).where(
            Gloss.word_id == word.id,
            Gloss.language == language,
        )
    )
    if existing.scalar_one_or_none() is not None:
        # A gloss for this language already exists — skip (don't overwrite)
        return

    # ── Create the gloss ──────────────────────────────────────
    gloss = Gloss(word_id=word.id, language=language, text=text)
    db.add(gloss)

    # ── Audit log ─────────────────────────────────────────────
    db.add(
        EditLog(
            actor_user_id=actor_id,
            action="create",
            entity_type="gloss",
            entity_id=word.id,  # we log the word ID for easy lookup
            after={
                "language": language,
                "text": text,
                "source": "auto-promote",
                "suggestion_id": str(suggestion.id),
            },
        )
    )


async def _apply_relation(
    db: AsyncSession, suggestion: Suggestion, actor_id: UUID | None
) -> None:
    """Apply a relation suggestion: link this word to another word.

    proposed_value should contain:
      - related_word: headword (string) or word ID (string UUID)
      - relation_type: 'variant', 'conjugation', 'antonym', 'plural', 'singular', etc.
    """
    if not suggestion.target_id:
        return

    pv = suggestion.proposed_value
    related_word = pv.get("related_word")
    relation_type = pv.get("relation_type")

    if not related_word or not relation_type:
        return

    # ── Find the related word (by ID or by headword/normalized_form) ──
    related = None
    # Try as UUID first
    try:
        related_id = UUID(str(related_word))
        result = await db.execute(select(Word).where(Word.id == related_id))
        related = result.scalar_one_or_none()
    except (ValueError, AttributeError):
        pass

    # If not found by ID, try by headword or normalized_form
    if related is None:
        normalized = _normalize_form(str(related_word))
        result = await db.execute(
            select(Word).where(
                Word.status == "live",
                (Word.headword.ilike(str(related_word)))
                | (Word.normalized_form == normalized),
            )
        )
        related = result.scalar_one_or_none()

    if related is None:
        # Related word doesn't exist — can't create the relation
        return

    # ── Check if this relation already exists ─────────────────
    existing = await db.execute(
        select(WordRelation).where(
            WordRelation.from_word_id == suggestion.target_id,
            WordRelation.to_word_id == related.id,
            WordRelation.relation_type == relation_type,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return  # relation already exists

    # ── Create the relation ───────────────────────────────────
    relation = WordRelation(
        from_word_id=suggestion.target_id,
        to_word_id=related.id,
        relation_type=relation_type,
    )
    db.add(relation)

    # ── Audit log ─────────────────────────────────────────────
    db.add(
        EditLog(
            actor_user_id=actor_id,
            action="create",
            entity_type="relation",
            entity_id=suggestion.target_id,
            after={
                "related_word_id": str(related.id),
                "related_headword": related.headword,
                "relation_type": relation_type,
                "source": "auto-promote",
                "suggestion_id": str(suggestion.id),
            },
        )
    )


async def check_and_promote(db: AsyncSession, suggestion: Suggestion) -> bool:
    """Check if a suggestion meets the promote threshold, and apply if so.

    Returns True if the suggestion was promoted, False otherwise.
    Does NOT commit — caller manages the transaction.
    """
    if not await _meets_threshold(db, suggestion):
        return False

    # ── Apply the suggestion ──────────────────────────────────
    # System is the actor for auto-promote (actor_user_id = None)
    if suggestion.target_type == "new_word":
        await _apply_new_word(db, suggestion, actor_id=None)
    elif suggestion.target_type == "word":
        await _apply_word_correction(db, suggestion, actor_id=None)
    elif suggestion.target_type == "gloss":
        await _apply_gloss(db, suggestion, actor_id=None)
    elif suggestion.target_type == "relation":
        await _apply_relation(db, suggestion, actor_id=None)
    else:
        return False

    # ── Mark suggestion as accepted + applied ────────────────
    suggestion.status = "accepted"
    suggestion.applied_at = datetime.now(timezone.utc)
    # decided_by_user_id stays None — this was a system decision

    return True

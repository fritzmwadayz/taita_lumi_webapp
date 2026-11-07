"""Auto-promote logic for suggestions.

A suggestion is auto-promoted (accepted and applied) when BOTH:
  - status == 'open'
  - age >= 7 days  (created_at is at least 7 days old)
  - net votes (upvotes - downvotes) >= 3

(Reviewers/admins can also manually promote a suggestion via
POST /api/suggestions/{id}/decide or POST /api/admin/suggestions/{id}/decide,
bypassing the threshold entirely.)

Applying a suggestion:
  - target_type='new_word': create a Word row with translations + examples
  - target_type='word':     update the Word row's field
  - target_type='translation': add a translation to an existing word
    (was 'gloss' in v1.2 — 'gloss' still accepted as a legacy alias)
  - target_type='example':  add a translation to an existing example
  - target_type='relation': link this word to another word

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

from app.models import EditLog, Example, Sense, Suggestion, Translation, Vote, Word, WordRelationship, WordVariation
from app.slugs import generate_unique_slug

# ── Threshold config ──────────────────────────────────────────
PROMOTE_MIN_AGE_DAYS = 7
PROMOTE_MIN_NET_VOTES = 3


# Types that go to the word_variations table (bidirectional, definitional)
VARIATION_TYPES = frozenset({
    "variant", "plural", "singular", "conjugation",
    "diminutive", "augmentative",
})

# Types that go to the word_relationships table (typed, may be directional)
# Symmetric ones default to 'bidirectional' direction; directional ones to 'forward'.
SYMMETRIC_RELATIONSHIP_TYPES = frozenset({"antonym", "synonym", "see_also"})
DIRECTIONAL_RELATIONSHIP_TYPES = frozenset({"derived", "etymological"})
RELATIONSHIP_TYPES = SYMMETRIC_RELATIONSHIP_TYPES | DIRECTIONAL_RELATIONSHIP_TYPES


def _normalize_form(text: str) -> str:
    """Lowercase + strip non-alpha (keep apostrophes). Mirrors export script."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def _meets_threshold(db: AsyncSession, suggestion: Suggestion) -> bool:
    """Check if a suggestion meets the auto-promote threshold.

    Two conditions (matching the integration doc §9):
      - age >= 7 days
      - net votes (up - down) >= 3
    """
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

    return True


async def _apply_new_word(
    db: AsyncSession, suggestion: Suggestion, actor_id: UUID | None
) -> UUID:
    """Apply a new_word suggestion: create the Word + Translations + Examples.

    Returns the new Word ID.
    """
    pv = suggestion.proposed_value
    headword = pv.get("headword", "").strip()
    normalized = _normalize_form(headword)
    slug = await generate_unique_slug(db, headword)

    word = Word(
        headword=headword,
        normalized_form=normalized,
        slug=slug,
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

    # ── Default sense (order_index=1) for the new word ────────
    # Every word has at least one sense. The default sense holds the
    # translations + examples proposed in this suggestion.
    default_sense = Sense(
        word_id=word.id,
        order_index=1,
        definition=None,
        notes=None,
    )
    db.add(default_sense)
    await db.flush()  # populate default_sense.id

    # ── Translations (scoped to the default sense) ─────────
    # Accept both new key names (swahili_translation) and legacy (swahili_gloss)
    # so in-flight suggestions created before the v1.3 rename still apply.
    sw = pv.get("swahili_translation") or pv.get("swahili_gloss")
    en = pv.get("english_translation") or pv.get("english_gloss")
    if sw:
        db.add(Translation(word_id=word.id, sense_id=default_sense.id, language="sw", text=sw))
    if en:
        db.add(Translation(word_id=word.id, sense_id=default_sense.id, language="en", text=en))

    # ── Examples (scoped to the default sense) ────────────────
    for ex in pv.get("examples") or []:
        if ex.get("taita_text"):
            db.add(Example(
                word_id=word.id,
                sense_id=default_sense.id,
                taita_text=ex["taita_text"],
                swahili_text=ex.get("swahili_text"),
                english_text=ex.get("english_text"),
                source_ref=ex.get("source_ref"),
            ))

    # ── Audit log ─────────────────────────────────────────────
    db.add(
        EditLog(
            actor_user_id=actor_id,
            action="create",
            entity_type="word",
            entity_id=word.id,
            after={
                "headword": word.headword,
                "slug": word.slug,
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
    morphology_notes). Translation/example corrections come via target_type='translation'
    and target_type='example' respectively.
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

    # ── Special handling for headword (also update normalized_form + slug) ─
    before_value = getattr(word, field, None) if hasattr(word, field) else None

    if field == "headword":
        word.headword = str(new_value)
        word.normalized_form = _normalize_form(str(new_value))
        # Regenerate slug (excluding this word's own current slug)
        word.slug = await generate_unique_slug(db, str(new_value), exclude_word_id=word.id)
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


async def _apply_translation(
    db: AsyncSession, suggestion: Suggestion, actor_id: UUID | None
) -> None:
    """Apply a translation suggestion: add a translation to an existing word.

    proposed_value should contain:
      - language: 'sw' or 'en'
      - text: the translation text
      - sense_id (optional): the sense to scope the translation to. If not provided,
        the word's default sense (order_index=1) is used.
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

    # ── Resolve the sense to scope this translation to ────────
    sense_id = pv.get("sense_id")
    if sense_id:
        try:
            sense_id = UUID(str(sense_id))
        except (ValueError, TypeError):
            sense_id = None

    if not sense_id:
        # Use the word's default sense (order_index=1); create if missing
        result = await db.execute(
            select(Sense).where(Sense.word_id == word.id, Sense.order_index == 1)
        )
        default_sense = result.scalar_one_or_none()
        if default_sense is None:
            default_sense = Sense(word_id=word.id, order_index=1)
            db.add(default_sense)
            await db.flush()
        sense_id = default_sense.id

    # ── Check if a translation for this language already exists in this sense ──
    existing = await db.execute(
        select(Translation).where(
            Translation.word_id == word.id,
            Translation.sense_id == sense_id,
            Translation.language == language,
        )
    )
    if existing.scalar_one_or_none() is not None:
        # A translation for this language already exists in this sense — skip (don't overwrite)
        return

    # ── Create the translation ──────────────────────────────
    translation = Translation(word_id=word.id, sense_id=sense_id, language=language, text=text)
    db.add(translation)

    # ── Audit log ─────────────────────────────────────────────
    db.add(
        EditLog(
            actor_user_id=actor_id,
            action="create",
            entity_type="translation",
            entity_id=word.id,  # we log the word ID for easy lookup
            after={
                "language": language,
                "text": text,
                "sense_id": str(sense_id),
                "source": "auto-promote",
                "suggestion_id": str(suggestion.id),
            },
        )
    )


async def _apply_example(
    db: AsyncSession, suggestion: Suggestion, actor_id: UUID | None
) -> None:
    """Apply an example suggestion: add a translation to an existing example.

    target_type='example' is used when a reader suggests a translation for an
    example that already has taita_text but is missing swahili_text or
    english_text. The frontend's "See also / suggest a translation" affordance
    posts here.

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

    # ── Fetch the example ─────────────────────────────────────
    result = await db.execute(select(Example).where(Example.id == suggestion.target_id))
    example = result.scalar_one_or_none()
    if example is None:
        return

    # ── Don't overwrite an existing translation ───────────────
    if language == "sw" and example.swahili_text:
        return
    if language == "en" and example.english_text:
        return

    # ── Apply ─────────────────────────────────────────────────
    before = {}
    if language == "sw":
        before["swahili_text"] = example.swahili_text
        example.swahili_text = text
    elif language == "en":
        before["english_text"] = example.english_text
        example.english_text = text
    else:
        return  # unsupported language

    # ── Audit log (entity_id = the example's id) ──────────────
    db.add(
        EditLog(
            actor_user_id=actor_id,
            action="update",
            entity_type="example",
            entity_id=example.id,
            before=before or None,
            after={
                "language": language,
                "text": text,
                "source": "auto-promote",
                "suggestion_id": str(suggestion.id),
            },
        )
    )


async def _apply_new_example(
    db: AsyncSession, suggestion: Suggestion, actor_id: UUID | None
) -> None:
    """Apply a new_example suggestion: create a new Example row on an existing word.

    target_type='new_example' is used when a reader suggests a brand-new example
    sentence for a word that has no examples (or that should have more).
    The frontend's "Suggest an example" affordance posts here.

    proposed_value should contain:
      - taita_text: required, the example sentence in Taita
      - swahili_text: optional translation
      - english_text: optional translation
      - source_ref: optional citation
      - sense_id: optional, the UUID of the sense to scope this example to.
        If not provided, the word's default sense (order_index=1) is used.
        If the word has no senses, a default one is created.

    On accept, creates an Example row attached to suggestion.target_id (the word).
    The optional translations are set if provided; missing ones can be filled in
    later via target_type='example' suggestions on the new example.
    """
    if not suggestion.target_id:
        return

    pv = suggestion.proposed_value
    taita_text = (pv.get("taita_text") or "").strip()
    if not taita_text:
        return

    # ── Verify the word still exists ──────────────────────────
    result = await db.execute(select(Word).where(Word.id == suggestion.target_id))
    word = result.scalar_one_or_none()
    if word is None:
        return  # word was deleted; can't apply

    # ── Resolve the sense to scope this example to ────────────
    sense_id = pv.get("sense_id")
    if sense_id:
        try:
            sense_id = UUID(str(sense_id))
        except (ValueError, TypeError):
            sense_id = None

    if not sense_id:
        # Use the word's default sense (order_index=1); create if missing
        result = await db.execute(
            select(Sense).where(Sense.word_id == word.id, Sense.order_index == 1)
        )
        default_sense = result.scalar_one_or_none()
        if default_sense is None:
            # Word has no senses (legacy data not backfilled?) — create one
            default_sense = Sense(word_id=word.id, order_index=1)
            db.add(default_sense)
            await db.flush()
        sense_id = default_sense.id

    # ── Create the example (scoped to the resolved sense) ─────
    example = Example(
        word_id=word.id,
        sense_id=sense_id,
        taita_text=taita_text,
        swahili_text=(pv.get("swahili_text") or "").strip() or None,
        english_text=(pv.get("english_text") or "").strip() or None,
        source_ref=pv.get("source_ref"),
    )
    db.add(example)

    # ── Audit log ─────────────────────────────────────────────
    db.add(
        EditLog(
            actor_user_id=actor_id,
            action="create",
            entity_type="example",
            entity_id=word.id,  # we log the word ID for easy lookup
            after={
                "taita_text": example.taita_text,
                "swahili_text": example.swahili_text,
                "english_text": example.english_text,
                "source_ref": example.source_ref,
                "sense_id": str(sense_id),
                "source": "auto-promote",
                "suggestion_id": str(suggestion.id),
            },
        )
    )


async def _apply_relation(
    db: AsyncSession, suggestion: Suggestion, actor_id: UUID | None
) -> None:
    """Apply a relation suggestion: link this word to another word.

    DEPRECATED in favor of target_type='variation' and target_type='relationship'
    (which are explicit about which table to write to). Kept for backward compat
    with v1.1 frontend code that may still send target_type='relation'.

    proposed_value should contain:
      - related_word: headword (string) or word ID (string UUID)
      - relation_type: 'variant', 'see_also', 'plural', 'singular',
                       'antonym', 'synonym', 'derived', 'etymological', etc.

    Auto-dispatches:
      - relation_type IN VARIATION_TYPES → word_variations table
      - relation_type IN RELATIONSHIP_TYPES → word_relationships table
        (with direction='bidirectional' for symmetric, 'forward' for directional)
    """
    if not suggestion.target_id:
        return

    pv = suggestion.proposed_value
    related_word = pv.get("related_word")
    relation_type = pv.get("relation_type")

    if not related_word or not relation_type:
        return

    # ── Find the related word (by ID or by headword/normalized_form/slug) ──
    related = None
    try:
        related_id = UUID(str(related_word))
        result = await db.execute(select(Word).where(Word.id == related_id))
        related = result.scalar_one_or_none()
    except (ValueError, AttributeError):
        pass

    if related is None:
        normalized = _normalize_form(str(related_word))
        result = await db.execute(
            select(Word).where(
                Word.status == "live",
                (Word.headword.ilike(str(related_word)))
                | (Word.normalized_form == normalized)
                | (Word.slug == str(related_word).lower()),
            )
        )
        related = result.scalar_one_or_none()

    if related is None:
        return

    # ── Dispatch to the right table ───────────────────────────
    if relation_type in VARIATION_TYPES:
        await _create_variation(db, suggestion.target_id, related, relation_type, suggestion, actor_id)
    elif relation_type in RELATIONSHIP_TYPES:
        direction = "bidirectional" if relation_type in SYMMETRIC_RELATIONSHIP_TYPES else "forward"
        await _create_relationship(db, suggestion.target_id, related, relation_type, direction, suggestion, actor_id)
    # else: unknown relation_type — silently skip


async def _apply_variation(
    db: AsyncSession, suggestion: Suggestion, actor_id: UUID | None
) -> None:
    """Apply a variation suggestion: create a bidirectional link between two
    forms of the same lemma (e.g. mlima ↔ milima).

    proposed_value should contain:
      - related_word: headword (string) or word ID (string UUID) of the other form
      - variation_type: 'variant' | 'plural' | 'singular' | 'conjugation'
                       | 'diminutive' | 'augmentative'
    """
    if not suggestion.target_id:
        return

    pv = suggestion.proposed_value
    related_word = pv.get("related_word") or pv.get("other_word")
    variation_type = pv.get("variation_type") or pv.get("relation_type")

    if not related_word or not variation_type:
        return

    if variation_type not in VARIATION_TYPES:
        return  # invalid variation_type — silently skip

    related = await _find_related_word(db, related_word)
    if related is None:
        return

    await _create_variation(db, suggestion.target_id, related, variation_type, suggestion, actor_id)


async def _apply_relationship(
    db: AsyncSession, suggestion: Suggestion, actor_id: UUID | None
) -> None:
    """Apply a relationship suggestion: create a typed link between two
    different lemmas (e.g. kuja ↔ enda as antonyms).

    proposed_value should contain:
      - related_word: headword (string) or word ID (string UUID)
      - relationship_type: 'antonym' | 'synonym' | 'see_also'
                         | 'derived' | 'etymological'
      - direction (optional): 'bidirectional' | 'forward' | 'reverse'
        Defaults to 'bidirectional' for antonym/synonym/see_also,
        'forward' for derived/etymological.
      - note (optional): why these are related
    """
    if not suggestion.target_id:
        return

    pv = suggestion.proposed_value
    related_word = pv.get("related_word") or pv.get("other_word")
    relationship_type = pv.get("relationship_type") or pv.get("relation_type")

    if not related_word or not relationship_type:
        return

    if relationship_type not in RELATIONSHIP_TYPES:
        return

    related = await _find_related_word(db, related_word)
    if related is None:
        return

    # Determine direction with sensible defaults
    direction = pv.get("direction")
    if direction not in ("bidirectional", "forward", "reverse"):
        direction = "bidirectional" if relationship_type in SYMMETRIC_RELATIONSHIP_TYPES else "forward"

    await _create_relationship(
        db, suggestion.target_id, related, relationship_type, direction, suggestion, actor_id,
        note=pv.get("note"),
    )


async def _find_related_word(db: AsyncSession, related_word) -> Word | None:
    """Find a word by UUID, headword, slug, or normalized_form."""
    # Try as UUID first
    try:
        related_id = UUID(str(related_word))
        result = await db.execute(select(Word).where(Word.id == related_id))
        word = result.scalar_one_or_none()
        if word is not None:
            return word
    except (ValueError, AttributeError):
        pass

    # Try by headword, slug, or normalized_form
    normalized = _normalize_form(str(related_word))
    result = await db.execute(
        select(Word).where(
            Word.status == "live",
            (Word.headword.ilike(str(related_word)))
            | (Word.normalized_form == normalized)
            | (Word.slug == str(related_word).lower()),
        )
    )
    return result.scalar_one_or_none()


async def _create_variation(
    db: AsyncSession,
    word_id: UUID,
    related: Word,
    variation_type: str,
    suggestion: Suggestion,
    actor_id: UUID | None,
) -> None:
    """Create a word_variations row, deduping in both directions."""
    # Check if this variation already exists (in either direction — they're symmetric)
    existing = await db.execute(
        select(WordVariation).where(
            WordVariation.variation_type == variation_type,
            (
                ((WordVariation.word_id == word_id) & (WordVariation.other_word_id == related.id))
                | ((WordVariation.word_id == related.id) & (WordVariation.other_word_id == word_id))
            ),
        )
    )
    if existing.scalar_one_or_none() is not None:
        return  # already exists

    db.add(WordVariation(
        word_id=word_id,
        other_word_id=related.id,
        variation_type=variation_type,
    ))

    db.add(
        EditLog(
            actor_user_id=actor_id,
            action="create",
            entity_type="variation",
            entity_id=word_id,
            after={
                "related_word_id": str(related.id),
                "related_headword": related.headword,
                "variation_type": variation_type,
                "source": "auto-promote",
                "suggestion_id": str(suggestion.id),
            },
        )
    )


async def _create_relationship(
    db: AsyncSession,
    word_id: UUID,
    related: Word,
    relationship_type: str,
    direction: str,
    suggestion: Suggestion,
    actor_id: UUID | None,
    *,
    note: str | None = None,
) -> None:
    """Create a word_relationships row, deduping in both directions for
    bidirectional relationships."""
    # For bidirectional relationships, dedupe in both directions
    if direction == "bidirectional":
        existing = await db.execute(
            select(WordRelationship).where(
                WordRelationship.relationship_type == relationship_type,
                (
                    ((WordRelationship.word_id == word_id) & (WordRelationship.other_word_id == related.id))
                    | ((WordRelationship.word_id == related.id) & (WordRelationship.other_word_id == word_id))
                ),
            )
        )
    else:
        existing = await db.execute(
            select(WordRelationship).where(
                WordRelationship.word_id == word_id,
                WordRelationship.other_word_id == related.id,
                WordRelationship.relationship_type == relationship_type,
            )
        )
    if existing.scalar_one_or_none() is not None:
        return

    db.add(WordRelationship(
        word_id=word_id,
        other_word_id=related.id,
        relationship_type=relationship_type,
        direction=direction,
        note=note,
    ))

    db.add(
        EditLog(
            actor_user_id=actor_id,
            action="create",
            entity_type="relationship",
            entity_id=word_id,
            after={
                "related_word_id": str(related.id),
                "related_headword": related.headword,
                "relationship_type": relationship_type,
                "direction": direction,
                "note": note,
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
    elif suggestion.target_type in ("translation", "gloss"):
        await _apply_translation(db, suggestion, actor_id=None)
    elif suggestion.target_type == "example":
        await _apply_example(db, suggestion, actor_id=None)
    elif suggestion.target_type == "new_example":
        await _apply_new_example(db, suggestion, actor_id=None)
    elif suggestion.target_type == "relation":
        # Legacy target type — auto-dispatches to variation or relationship
        await _apply_relation(db, suggestion, actor_id=None)
    elif suggestion.target_type == "variation":
        await _apply_variation(db, suggestion, actor_id=None)
    elif suggestion.target_type == "relationship":
        await _apply_relationship(db, suggestion, actor_id=None)
    else:
        return False

    # ── Mark suggestion as accepted + applied ────────────────
    suggestion.status = "accepted"
    suggestion.applied_at = datetime.now(timezone.utc)
    # decided_by_user_id stays None — this was a system decision

    return True

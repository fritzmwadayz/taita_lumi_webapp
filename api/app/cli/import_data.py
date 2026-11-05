"""Import NDJSON export from taita-dictionary into the TaitaLumi web Postgres DB.

Usage:
  python -m app.cli.import_data path/to/export.ndjson
  python -m app.cli.import_data path/to/export.ndjson --dry-run
  python -m app.cli.import_data path/to/export.ndjson --source-commit abc123

Reads the NDJSON produced by taita-dictionary/scripts/export_for_web.py
and inserts each entry as a Word row, with child Gloss, Example, and
WordRelation rows. Wraps everything in a transaction; on any error,
rolls back and exits non-zero.

Idempotency:
  - If a Word with the same normalized_form already exists, the entry
    is skipped (and logged to stderr).
  - Variations: if the variation text matches an existing Word's
    normalized_form, we link to it. Otherwise, we create a stub Word
    row (headword=variation text, source='import', status='live') and
    link to that.

Audit:
  - Creates an ImportBatch row recording filename, commit, word_count.
  - Each imported Word row gets import_batch_id set.
  - Each Word creation is also written to edit_log.

This is the Phase 1 CLI. Phase 6 adds an admin UI that uploads NDJSON
via POST /api/admin/import and runs this same logic.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db import async_session
from app.models import (
    EditLog,
    Gloss,
    ImportBatch,
    Word,
    WordRelation,
)

# ── Stub admin user ID for Phase 1 ────────────────────────────
# Phase 6 will replace this with a real admin user lookup.
# For now, the first import will fail if no admin user exists —
# so we create a system admin user on first run if needed.
SYSTEM_ADMIN_EMAIL = "system@taitalumi.local"


async def get_or_create_system_admin(session) -> uuid.UUID:
    """Get the system admin user, creating it if necessary.

    This is a Phase 1 convenience — Phase 6 will require a real
    admin user to be authenticated.
    """
    from app.models import User

    result = await session.execute(
        select(User).where(User.email == SYSTEM_ADMIN_EMAIL)
    )
    user = result.scalar_one_or_none()
    if user is not None:
        return user.id

    user = User(
        email=SYSTEM_ADMIN_EMAIL,
        display_name="System (imports)",
        role="admin",
    )
    session.add(user)
    await session.flush()
    return user.id


def read_ndjson(path: Path) -> list[dict]:
    """Read NDJSON file, return list of dicts. Validates each line."""
    entries = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"ERROR: line {line_no}: invalid JSON: {e}", file=sys.stderr)
                sys.exit(1)
            entries.append(entry)
    return entries


async def import_entry(
    session,
    entry: dict,
    batch_id: uuid.UUID,
    admin_user_id: uuid.UUID,
) -> str:
    """Import a single entry. Returns 'created' or 'skipped'.

    Does NOT commit — the caller manages the transaction.
    """
    normalized = entry["normalized_form"]
    if not normalized:
        return "skipped_empty"

    # ── Idempotency check ─────────────────────────────────────
    existing = await session.execute(
        select(Word).where(Word.normalized_form == normalized)
    )
    existing_word = existing.scalar_one_or_none()
    if existing_word is not None:
        return "skipped_duplicate"

    # ── Create the Word row ───────────────────────────────────
    word = Word(
        headword=entry["headword"],
        normalized_form=normalized,
        part_of_speech=entry.get("part_of_speech"),
        noun_class=entry.get("noun_class"),
        dialect=entry.get("dialect"),
        literal_translation=entry.get("literal_translation"),
        morphology_notes=entry.get("morphology_notes"),
        status="live",
        source="import",
        created_by_user_id=admin_user_id,
        import_batch_id=batch_id,
    )
    session.add(word)
    await session.flush()  # populate word.id

    # ── Audit log: word creation ──────────────────────────────
    session.add(
        EditLog(
            actor_user_id=admin_user_id,
            action="import",
            entity_type="word",
            entity_id=word.id,
            after={
                "headword": word.headword,
                "normalized_form": word.normalized_form,
                "source_entry_id": entry.get("source_entry_id"),
            },
        )
    )

    # ── Glosses (Swahili first, English second) ───────────────
    # Only the translation(s) provided in lexicon.db are imported.
    # Most entries have swahili (auto-mapped); english is rarer.
    if entry.get("swahili_gloss"):
        session.add(
            Gloss(word_id=word.id, language="sw", text=entry["swahili_gloss"])
        )
    if entry.get("english_gloss"):
        session.add(
            Gloss(word_id=word.id, language="en", text=entry["english_gloss"])
        )

    # ── Examples: intentionally NOT imported ──────────────────
    # The web app starts with just words + translations. Examples will
    # be contributed via the web UI in later phases.

    # ── Variations → word_relations ───────────────────────────
    # For each variation, find or create a stub Word, then link.
    for var in entry.get("variations", []):
        var_text = var.get("variation", "").strip()
        if not var_text:
            continue
        var_normalized = var_text.lower()
        # Reuse tokenizer-style normalization (strip non-alpha)
        import re
        var_normalized = re.sub(r"[^a-z']", " ", var_normalized)
        var_normalized = re.sub(r"\s+", " ", var_normalized).strip()
        if not var_normalized:
            continue

        # Find existing word by normalized_form
        existing_var = await session.execute(
            select(Word).where(Word.normalized_form == var_normalized)
        )
        var_word = existing_var.scalar_one_or_none()

        if var_word is None:
            # Create stub Word for the variation
            var_word = Word(
                headword=var_text,
                normalized_form=var_normalized,
                dialect=var.get("dialect"),
                morphology_notes=var.get("notes"),
                status="live",
                source="import",
                created_by_user_id=admin_user_id,
                import_batch_id=batch_id,
            )
            session.add(var_word)
            await session.flush()

            session.add(
                EditLog(
                    actor_user_id=admin_user_id,
                    action="import",
                    entity_type="word",
                    entity_id=var_word.id,
                    after={
                        "headword": var_word.headword,
                        "note": "stub created from variation",
                    },
                )
            )

        # Create the relation: main word → variation, type='variant'
        session.add(
            WordRelation(
                from_word_id=word.id,
                to_word_id=var_word.id,
                relation_type="variant",
            )
        )

    return "created"


async def run_import(
    ndjson_path: Path,
    source_commit: str | None,
    dry_run: bool,
) -> int:
    """Run the import. Returns exit code (0 success, 1 failure)."""
    if not ndjson_path.exists():
        print(f"ERROR: file not found: {ndjson_path}", file=sys.stderr)
        return 1

    entries = read_ndjson(ndjson_path)
    if not entries:
        print("ERROR: no entries found in NDJSON file", file=sys.stderr)
        return 1

    print(f"Read {len(entries)} entries from {ndjson_path}", file=sys.stderr)
    if dry_run:
        print("DRY RUN — no changes will be made", file=sys.stderr)

    if dry_run:
        # Just validate that all entries have required fields
        for i, entry in enumerate(entries, start=1):
            if not entry.get("headword"):
                print(f"ERROR: entry {i} missing 'headword'", file=sys.stderr)
                return 1
            if not entry.get("normalized_form"):
                print(f"ERROR: entry {i} missing 'normalized_form'", file=sys.stderr)
                return 1
        print(f"DRY RUN OK: {len(entries)} entries validated", file=sys.stderr)
        return 0

    # ── Real import ───────────────────────────────────────────
    stats = {"created": 0, "skipped_duplicate": 0, "skipped_empty": 0, "errors": 0}

    async with async_session() as session:
        async with session.begin():
            try:
                # Get or create system admin
                admin_id = await get_or_create_system_admin(session)

                # Create import batch
                batch = ImportBatch(
                    source_filename=str(ndjson_path.name),
                    source_commit=source_commit or "unknown",
                    imported_by_user_id=admin_id,
                    word_count=0,  # will update at end
                )
                session.add(batch)
                await session.flush()  # populate batch.id

                # Import each entry
                for i, entry in enumerate(entries, start=1):
                    try:
                        result = await import_entry(session, entry, batch.id, admin_id)
                        stats[result] = stats.get(result, 0) + 1
                    except SQLAlchemyError as e:
                        stats["errors"] += 1
                        print(
                            f"ERROR on entry {i} ({entry.get('headword', '?')}): {e}",
                            file=sys.stderr,
                        )
                        raise  # abort the transaction

                    if i % 50 == 0:
                        print(f"  ... {i}/{len(entries)}", file=sys.stderr)

                # Update batch word_count with actual created count
                batch.word_count = stats["created"]

            except SQLAlchemyError as e:
                print(f"\nFATAL: transaction rolled back: {e}", file=sys.stderr)
                return 1

    # ── Summary ───────────────────────────────────────────────
    print("", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print(f"Import complete.", file=sys.stderr)
    print(f"  Created:         {stats['created']}", file=sys.stderr)
    print(f"  Skipped (dup):   {stats['skipped_duplicate']}", file=sys.stderr)
    print(f"  Skipped (empty): {stats['skipped_empty']}", file=sys.stderr)
    print(f"  Errors:          {stats['errors']}", file=sys.stderr)
    print(f"  Batch ID:        {batch.id}", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    return 0 if stats["errors"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import NDJSON export from taita-dictionary into Postgres."
    )
    parser.add_argument(
        "ndjson_path",
        type=Path,
        help="Path to the .ndjson file produced by export_for_web.py",
    )
    parser.add_argument(
        "--source-commit",
        type=str,
        default=None,
        help="Git commit SHA of the taita-dictionary repo at export time",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only — don't write to the database",
    )
    args = parser.parse_args()

    return asyncio.run(
        run_import(
            ndjson_path=args.ndjson_path,
            source_commit=args.source_commit,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    sys.exit(main())

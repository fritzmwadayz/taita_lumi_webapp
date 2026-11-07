"""rename glosses table to translations

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-07

Renames the `glosses` table to `translations` and its indexes accordingly.
"Translation" is more intuitive than "gloss" for non-lexicographers.

This is a pure rename — no data changes, no logic changes. The columns
(id, word_id, sense_id, language, text, created_at) stay exactly the same.

The model class `Gloss` → `Translation`, the API field `swahili_gloss` →
`swahili_translation` (and `english_gloss` → `english_translation`), and
the suggestion `target_type='gloss'` → `target_type='translation'` (with
'gloss' kept as a legacy alias for in-flight suggestions).

Existing audit_log rows with `entity_type='gloss'` are NOT migrated — they
remain as historical entries. The `_map_action()` function will surface them
as `gloss.create` in the public API (historical accuracy). New entries are
written with `entity_type='translation'` and surface as `translation.create`.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename the table
    op.rename_table("glosses", "translations")

    # Rename indexes for clarity (Postgres doesn't auto-rename them on table rename)
    op.execute("ALTER INDEX IF EXISTS ix_glosses_word_id RENAME TO ix_translations_word_id")
    op.execute("ALTER INDEX IF EXISTS ix_glosses_language RENAME TO ix_translations_language")
    op.execute("ALTER INDEX IF EXISTS ix_glosses_sense RENAME TO ix_translations_sense")


def downgrade() -> None:
    # Rename indexes back
    op.execute("ALTER INDEX IF EXISTS ix_translations_sense RENAME TO ix_glosses_sense")
    op.execute("ALTER INDEX IF EXISTS ix_translations_language RENAME TO ix_glosses_language")
    op.execute("ALTER INDEX IF EXISTS ix_translations_word_id RENAME TO ix_glosses_word_id")

    # Rename the table back
    op.rename_table("translations", "glosses")

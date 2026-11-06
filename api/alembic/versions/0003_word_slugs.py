"""add words.slug column + backfill + unique index

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06

Adds a human-readable, URL-safe slug to every word so word URLs become
/words/mlima instead of /words/8f3a2b1c-....

The slug is derived from the headword:
  - lowercase
  - non-[a-z'] characters replaced with spaces, then collapsed to hyphens
  - leading/trailing hyphens stripped

Collisions are resolved by appending -2, -3, ... (mlima, mlima-2, mlima-3).

The UUID primary key is unchanged — slug is a secondary lookup field,
kept NOT NULL + UNIQUE + indexed for fast resolution and SEO-friendly URLs.

Backward compatibility: GET /api/words/{slug_or_id} accepts either form.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add nullable column first so the backfill can write rows
    #    without violating NOT NULL on existing rows.
    op.add_column("words", sa.Column("slug", sa.Text, nullable=True))

    # 2. Backfill: derive slug from headword.
    #    - LOWER(headword)
    #    - Replace anything that isn't a-z or apostrophe with a space
    #    - Collapse runs of whitespace into a single hyphen
    #    - Strip leading/trailing hyphens
    op.execute(r"""
        UPDATE words
        SET slug = BTRIM(REGEXP_REPLACE(
                   REGEXP_REPLACE(LOWER(headword), '[^a-z''-]', ' ', 'g'),
                   '\s+', '-', 'g'
                 ), '-')
        WHERE slug IS NULL
    """)

    # 3. Handle empty slugs (headwords with no [a-z] chars) — fall back to 'word-<id>'
    #    so the NOT NULL constraint can be applied cleanly.
    op.execute("""
        UPDATE words
        SET slug = 'word-' || id::text
        WHERE slug = '' OR slug IS NULL
    """)

    # 4. De-collide: for each set of duplicates, the oldest row keeps the base slug
    #    and the rest get -2, -3, ... appended.
    op.execute("""
        WITH ranked AS (
            SELECT id, slug,
                   ROW_NUMBER() OVER (PARTITION BY slug ORDER BY created_at, id) AS rn
            FROM words
            WHERE slug IS NOT NULL
        )
        UPDATE words w
        SET slug = CASE
            WHEN r.rn = 1 THEN w.slug
            ELSE w.slug || '-' || (r.rn)::text
        END
        FROM ranked r
        WHERE w.id = r.id AND r.rn > 1
    """)

    # 5. Make NOT NULL + unique + secondary index
    op.alter_column("words", "slug", nullable=False)
    op.create_index("uq_words_slug", "words", ["slug"], unique=True)
    op.create_index("ix_words_slug", "words", ["slug"])


def downgrade() -> None:
    op.drop_index("ix_words_slug", table_name="words")
    op.drop_index("uq_words_slug", table_name="words")
    op.drop_column("words", "slug")

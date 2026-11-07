"""add senses table with strict scoping for glosses + examples

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-06

A sense is a distinct meaning of a word. Words can have multiple senses
(polysemy) — e.g. "mlima" can mean "mountain" (sense 1) or "pile/heap"
(sense 2). Each sense has its own glosses and examples.

This migration:
  1. Creates the senses table.
  2. Adds sense_id (nullable) to glosses and examples for strict scoping.
  3. Backfills: for every existing word, creates one default Sense
     (order_index=1) and points all existing glosses and examples at it.
  4. (Does NOT make sense_id NOT NULL yet — that comes in a later
     migration once the frontend is fully migrated. This way the API
     can serve both old and new clients.)

Strict scoping means:
  - Each gloss belongs to exactly one sense.
  - Each example belongs to exactly one sense.
  - An example cannot span multiple senses (no join table).

The frontend should render a word's senses as separate numbered sections,
each with its own glosses and examples. The top-level WordDetail.glosses
and WordDetail.examples fields remain (they're the union of all senses'
glosses/examples) for backward compatibility.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create senses table ───────────────────────────────
    op.create_table(
        "senses",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("word_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("words.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_index", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("part_of_speech", sa.Text, nullable=True),
        sa.Column("definition", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.UniqueConstraint("word_id", "order_index", name="uq_senses_word_order"),
    )
    op.create_index("ix_senses_word", "senses", ["word_id"])

    # ── 2. Add sense_id to glosses and examples (nullable for now) ──
    op.add_column("glosses", sa.Column("sense_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("senses.id", ondelete="CASCADE"), nullable=True))
    op.add_column("examples", sa.Column("sense_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("senses.id", ondelete="CASCADE"), nullable=True))
    op.create_index("ix_glosses_sense", "glosses", ["sense_id"])
    op.create_index("ix_examples_sense", "examples", ["sense_id"])

    # ── 3. Backfill: create one default Sense per word ────────
    #    Then point all existing glosses and examples at it.
    op.execute("""
        INSERT INTO senses (id, word_id, order_index, definition, notes, created_at)
        SELECT
            gen_random_uuid(),
            w.id,
            1,
            NULL,
            'Default sense (auto-created from pre-senses data)',
            now()
        FROM words w
    """)

    # ── 4. Update glosses.sense_id to point at the default sense ──
    op.execute("""
        UPDATE glosses g
        SET sense_id = s.id
        FROM senses s
        WHERE s.word_id = g.word_id
          AND s.order_index = 1
          AND g.sense_id IS NULL
    """)

    # ── 5. Update examples.sense_id to point at the default sense ──
    op.execute("""
        UPDATE examples e
        SET sense_id = s.id
        FROM senses s
        WHERE s.word_id = e.word_id
          AND s.order_index = 1
          AND e.sense_id IS NULL
    """)


def downgrade() -> None:
    # Drop the sense_id columns and indexes from glosses + examples
    op.drop_index("ix_examples_sense", table_name="examples")
    op.drop_column("examples", "sense_id")
    op.drop_index("ix_glosses_sense", table_name="glosses")
    op.drop_column("glosses", "sense_id")

    # Drop the senses table (this cascades to any future sense-scoped rows,
    # but since we never made sense_id NOT NULL, glosses/examples survive)
    op.drop_index("ix_senses_word", table_name="senses")
    op.drop_table("senses")

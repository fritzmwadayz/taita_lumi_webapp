"""split word_relations into word_variations + word_relationships

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-06

Splits the single word_relations table into two purpose-specific tables:

  word_variations    — bidirectional, definitional
    (variant, plural, singular, conjugation, diminutive, augmentative)
    Examples: mlima/milima (singular/plural), kuja/anakuja (lemma/conjugation)
    These represent forms of the SAME lemma. Always symmetric.

  word_relationships — typed, may be directional, contextual
    (antonym, synonym, derived, see_also, etymological)
    Examples: kuja/enda (antonyms — different verbs that happen to be opposites)
    These connect DIFFERENT lemmas. May be bidirectional (antonym, synonym)
    or directional (derived, etymological).

The split matches standard Bantu lexicographic practice (TUKI/Kamusi):
  - Variations are part of what a word IS (its paradigm).
  - Relationships are about how a word relates to OTHER words.

Migration of existing data:
  - relation_type IN ('variant', 'plural', 'singular', 'conjugation',
                      'diminutive', 'augmentative')
    → moved to word_variations (variation_type = relation_type)
  - relation_type IN ('antonym', 'synonym', 'derived', 'see_also',
                      'etymological')
    → moved to word_relationships (relationship_type = relation_type)
      direction defaults to 'bidirectional' for antonym/synonym/see_also,
      'forward' for derived/etymological

The old word_relations table is dropped at the end.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Variation types: always bidirectional, definitional (forms of the same lemma)
VARIATION_TYPES = {
    "variant", "plural", "singular", "conjugation",
    "diminutive", "augmentative",
}

# Relationship types: typed, may be directional, contextual (different lemmas)
# Mapped to their default direction on insert.
SYMMETRIC_RELATIONSHIPS = {"antonym", "synonym", "see_also"}
DIRECTIONAL_RELATIONSHIPS = {"derived", "etymological"}
RELATIONSHIP_TYPES = SYMMETRIC_RELATIONSHIPS | DIRECTIONAL_RELATIONSHIPS


def upgrade() -> None:
    # ── 1. Create word_variations ────────────────────────────
    op.create_table(
        "word_variations",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("word_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("words.id", ondelete="CASCADE"), nullable=False),
        sa.Column("other_word_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("words.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variation_type", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("word_id <> other_word_id", name="ck_word_variations_no_self"),
    )
    op.create_index("ix_word_variations_word", "word_variations", ["word_id"])
    op.create_index("ix_word_variations_other", "word_variations", ["other_word_id"])
    op.create_index("ix_word_variations_type", "word_variations", ["variation_type"])
    # Unique pair: prevent duplicate (A, B, type) AND (B, A, type) — use LEAST/GREATEST
    op.execute("""
        CREATE UNIQUE INDEX uq_word_variations_pair ON word_variations (
            LEAST(word_id, other_word_id),
            GREATEST(word_id, other_word_id),
            variation_type
        )
    """)

    # ── 2. Create word_relationships ─────────────────────────
    op.create_table(
        "word_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("word_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("words.id", ondelete="CASCADE"), nullable=False),
        sa.Column("other_word_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("words.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.Text, nullable=False),
        sa.Column("direction", sa.Text, nullable=False,
                  server_default=sa.text("'bidirectional'")),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("word_id <> other_word_id", name="ck_word_relationships_no_self"),
        sa.CheckConstraint(
            "direction IN ('bidirectional', 'forward', 'reverse')",
            name="ck_word_relationships_direction",
        ),
    )
    op.create_index("ix_word_relationships_word", "word_relationships", ["word_id"])
    op.create_index("ix_word_relationships_other", "word_relationships", ["other_word_id"])
    op.create_index("ix_word_relationships_type", "word_relationships", ["relationship_type"])

    # ── 3. Migrate existing data from word_relations ─────────
    # Variations: variant, plural, singular, conjugation, diminutive, augmentative
    op.execute(f"""
        INSERT INTO word_variations (id, word_id, other_word_id, variation_type, created_at)
        SELECT id, from_word_id, to_word_id, relation_type, created_at
        FROM word_relations
        WHERE relation_type IN ({",".join(f"'{t}'" for t in VARIATION_TYPES)})
    """)

    # Relationships: antonym, synonym, see_also (symmetric → bidirectional)
    op.execute(f"""
        INSERT INTO word_relationships (id, word_id, other_word_id, relationship_type, direction, created_at)
        SELECT id, from_word_id, to_word_id, relation_type, 'bidirectional', created_at
        FROM word_relations
        WHERE relation_type IN ({",".join(f"'{t}'" for t in SYMMETRIC_RELATIONSHIPS)})
    """)

    # Relationships: derived, etymological (directional → forward)
    op.execute(f"""
        INSERT INTO word_relationships (id, word_id, other_word_id, relationship_type, direction, created_at)
        SELECT id, from_word_id, to_word_id, relation_type, 'forward', created_at
        FROM word_relations
        WHERE relation_type IN ({",".join(f"'{t}'" for t in DIRECTIONAL_RELATIONSHIPS)})
    """)

    # ── 4. Drop the old word_relations table ─────────────────
    op.drop_index("ix_word_relations_from", table_name="word_relations")
    op.drop_index("ix_word_relations_to", table_name="word_relations")
    op.drop_index("ix_word_relations_type", table_name="word_relations")
    op.drop_table("word_relations")


def downgrade() -> None:
    # ── Recreate word_relations ──────────────────────────────
    op.create_table(
        "word_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("from_word_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("words.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_word_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("words.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation_type", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_word_relations_from", "word_relations", ["from_word_id"])
    op.create_index("ix_word_relations_to", "word_relations", ["to_word_id"])
    op.create_index("ix_word_relations_type", "word_relations", ["relation_type"])

    # Migrate data back from word_variations
    op.execute("""
        INSERT INTO word_relations (id, from_word_id, to_word_id, relation_type, created_at)
        SELECT id, word_id, other_word_id, variation_type, created_at
        FROM word_variations
    """)

    # Migrate data back from word_relationships
    op.execute("""
        INSERT INTO word_relations (id, from_word_id, to_word_id, relation_type, created_at)
        SELECT id, word_id, other_word_id, relationship_type, created_at
        FROM word_relationships
    """)

    # ── Drop the new tables ──────────────────────────────────
    op.execute("DROP INDEX IF EXISTS uq_word_variations_pair")
    op.drop_index("ix_word_variations_type", table_name="word_variations")
    op.drop_index("ix_word_variations_other", table_name="word_variations")
    op.drop_index("ix_word_variations_word", table_name="word_variations")
    op.drop_table("word_variations")

    op.drop_index("ix_word_relationships_type", table_name="word_relationships")
    op.drop_index("ix_word_relationships_other", table_name="word_relationships")
    op.drop_index("ix_word_relationships_word", table_name="word_relationships")
    op.drop_table("word_relationships")

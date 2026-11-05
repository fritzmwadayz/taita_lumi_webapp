"""rename contributor role to reviewer, add user role, change default

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05

Changes:
  - Existing users with role='contributor' → role='reviewer'
  - Column default changes from 'contributor' to 'user'
  - New signups will be role='user' (registered, non-reviewer)
  - Admins can promote users to 'reviewer' or 'admin'

Permission model after this migration:
  - anon (no account): suggest 5/hr, cannot vote
  - user (registered): suggest 15/hr, can vote
  - reviewer: suggest unlimited, can vote, can add words directly
  - admin: everything + admin panel
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Rename existing contributor → reviewer ───────────────
    op.execute("UPDATE users SET role = 'reviewer' WHERE role = 'contributor'")

    # ── Change column default ────────────────────────────────
    op.alter_column(
        "users",
        "role",
        server_default=sa.text("'user'"),
    )


def downgrade() -> None:
    # Revert: reviewer → contributor, default back to 'contributor'
    op.alter_column(
        "users",
        "role",
        server_default=sa.text("'contributor'"),
    )
    op.execute("UPDATE users SET role = 'contributor' WHERE role = 'reviewer'")
    # Note: users with role='user' stay as 'user' on downgrade —
    # they'd need manual cleanup if you really want to go back.

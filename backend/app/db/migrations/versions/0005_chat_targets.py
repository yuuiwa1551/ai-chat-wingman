from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005_chat_targets"
down_revision = "0004_style_test"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_targets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("relationship", sa.String(), nullable=True),
        sa.Column("style_summary", sa.Text(), nullable=True),
        sa.Column("preferences", sa.Text(), nullable=True),
        sa.Column("taboos", sa.Text(), nullable=True),
        sa.Column("strategy_guideline", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.add_column("chat_sessions", sa.Column("target_id", sa.Integer(), nullable=True))
    op.add_column("conversations", sa.Column("target_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "target_id")
    op.drop_column("chat_sessions", "target_id")
    op.drop_table("chat_targets")
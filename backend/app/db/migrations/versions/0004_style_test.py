from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_style_test"
down_revision = "0003_reply_generation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "style_test_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("scenario", sa.Text(), nullable=False),
        sa.Column("simulated_target_profile", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_table(
        "style_test_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["style_test_sessions.id"]),
    )


def downgrade() -> None:
    op.drop_table("style_test_messages")
    op.drop_table("style_test_sessions")
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_reply_generation"
down_revision = "0002_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("target_name", sa.String(), nullable=True),
        sa.Column("target_strategy", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_session_id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("llm_call_id", sa.Integer(), nullable=True),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("target_name", sa.String(), nullable=True),
        sa.Column("target_strategy", sa.Text(), nullable=True),
        sa.Column("reply_goal", sa.String(), nullable=False),
        sa.Column("tone", sa.String(), nullable=False),
        sa.Column("length", sa.String(), nullable=False),
        sa.Column("proactivity", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=False),
        sa.Column("generated_replies", sa.Text(), nullable=True),
        sa.Column("selected_reply", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("conversations")
    op.drop_table("chat_sessions")
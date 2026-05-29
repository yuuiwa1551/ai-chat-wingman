from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0006_memories"
down_revision = "0005_chat_targets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("memory_type", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("source_conversation_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_index("ix_memories_target_status", "memories", ["target_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_memories_target_status", table_name="memories")
    op.drop_table("memories")

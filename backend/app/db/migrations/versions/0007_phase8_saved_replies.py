from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007_phase8_saved_replies"
down_revision = "0006_memories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_replies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("candidate_index", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("saved_replies")

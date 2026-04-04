"""add roadmap chat threads table

Revision ID: 20260402_roadmap_chat_threads
Revises: 20260331_user_feedbacks, 20260331_roadmap_public
Create Date: 2026-04-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260402_roadmap_chat_threads"
down_revision: Union[str, Sequence[str], None] = (
    "20260331_user_feedbacks",
    "20260331_roadmap_public",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移。"""

    op.create_table(
        "roadmap_chat_threads",
        sa.Column("thread_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("roadmap_id", sa.String(length=255), nullable=False),
        sa.Column("stage_id", sa.String(length=255), nullable=True),
        sa.Column("task_id", sa.String(length=255), nullable=True),
        sa.Column("concept_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=255), nullable=False, server_default="deer_flow"),
        sa.Column("assistant_id", sa.String(length=255), nullable=True),
        sa.Column("model_id", sa.String(length=255), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_message_preview", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_message_at", sa.DateTime(timezone=False), nullable=True),
        sa.PrimaryKeyConstraint("thread_id"),
    )
    op.create_index(
        "ix_roadmap_chat_threads_user_id",
        "roadmap_chat_threads",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_roadmap_chat_threads_roadmap_id",
        "roadmap_chat_threads",
        ["roadmap_id"],
        unique=False,
    )
    op.create_index(
        "ix_roadmap_chat_threads_stage_id",
        "roadmap_chat_threads",
        ["stage_id"],
        unique=False,
    )
    op.create_index(
        "ix_roadmap_chat_threads_task_id",
        "roadmap_chat_threads",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "ix_roadmap_chat_threads_concept_id",
        "roadmap_chat_threads",
        ["concept_id"],
        unique=False,
    )
    op.create_index(
        "ix_roadmap_chat_threads_source",
        "roadmap_chat_threads",
        ["source"],
        unique=False,
    )
    op.create_index(
        "idx_roadmap_chat_threads_user_roadmap_updated",
        "roadmap_chat_threads",
        ["user_id", "roadmap_id", "updated_at"],
        unique=False,
    )
    op.create_index(
        "idx_roadmap_chat_threads_user_concept_updated",
        "roadmap_chat_threads",
        ["user_id", "concept_id", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    """回滚迁移。"""

    op.drop_index(
        "idx_roadmap_chat_threads_user_concept_updated",
        table_name="roadmap_chat_threads",
    )
    op.drop_index(
        "idx_roadmap_chat_threads_user_roadmap_updated",
        table_name="roadmap_chat_threads",
    )
    op.drop_index("ix_roadmap_chat_threads_source", table_name="roadmap_chat_threads")
    op.drop_index("ix_roadmap_chat_threads_concept_id", table_name="roadmap_chat_threads")
    op.drop_index("ix_roadmap_chat_threads_task_id", table_name="roadmap_chat_threads")
    op.drop_index("ix_roadmap_chat_threads_stage_id", table_name="roadmap_chat_threads")
    op.drop_index("ix_roadmap_chat_threads_roadmap_id", table_name="roadmap_chat_threads")
    op.drop_index("ix_roadmap_chat_threads_user_id", table_name="roadmap_chat_threads")
    op.drop_table("roadmap_chat_threads")

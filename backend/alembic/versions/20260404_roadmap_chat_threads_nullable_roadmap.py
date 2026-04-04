"""roadmap_chat_threads roadmap_id nullable for DeerFlow standalone

Revision ID: 20260404_rmap_thread_null
Revises: 20260402_roadmap_chat_threads
Create Date: 2026-04-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260404_rmap_thread_null"
down_revision: Union[str, Sequence[str], None] = "20260402_roadmap_chat_threads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """允许 roadmap_id 为空，以区分独立 DeerFlow 实验室线程。"""

    op.alter_column(
        "roadmap_chat_threads",
        "roadmap_id",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    """恢复为非空（独立线程需先清理）。"""

    op.alter_column(
        "roadmap_chat_threads",
        "roadmap_id",
        existing_type=sa.String(length=255),
        nullable=False,
    )

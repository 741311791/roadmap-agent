"""add_home_perf_indexes

Revision ID: 20260315_home_perf_idx
Revises: a1b2c3d4e5f6
Create Date: 2026-03-15 23:30:00.000000

为 /home、/roadmaps、/tasks 相关高频查询补充索引：
1. roadmap_tasks(user_id, created_at)
2. roadmap_tasks(user_id, status, created_at)
3. roadmap_tasks(task_type, status, created_at)
4. roadmap_metadata(user_id, deleted_at, created_at)
5. concept_progress(user_id, roadmap_id, is_completed)
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260315_home_perf_idx"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加首页与列表查询相关索引。"""
    op.create_index(
        "idx_roadmap_tasks_user_created_at",
        "roadmap_tasks",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_roadmap_tasks_user_status_created_at",
        "roadmap_tasks",
        ["user_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_roadmap_tasks_creation_pending_created_at",
        "roadmap_tasks",
        ["task_type", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_roadmap_metadata_user_deleted_created_at",
        "roadmap_metadata",
        ["user_id", "deleted_at", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_concept_progress_user_roadmap_completed",
        "concept_progress",
        ["user_id", "roadmap_id", "is_completed"],
        unique=False,
    )


def downgrade() -> None:
    """回滚首页与列表查询相关索引。"""
    op.drop_index("idx_concept_progress_user_roadmap_completed", table_name="concept_progress")
    op.drop_index("idx_roadmap_metadata_user_deleted_created_at", table_name="roadmap_metadata")
    op.drop_index("idx_roadmap_tasks_creation_pending_created_at", table_name="roadmap_tasks")
    op.drop_index("idx_roadmap_tasks_user_status_created_at", table_name="roadmap_tasks")
    op.drop_index("idx_roadmap_tasks_user_created_at", table_name="roadmap_tasks")

"""add celery_task_id to roadmap_tasks

Revision ID: c7e9f8b1a2d3
Revises: add_waitlist_invite_fields
Create Date: 2025-12-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7e9f8b1a2d3'
down_revision = 'add_waitlist_invite_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    添加 celery_task_id 字段到 roadmap_tasks 表
    
    用于记录内容生成任务的 Celery task ID，
    以便后续查询任务状态或取消任务。
    """
    # 添加 celery_task_id 字段
    op.add_column(
        'roadmap_tasks',
        sa.Column(
            'celery_task_id',
            sa.String(),
            nullable=True,
            comment='Celery 任务 ID，用于查询内容生成任务状态或取消任务'
        )
    )


def downgrade() -> None:
    """
    回滚：删除 celery_task_id 字段
    """
    op.drop_column('roadmap_tasks', 'celery_task_id')


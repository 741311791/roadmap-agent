"""add_content_generation_tracking_to_task

Revision ID: 2db1e86f6eee
Revises: 6df605025673
Create Date: 2026-01-26 22:59:10.203488

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2db1e86f6eee'
down_revision: Union[str, None] = '6df605025673'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    添加内容生成追踪字段到 roadmap_tasks 表
    
    新增字段：
    - content_generation_celery_id: 内容生成 Celery 任务 ID
    - content_generation_status: 内容生成状态（pending | processing | completed | partial_failure | failed）
    """
    # 添加 content_generation_celery_id 字段
    op.add_column(
        'roadmap_tasks',
        sa.Column(
            'content_generation_celery_id',
            sa.String(length=255),
            nullable=True,
            comment='内容生成 Celery 任务 ID'
        )
    )
    
    # 添加 content_generation_status 字段
    op.add_column(
        'roadmap_tasks',
        sa.Column(
            'content_generation_status',
            sa.String(length=50),
            nullable=False,
            server_default='pending',
            comment='内容生成状态: pending | processing | completed | partial_failure | failed'
        )
    )
    
    # 添加索引以提升查询性能
    op.create_index(
        'ix_roadmap_tasks_content_generation_status',
        'roadmap_tasks',
        ['content_generation_status'],
    )


def downgrade() -> None:
    """回滚迁移"""
    # 删除索引
    op.drop_index('ix_roadmap_tasks_content_generation_status', table_name='roadmap_tasks')
    
    # 删除字段
    op.drop_column('roadmap_tasks', 'content_generation_status')
    op.drop_column('roadmap_tasks', 'content_generation_celery_id')


"""phase3_add_composite_indexes_for_performance

Revision ID: phase3_composite_idx
Revises: 28dd152748bd
Create Date: 2025-01-05 14:00:00.000000

添加复合索引以优化常见查询模式：
1. roadmap_tasks: (roadmap_id, status) - 查询活跃任务
2. tutorial_metadata: (roadmap_id, concept_id, is_latest) - 查询最新教程
3. resource_recommendation_metadata: (roadmap_id, concept_id) - 查询资源推荐
4. quiz_metadata: (roadmap_id, concept_id) - 查询测验
5. execution_logs: (trace_id, level, created_at) - 查询日志（按级别）
6. execution_logs: (trace_id, category, created_at) - 查询日志（按分类）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'phase3_composite_idx'
down_revision: Union[str, None] = '28dd152748bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    添加复合索引以优化查询性能
    
    使用 CONCURRENTLY 选项避免锁表（PostgreSQL）
    如果是其他数据库，需要移除 postgresql_concurrently 参数
    """
    
    # 1. roadmap_tasks: (roadmap_id, status)
    # 优化查询：根据 roadmap_id 和 status 查询活跃任务
    op.create_index(
        'idx_roadmap_tasks_roadmap_status',
        'roadmap_tasks',
        ['roadmap_id', 'status'],
        unique=False,
    )
    
    # 2. tutorial_metadata: (roadmap_id, concept_id, is_latest)
    # 优化查询：根据 roadmap_id 和 concept_id 查询最新教程版本
    op.create_index(
        'idx_tutorial_metadata_roadmap_concept_latest',
        'tutorial_metadata',
        ['roadmap_id', 'concept_id', 'is_latest'],
        unique=False,
    )
    
    # 3. resource_recommendation_metadata: (roadmap_id, concept_id)
    # 优化查询：根据 roadmap_id 和 concept_id 查询资源推荐
    op.create_index(
        'idx_resource_recommendation_roadmap_concept',
        'resource_recommendation_metadata',
        ['roadmap_id', 'concept_id'],
        unique=False,
    )
    
    # 4. quiz_metadata: (roadmap_id, concept_id)
    # 优化查询：根据 roadmap_id 和 concept_id 查询测验
    op.create_index(
        'idx_quiz_metadata_roadmap_concept',
        'quiz_metadata',
        ['roadmap_id', 'concept_id'],
        unique=False,
    )
    
    # 5. execution_logs: (trace_id, level, created_at DESC)
    # 优化查询：根据 trace_id 和 level 查询日志，按时间倒序
    op.create_index(
        'idx_execution_logs_trace_level_created',
        'execution_logs',
        ['trace_id', 'level', sa.desc('created_at')],
        unique=False,
    )
    
    # 6. execution_logs: (trace_id, category, created_at DESC)
    # 优化查询：根据 trace_id 和 category 查询日志，按时间倒序
    op.create_index(
        'idx_execution_logs_trace_category_created',
        'execution_logs',
        ['trace_id', 'category', sa.desc('created_at')],
        unique=False,
    )


def downgrade() -> None:
    """
    删除所有添加的复合索引
    """
    
    # 按照创建的相反顺序删除索引
    op.drop_index('idx_execution_logs_trace_category_created', table_name='execution_logs')
    op.drop_index('idx_execution_logs_trace_level_created', table_name='execution_logs')
    op.drop_index('idx_quiz_metadata_roadmap_concept', table_name='quiz_metadata')
    op.drop_index('idx_resource_recommendation_roadmap_concept', table_name='resource_recommendation_metadata')
    op.drop_index('idx_tutorial_metadata_roadmap_concept_latest', table_name='tutorial_metadata')
    op.drop_index('idx_roadmap_tasks_roadmap_status', table_name='roadmap_tasks')

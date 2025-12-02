"""Add composite unique constraint for concept uniqueness

Revision ID: add_concept_uniqueness_constraint
Revises: add_task_execution_fields
Create Date: 2024-12-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_concept_uniqueness_constraint'
down_revision: Union[str, None] = 'add_task_execution_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add composite unique constraint and index for tutorial_metadata"""
    
    # 添加复合唯一约束：roadmap_id + concept_id + content_version
    # 这确保同一个 concept 在同一个 roadmap 中的同一版本只有一条记录
    op.create_unique_constraint(
        'uq_tutorial_roadmap_concept_version',
        'tutorial_metadata',
        ['roadmap_id', 'concept_id', 'content_version']
    )
    
    # 添加复合索引：roadmap_id + concept_id + is_latest
    # 用于快速查询某个 concept 的最新教程
    op.create_index(
        'ix_tutorial_roadmap_concept_latest',
        'tutorial_metadata',
        ['roadmap_id', 'concept_id', 'is_latest']
    )
    
    # 对 resource_recommendation_metadata 表添加类似约束
    op.create_unique_constraint(
        'uq_resource_roadmap_concept',
        'resource_recommendation_metadata',
        ['roadmap_id', 'concept_id']
    )
    
    # 对 quiz_metadata 表添加类似约束
    op.create_unique_constraint(
        'uq_quiz_roadmap_concept',
        'quiz_metadata',
        ['roadmap_id', 'concept_id']
    )


def downgrade() -> None:
    """Remove composite unique constraint and index"""
    
    # 删除 quiz_metadata 约束
    op.drop_constraint('uq_quiz_roadmap_concept', 'quiz_metadata', type_='unique')
    
    # 删除 resource_recommendation_metadata 约束
    op.drop_constraint('uq_resource_roadmap_concept', 'resource_recommendation_metadata', type_='unique')
    
    # 删除 tutorial_metadata 索引和约束
    op.drop_index('ix_tutorial_roadmap_concept_latest', 'tutorial_metadata')
    op.drop_constraint('uq_tutorial_roadmap_concept_version', 'tutorial_metadata', type_='unique')


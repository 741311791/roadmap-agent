"""add_agent_metadata_tables

添加新 Agent 的元数据表：
- intent_analysis_metadata: A1 需求分析师产出
- resource_recommendation_metadata: A5 资源推荐师产出
- quiz_metadata: A6 测验生成器产出

Revision ID: add_agent_metadata_001
Revises: 773c5c76a4c1
Create Date: 2025-11-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_agent_metadata_001'
down_revision: Union[str, None] = '773c5c76a4c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 intent_analysis_metadata 表（A1: 需求分析师产出）
    op.create_table(
        'intent_analysis_metadata',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('parsed_goal', sa.Text(), nullable=False),
        sa.Column('key_technologies', sa.JSON(), nullable=False),
        sa.Column('difficulty_profile', sa.Text(), nullable=False),
        sa.Column('time_constraint', sa.Text(), nullable=False),
        sa.Column('recommended_focus', sa.JSON(), nullable=False),
        sa.Column('full_analysis_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['roadmap_tasks.task_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_intent_analysis_metadata_task_id'),
        'intent_analysis_metadata',
        ['task_id'],
        unique=False
    )

    # 创建 resource_recommendation_metadata 表（A5: 资源推荐师产出）
    op.create_table(
        'resource_recommendation_metadata',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('concept_id', sa.String(), nullable=False),
        sa.Column('roadmap_id', sa.String(), nullable=False),
        sa.Column('resources', sa.JSON(), nullable=False),
        sa.Column('resources_count', sa.Integer(), nullable=False, default=0),
        sa.Column('search_queries_used', sa.JSON(), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['roadmap_id'], ['roadmap_metadata.roadmap_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_resource_recommendation_metadata_concept_id'),
        'resource_recommendation_metadata',
        ['concept_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_resource_recommendation_metadata_roadmap_id'),
        'resource_recommendation_metadata',
        ['roadmap_id'],
        unique=False
    )

    # 创建 quiz_metadata 表（A6: 测验生成器产出）
    op.create_table(
        'quiz_metadata',
        sa.Column('quiz_id', sa.String(), nullable=False),
        sa.Column('concept_id', sa.String(), nullable=False),
        sa.Column('roadmap_id', sa.String(), nullable=False),
        sa.Column('questions', sa.JSON(), nullable=False),
        sa.Column('total_questions', sa.Integer(), nullable=False, default=0),
        sa.Column('easy_count', sa.Integer(), nullable=False, default=0),
        sa.Column('medium_count', sa.Integer(), nullable=False, default=0),
        sa.Column('hard_count', sa.Integer(), nullable=False, default=0),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['roadmap_id'], ['roadmap_metadata.roadmap_id'], ),
        sa.PrimaryKeyConstraint('quiz_id')
    )
    op.create_index(
        op.f('ix_quiz_metadata_concept_id'),
        'quiz_metadata',
        ['concept_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_quiz_metadata_roadmap_id'),
        'quiz_metadata',
        ['roadmap_id'],
        unique=False
    )


def downgrade() -> None:
    # 删除 quiz_metadata 表
    op.drop_index(op.f('ix_quiz_metadata_roadmap_id'), table_name='quiz_metadata')
    op.drop_index(op.f('ix_quiz_metadata_concept_id'), table_name='quiz_metadata')
    op.drop_table('quiz_metadata')

    # 删除 resource_recommendation_metadata 表
    op.drop_index(
        op.f('ix_resource_recommendation_metadata_roadmap_id'),
        table_name='resource_recommendation_metadata'
    )
    op.drop_index(
        op.f('ix_resource_recommendation_metadata_concept_id'),
        table_name='resource_recommendation_metadata'
    )
    op.drop_table('resource_recommendation_metadata')

    # 删除 intent_analysis_metadata 表
    op.drop_index(
        op.f('ix_intent_analysis_metadata_task_id'),
        table_name='intent_analysis_metadata'
    )
    op.drop_table('intent_analysis_metadata')


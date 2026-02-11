"""fix_timestamps_consistency

修复内容：
1. 统一时间戳字段命名：将 generated_at 改为 created_at
2. 为缺失的表添加 updated_at 字段

Revision ID: fix_roadmap_id_timestamps
Revises: add_cover_image_and_tavily_tables
Create Date: 2026-01-14

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = 'fix_roadmap_id_timestamps'
down_revision: Union[str, None] = '354c6fbf7a16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """升级数据库Schema"""
    
    # ============================================================
    # 第一部分：统一时间戳字段命名（generated_at -> created_at）
    # ============================================================
    
    # TutorialMetadata: generated_at -> created_at
    op.alter_column(
        'tutorial_metadata',
        'generated_at',
        new_column_name='created_at',
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
    )
    
    # ResourceRecommendationMetadata: generated_at -> created_at
    op.alter_column(
        'resource_recommendation_metadata',
        'generated_at',
        new_column_name='created_at',
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
    )
    
    # QuizMetadata: generated_at -> created_at
    op.alter_column(
        'quiz_metadata',
        'generated_at',
        new_column_name='created_at',
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
    )
    
    # TechStackAssessment: generated_at -> created_at
    op.alter_column(
        'tech_stack_assessments',
        'generated_at',
        new_column_name='created_at',
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
    )
    
    # ============================================================
    # 第二部分：添加缺失的 updated_at 字段
    # ============================================================
    
    # RoadmapMetadata
    op.add_column(
        'roadmap_metadata',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP')
        )
    )
    
    # TutorialMetadata
    op.add_column(
        'tutorial_metadata',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP')
        )
    )
    
    # IntentAnalysisMetadata
    op.add_column(
        'intent_analysis_metadata',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP')
        )
    )
    
    # ResourceRecommendationMetadata
    op.add_column(
        'resource_recommendation_metadata',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP')
        )
    )
    
    # QuizMetadata
    op.add_column(
        'quiz_metadata',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP')
        )
    )
    
    # TechStackAssessment
    op.add_column(
        'tech_stack_assessments',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP')
        )
    )


def downgrade():
    """回滚数据库Schema"""
    
    # ============================================================
    # 回滚第二部分：移除 updated_at 字段
    # ============================================================
    
    op.drop_column('roadmap_metadata', 'updated_at')
    op.drop_column('tutorial_metadata', 'updated_at')
    op.drop_column('intent_analysis_metadata', 'updated_at')
    op.drop_column('resource_recommendation_metadata', 'updated_at')
    op.drop_column('quiz_metadata', 'updated_at')
    op.drop_column('tech_stack_assessments', 'updated_at')
    
    # ============================================================
    # 回滚第一部分：恢复 generated_at 字段名
    # ============================================================
    
    op.alter_column(
        'tutorial_metadata',
        'created_at',
        new_column_name='generated_at',
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
    )
    
    op.alter_column(
        'resource_recommendation_metadata',
        'created_at',
        new_column_name='generated_at',
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
    )
    
    op.alter_column(
        'quiz_metadata',
        'created_at',
        new_column_name='generated_at',
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
    )
    
    op.alter_column(
        'tech_stack_assessments',
        'created_at',
        new_column_name='generated_at',
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
    )


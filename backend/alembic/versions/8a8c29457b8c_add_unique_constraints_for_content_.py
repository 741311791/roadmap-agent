"""add_unique_constraints_for_content_metadata

Revision ID: 8a8c29457b8c
Revises: add_retry_count_cover
Create Date: 2026-01-13 23:44:33.210704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a8c29457b8c'
down_revision: Union[str, None] = 'add_retry_count_cover'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    添加唯一约束以防止重复记录
    
    业务规则：
    - ResourceRecommendationMetadata: (roadmap_id, concept_id) 唯一
    - QuizMetadata: (roadmap_id, concept_id) 唯一
    - TutorialMetadata: (roadmap_id, concept_id, is_latest=true) 唯一
    """
    # 1. 清理可能存在的重复数据（保留最新的）
    op.execute("""
        -- 清理 resource_recommendation_metadata 重复数据
        DELETE FROM resource_recommendation_metadata
        WHERE id IN (
            SELECT id FROM (
                SELECT id, 
                       ROW_NUMBER() OVER (
                           PARTITION BY roadmap_id, concept_id 
                           ORDER BY generated_at DESC
                       ) as rn
                FROM resource_recommendation_metadata
            ) t
            WHERE rn > 1
        );
    """)
    
    op.execute("""
        -- 清理 quiz_metadata 重复数据
        DELETE FROM quiz_metadata
        WHERE quiz_id IN (
            SELECT quiz_id FROM (
                SELECT quiz_id, 
                       ROW_NUMBER() OVER (
                           PARTITION BY roadmap_id, concept_id 
                           ORDER BY generated_at DESC
                       ) as rn
                FROM quiz_metadata
            ) t
            WHERE rn > 1
        );
    """)
    
    # 2. 添加唯一索引
    op.create_index(
        'uix_resource_roadmap_concept',
        'resource_recommendation_metadata',
        ['roadmap_id', 'concept_id'],
        unique=True
    )
    
    op.create_index(
        'uix_quiz_roadmap_concept',
        'quiz_metadata',
        ['roadmap_id', 'concept_id'],
        unique=True
    )
    
    # Tutorial 的唯一约束：只约束 is_latest=true 的记录
    op.execute("""
        CREATE UNIQUE INDEX uix_tutorial_roadmap_concept_latest
        ON tutorial_metadata (roadmap_id, concept_id, is_latest)
        WHERE is_latest = true;
    """)


def downgrade() -> None:
    """
    移除唯一约束
    """
    op.drop_index('uix_resource_roadmap_concept', table_name='resource_recommendation_metadata')
    op.drop_index('uix_quiz_roadmap_concept', table_name='quiz_metadata')
    op.execute('DROP INDEX IF EXISTS uix_tutorial_roadmap_concept_latest;')


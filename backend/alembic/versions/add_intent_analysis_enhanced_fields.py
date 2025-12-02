"""add intent analysis enhanced fields

添加需求分析增强字段到 intent_analysis_metadata 表。

Revision ID: add_intent_enhanced
Revises: add_user_profile
Create Date: 2025-12-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_intent_enhanced'
down_revision: Union[str, None] = 'add_concept_uniqueness_constraint'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加需求分析增强字段"""
    # 添加新字段到 intent_analysis_metadata 表
    op.add_column('intent_analysis_metadata', 
        sa.Column('user_profile_summary', sa.Text(), nullable=True))
    op.add_column('intent_analysis_metadata', 
        sa.Column('skill_gap_analysis', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('intent_analysis_metadata', 
        sa.Column('personalized_suggestions', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('intent_analysis_metadata', 
        sa.Column('estimated_learning_path_type', sa.String(), nullable=True))
    op.add_column('intent_analysis_metadata', 
        sa.Column('content_format_weights', sa.JSON(), nullable=True))


def downgrade() -> None:
    """移除需求分析增强字段"""
    op.drop_column('intent_analysis_metadata', 'content_format_weights')
    op.drop_column('intent_analysis_metadata', 'estimated_learning_path_type')
    op.drop_column('intent_analysis_metadata', 'personalized_suggestions')
    op.drop_column('intent_analysis_metadata', 'skill_gap_analysis')
    op.drop_column('intent_analysis_metadata', 'user_profile_summary')



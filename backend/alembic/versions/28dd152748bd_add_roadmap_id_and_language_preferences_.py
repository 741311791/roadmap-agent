"""add_roadmap_id_and_language_preferences_to_intent_analysis

Revision ID: 28dd152748bd
Revises: add_execution_log_table
Create Date: 2025-12-04 01:06:23.054942

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28dd152748bd'
down_revision: Union[str, None] = 'add_execution_log_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 roadmap_id 字段到 intent_analysis_metadata 表
    op.add_column('intent_analysis_metadata', sa.Column('roadmap_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_intent_analysis_metadata_roadmap_id'), 'intent_analysis_metadata', ['roadmap_id'], unique=False)
    
    # 添加 language_preferences 字段到 intent_analysis_metadata 表
    op.add_column('intent_analysis_metadata', sa.Column('language_preferences', sa.JSON(), nullable=True))


def downgrade() -> None:
    # 删除 language_preferences 字段
    op.drop_column('intent_analysis_metadata', 'language_preferences')
    
    # 删除 roadmap_id 字段及其索引
    op.drop_index(op.f('ix_intent_analysis_metadata_roadmap_id'), table_name='intent_analysis_metadata')
    op.drop_column('intent_analysis_metadata', 'roadmap_id')


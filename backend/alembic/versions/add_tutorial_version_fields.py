"""add tutorial version fields

为 TutorialMetadata 表添加版本管理字段：
- content_version: 版本号，从 1 开始
- is_latest: 是否为最新版本

Revision ID: add_tutorial_version
Revises: add_agent_metadata_001
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_tutorial_version'
down_revision: Union[str, None] = 'add_agent_metadata_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加版本管理字段"""
    # 添加 content_version 字段（默认值为 1）
    op.add_column(
        'tutorial_metadata',
        sa.Column('content_version', sa.Integer(), nullable=False, server_default='1')
    )
    
    # 添加 is_latest 字段（默认值为 True）
    op.add_column(
        'tutorial_metadata',
        sa.Column('is_latest', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # 为 is_latest 创建索引（便于查询最新版本）
    op.create_index(
        'ix_tutorial_metadata_is_latest',
        'tutorial_metadata',
        ['is_latest']
    )
    
    # 创建复合索引：roadmap_id + concept_id + is_latest（便于查询特定概念的最新教程）
    op.create_index(
        'ix_tutorial_metadata_roadmap_concept_latest',
        'tutorial_metadata',
        ['roadmap_id', 'concept_id', 'is_latest']
    )


def downgrade() -> None:
    """移除版本管理字段"""
    # 删除索引
    op.drop_index('ix_tutorial_metadata_roadmap_concept_latest', table_name='tutorial_metadata')
    op.drop_index('ix_tutorial_metadata_is_latest', table_name='tutorial_metadata')
    
    # 删除字段
    op.drop_column('tutorial_metadata', 'is_latest')
    op.drop_column('tutorial_metadata', 'content_version')


"""add user profile table

添加用户画像表 user_profiles，存储用户个人偏好设置。

Revision ID: add_user_profile
Revises: add_tutorial_version
Create Date: 2025-12-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_user_profile'
down_revision: Union[str, None] = 'add_tutorial_version'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 user_profiles 表"""
    op.create_table(
        'user_profiles',
        sa.Column('user_id', sa.String(), nullable=False),
        # 职业背景
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('current_role', sa.String(), nullable=True),
        # 技术栈 (JSON)
        sa.Column('tech_stack', sa.JSON(), nullable=False, server_default='[]'),
        # 语言偏好
        sa.Column('primary_language', sa.String(), nullable=False, server_default='zh'),
        sa.Column('secondary_language', sa.String(), nullable=True),
        # 学习习惯
        sa.Column('weekly_commitment_hours', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('learning_style', sa.JSON(), nullable=False, server_default='[]'),
        # AI 个性化开关
        sa.Column('ai_personalization', sa.Boolean(), nullable=False, server_default='true'),
        # 时间戳
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('user_id')
    )


def downgrade() -> None:
    """删除 user_profiles 表"""
    op.drop_table('user_profiles')


"""add tech stack assessments table

添加技术栈能力测试表 tech_stack_assessments，用于存储每个技术栈在不同能力级别的测验题目。

Revision ID: add_tech_stack_assessments
Revises: add_fastapi_users_fields
Create Date: 2025-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = 'add_tech_stack_assessments'
down_revision: Union[str, None] = 'add_fastapi_users_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 tech_stack_assessments 表"""
    op.create_table(
        'tech_stack_assessments',
        sa.Column('assessment_id', sa.String(), nullable=False),
        sa.Column('technology', sa.String(), nullable=False),
        sa.Column('proficiency_level', sa.String(), nullable=False),
        # 复用quiz_metadata字段
        sa.Column('questions', JSON, nullable=False),
        sa.Column('total_questions', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('easy_count', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('medium_count', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('hard_count', sa.Integer(), nullable=False, server_default='6'),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('assessment_id'),
        # 创建索引
        sa.Index('ix_tech_stack_assessments_technology', 'technology'),
        sa.Index('ix_tech_stack_assessments_proficiency_level', 'proficiency_level'),
        # 唯一约束：每个技术栈+能力级别组合只能有一条记录
        sa.UniqueConstraint('technology', 'proficiency_level', name='uq_tech_proficiency')
    )


def downgrade() -> None:
    """删除 tech_stack_assessments 表"""
    op.drop_table('tech_stack_assessments')


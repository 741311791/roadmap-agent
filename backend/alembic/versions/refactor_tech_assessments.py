"""refactor tech assessments table

重构技术栈能力测试表：
- 删除 easy_count, medium_count, hard_count 字段（题目不再按难度分类）
- 添加 examination_plan 字段（存储考察内容规划）
- 清空现有题库数据（因为题目结构发生变化）

Revision ID: refactor_tech_assessments
Revises: add_tech_stack_capability_analysis
Create Date: 2025-12-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = 'refactor_tech_assessments'
down_revision: Union[str, None] = 'add_tech_stack_assessments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """重构 tech_stack_assessments 表"""
    
    # 清空现有题库数据（因为题目结构发生变化）
    op.execute("DELETE FROM tech_stack_assessments")
    
    # 删除旧的难度统计字段
    op.drop_column('tech_stack_assessments', 'easy_count')
    op.drop_column('tech_stack_assessments', 'medium_count')
    op.drop_column('tech_stack_assessments', 'hard_count')
    
    # 添加考察内容规划字段
    op.add_column(
        'tech_stack_assessments',
        sa.Column('examination_plan', JSON, nullable=True)
    )


def downgrade() -> None:
    """回滚：恢复旧的表结构"""
    
    # 删除新字段
    op.drop_column('tech_stack_assessments', 'examination_plan')
    
    # 恢复旧字段
    op.add_column(
        'tech_stack_assessments',
        sa.Column('easy_count', sa.Integer(), nullable=False, server_default='7')
    )
    op.add_column(
        'tech_stack_assessments',
        sa.Column('medium_count', sa.Integer(), nullable=False, server_default='7')
    )
    op.add_column(
        'tech_stack_assessments',
        sa.Column('hard_count', sa.Integer(), nullable=False, server_default='6')
    )

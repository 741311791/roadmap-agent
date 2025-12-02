"""Add execution_log table for trace tracking

Revision ID: add_execution_log_table
Revises: add_concept_uniqueness_constraint
Create Date: 2024-12-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_execution_log_table'
down_revision: Union[str, None] = 'add_intent_enhanced'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create execution_logs table"""
    op.create_table(
        'execution_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('trace_id', sa.String(), nullable=False),
        sa.Column('roadmap_id', sa.String(), nullable=True),
        sa.Column('concept_id', sa.String(), nullable=True),
        sa.Column('level', sa.String(), nullable=False, server_default='info'),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('step', sa.String(), nullable=True),
        sa.Column('agent_name', sa.String(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 添加索引以支持高效查询
    op.create_index('ix_execution_logs_trace_id', 'execution_logs', ['trace_id'])
    op.create_index('ix_execution_logs_roadmap_id', 'execution_logs', ['roadmap_id'])
    op.create_index('ix_execution_logs_concept_id', 'execution_logs', ['concept_id'])
    op.create_index('ix_execution_logs_level', 'execution_logs', ['level'])
    op.create_index('ix_execution_logs_category', 'execution_logs', ['category'])
    op.create_index('ix_execution_logs_step', 'execution_logs', ['step'])
    op.create_index('ix_execution_logs_agent_name', 'execution_logs', ['agent_name'])
    op.create_index('ix_execution_logs_created_at', 'execution_logs', ['created_at'])
    
    # 复合索引用于常见查询模式
    op.create_index(
        'ix_execution_logs_trace_level',
        'execution_logs',
        ['trace_id', 'level']
    )
    op.create_index(
        'ix_execution_logs_trace_category',
        'execution_logs',
        ['trace_id', 'category']
    )


def downgrade() -> None:
    """Drop execution_logs table"""
    # 删除复合索引
    op.drop_index('ix_execution_logs_trace_category', 'execution_logs')
    op.drop_index('ix_execution_logs_trace_level', 'execution_logs')
    
    # 删除单列索引
    op.drop_index('ix_execution_logs_created_at', 'execution_logs')
    op.drop_index('ix_execution_logs_agent_name', 'execution_logs')
    op.drop_index('ix_execution_logs_step', 'execution_logs')
    op.drop_index('ix_execution_logs_category', 'execution_logs')
    op.drop_index('ix_execution_logs_level', 'execution_logs')
    op.drop_index('ix_execution_logs_concept_id', 'execution_logs')
    op.drop_index('ix_execution_logs_roadmap_id', 'execution_logs')
    op.drop_index('ix_execution_logs_trace_id', 'execution_logs')
    
    # 删除表
    op.drop_table('execution_logs')


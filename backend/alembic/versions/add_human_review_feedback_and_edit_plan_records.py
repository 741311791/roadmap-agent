"""add_human_review_feedback_and_edit_plan_records

Revision ID: 9a8f7b6c5d4e
Revises: 75fa6a3a3135
Create Date: 2025-12-22 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '9a8f7b6c5d4e'
down_revision: Union[str, None] = '75fa6a3a3135'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    添加 human_review_feedbacks 和 edit_plan_records 表
    
    用于记录用户在 human_review 节点的审核反馈以及 EditPlanAnalyzerAgent 生成的修改计划
    """
    # ### 创建 human_review_feedbacks 表 ###
    op.create_table('human_review_feedbacks',
        sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('task_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('roadmap_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('user_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('approved', sa.Boolean(), nullable=False),
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('roadmap_version_snapshot', sa.JSON(), nullable=False),
        sa.Column('review_round', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['roadmap_tasks.task_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_human_review_feedbacks_task_id'), 'human_review_feedbacks', ['task_id'], unique=False)
    op.create_index(op.f('ix_human_review_feedbacks_roadmap_id'), 'human_review_feedbacks', ['roadmap_id'], unique=False)
    op.create_index(op.f('ix_human_review_feedbacks_user_id'), 'human_review_feedbacks', ['user_id'], unique=False)
    op.create_index(op.f('ix_human_review_feedbacks_review_round'), 'human_review_feedbacks', ['review_round'], unique=False)
    
    # ### 创建 edit_plan_records 表 ###
    op.create_table('edit_plan_records',
        sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('task_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('roadmap_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('feedback_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('feedback_summary', sa.Text(), nullable=False),
        sa.Column('scope_analysis', sa.Text(), nullable=False),
        sa.Column('intents', sa.JSON(), nullable=False),
        sa.Column('preservation_requirements', sa.JSON(), nullable=False),
        sa.Column('full_plan_data', sa.JSON(), nullable=False),
        sa.Column('confidence', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('needs_clarification', sa.Boolean(), nullable=False),
        sa.Column('clarification_questions', sa.JSON(), nullable=True),
        sa.Column('execution_status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['roadmap_tasks.task_id'], ),
        sa.ForeignKeyConstraint(['feedback_id'], ['human_review_feedbacks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_edit_plan_records_task_id'), 'edit_plan_records', ['task_id'], unique=False)
    op.create_index(op.f('ix_edit_plan_records_roadmap_id'), 'edit_plan_records', ['roadmap_id'], unique=False)
    op.create_index(op.f('ix_edit_plan_records_feedback_id'), 'edit_plan_records', ['feedback_id'], unique=False)
    op.create_index(op.f('ix_edit_plan_records_execution_status'), 'edit_plan_records', ['execution_status'], unique=False)


def downgrade() -> None:
    """
    回滚：删除 edit_plan_records 和 human_review_feedbacks 表
    """
    # ### 删除 edit_plan_records 表 ###
    op.drop_index(op.f('ix_edit_plan_records_execution_status'), table_name='edit_plan_records')
    op.drop_index(op.f('ix_edit_plan_records_feedback_id'), table_name='edit_plan_records')
    op.drop_index(op.f('ix_edit_plan_records_roadmap_id'), table_name='edit_plan_records')
    op.drop_index(op.f('ix_edit_plan_records_task_id'), table_name='edit_plan_records')
    op.drop_table('edit_plan_records')
    
    # ### 删除 human_review_feedbacks 表 ###
    op.drop_index(op.f('ix_human_review_feedbacks_review_round'), table_name='human_review_feedbacks')
    op.drop_index(op.f('ix_human_review_feedbacks_user_id'), table_name='human_review_feedbacks')
    op.drop_index(op.f('ix_human_review_feedbacks_roadmap_id'), table_name='human_review_feedbacks')
    op.drop_index(op.f('ix_human_review_feedbacks_task_id'), table_name='human_review_feedbacks')
    op.drop_table('human_review_feedbacks')


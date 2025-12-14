"""add_mentor_chat_tables

添加伴学Agent相关的数据表：
- chat_sessions: 聊天会话表
- chat_messages: 聊天消息表
- learning_notes: 学习笔记表

Revision ID: add_mentor_chat_tables
Revises: 1b8068b4dc44
Create Date: 2025-12-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel.sql.sqltypes

# revision identifiers, used by Alembic.
revision: str = 'add_mentor_chat_tables'
down_revision: Union[str, None] = '1b8068b4dc44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === 创建 chat_sessions 表 ===
    op.create_table(
        'chat_sessions',
        sa.Column('session_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('user_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('roadmap_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('concept_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_message_preview', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('session_id')
    )
    op.create_index(op.f('ix_chat_sessions_user_id'), 'chat_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_chat_sessions_roadmap_id'), 'chat_sessions', ['roadmap_id'], unique=False)
    op.create_index(op.f('ix_chat_sessions_concept_id'), 'chat_sessions', ['concept_id'], unique=False)
    # 复合索引：按用户和路线图快速查询会话列表
    op.create_index(
        'ix_chat_sessions_user_roadmap',
        'chat_sessions',
        ['user_id', 'roadmap_id'],
        unique=False
    )
    
    # === 创建 chat_messages 表 ===
    op.create_table(
        'chat_messages',
        sa.Column('message_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('session_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('role', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('intent_type', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('message_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.session_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('message_id')
    )
    op.create_index(op.f('ix_chat_messages_session_id'), 'chat_messages', ['session_id'], unique=False)
    # 复合索引：按会话和时间排序快速查询消息
    op.create_index(
        'ix_chat_messages_session_created',
        'chat_messages',
        ['session_id', 'created_at'],
        unique=False
    )
    
    # === 创建 learning_notes 表 ===
    op.create_table(
        'learning_notes',
        sa.Column('note_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('user_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('roadmap_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('concept_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='manual'),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('note_id')
    )
    op.create_index(op.f('ix_learning_notes_user_id'), 'learning_notes', ['user_id'], unique=False)
    op.create_index(op.f('ix_learning_notes_roadmap_id'), 'learning_notes', ['roadmap_id'], unique=False)
    op.create_index(op.f('ix_learning_notes_concept_id'), 'learning_notes', ['concept_id'], unique=False)
    # 复合索引：按用户/路线图/概念快速查询笔记
    op.create_index(
        'ix_learning_notes_user_roadmap_concept',
        'learning_notes',
        ['user_id', 'roadmap_id', 'concept_id'],
        unique=False
    )


def downgrade() -> None:
    # 删除 learning_notes 表
    op.drop_index('ix_learning_notes_user_roadmap_concept', table_name='learning_notes')
    op.drop_index(op.f('ix_learning_notes_concept_id'), table_name='learning_notes')
    op.drop_index(op.f('ix_learning_notes_roadmap_id'), table_name='learning_notes')
    op.drop_index(op.f('ix_learning_notes_user_id'), table_name='learning_notes')
    op.drop_table('learning_notes')
    
    # 删除 chat_messages 表
    op.drop_index('ix_chat_messages_session_created', table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_session_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    
    # 删除 chat_sessions 表
    op.drop_index('ix_chat_sessions_user_roadmap', table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_concept_id'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_roadmap_id'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_user_id'), table_name='chat_sessions')
    op.drop_table('chat_sessions')

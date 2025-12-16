"""add waitlist_emails table

Revision ID: add_waitlist_emails
Revises: 
Create Date: 2024-12-16

创建候补名单邮箱表，用于存储 Join Waitlist 用户。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_waitlist_emails'
down_revision = 'add_mentor_chat_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 waitlist_emails 表"""
    op.create_table(
        'waitlist_emails',
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False, server_default='landing_page'),
        sa.Column('invited', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('invited_at', sa.DateTime(timezone=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint('email')
    )
    
    # 创建索引以便于查询未邀请用户
    op.create_index('ix_waitlist_emails_invited', 'waitlist_emails', ['invited'])
    op.create_index('ix_waitlist_emails_created_at', 'waitlist_emails', ['created_at'])


def downgrade() -> None:
    """删除 waitlist_emails 表"""
    op.drop_index('ix_waitlist_emails_created_at', table_name='waitlist_emails')
    op.drop_index('ix_waitlist_emails_invited', table_name='waitlist_emails')
    op.drop_table('waitlist_emails')


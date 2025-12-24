"""add waitlist invite fields

Revision ID: add_waitlist_invite_fields
Revises: ede0773860b9
Create Date: 2025-12-24

为 waitlist_emails 表添加邀请凭证相关字段，支持管理员发送临时账号。
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'add_waitlist_invite_fields'
down_revision = 'ede0773860b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加 username, password, expires_at, sent_content 字段"""
    # 添加用户名字段
    op.add_column('waitlist_emails', sa.Column('username', sa.String(), nullable=True))
    
    # 添加临时密码字段（明文存储用于邮件发送）
    op.add_column('waitlist_emails', sa.Column('password', sa.String(), nullable=True))
    
    # 添加密码过期时间字段
    op.add_column('waitlist_emails', sa.Column('expires_at', sa.DateTime(timezone=False), nullable=True))
    
    # 添加发送内容历史记录字段（JSON 格式）
    op.add_column('waitlist_emails', sa.Column('sent_content', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """删除添加的字段"""
    op.drop_column('waitlist_emails', 'sent_content')
    op.drop_column('waitlist_emails', 'expires_at')
    op.drop_column('waitlist_emails', 'password')
    op.drop_column('waitlist_emails', 'username')


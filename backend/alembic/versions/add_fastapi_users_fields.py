"""add fastapi users fields to users table

Revision ID: add_fastapi_users_fields
Revises: add_waitlist_emails
Create Date: 2024-12-16

为 users 表添加 FastAPI Users 所需的字段：
- hashed_password: 密码哈希
- is_active: 是否激活
- is_superuser: 是否超级管理员
- is_verified: 是否已验证邮箱
- password_expires_at: 临时密码过期时间
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_fastapi_users_fields'
down_revision = 'add_waitlist_emails'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加 FastAPI Users 所需字段"""
    # 添加 hashed_password 字段
    op.add_column(
        'users',
        sa.Column('hashed_password', sa.String(length=1024), nullable=True)
    )
    
    # 添加 is_active 字段
    op.add_column(
        'users',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # 添加 is_superuser 字段
    op.add_column(
        'users',
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # 添加 is_verified 字段
    op.add_column(
        'users',
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # 添加 password_expires_at 字段
    op.add_column(
        'users',
        sa.Column('password_expires_at', sa.DateTime(timezone=False), nullable=True)
    )
    
    # 为现有用户设置默认密码哈希（临时值，需要后续更新）
    # 这是一个占位符，真实用户需要通过管理员邀请重新设置密码
    op.execute(
        "UPDATE users SET hashed_password = '' WHERE hashed_password IS NULL"
    )
    
    # 将 hashed_password 设为非空
    op.alter_column(
        'users',
        'hashed_password',
        existing_type=sa.String(length=1024),
        nullable=False
    )


def downgrade() -> None:
    """移除 FastAPI Users 字段"""
    op.drop_column('users', 'password_expires_at')
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'is_superuser')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'hashed_password')


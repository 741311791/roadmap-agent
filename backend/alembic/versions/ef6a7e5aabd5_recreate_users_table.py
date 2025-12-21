"""recreate_users_table

Revision ID: ef6a7e5aabd5
Revises: 18666a4389a6
Create Date: 2025-12-20 21:33:43.175982

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ef6a7e5aabd5'
down_revision: Union[str, None] = '18666a4389a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """重新创建 users 表（FastAPI Users）"""
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(100), nullable=False, server_default=''),
        sa.Column('hashed_password', sa.String(1024), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('password_expires_at', sa.DateTime(timezone=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # 创建唯一索引
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)


def downgrade() -> None:
    """删除 users 表"""
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')


"""add avatar_config to users

Revision ID: a1b2c3d4e5f6
Revises: 6df605025673
Create Date: 2026-02-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'bd3a3251d400'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """在 users 表中添加 avatar_config JSON 列，存储 react-nice-avatar 头像配置。"""
    op.add_column(
        'users',
        sa.Column('avatar_config', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    """回滚：删除 avatar_config 列。"""
    op.drop_column('users', 'avatar_config')

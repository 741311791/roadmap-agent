"""add retry_count to roadmap_cover_images

Revision ID: add_retry_count_cover
Revises: 4642afc7b515
Create Date: 2026-01-10 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_retry_count_cover'
down_revision: Union[str, None] = '4642afc7b515'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    添加 retry_count 字段到 roadmap_cover_images 表
    
    用于支持幂等性检查和重试限制（方案2架构优化）
    """
    # 添加 retry_count 字段，默认值为 0
    op.add_column(
        'roadmap_cover_images',
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    """回滚：删除 retry_count 字段"""
    op.drop_column('roadmap_cover_images', 'retry_count')


"""remove intent_analysis foreign key

Revision ID: 20260115_remove_fkey
Revises: 20260115_refactor_intent
Create Date: 2026-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260115_remove_fkey'
down_revision: Union[str, None] = '20260115_refactor_intent'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    移除 intent_analysis_metadata 表的外键约束
    
    原因：intent_analysis 在 roadmap_metadata 创建之前执行，
    外键约束会导致插入失败。应用层通过工作流保证数据一致性。
    """
    # 查找并删除外键约束（如果存在）
    # 外键名称通常为: intent_analysis_metadata_roadmap_id_fkey
    from sqlalchemy import inspect
    from alembic import context
    
    conn = context.get_bind()
    inspector = inspect(conn)
    
    # 检查约束是否存在
    foreign_keys = inspector.get_foreign_keys('intent_analysis_metadata')
    fk_names = [fk['name'] for fk in foreign_keys]
    
    if 'intent_analysis_metadata_roadmap_id_fkey' in fk_names:
        op.drop_constraint(
            'intent_analysis_metadata_roadmap_id_fkey',
            'intent_analysis_metadata',
            type_='foreignkey'
        )
    
    # 保留索引（用于查询性能）
    # 索引应该已经存在，不需要重新创建


def downgrade() -> None:
    """
    恢复外键约束（不推荐）
    """
    op.create_foreign_key(
        'intent_analysis_metadata_roadmap_id_fkey',
        'intent_analysis_metadata',
        'roadmap_metadata',
        ['roadmap_id'],
        ['roadmap_id']
    )


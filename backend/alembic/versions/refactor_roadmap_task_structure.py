"""重构路线图任务架构：扩展 roadmap_tasks 表，移除 roadmap_metadata.task_id

Revision ID: refactor_task_arch
Revises: phase3_add_composite_indexes
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'refactor_task_arch'
down_revision = '46b11db29fd5'
branch_labels = None
depends_on = None


def upgrade():
    """
    升级数据库结构：
    1. 在 roadmap_tasks 表添加新字段（task_type, concept_id, content_type）
    2. 更新现有记录设置 task_type='creation'
    3. 创建索引提升查询性能
    4. 删除 roadmap_metadata.task_id 字段
    """
    # 1. 在 roadmap_tasks 表上添加新字段
    op.add_column('roadmap_tasks', sa.Column('task_type', sa.String(), nullable=True))
    op.add_column('roadmap_tasks', sa.Column('concept_id', sa.String(), nullable=True))
    op.add_column('roadmap_tasks', sa.Column('content_type', sa.String(), nullable=True))
    
    # 2. 为现有记录设置默认值（所有现有任务都是创建任务）
    op.execute("""
        UPDATE roadmap_tasks 
        SET task_type = 'creation' 
        WHERE task_type IS NULL
    """)
    
    # 3. 创建复合索引以提升查询性能
    # 用于查询路线图的活跃任务
    op.create_index(
        'idx_roadmap_tasks_roadmap_id_status', 
        'roadmap_tasks', 
        ['roadmap_id', 'status']
    )
    
    # 用于按时间排序查询
    op.create_index(
        'idx_roadmap_tasks_roadmap_id_created_at', 
        'roadmap_tasks', 
        ['roadmap_id', sa.text('created_at DESC')],
        postgresql_using='btree'
    )
    
    # 4. 删除 roadmap_metadata.task_id 字段（不再需要）
    op.drop_column('roadmap_metadata', 'task_id')


def downgrade():
    """
    回滚数据库结构：
    1. 恢复 roadmap_metadata.task_id 字段
    2. 从 roadmap_tasks 恢复数据（每个 roadmap 取最早的创建任务）
    3. 删除索引
    4. 删除新增字段
    """
    # 1. 恢复 roadmap_metadata.task_id 字段
    op.add_column('roadmap_metadata', sa.Column('task_id', sa.String(), nullable=True))
    
    # 2. 从 roadmap_tasks 恢复数据（每个 roadmap 取最早的创建任务）
    op.execute("""
        UPDATE roadmap_metadata m
        SET task_id = (
            SELECT t.task_id
            FROM roadmap_tasks t
            WHERE t.roadmap_id = m.roadmap_id
            AND t.task_type = 'creation'
            ORDER BY t.created_at ASC
            LIMIT 1
        )
    """)
    
    # 3. 删除索引
    op.drop_index('idx_roadmap_tasks_roadmap_id_created_at', 'roadmap_tasks')
    op.drop_index('idx_roadmap_tasks_roadmap_id_status', 'roadmap_tasks')
    
    # 4. 删除新增字段
    op.drop_column('roadmap_tasks', 'content_type')
    op.drop_column('roadmap_tasks', 'concept_id')
    op.drop_column('roadmap_tasks', 'task_type')


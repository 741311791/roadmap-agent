"""refactor intent_analysis_metadata table

Revision ID: 20260115_refactor_intent
Revises: 20260114_fix_roadmap_id_and_timestamps
Create Date: 2026-01-15 00:00:00.000000

修改说明：
1. 将 id 列重命名为 intent_id（保持UUID主键）
2. 删除 task_id 列和外键约束
3. 将 roadmap_id 设置为外键（添加唯一约束）
4. 统一元数据表设计规范（与TutorialMetadata、QuizMetadata保持一致）

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260115_refactor_intent'
down_revision = 'fix_roadmap_id_timestamps'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    升级操作
    
    注意事项：
    1. 将 id 重命名为 intent_id（保持主键）
    2. 删除 task_id 及其约束
    3. roadmap_id 添加唯一约束和外键约束
    """
    
    # 1. 删除 task_id 的外键约束（如果存在）
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'intent_analysis_metadata_task_id_fkey'
                AND table_name = 'intent_analysis_metadata'
            ) THEN
                ALTER TABLE intent_analysis_metadata 
                DROP CONSTRAINT intent_analysis_metadata_task_id_fkey;
            END IF;
        END $$;
    """)
    
    # 2. 删除 task_id 的唯一约束/索引（如果存在）
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'ix_intent_analysis_metadata_task_id'
            ) THEN
                DROP INDEX ix_intent_analysis_metadata_task_id;
            END IF;
        END $$;
    """)
    
    # 3. 删除 task_id 列
    op.execute("""
        ALTER TABLE intent_analysis_metadata 
        DROP COLUMN IF EXISTS task_id;
    """)
    
    # 4. 将 id 列重命名为 intent_id（保持主键）
    op.execute("""
        ALTER TABLE intent_analysis_metadata 
        RENAME COLUMN id TO intent_id;
    """)
    
    # 5. 确保 roadmap_id 不为空
    # （如果表中有 roadmap_id 为空的数据，用 intent_id 填充）
    op.execute("""
        UPDATE intent_analysis_metadata 
        SET roadmap_id = 'unknown-' || intent_id::text
        WHERE roadmap_id IS NULL;
    """)
    
    # 6. 修改 roadmap_id 为非空
    op.alter_column(
        'intent_analysis_metadata',
        'roadmap_id',
        existing_type=sa.String(),
        nullable=False,
    )
    
    # 7. 添加 roadmap_id 的唯一约束
    op.create_unique_constraint(
        'uix_intent_roadmap_id',
        'intent_analysis_metadata',
        ['roadmap_id']
    )
    
    # 8. 添加 roadmap_id 的外键约束
    op.create_foreign_key(
        'intent_analysis_metadata_roadmap_id_fkey',
        'intent_analysis_metadata',
        'roadmap_metadata',
        ['roadmap_id'],
        ['roadmap_id']
    )


def downgrade() -> None:
    """
    降级操作
    
    注意：此降级操作会丢失数据关联性，谨慎使用
    """
    
    # 1. 删除 roadmap_id 的外键约束
    op.drop_constraint(
        'intent_analysis_metadata_roadmap_id_fkey',
        'intent_analysis_metadata',
        type_='foreignkey'
    )
    
    # 2. 删除 roadmap_id 的唯一约束
    op.drop_constraint(
        'uix_intent_roadmap_id',
        'intent_analysis_metadata',
        type_='unique'
    )
    
    # 3. roadmap_id 改为可空
    op.alter_column(
        'intent_analysis_metadata',
        'roadmap_id',
        existing_type=sa.String(),
        nullable=True,
    )
    
    # 4. 将 intent_id 列重命名回 id
    op.execute("""
        ALTER TABLE intent_analysis_metadata 
        RENAME COLUMN intent_id TO id;
    """)
    
    # 5. 添加回 task_id 列
    op.add_column(
        'intent_analysis_metadata',
        sa.Column('task_id', sa.String(), nullable=True)
    )
    
    # 6. 添加回 task_id 索引和唯一约束
    op.create_index(
        'ix_intent_analysis_metadata_task_id',
        'intent_analysis_metadata',
        ['task_id'],
        unique=True
    )
    
    # 7. 添加回外键约束（需要确保 roadmap_tasks 表存在）
    # 注意：降级后 task_id 为空，外键约束可能失败
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'roadmap_tasks'
            ) THEN
                ALTER TABLE intent_analysis_metadata 
                ADD CONSTRAINT intent_analysis_metadata_task_id_fkey 
                FOREIGN KEY (task_id) REFERENCES roadmap_tasks(task_id);
            END IF;
        END $$;
    """)


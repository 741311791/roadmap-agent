#!/usr/bin/env python
"""
检查并修复数据库迁移状态

问题场景：
- 之前使用 alembic stamp head 标记了版本，但实际未执行迁移
- 导致数据库缺少某些列（如 roadmap_tasks.celery_task_id）
- alembic upgrade head 会跳过已标记的迁移

解决方案：
- 检查关键列是否存在
- 如果列不存在但版本已标记，清除版本标记
- 强制重新运行迁移
"""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config.settings import settings


async def check_column_exists(engine, table: str, column: str) -> bool:
    """检查列是否存在"""
    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = :table 
                    AND column_name = :column
                )
            """),
            {"table": table, "column": column}
        )
        return result.scalar()


async def get_alembic_version(engine) -> str | None:
    """获取当前 Alembic 版本"""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            return result.scalar()
    except Exception:
        return None


async def clear_alembic_version(engine):
    """清除 Alembic 版本表"""
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    print("✅ Alembic version table cleared")


async def main():
    """主函数"""
    print("🔍 Checking database migration status...")
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    try:
        # 检查关键列是否存在
        celery_task_id_exists = await check_column_exists(
            engine, "roadmap_tasks", "celery_task_id"
        )
        
        # 获取当前版本
        current_version = await get_alembic_version(engine)
        
        print(f"📌 Current Alembic version: {current_version or 'None'}")
        print(f"📋 Column roadmap_tasks.celery_task_id exists: {celery_task_id_exists}")
        
        # 如果版本已标记但列不存在，说明迁移未实际执行
        if current_version and not celery_task_id_exists:
            print("⚠️  Migration version is marked but column is missing!")
            print("🔧 This indicates 'alembic stamp' was used instead of 'alembic upgrade'")
            print("🔄 Clearing version table to force re-migration...")
            
            await clear_alembic_version(engine)
            
            print("✅ Migration state fixed. Run 'alembic upgrade head' to apply migrations.")
            return 0
        elif not celery_task_id_exists:
            print("⚠️  Column is missing but no version is marked")
            print("✅ This is normal for a fresh database. Proceed with 'alembic upgrade head'")
            return 0
        else:
            print("✅ Database migration state is correct")
            return 0
            
    except Exception as e:
        print(f"❌ Error checking migration state: {e}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))


"""
执行数据库迁移脚本

用法：
    python scripts/run_migration.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import async_engine
import structlog

logger = structlog.get_logger()


async def remove_foreign_key():
    """移除 intent_analysis_metadata 表的外键约束"""
    async with async_engine.begin() as conn:
        try:
            # 检查外键是否存在
            check_sql = """
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'intent_analysis_metadata' 
            AND constraint_type = 'FOREIGN KEY'
            AND constraint_name = 'intent_analysis_metadata_roadmap_id_fkey'
            """
            result = await conn.execute(text(check_sql))
            exists = result.fetchone() is not None
            
            if exists:
                # 删除外键约束
                drop_sql = """
                ALTER TABLE intent_analysis_metadata 
                DROP CONSTRAINT intent_analysis_metadata_roadmap_id_fkey
                """
                await conn.execute(text(drop_sql))
                logger.info(
                    "foreign_key_removed",
                    constraint="intent_analysis_metadata_roadmap_id_fkey",
                    table="intent_analysis_metadata",
                )
                print("✅ 成功移除外键约束: intent_analysis_metadata_roadmap_id_fkey")
            else:
                logger.info(
                    "foreign_key_not_found",
                    constraint="intent_analysis_metadata_roadmap_id_fkey",
                )
                print("ℹ️  外键约束不存在，无需删除")
            
            # 确认索引仍然存在（用于查询性能）
            index_check_sql = """
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'intent_analysis_metadata' 
            AND indexname LIKE '%roadmap_id%'
            """
            result = await conn.execute(text(index_check_sql))
            indexes = result.fetchall()
            
            if indexes:
                print(f"✅ roadmap_id 索引存在: {[idx[0] for idx in indexes]}")
            else:
                print("⚠️  警告: roadmap_id 索引不存在，可能影响查询性能")
                
        except Exception as e:
            logger.error(
                "migration_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            print(f"❌ 迁移失败: {e}")
            raise


async def main():
    """主函数"""
    print("=" * 60)
    print("数据库迁移: 移除 intent_analysis_metadata 外键约束")
    print("=" * 60)
    print()
    print("原因: intent_analysis 在 roadmap_metadata 创建之前执行")
    print("解决: 移除外键约束，由应用层保证数据一致性")
    print()
    
    try:
        await remove_foreign_key()
        print()
        print("=" * 60)
        print("✅ 迁移完成")
        print("=" * 60)
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ 迁移失败")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


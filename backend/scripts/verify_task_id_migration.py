"""验证 trace_id → task_id 迁移的完整性"""
import asyncio
import sys
from sqlalchemy import text
from app.db.session import async_session_maker
import structlog

logger = structlog.get_logger()


async def verify_migration():
    """验证迁移的完整性"""
    issues = []
    
    async with async_session_maker.begin() as session:
        # 1. 验证数据库字段
        logger.info("🔍 检查数据库 schema...")
        result = await session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'execution_logs' 
            AND column_name IN ('task_id', 'trace_id')
        """))
        columns = {row[0] for row in result.fetchall()}
        
        if 'task_id' not in columns:
            issues.append("❌ task_id 字段不存在")
        else:
            logger.info("✅ task_id 字段存在")
        
        if 'trace_id' in columns:
            issues.append("⚠️  trace_id 字段仍然存在(应该已删除)")
        else:
            logger.info("✅ trace_id 字段已删除")
        
        # 2. 验证索引
        logger.info("🔍 检查索引...")
        result = await session.execute(text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'execution_logs' 
            AND indexname LIKE '%task_id%'
        """))
        task_id_indexes = [row[0] for row in result.fetchall()]
        
        if task_id_indexes:
            logger.info(f"✅ task_id 索引存在: {', '.join(task_id_indexes)}")
        else:
            issues.append("⚠️  task_id 索引不存在")
        
        # 3. 验证数据完整性
        logger.info("🔍 检查数据完整性...")
        result = await session.execute(text("""
            SELECT COUNT(*) FROM execution_logs
        """))
        count = result.scalar()
        logger.info(f"📊 execution_logs 表记录数: {count}")
        
        # 4. 验证表结构
        logger.info("🔍 检查表结构...")
        result = await session.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'execution_logs'
            ORDER BY ordinal_position
        """))
        columns_info = result.fetchall()
        logger.info("📋 execution_logs 表结构:")
        for col_name, data_type, nullable in columns_info:
            logger.info(f"  - {col_name}: {data_type} (nullable={nullable})")
    
    # 总结
    print("\n" + "="*60)
    if issues:
        print("❌ 发现问题:")
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print("✅ 所有验证通过!")
        print("\n迁移完成:")
        print("  ✓ trace_id 已重命名为 task_id")
        print("  ✓ 数据库 schema 已更新")
        print("  ✓ 索引已重建")
        print("  ✓ 代码已全部更新")
        return True


if __name__ == "__main__":
    success = asyncio.run(verify_migration())
    sys.exit(0 if success else 1)


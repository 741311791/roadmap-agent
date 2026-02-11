#!/usr/bin/env python3
"""
直接执行数据库迁移
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 设置异步事件循环策略 (避免 Windows 上的问题)
if sys.platform.startswith('win'):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


async def main():
    """执行迁移"""
    # 延迟导入，确保环境变量已加载
    from sqlalchemy import text
    from app.db.session import engine
    
    print("=" * 60)
    print("🗄️  执行数据库迁移")
    print("=" * 60)
    print()
    print("目标: 移除 intent_analysis_metadata 的外键约束")
    print()
    
    async with engine.begin() as conn:
        # 1. 检查外键是否存在
        print("📋 检查外键约束...")
        check_sql = """
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'intent_analysis_metadata' 
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name = 'intent_analysis_metadata_roadmap_id_fkey'
        """
        result = await conn.execute(text(check_sql))
        row = result.fetchone()
        
        if row:
            print(f"   找到外键约束: {row[0]}")
            
            # 2. 删除外键约束
            print()
            print("🔧 删除外键约束...")
            drop_sql = """
            ALTER TABLE intent_analysis_metadata 
            DROP CONSTRAINT intent_analysis_metadata_roadmap_id_fkey
            """
            await conn.execute(text(drop_sql))
            print("   ✅ 外键约束已删除")
        else:
            print("   ℹ️  外键约束不存在，无需删除")
        
        # 3. 检查索引
        print()
        print("📋 检查 roadmap_id 索引...")
        index_sql = """
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'intent_analysis_metadata' 
        AND indexname LIKE '%roadmap_id%'
        """
        result = await conn.execute(text(index_sql))
        indexes = result.fetchall()
        
        if indexes:
            print(f"   ✅ 索引存在: {', '.join(idx[0] for idx in indexes)}")
        else:
            print("   ⚠️  警告: 没有找到 roadmap_id 相关索引")
    
    print()
    print("=" * 60)
    print("✅ 迁移完成")
    print("=" * 60)
    print()
    print("📝 变更说明:")
    print("   - 移除了 intent_analysis_metadata.roadmap_id 的外键约束")
    print("   - 保留了 roadmap_id 索引（用于查询性能）")
    print("   - 数据一致性由应用层工作流保证")
    print()


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ 迁移失败: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)


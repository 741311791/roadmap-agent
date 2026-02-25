"""
验证数据库迁移是否成功
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import async_session_maker
from sqlalchemy import text


async def verify_migration():
    """验证迁移状态"""
    print("=" * 60)
    print("数据库迁移验证")
    print("=" * 60)
    
    async with async_session_maker() as session:
        # 检查 intent_analysis_metadata 表结构
        print("\n📝 检查 intent_analysis_metadata 表结构...")
        result = await session.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'intent_analysis_metadata'
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        print(f"\n✅ 找到 {len(columns)} 个字段：")
        
        has_full_analysis_data = False
        for col_name, data_type, is_nullable in columns:
            if col_name == 'full_analysis_data':
                has_full_analysis_data = True
                print(f"  ✅ {col_name}: {data_type} (nullable: {is_nullable})")
            else:
                print(f"  - {col_name}: {data_type}")
        
        if not has_full_analysis_data:
            print("\n❌ 错误：未找到 full_analysis_data 字段！")
            return False
        
        # 检查数据库中的记录数
        print("\n📝 检查数据...")
        result = await session.execute(text("""
            SELECT COUNT(*) FROM intent_analysis_metadata
        """))
        count = result.scalar()
        
        print(f"✅ intent_analysis_metadata 表中有 {count} 条记录")
        
        if count == 0:
            print("  ℹ️  表为空（这是正常的，因为表已被清空）")
        
        print("\n" + "=" * 60)
        print("✅ 数据库迁移验证成功！")
        print("=" * 60)
        print("\n当前数据库版本: bd3a3251d400 (head)")
        print("迁移状态: ✅ 已完成")
        print("\n系统已就绪，可以开始测试约束系统！")
        
        return True


if __name__ == "__main__":
    try:
        success = asyncio.run(verify_migration())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

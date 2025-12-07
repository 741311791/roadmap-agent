"""清空所有表数据（保留表结构）"""
import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
import structlog

logger = structlog.get_logger()

TABLES_TO_CLEAR = [
    "execution_logs",                      # 执行日志
    "quiz_metadata",                       # 测验元数据
    "resource_recommendation_metadata",    # 资源推荐元数据
    "tutorial_metadata",                   # 教程元数据
    "intent_analysis_metadata",            # 需求分析元数据
    "roadmap_metadata",                    # 路线图元数据
    "roadmap_tasks",                       # 任务记录
    "user_profiles",                       # 用户画像
]

async def clear_all_tables():
    """清空所有表数据"""
    async with AsyncSessionLocal() as session:
        try:
            for table in TABLES_TO_CLEAR:
                logger.info(f"清空表: {table}")
                await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            
            await session.commit()
            logger.info("✅ 所有表数据清空完成")
            
            # 显示清空结果
            for table in TABLES_TO_CLEAR:
                result = await session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                )
                count = result.scalar()
                logger.info(f"  {table}: {count} 条记录")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ 清空失败: {e}")
            raise

if __name__ == "__main__":
    print("⚠️  警告：此操作将删除所有数据！")
    confirm = input("确认清空所有表数据？(yes/no): ")
    
    if confirm.lower() == "yes":
        asyncio.run(clear_all_tables())
        print("✅ 数据清空完成")
    else:
        print("❌ 操作已取消")

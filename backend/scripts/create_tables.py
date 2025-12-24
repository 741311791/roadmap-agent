"""
强制创建所有数据库表（用于生产环境部署）
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.models.database import SQLModel, Base
from app.db.session import engine
import structlog

logger = structlog.get_logger()


async def main():
    """创建所有表"""
    try:
        logger.info("creating_database_tables")
        
        async with engine.begin() as conn:
            # 创建 Base 的表（包括 User 表）
            await conn.run_sync(Base.metadata.create_all)
            # 创建 SQLModel 的表（其他所有表）
            await conn.run_sync(SQLModel.metadata.create_all)
        
        logger.info("database_tables_created_successfully")
        print("✅ 数据库表创建成功（包括 users 表）")
        
    except Exception as e:
        logger.error("database_tables_creation_failed", error=str(e))
        print(f"❌ 数据库表创建失败: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())


"""
数据库初始化脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import settings
from app.config.logging_config import setup_logging
from app.db.session import init_db, engine
from app.models.database import SQLModel
import structlog

logger = structlog.get_logger()


async def main():
    """初始化数据库"""
    setup_logging()
    
    logger.info(
        "database_initialization_started",
        database_url=settings.DATABASE_URL.replace(settings.POSTGRES_PASSWORD, "***"),
    )
    
    try:
        # 初始化数据库（创建表）
        await init_db()
        logger.info("database_initialization_completed")
        
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e))
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())


#!/usr/bin/env python3
"""
Tavily 配额更新功能测试脚本

功能：
- 测试单次配额更新流程
- 验证数据库连接
- 检查 Tavily API 调用
- 不启动定时调度（方便快速测试）

使用：
python scripts/test_tavily_quota_update.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import structlog
from sqlalchemy import select

from app.config.settings import settings
from app.db.session import AsyncSessionLocal
from app.models.database import TavilyAPIKey

# 配置日志（简化输出）
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),  # 使用彩色控制台输出
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


async def test_database_connection():
    """
    测试数据库连接
    """
    logger.info("Testing database connection...")
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(TavilyAPIKey)
            result = await session.execute(stmt)
            keys = result.scalars().all()
            
            logger.info(
                "Database connection successful",
                total_keys=len(keys),
                database_host=settings.POSTGRES_HOST
            )
            
            if len(keys) == 0:
                logger.warning(
                    "No API keys found in database",
                    hint="Please add some keys using the admin panel at /admin/api-keys"
                )
                return False
            
            # 显示前 3 个 Key 的信息
            for key in keys[:3]:
                logger.info(
                    "Found API key",
                    key_prefix=key.api_key[:10] + "...",
                    remaining_quota=key.remaining_quota,
                    plan_limit=key.plan_limit,
                    updated_at=key.updated_at.isoformat()
                )
            
            return True
            
    except Exception as e:
        logger.error(
            "Database connection failed",
            error=str(e),
            error_type=type(e).__name__
        )
        return False


async def test_single_update():
    """
    测试单次配额更新（调用实际更新逻辑）
    """
    logger.info("Starting single quota update test...")
    
    try:
        # 导入更新函数
        from update_tavily_quota import update_all_keys_quota
        
        # 执行更新
        await update_all_keys_quota()
        
        logger.info("Single update test completed successfully")
        return True
        
    except Exception as e:
        logger.error(
            "Single update test failed",
            error=str(e),
            error_type=type(e).__name__
        )
        return False


async def main():
    """
    主测试流程
    """
    logger.info("=" * 60)
    logger.info("Tavily Quota Update Test Script")
    logger.info("=" * 60)
    
    # 测试 1: 数据库连接
    logger.info("\n[Test 1] Database Connection")
    db_ok = await test_database_connection()
    
    if not db_ok:
        logger.error("Database test failed, aborting further tests")
        return False
    
    # 测试 2: 单次更新
    logger.info("\n[Test 2] Single Quota Update")
    update_ok = await test_single_update()
    
    # 总结
    logger.info("\n" + "=" * 60)
    if db_ok and update_ok:
        logger.info("✅ All tests passed!")
        logger.info("You can now run the full scheduler:")
        logger.info("  python scripts/update_tavily_quota.py")
    else:
        logger.error("❌ Some tests failed, please check the logs above")
    logger.info("=" * 60)
    
    return db_ok and update_ok


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(
            "Test script crashed",
            error=str(e),
            error_type=type(e).__name__
        )
        sys.exit(1)


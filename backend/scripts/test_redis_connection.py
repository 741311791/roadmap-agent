#!/usr/bin/env python3
"""
测试 Redis 连接
用于验证 SSL 配置修复是否成功
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.redis_client import redis_client
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


async def test_redis_connection():
    """测试 Redis 连接和基本操作"""
    try:
        # 1. 测试连接
        logger.info("testing_redis_connection", redis_url=settings.get_redis_url)
        await redis_client.connect()
        
        # 2. 测试 ping
        logger.info("testing_redis_ping")
        result = await redis_client.ping()
        logger.info("redis_ping_success", result=result)
        
        # 3. 测试写入和读取 JSON
        test_key = "test:connection:json"
        test_data = {
            "message": "Redis connection test",
            "timestamp": "2025-12-27",
            "status": "success"
        }
        
        logger.info("testing_redis_json_operations", key=test_key)
        await redis_client.set_json(test_key, test_data, ex=60)
        
        # 4. 读取 JSON
        retrieved_data = await redis_client.get_json(test_key)
        logger.info("redis_json_retrieved", data=retrieved_data)
        
        # 5. 验证数据一致性
        if retrieved_data == test_data:
            logger.info("redis_data_consistency_verified")
        else:
            logger.error("redis_data_mismatch", expected=test_data, actual=retrieved_data)
            return False
        
        # 6. 测试删除
        await redis_client.delete(test_key)
        exists = await redis_client.exists(test_key)
        if not exists:
            logger.info("redis_delete_success")
        else:
            logger.error("redis_delete_failed")
            return False
        
        # 7. 关闭连接
        await redis_client.close()
        logger.info("redis_connection_test_completed", status="success")
        return True
        
    except Exception as e:
        logger.error("redis_connection_test_failed", error=str(e), error_type=type(e).__name__)
        return False


async def main():
    """主函数"""
    success = await test_redis_connection()
    if success:
        print("\n✅ Redis 连接测试成功！SSL 配置修复已生效。")
        sys.exit(0)
    else:
        print("\n❌ Redis 连接测试失败，请检查配置。")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


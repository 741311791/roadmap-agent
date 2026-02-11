#!/usr/bin/env python3
"""
验证Tavily API速率限制配置（简化版）

功能：
1. 查看环境变量配置
2. 测试速率限制器是否正常工作
3. 显示当前使用情况

使用方法：
    python scripts/verify_tavily_rate_limit.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import structlog
from sqlalchemy import text

from app.db.session import async_session_maker
from app.core.tavily_key_cache import get_tavily_key_cache
from app.utils.rate_limiter import get_tavily_rate_limiter
from app.config.settings import settings

logger = structlog.get_logger()


async def show_env_config():
    """显示环境变量配置"""
    logger.info("=== 环境变量配置 ===")
    
    print(f"\n速率限制配置:")
    print(f"  TAVILY_RATE_LIMIT_PER_MINUTE: {settings.TAVILY_RATE_LIMIT_PER_MINUTE} 次/分钟")
    print(f"  USE_DUCKDUCKGO_FALLBACK: {settings.USE_DUCKDUCKGO_FALLBACK}")


async def show_database_keys():
    """显示数据库中的key信息"""
    logger.info("\n=== 数据库Keys ===")
    
    async with async_session_maker() as db:
        query_sql = text("""
            SELECT 
                COUNT(*) as total,
                SUM(remaining_quota) as total_quota
            FROM tavily_api_keys
            WHERE remaining_quota > 0
        """)
        result = await db.execute(query_sql)
        row = result.fetchone()
        
        print(f"\n数据库统计:")
        print(f"  可用keys数量: {row[0]}")
        print(f"  总剩余配额: {row[1]}")


async def show_redis_cache():
    """显示Redis缓存信息"""
    logger.info("\n=== Redis缓存 ===")
    
    key_cache = get_tavily_key_cache()
    stats = await key_cache.get_cache_stats()
    
    print(f"\n缓存统计:")
    print(f"  缓存keys数量: {stats['total_keys']}")
    print(f"  缓存版本: {stats['cache_version']}")
    print(f"  最后更新: {stats['last_updated']}")


async def test_rate_limiter():
    """测试全局速率限制器"""
    logger.info("\n=== 测试速率限制器 ===")
    
    # 获取全局限制器
    rate_limiter = await get_tavily_rate_limiter()
    
    print(f"\n速率限制器配置:")
    print(f"  最大请求数: {rate_limiter.max_requests} 次/分钟")
    print(f"  时间窗口: {rate_limiter.window_seconds} 秒")
    print(f"  Redis Key: {rate_limiter.key}")
    
    # 获取当前使用情况
    current_count = await rate_limiter.get_current_count()
    remaining = rate_limiter.max_requests - current_count
    
    print(f"\n当前使用情况:")
    print(f"  最近1分钟请求数: {current_count}/{rate_limiter.max_requests}")
    print(f"  剩余配额: {remaining}")
    
    if remaining > 0:
        print(f"\n✅ 速率限制器正常工作")
    else:
        print(f"\n⚠️ 当前已达速率限制，需要等待...")


async def test_acquire():
    """测试获取许可"""
    logger.info("\n=== 测试获取许可 ===")
    
    rate_limiter = await get_tavily_rate_limiter()
    
    print(f"\n尝试获取3个请求许可...")
    
    for i in range(3):
        try:
            await rate_limiter.acquire(timeout=5.0)
            current_count = await rate_limiter.get_current_count()
            print(f"  [{i+1}/3] ✅ 许可获取成功 (当前: {current_count}/{rate_limiter.max_requests})")
            await asyncio.sleep(0.1)  # 短暂延迟
        except TimeoutError:
            print(f"  [{i+1}/3] ❌ 超时：速率限制已满")
            break
    
    # 显示最终状态
    final_count = await rate_limiter.get_current_count()
    print(f"\n最终状态: {final_count}/{rate_limiter.max_requests} 请求在最近1分钟内")


async def main():
    """主函数"""
    try:
        # 显示环境变量配置
        await show_env_config()
        
        # 显示数据库keys
        await show_database_keys()
        
        # 显示Redis缓存信息
        await show_redis_cache()
        
        # 测试速率限制器
        await test_rate_limiter()
        
        # 测试获取许可
        await test_acquire()
        
        print("\n" + "="*80)
        print("✅ 验证完成！速率限制配置正常")
        print(f"   当前配置: {settings.TAVILY_RATE_LIMIT_PER_MINUTE} 次/分钟（从环境变量读取）")
        print("="*80 + "\n")
        
        return 0
        
    except Exception as e:
        logger.error(
            "verification_failed",
            error=str(e),
            exc_info=True,
        )
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))


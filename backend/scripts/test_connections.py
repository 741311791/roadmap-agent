#!/usr/bin/env python3
"""测试数据库和 Redis 连接"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.session import engine
from app.config.settings import settings
from sqlalchemy import text
import structlog

logger = structlog.get_logger()

async def test_postgres():
    """测试 PostgreSQL 连接"""
    print("测试 PostgreSQL 连接...")
    print(f"  连接地址: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
    print(f"  数据库: {settings.POSTGRES_DB}")
    
    try:
        async with engine.connect() as conn:
            # 测试基本查询
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            
            # 测试数据库响应时间
            import time
            start = time.time()
            await conn.execute(text("SELECT 1"))
            duration_ms = int((time.time() - start) * 1000)
            
            print(f"✅ PostgreSQL 连接成功")
            print(f"   版本: {version[:80]}...")
            print(f"   响应时间: {duration_ms}ms")
            return True
    except Exception as e:
        print(f"❌ PostgreSQL 连接失败")
        print(f"   错误: {type(e).__name__}: {e}")
        return False

async def test_redis():
    """测试 Redis 连接"""
    print("\n测试 Redis 连接...")
    print(f"  连接地址: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    
    try:
        import redis.asyncio as redis
        
        client = redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=10,
            socket_timeout=10,
        )
        
        # 测试 ping
        import time
        start = time.time()
        await client.ping()
        duration_ms = int((time.time() - start) * 1000)
        
        # 获取服务器信息
        info = await client.info("server")
        
        print(f"✅ Redis 连接成功")
        print(f"   版本: {info.get('redis_version', 'unknown')}")
        print(f"   响应时间: {duration_ms}ms")
        
        await client.close()
        return True
    except Exception as e:
        print(f"❌ Redis 连接失败")
        print(f"   错误: {type(e).__name__}: {e}")
        return False

async def test_checkpointer():
    """测试 LangGraph Checkpointer 连接"""
    print("\n测试 LangGraph Checkpointer...")
    print(f"  连接地址: {settings.CHECKPOINTER_DATABASE_URL.split('@')[-1]}")
    
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        
        # 尝试创建 checkpointer
        checkpointer_cm = AsyncPostgresSaver.from_conn_string(
            settings.CHECKPOINTER_DATABASE_URL
        )
        checkpointer = await checkpointer_cm.__aenter__()
        
        # 尝试 setup
        import time
        start = time.time()
        await checkpointer.setup()
        duration_ms = int((time.time() - start) * 1000)
        
        print(f"✅ Checkpointer 初始化成功")
        print(f"   初始化时间: {duration_ms}ms")
        
        # 清理
        await checkpointer_cm.__aexit__(None, None, None)
        return True
    except Exception as e:
        print(f"❌ Checkpointer 初始化失败")
        print(f"   错误: {type(e).__name__}: {e}")
        return False

async def main():
    print("=" * 60)
    print("远程服务连接测试")
    print("=" * 60)
    print()
    
    pg_ok = await test_postgres()
    redis_ok = await test_redis()
    checkpointer_ok = await test_checkpointer()
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"PostgreSQL:  {'✅ 通过' if pg_ok else '❌ 失败'}")
    print(f"Redis:       {'✅ 通过' if redis_ok else '❌ 失败'}")
    print(f"Checkpointer: {'✅ 通过' if checkpointer_ok else '❌ 失败'}")
    print()
    
    if pg_ok and redis_ok and checkpointer_ok:
        print("✅ 所有连接测试通过！系统可以正常运行。")
        return 0
    else:
        print("❌ 部分连接测试失败！请检查配置和网络连接。")
        print()
        print("建议:")
        if not pg_ok:
            print("  - 检查 PostgreSQL 服务是否运行")
            print("  - 验证 POSTGRES_HOST 和 POSTGRES_PORT 配置")
            print("  - 检查防火墙和网络连接")
        if not redis_ok:
            print("  - 检查 Redis 服务是否运行")
            print("  - 验证 REDIS_HOST 和 REDIS_PORT 配置")
            print("  - 检查防火墙和网络连接")
        if not checkpointer_ok:
            print("  - Checkpointer 依赖 PostgreSQL，请先修复 PostgreSQL 连接")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 测试脚本执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


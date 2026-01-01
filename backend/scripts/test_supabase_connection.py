#!/usr/bin/env python3
"""
测试 Supabase 连接
验证 asyncpg 和 SQLAlchemy 连接配置是否正确
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config.settings import settings


async def test_asyncpg_direct():
    """测试 asyncpg 直连（禁用预处理语句缓存）"""
    print("\n🔍 测试 asyncpg 直连...")
    try:
        conn = await asyncpg.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            statement_cache_size=0,  # 必须禁用（Supabase Transaction Mode）
        )
        
        # 执行测试查询
        version = await conn.fetchval("SELECT version()")
        result = await conn.fetchval("SELECT 1 + 1")
        
        await conn.close()
        
        print(f"✅ asyncpg 连接成功")
        print(f"   数据库版本: {version[:50]}...")
        print(f"   测试查询: 1 + 1 = {result}")
        return True
        
    except Exception as e:
        print(f"❌ asyncpg 连接失败: {e}")
        print(f"   错误类型: {type(e).__name__}")
        return False


async def test_sqlalchemy_engine():
    """测试 SQLAlchemy 引擎（禁用预处理语句缓存）"""
    print("\n🔍 测试 SQLAlchemy 引擎...")
    try:
        engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=2,
            max_overflow=2,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={
                "statement_cache_size": 0,
                "max_cached_statement_lifetime": 0,
            }
        )
        
        # 执行测试查询
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 + 1 AS result"))
            value = result.scalar()
            
            # 测试表查询
            tables_result = await conn.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            )
            table_count = tables_result.scalar()
        
        await engine.dispose()
        
        print(f"✅ SQLAlchemy 连接成功")
        print(f"   测试查询: 1 + 1 = {value}")
        print(f"   public schema 表数量: {table_count}")
        return True
        
    except Exception as e:
        print(f"❌ SQLAlchemy 连接失败: {e}")
        print(f"   错误类型: {type(e).__name__}")
        return False


async def test_connection_pool():
    """测试连接池配置"""
    print("\n🔍 测试连接池配置...")
    try:
        from app.db.session import get_engine, get_pool_status
        
        # 获取引擎
        engine = await get_engine()
        
        # 获取连接池状态
        pool_status = await get_pool_status()
        
        print("✅ 连接池配置正常")
        print(f"   Pool Size: {pool_status['pool_size']}")
        print(f"   Checked Out: {pool_status['checked_out']}")
        print(f"   Max Connections: {pool_status['max_connections']}")
        print(f"   Usage Ratio: {pool_status['usage_ratio']}%")
        return True
        
    except Exception as e:
        print(f"❌ 连接池测试失败: {e}")
        print(f"   错误类型: {type(e).__name__}")
        return False


async def test_checkpointer_url():
    """测试 Checkpointer 连接 URL"""
    print("\n🔍 测试 Checkpointer 连接...")
    try:
        import psycopg
        from psycopg_pool import AsyncConnectionPool
        
        # 创建临时连接池
        pool = AsyncConnectionPool(
            conninfo=settings.CHECKPOINTER_DATABASE_URL,
            min_size=1,
            max_size=2,
            open=False,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,  # 必须禁用（Supabase Transaction Mode）
            },
        )
        
        await pool.open()
        
        # 测试连接
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 + 1")
                result = await cur.fetchone()
        
        await pool.close()
        
        print(f"✅ Checkpointer 连接成功")
        print(f"   测试查询: 1 + 1 = {result[0]}")
        return True
        
    except Exception as e:
        print(f"❌ Checkpointer 连接失败: {e}")
        print(f"   错误类型: {type(e).__name__}")
        return False


async def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 Supabase 连接配置测试")
    print("=" * 60)
    
    print(f"\n📋 连接配置:")
    print(f"   Host: {settings.POSTGRES_HOST}")
    print(f"   Port: {settings.POSTGRES_PORT}")
    print(f"   User: {settings.POSTGRES_USER}")
    print(f"   Database: {settings.POSTGRES_DB}")
    print(f"   Pool Size: {settings.DB_POOL_SIZE}")
    print(f"   Max Overflow: {settings.DB_MAX_OVERFLOW}")
    
    # 执行所有测试
    results = []
    
    results.append(("asyncpg 直连", await test_asyncpg_direct()))
    results.append(("SQLAlchemy 引擎", await test_sqlalchemy_engine()))
    results.append(("连接池配置", await test_connection_pool()))
    results.append(("Checkpointer 连接", await test_checkpointer_url()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！Supabase 连接配置正确。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查配置。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


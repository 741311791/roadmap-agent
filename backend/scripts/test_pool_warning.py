#!/usr/bin/env python3
"""
测试 AsyncConnectionPool 初始化是否产生警告

运行此脚本验证修复是否生效
"""
import asyncio
import warnings
from psycopg_pool import AsyncConnectionPool
import os

# 捕获所有警告
warnings.simplefilter("always")


async def test_pool_initialization():
    """测试连接池初始化"""
    print("=" * 80)
    print("测试 AsyncConnectionPool 初始化")
    print("=" * 80)
    print()
    
    # 构建数据库 URL
    db_url = (
        f"postgresql://{os.getenv('POSTGRES_USER', 'roadmap_user')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'roadmap_pass')}"
        f"@{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}"
        f"/{os.getenv('POSTGRES_DB', 'roadmap_db')}"
    )
    
    print("📝 方式 1: 旧方式（构造时自动打开 - 会产生警告）")
    print("-" * 80)
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # 旧方式：构造时自动打开
            pool_old = AsyncConnectionPool(
                conninfo=db_url,
                min_size=1,
                max_size=2,
                timeout=5,
                # 没有 open=False 参数
            )
            
            if w:
                print(f"⚠️  警告数量: {len(w)}")
                for warning in w:
                    print(f"   类型: {warning.category.__name__}")
                    print(f"   消息: {warning.message}")
            else:
                print("✅ 无警告")
            
            await pool_old.close()
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print()
    print("📝 方式 2: 新方式（手动打开 - 不会产生警告）")
    print("-" * 80)
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # 新方式：使用 open=False，然后手动调用 open()
            pool_new = AsyncConnectionPool(
                conninfo=db_url,
                min_size=1,
                max_size=2,
                timeout=5,
                open=False,  # ✅ 添加此参数
            )
            
            # 手动打开连接池
            await pool_new.open()
            
            if w:
                print(f"⚠️  警告数量: {len(w)}")
                for warning in w:
                    print(f"   类型: {warning.category.__name__}")
                    print(f"   消息: {warning.message}")
            else:
                print("✅ 无警告（修复成功）")
            
            await pool_new.close()
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print()
    print("=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_pool_initialization())


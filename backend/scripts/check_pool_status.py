#!/usr/bin/env python3
"""
连接池状态检查工具

用于诊断数据库连接池使用情况，帮助定位连接泄漏问题。
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import get_pool_status


async def main():
    """主函数：查询并打印连接池状态"""
    print("🔍 正在检查数据库连接池状态...\n")
    
    try:
        status = await get_pool_status()
        
        print("=" * 60)
        print("数据库连接池状态")
        print("=" * 60)
        print(f"✅ 池大小 (pool_size):         {status['pool_size']}")
        print(f"🔓 空闲连接 (checked_in):      {status['checked_in']}")
        print(f"🔒 使用中连接 (checked_out):   {status['checked_out']}")
        print(f"📈 溢出连接 (overflow):        {status['overflow']}")
        print(f"❌ 失效连接 (invalid):         {status['invalid']}")
        print(f"⚙️  最大溢出 (max_overflow):   {status['max_overflow']}")
        print(f"🎯 最大连接数:                 {status['max_connections']}")
        print(f"📊 使用率:                     {status['usage_ratio']}%")
        print("=" * 60)
        
        # 健康评估
        usage_ratio = status['usage_ratio']
        if usage_ratio > 90:
            print("\n🚨 警告: 连接池使用率超过 90%，可能即将耗尽！")
            print("建议:")
            print("  1. 检查是否有连接泄漏（未关闭的会话）")
            print("  2. 降低 Celery Worker 并发数")
            print("  3. 增加连接池大小")
        elif usage_ratio > 70:
            print("\n⚠️  注意: 连接池使用率较高 (>70%)")
            print("建议监控连接池状态，确保不会耗尽")
        else:
            print("\n✅ 连接池状态健康")
        
    except Exception as e:
        print(f"\n❌ 错误: 无法获取连接池状态")
        print(f"   {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


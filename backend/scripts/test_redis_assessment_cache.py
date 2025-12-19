#!/usr/bin/env python3
"""
Redis 缓存测试脚本

验证技术栈测试的 Redis 缓存机制是否正常工作
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.redis_client import redis_client
import structlog

logger = structlog.get_logger()

# 缓存配置（与 tech_assessment.py 保持一致）
ASSESSMENT_CACHE_PREFIX = "assessment:session:"


async def test_redis_connection():
    """测试 Redis 连接"""
    print("=" * 60)
    print("测试 1: Redis 连接")
    print("=" * 60)
    
    try:
        await redis_client.connect()
        pong = await redis_client.ping()
        print(f"✅ Redis 连接成功: {pong}")
        return True
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        return False


async def test_save_assessment():
    """测试保存测验到缓存"""
    print("\n" + "=" * 60)
    print("测试 2: 保存测验到 Redis")
    print("=" * 60)
    
    assessment_id = "test-assessment-12345"
    test_questions = [
        {
            "question": "What is Python?",
            "type": "single_choice",
            "options": ["A language", "A snake", "A framework"],
            "correct_answer": "A language",
            "proficiency_level": "beginner"
        },
        {
            "question": "What is async/await?",
            "type": "single_choice",
            "options": ["Async programming", "Sync programming"],
            "correct_answer": "Async programming",
            "proficiency_level": "intermediate"
        }
    ]
    
    try:
        cache_key = f"{ASSESSMENT_CACHE_PREFIX}{assessment_id}"
        await redis_client.set_json(cache_key, test_questions, ex=7200)
        print(f"✅ 测验保存成功")
        print(f"   - Assessment ID: {assessment_id}")
        print(f"   - Cache Key: {cache_key}")
        print(f"   - Question Count: {len(test_questions)}")
        print(f"   - TTL: 7200 seconds (2 hours)")
        return assessment_id
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        return None


async def test_get_assessment(assessment_id: str):
    """测试从缓存获取测验"""
    print("\n" + "=" * 60)
    print("测试 3: 从 Redis 获取测验")
    print("=" * 60)
    
    try:
        cache_key = f"{ASSESSMENT_CACHE_PREFIX}{assessment_id}"
        questions = await redis_client.get_json(cache_key)
        
        if questions:
            print(f"✅ 测验获取成功")
            print(f"   - Assessment ID: {assessment_id}")
            print(f"   - Question Count: {len(questions)}")
            print(f"\n   题目详情:")
            for i, q in enumerate(questions, 1):
                print(f"      {i}. {q['question']}")
                print(f"         Level: {q['proficiency_level']}")
                print(f"         Answer: {q['correct_answer']}")
            return True
        else:
            print(f"❌ 测验不存在或已过期")
            return False
    except Exception as e:
        print(f"❌ 获取失败: {e}")
        return False


async def test_cache_expiration():
    """测试缓存过期"""
    print("\n" + "=" * 60)
    print("测试 4: 缓存过期机制")
    print("=" * 60)
    
    assessment_id = "test-expiration-67890"
    cache_key = f"{ASSESSMENT_CACHE_PREFIX}{assessment_id}"
    test_data = {"test": "data"}
    
    try:
        # 保存一个 5 秒过期的缓存
        await redis_client.set_json(cache_key, test_data, ex=5)
        print(f"✅ 保存测试数据（5秒过期）")
        
        # 立即读取
        data = await redis_client.get_json(cache_key)
        if data:
            print(f"✅ 立即读取成功: {data}")
        else:
            print(f"❌ 立即读取失败")
            return False
        
        # 等待 6 秒后再读取
        print(f"⏳ 等待 6 秒...")
        await asyncio.sleep(6)
        
        data = await redis_client.get_json(cache_key)
        if data is None:
            print(f"✅ 缓存已过期（符合预期）")
            return True
        else:
            print(f"❌ 缓存未过期（不符合预期）: {data}")
            return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


async def test_cleanup(assessment_id: str):
    """清理测试数据"""
    print("\n" + "=" * 60)
    print("清理测试数据")
    print("=" * 60)
    
    try:
        cache_key = f"{ASSESSMENT_CACHE_PREFIX}{assessment_id}"
        await redis_client.delete(cache_key)
        print(f"✅ 测试数据已清理")
    except Exception as e:
        print(f"⚠️  清理失败: {e}")


async def main():
    """主测试流程"""
    print("\n" + "🚀 " * 20)
    print("技术栈测试 Redis 缓存验证")
    print("🚀 " * 20)
    
    # 测试 1: Redis 连接
    if not await test_redis_connection():
        print("\n❌ Redis 连接失败，终止测试")
        return
    
    # 测试 2: 保存测验
    assessment_id = await test_save_assessment()
    if not assessment_id:
        print("\n❌ 保存测验失败，终止测试")
        return
    
    # 测试 3: 获取测验
    if not await test_get_assessment(assessment_id):
        print("\n❌ 获取测验失败")
    
    # 测试 4: 缓存过期
    await test_cache_expiration()
    
    # 清理测试数据
    await test_cleanup(assessment_id)
    
    # 关闭 Redis 连接
    await redis_client.close()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

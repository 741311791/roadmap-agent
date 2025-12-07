#!/usr/bin/env python3
"""
资源推荐质量快速测试脚本 - 简化版

只测试一个概念，快速验证web_search工具是否被调用
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
import structlog
from app.agents.factory import AgentFactory
from app.models.domain import Concept, LearningPreferences
from app.config.settings import settings

logger = structlog.get_logger()


async def quick_test():
    """快速测试"""
    print("🚀 ResourceRecommender 快速测试")
    print("=" * 80)
    
    # 创建 Agent
    print("\n📦 正在初始化 Agent Factory...")
    factory = AgentFactory(settings)
    recommender = factory.create_resource_recommender()
    
    # 构建测试概念
    concept = Concept(
        concept_id="test-react-hooks",
        name="React Hooks",
        description="React 16.8引入的函数组件状态管理机制",
        difficulty="medium",
        estimated_hours=8,
        keywords=["React", "Hooks", "useState", "useEffect"],
    )
    
    # 用户偏好
    preferences = LearningPreferences(
        learning_goal="学习React Hooks",
        available_hours_per_week=10,
        motivation="提升前端技能",
        current_level="intermediate",
        career_background="前端开发工程师",
        content_preference=["visual", "text"],
        preferred_language="zh",
    )
    
    print(f"\n🔍 测试概念: {concept.name}")
    print(f"📝 描述: {concept.description}")
    print(f"👤 用户水平: {preferences.current_level}")
    print(f"🌐 语言偏好: {preferences.preferred_language}")
    
    try:
        print(f"\n⏳ 正在调用 ResourceRecommenderAgent...")
        print(f"{'─'*80}")
        
        result = await recommender.recommend(
            concept=concept,
            context={"stage_name": "React进阶", "module_name": "状态管理"},
            user_preferences=preferences,
        )
        
        print(f"\n✅ 推荐完成!")
        print(f"{'='*80}")
        print(f"\n📊 推荐结果统计:")
        print(f"   资源数量: {len(result.resources)}")
        print(f"   搜索查询: {', '.join(result.search_queries_used) if result.search_queries_used else '无'}")
        
        # 检查是否使用了web_search
        if result.search_queries_used:
            print(f"\n✅ 已调用 web_search 工具!")
            print(f"   使用的搜索查询数量: {len(result.search_queries_used)}")
            for i, query in enumerate(result.search_queries_used, 1):
                print(f"   {i}. {query}")
        else:
            print(f"\n⚠️  未检测到 web_search 调用（可能LLM未使用工具）")
        
        # 显示推荐的资源
        print(f"\n{'='*80}")
        print(f"📋 推荐的资源列表:")
        print(f"{'='*80}")
        
        for i, resource in enumerate(result.resources, 1):
            print(f"\n{i}. {resource.title}")
            print(f"   类型: {resource.type}")
            print(f"   URL: {resource.url}")
            print(f"   相关性: {resource.relevance_score:.2f}")
            print(f"   描述: {resource.description[:100]}...")
            
            # 验证URL
            print(f"   验证中...", end=" ", flush=True)
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    response = await client.head(resource.url)
                    if response.status_code == 200:
                        print(f"✅ 有效 [200]")
                    elif response.status_code == 403:
                        print(f"⚠️  [403] 可能需要浏览器访问")
                    elif response.status_code == 404:
                        print(f"❌ 404 Not Found")
                    else:
                        print(f"⚠️  [{response.status_code}]")
            except Exception as e:
                print(f"❌ 无法访问: {str(e)[:50]}")
        
        print(f"\n{'='*80}")
        print(f"✅ 测试完成!")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(quick_test())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


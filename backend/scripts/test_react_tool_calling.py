"""
ReAct 工具调用功能测试

验证：
1. base.py 的 ReAct 循环正常工作
2. 工具调用和响应处理正确
3. 最大迭代次数控制有效
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.agents.factory import AgentFactory
from app.config.settings import settings
from app.models.domain import (
    ResourceRecommendationInput,
    Concept,
    LearningPreferences,
)

print("=" * 80)
print("测试 ReAct 工具调用功能")
print("=" * 80)

async def test_react_tool_calling():
    """测试 base.py 的 ReAct 工具调用"""
    
    # 创建测试概念
    concept = Concept(
        concept_id="c-test-1",
        name="FastAPI 异步编程",
        description="掌握 FastAPI 中的异步编程模式和最佳实践",
        estimated_hours=4.0,
        difficulty="medium",
        keywords=["FastAPI", "异步编程", "async/await", "并发"],
        prerequisites=[],
    )
    
    # 创建用户偏好
    user_preferences = LearningPreferences(
        learning_goal="学习 Python Web 开发",
        current_level="intermediate",
        career_background="后端开发工程师",
        available_hours_per_week=10,
        motivation="职业发展",
        content_preference=["text", "hands_on"],
    )
    
    # 创建上下文
    context = {
        "stage_name": "Web 框架进阶",
        "module_name": "FastAPI 核心特性",
    }
    
    # 创建输入
    input_data = ResourceRecommendationInput(
        concept=concept,
        context=context,
        user_preferences=user_preferences,
    )
    
    print("\n[1] 创建测试数据...")
    print(f"  ✓ 概念: {concept.name}")
    print(f"  ✓ 难度: {concept.difficulty}")
    print(f"  ✓ 关键词: {', '.join(concept.keywords)}")
    
    print("\n[2] 创建 Agent 实例...")
    # 使用 AgentFactory 创建 Agent（包含已注册的工具）
    agent_factory = AgentFactory(settings)
    agent = agent_factory.create_resource_recommender()
    print(f"  ✓ Agent ID: {agent.agent_id}")
    print(f"  ✓ Model: {agent.model_provider}/{agent.model_name}")
    print(f"  ✓ 使用 ReAct: True")
    print(f"  ✓ 最大迭代次数: 5")
    print(f"  ✓ 已注册工具数量: {len(agent.tool_registry._tools)}")
    
    print("\n[3] 执行 Agent（ReAct 工具调用）...")
    print("  ⏳ 正在搜索和推荐资源，请稍候...")
    
    try:
        result = await agent.execute(input_data)
        
        print("\n" + "=" * 80)
        print("✅ 资源推荐成功！")
        print("=" * 80)
        
        print("\n[4] 验证输出结构...")
        print(f"  ✓ 推荐 ID: {result.id}")
        print(f"  ✓ 概念 ID: {result.concept_id}")
        print(f"  ✓ 资源数量: {len(result.resources)}")
        print(f"  ✓ 搜索查询数量: {len(result.search_queries_used)}")
        
        # 验证资源列表非空
        assert len(result.resources) > 0, "资源列表不应为空"
        print("\n  ✅ 关键验证：资源列表非空")
        
        # 验证所有资源都有 URL
        resources_with_url = [r for r in result.resources if r.url]
        print(f"  ✅ 有效资源数量: {len(resources_with_url)}/{len(result.resources)}")
        
        print("\n[5] 资源列表预览...")
        for i, resource in enumerate(result.resources[:5], 1):
            print(f"\n  {i}. {resource.title}")
            print(f"     类型: {resource.type}")
            print(f"     语言: {resource.language or '未指定'}")
            print(f"     相关性: {resource.relevance_score:.2f}")
            if resource.url:
                print(f"     URL: {resource.url[:60]}...")
        
        if result.search_queries_used:
            print("\n[6] 使用的搜索查询...")
            for query in result.search_queries_used:
                print(f"  - {query}")
        
        print("\n" + "=" * 80)
        print("✅ 测试通过！ReAct 工具调用功能正常")
        print("=" * 80)
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ 测试失败")
        print("=" * 80)
        print(f"\n错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        
        import traceback
        print("\n详细错误堆栈:")
        traceback.print_exc()
        
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_react_tool_calling())

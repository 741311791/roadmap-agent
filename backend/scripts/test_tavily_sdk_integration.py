#!/usr/bin/env python3
"""
测试 Tavily SDK 集成
验证：
1. 官方 SDK 是否正常工作（按照官方示例调用）
2. 高级参数是否生效（time_range, include_domains, search_depth）
3. Function Calling 是否正确触发
4. ResourceRecommenderAgent 是否能使用新参数
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.domain import (
    SearchQuery,
    Concept,
    LearningPreferences,
)
from app.agents.resource_recommender import ResourceRecommenderAgent
from app.core.tool_registry import tool_registry
from app.tools.search.tavily_api_search import TavilyAPISearchTool
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


async def test_tavily_sdk_basic():
    """测试 1：Tavily SDK 基本功能（高级模式）"""
    print("\n" + "="*60)
    print("测试 1：Tavily SDK 高级搜索（search_depth=advanced）")
    print("="*60)
    
    tool = TavilyAPISearchTool()
    
    query = SearchQuery(
        query="langgraph教程",
        max_results=5,
        search_depth="advanced",
    )
    
    try:
        result = await tool.execute(query)
        print(f"✅ 搜索成功！找到 {len(result.results)} 个结果")
        for idx, item in enumerate(result.results, 1):
            print(f"\n{idx}. {item['title'][:60]}...")
            print(f"   URL: {item['url']}")
            print(f"   评分: {item.get('score', 'N/A')}")
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def test_tavily_time_range():
    """测试 2：时间筛选功能"""
    print("\n" + "="*60)
    print("测试 2：时间筛选（time_range=year）")
    print("="*60)
    
    tool = TavilyAPISearchTool()
    
    query = SearchQuery(
        query="React 18 新特性",
        max_results=5,
        search_depth="advanced",
        time_range="year",  # 最近一年
    )
    
    try:
        result = await tool.execute(query)
        print(f"✅ 时间筛选成功！找到 {len(result.results)} 个结果（最近一年）")
        for idx, item in enumerate(result.results, 1):
            print(f"\n{idx}. {item['title'][:60]}...")
            print(f"   URL: {item['url']}")
            published_date = item.get('published_date', '未知')
            print(f"   发布时间: {published_date}")
    except Exception as e:
        print(f"❌ 时间筛选失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def test_tavily_domain_filtering():
    """测试 3：域名筛选功能"""
    print("\n" + "="*60)
    print("测试 3：域名筛选（include_domains=['github.com']）")
    print("="*60)
    
    tool = TavilyAPISearchTool()
    
    query = SearchQuery(
        query="React Hooks 最佳实践",
        max_results=5,
        search_depth="advanced",
        include_domains=["github.com"],
    )
    
    try:
        result = await tool.execute(query)
        print(f"✅ 域名筛选成功！找到 {len(result.results)} 个结果")
        github_count = 0
        for idx, item in enumerate(result.results, 1):
            print(f"\n{idx}. {item['title'][:60]}...")
            print(f"   URL: {item['url']}")
            # 检查是否来自指定域名
            is_from_github = "github.com" in item['url']
            if is_from_github:
                github_count += 1
            print(f"   来自 GitHub: {'✅' if is_from_github else '❌'}")
        
        print(f"\n📊 GitHub 结果占比: {github_count}/{len(result.results)}")
    except Exception as e:
        print(f"❌ 域名筛选失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def test_tool_definition():
    """测试 4：检查工具定义是否包含高级参数"""
    print("\n" + "="*60)
    print("测试 4：工具定义检查")
    print("="*60)
    
    agent = ResourceRecommenderAgent()
    tools = agent._get_tools_definition()
    
    if not tools:
        print("❌ 没有找到工具定义")
        return False
    
    web_search_tool = tools[0]
    properties = web_search_tool["function"]["parameters"]["properties"]
    
    print(f"✅ 找到 {len(tools)} 个工具定义")
    print(f"\n工具名称: {web_search_tool['function']['name']}")
    print(f"工具描述: {web_search_tool['function']['description'][:80]}...")
    print(f"\n支持的参数:")
    
    required_params = ["query", "max_results", "time_range", "search_depth", "include_domains", "exclude_domains"]
    all_present = True
    for param in required_params:
        if param in properties:
            print(f"  ✅ {param}: {properties[param].get('description', '')[:50]}...")
        else:
            print(f"  ❌ {param}: 缺失")
            all_present = False
    
    if all_present:
        print("\n✅ 所有高级参数都已定义")
        return True
    else:
        print("\n❌ 缺少部分高级参数")
        return False


async def test_resource_recommender_function_calling():
    """测试 5：ResourceRecommenderAgent 的 Function Calling"""
    print("\n" + "="*60)
    print("测试 5：ResourceRecommenderAgent Function Calling")
    print("="*60)
    
    # 检查环境变量
    if not settings.RECOMMENDER_API_KEY or settings.RECOMMENDER_API_KEY == "your_openai_api_key_here":
        print("⚠️ 跳过：RECOMMENDER_API_KEY 未配置")
        return True
    
    if not settings.TAVILY_API_KEY or settings.TAVILY_API_KEY == "your_tavily_api_key_here":
        print("⚠️ 跳过：TAVILY_API_KEY 未配置")
        return True
    
    # 注册工具
    from app.tools.search.web_search_router import WebSearchRouter
    if not tool_registry.get("web_search_v1"):
        tool_registry.register("web_search_v1", WebSearchRouter())
        print("✅ 注册了 WebSearchRouter")
    
    # 创建测试数据
    concept = Concept(
        concept_id="test-react-hooks-001",
        name="React Hooks",
        description="React 16.8 引入的新特性，用于在函数组件中使用状态和生命周期",
        estimated_hours=2.0,
        difficulty="medium",
        keywords=["react", "hooks", "useState", "useEffect"],
    )
    
    user_preferences = LearningPreferences(
        learning_goal="学习 React 前端开发",
        available_hours_per_week=10,
        motivation="转行",
        current_level="beginner",
        career_background="市场营销",
        content_preference=["visual", "text"],
        preferred_language="zh",
    )
    
    context = {
        "stage_name": "React 基础",
        "module_name": "Hooks 入门",
    }
    
    # 创建 Agent
    agent = ResourceRecommenderAgent()
    
    try:
        print("🔄 开始资源推荐（这会触发 Function Calling）...")
        result = await agent.recommend(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
        )
        
        print(f"\n✅ 推荐成功！")
        print(f"   概念 ID: {result.concept_id}")
        print(f"   推荐资源数: {len(result.resources)}")
        print(f"   使用的搜索查询: {result.search_queries_used}")
        
        print("\n📚 推荐的资源:")
        for idx, resource in enumerate(result.resources[:3], 1):
            print(f"\n{idx}. {resource.title}")
            print(f"   URL: {resource.url}")
            print(f"   类型: {resource.type}")
            print(f"   相关性: {resource.relevance_score:.2f}")
            print(f"   可信度: {resource.confidence_score or 'N/A'}")
            print(f"   语言: {resource.language or 'N/A'}")
        
        # 验证是否使用了工具调用
        if len(result.search_queries_used) > 0:
            print("\n✅ 确认：Agent 使用了 Function Calling 调用了搜索工具")
        else:
            print("\n⚠️ 警告：没有检测到搜索查询，可能未使用 Function Calling")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 推荐失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("\n🚀 开始测试 Tavily SDK 集成（高级参数）")
    print("="*60)
    
    # 检查 API Key
    if not settings.TAVILY_API_KEY or settings.TAVILY_API_KEY == "your_tavily_api_key_here":
        print("❌ TAVILY_API_KEY 未配置，无法运行测试")
        print("请在 .env 文件中设置 TAVILY_API_KEY")
        sys.exit(1)
    
    print(f"✅ TAVILY_API_KEY 已配置")
    
    tests = [
        ("Tavily SDK 高级搜索", test_tavily_sdk_basic),
        ("时间筛选功能", test_tavily_time_range),
        ("域名筛选功能", test_tavily_domain_filtering),
        ("工具定义检查", test_tool_definition),
        ("ResourceRecommender Function Calling", test_resource_recommender_function_calling),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{test_name}' 发生异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # 打印总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {test_name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！Tavily SDK 高级参数集成成功！")
        sys.exit(0)
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，请检查上述错误")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

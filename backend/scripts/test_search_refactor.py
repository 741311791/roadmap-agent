"""
Web Search 重构验证测试脚本

测试新的工具架构：
- TavilyAPISearchTool
- DuckDuckGoSearchTool
- WebSearchRouter
- ResourceRecommender with MCP
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.tool_registry import tool_registry
from app.models.domain import SearchQuery
from app.config.settings import settings


async def test_individual_tools():
    """测试独立的搜索工具"""
    print("=" * 70)
    print("测试 1：独立搜索工具")
    print("=" * 70)
    
    # 测试查询
    test_query = SearchQuery(
        query="Python 官方文档",
        max_results=3,
        language="zh",
    )
    
    # 测试 TavilyAPISearchTool
    print("\n1.1 测试 TavilyAPISearchTool")
    print("-" * 70)
    tavily_tool = tool_registry.get("tavily_api_search")
    if tavily_tool:
        if settings.TAVILY_API_KEY and settings.TAVILY_API_KEY != "your_tavily_api_key_here":
            try:
                result = await tavily_tool.execute(test_query)
                print(f"✅ Tavily API 搜索成功")
                print(f"   结果数量: {result.total_found}")
                if result.results:
                    print(f"   第一个结果: {result.results[0]['title'][:50]}...")
            except Exception as e:
                print(f"❌ Tavily API 搜索失败: {e}")
        else:
            print("⚠️  Tavily API Key 未配置，跳过测试")
    else:
        print("❌ TavilyAPISearchTool 未注册")
    
    # 测试 DuckDuckGoSearchTool
    print("\n1.2 测试 DuckDuckGoSearchTool")
    print("-" * 70)
    ddg_tool = tool_registry.get("duckduckgo_search")
    if ddg_tool:
        try:
            result = await ddg_tool.execute(test_query)
            print(f"✅ DuckDuckGo 搜索成功")
            print(f"   结果数量: {result.total_found}")
            if result.results:
                print(f"   第一个结果: {result.results[0]['title'][:50]}...")
        except Exception as e:
            print(f"❌ DuckDuckGo 搜索失败: {e}")
    else:
        print("❌ DuckDuckGoSearchTool 未注册")


async def test_web_search_router():
    """测试 WebSearchRouter 路由逻辑"""
    print("\n" + "=" * 70)
    print("测试 2：WebSearchRouter 路由逻辑")
    print("=" * 70)
    
    router = tool_registry.get("web_search_v1")
    if not router:
        print("❌ WebSearchRouter 未注册")
        return
    
    test_queries = [
        SearchQuery(query="React Hooks tutorial", max_results=3, language="en"),
        SearchQuery(query="Python 机器学习教程", max_results=3, language="zh"),
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n2.{i} 测试查询: {query.query}")
        print("-" * 70)
        try:
            result = await router.execute(query)
            print(f"✅ 搜索成功")
            print(f"   结果数量: {result.total_found}")
            if result.results:
                print(f"   前两个结果:")
                for idx, r in enumerate(result.results[:2], 1):
                    print(f"     {idx}. {r['title'][:60]}...")
        except Exception as e:
            print(f"❌ 搜索失败: {e}")


async def test_resource_recommender_integration():
    """测试 ResourceRecommender 集成"""
    print("\n" + "=" * 70)
    print("测试 3：ResourceRecommender 集成（工具定义）")
    print("=" * 70)
    
    from app.agents.resource_recommender import ResourceRecommenderAgent
    
    # 创建 Agent 实例
    agent = ResourceRecommenderAgent()
    
    # 获取工具定义
    tools = agent._get_tools_definition()
    
    print(f"\n工具数量: {len(tools)}")
    print("-" * 70)
    
    for i, tool in enumerate(tools, 1):
        tool_type = tool.get("type")
        print(f"\n工具 {i}:")
        print(f"  类型: {tool_type}")
        
        if tool_type == "function":
            func_name = tool.get("function", {}).get("name")
            func_desc = tool.get("function", {}).get("description", "")[:80]
            print(f"  名称: {func_name}")
            print(f"  描述: {func_desc}...")
        elif tool_type == "mcp":
            server_label = tool.get("server_label")
            print(f"  服务器: {server_label}")
            print(f"  说明: Tavily MCP 工具（由 OpenAI LLM 自动调用）")
    
    # 检查 MCP 工具是否正确配置
    has_mcp = any(t.get("type") == "mcp" for t in tools)
    has_function = any(t.get("type") == "function" for t in tools)
    
    print(f"\n工具配置检查:")
    print(f"  ✓ 普通 function calling 工具: {'是' if has_function else '否'}")
    print(f"  ✓ MCP 工具: {'是' if has_mcp else '否（需要 OpenAI LLM + Tavily API Key）'}")
    
    if agent.model_provider == "openai" and not has_mcp:
        if not settings.TAVILY_API_KEY or settings.TAVILY_API_KEY == "your_tavily_api_key_here":
            print("\n💡 提示: 配置 TAVILY_API_KEY 以启用 MCP 工具")


def test_tool_registry():
    """测试工具注册表"""
    print("\n" + "=" * 70)
    print("测试 4：工具注册表")
    print("=" * 70)
    
    all_tools = tool_registry.list_all()
    
    print(f"\n已注册工具数量: {len(all_tools)}")
    print("-" * 70)
    
    for tool_id, tool in all_tools.items():
        tool_class = tool.__class__.__name__
        print(f"  ✓ {tool_id:30s} → {tool_class}")
    
    # 检查关键工具
    required_tools = [
        "web_search_v1",        # WebSearchRouter
        "tavily_api_search",    # TavilyAPISearchTool
        "duckduckgo_search",    # DuckDuckGoSearchTool
    ]
    
    print(f"\n关键工具检查:")
    for tool_id in required_tools:
        exists = tool_id in all_tools
        status = "✅" if exists else "❌"
        print(f"  {status} {tool_id}")


async def main():
    """运行所有测试"""
    print("🚀 Web Search 重构验证测试")
    print("=" * 70)
    print()
    
    try:
        # 测试 1: 独立工具
        await test_individual_tools()
        
        # 测试 2: 路由器
        await test_web_search_router()
        
        # 测试 3: ResourceRecommender 集成
        await test_resource_recommender_integration()
        
        # 测试 4: 工具注册表
        test_tool_registry()
        
        print("\n" + "=" * 70)
        print("✅ 所有测试完成")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


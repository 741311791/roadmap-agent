"""
TutorialGeneratorAgent 独立测试脚本

用法：
    uv run python scripts/test_tutorial_generator_standalone.py

功能：
- 独立测试 TutorialGeneratorAgent 的完整流程
- 验证 ReAct 模式的工具调用
- 验证 Context7 MCP 集成
- 输出详细的执行日志

依赖：
- 需要配置 GENERATOR_PROVIDER、GENERATOR_MODEL、GENERATOR_API_KEY
- 需要 Context7 MCP Server 配置（mcp_servers.json）
"""
import asyncio
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.models.domain import Concept, LearningPreferences
import structlog

# 配置日志输出到控制台
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

logger = structlog.get_logger()


async def test_tutorial_generator():
    """测试 TutorialGeneratorAgent 完整流程"""
    
    print("=" * 80)
    print("TutorialGeneratorAgent 独立测试")
    print("=" * 80)
    
    # 1. 创建测试数据
    print("\n[1/6] 创建测试数据...")
    
    test_concept = Concept(
        concept_id="test-react-hooks-001",
        name="React Hooks",
        description="React 16.8 引入的状态管理特性，允许在函数组件中使用状态和其他 React 特性",
        difficulty="medium",
        estimated_hours=3.0,
        prerequisites=["react-basics", "javascript-es6"],
        keywords=["useState", "useEffect", "hooks", "functional-components"],
    )
    
    test_preferences = LearningPreferences(
        learning_goal="掌握 React Hooks 的原理和最佳实践",
        available_hours_per_week=10,
        motivation="提升前端开发技能",
        current_level="intermediate",
        career_background="前端开发 2 年经验",
        content_preference=["visual", "text", "hands_on"],
        primary_language="zh",
    )
    
    test_context = {
        "roadmap_id": "test-roadmap-001",
        "stage_name": "React 进阶",
        "module_name": "状态管理",
        "content_version": 1,
    }
    
    print(f"✅ 测试概念: {test_concept.name}")
    print(f"✅ 用户水平: {test_preferences.current_level}")
    
    # 2. 创建 Agent
    print("\n[2/6] 初始化 TutorialGeneratorAgent...")
    
    try:
        agent = TutorialGeneratorAgent()
        print(f"✅ Agent 初始化成功")
        print(f"   - Agent ID: {agent.agent_id}")
        print(f"   - Model: {agent.model_provider}/{agent.model_name}")
    except Exception as e:
        print(f"❌ Agent 初始化失败: {e}")
        return
    
    # 3. 测试场景判断
    print("\n[3/6] 判断场景类型...")
    
    try:
        is_dev_scenario = await agent._is_development_scenario(test_concept)
        scenario_type = "开发场景" if is_dev_scenario else "非开发场景"
        print(f"✅ 场景判断完成: {scenario_type}")
        print(f"   - 概念: {test_concept.name}")
        print(f"   - 结果: {'需要查询官方文档' if is_dev_scenario else '使用知识库'}")
    except Exception as e:
        print(f"❌ 场景判断失败: {e}")
        is_dev_scenario = True  # 默认为开发场景
    
    # 4. 测试工具加载
    print("\n[4/6] 加载工具...")
    
    try:
        tools = await agent._get_tools(is_dev_scenario=is_dev_scenario)
        print(f"✅ 工具加载成功: {len(tools)} 个工具")
        if tools:
            for tool in tools:
                # tools 是 OpenAI function calling 格式的字典列表
                tool_name = tool.get('function', {}).get('name', 'Unknown')
                tool_desc = tool.get('function', {}).get('description', 'No description')
                print(f"   - {tool_name}: {tool_desc[:60]}...")
        else:
            print(f"   - 无工具（非开发场景）")
    except Exception as e:
        print(f"❌ 工具加载失败: {e}")
        print(f"   错误详情: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return
    
    # 5. 测试 System Prompt 生成
    print("\n[5/6] 生成 System Prompt...")
    
    try:
        system_prompt = agent._get_system_prompt(
            concept=test_concept,
            context=test_context,
            user_preferences=test_preferences,
            is_dev_scenario=is_dev_scenario,
        )
        print(f"✅ System Prompt 生成成功")
        print(f"   - 长度: {len(system_prompt)} 字符")
        print(f"   - 场景类型: {'开发场景' if is_dev_scenario else '非开发场景'}")
        if is_dev_scenario:
            print(f"   - 包含 'resolve-library-id': {'resolve-library-id' in system_prompt}")
            print(f"   - 包含 'query-docs': {'query-docs' in system_prompt}")
        print(f"   - 包含 'JSON 格式': {'json' in system_prompt.lower()}")
        print(f"   - 包含 'Mermaid': {'mermaid' in system_prompt.lower()}")
    except Exception as e:
        print(f"❌ System Prompt 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 6. 测试教程生成（完整流程）
    print("\n[6/6] 生成教程（完整流程）...")
    print("⚠️  注意：此步骤会调用真实的 LLM API 并可能产生费用")
    print("⚠️  如果不想执行真实调用，请按 Ctrl+C 中断")
    
    # 给用户 3 秒时间中断
    import sys
    for i in range(3, 0, -1):
        print(f"   {i} 秒后开始...", end="\r")
        await asyncio.sleep(1)
    
    print("\n   开始生成教程...")
    
    try:
        result = await agent.generate(
            concept=test_concept,
            context=test_context,
            user_preferences=test_preferences,
        )
        
        print(f"\n✅ 教程生成成功！")
        print(f"   - Concept ID: {result.concept_id}")
        print(f"   - Tutorial ID: {result.tutorial_id}")
        print(f"   - Title: {result.title}")
        print(f"   - Summary: {result.summary[:100]}...")
        print(f"   - Content URL: {result.content_url}")
        print(f"   - Status: {result.content_status}")
        print(f"   - Estimated Time: {result.estimated_completion_time} 分钟")
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断测试")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 教程生成失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_tutorial_generator())


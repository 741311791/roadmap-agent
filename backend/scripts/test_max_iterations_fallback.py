"""
测试 ReAct 达到最大迭代次数时的优雅降级

用法：
    uv run python scripts/test_max_iterations_fallback.py

功能：
- 故意设置很小的 max_iterations (如 3)
- 验证达到上限时，LLM 能否基于已收集信息生成输出
- 而不是直接失败
"""
import asyncio
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.models.domain import Concept, LearningPreferences
import structlog

# 配置日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

logger = structlog.get_logger()


async def test_max_iterations_graceful_degradation():
    """测试达到最大迭代次数时的优雅降级"""
    
    print("=" * 80)
    print("测试 ReAct 最大迭代次数优雅降级")
    print("=" * 80)
    
    # 创建一个需要查询多次的复杂概念
    test_concept = Concept(
        concept_id="test-complex-concept",
        name="React 高级性能优化与服务端渲染完整指南",
        description="涵盖 React Performance Optimization、Memo、useMemo、useCallback、Code Splitting、Lazy Loading、Server-Side Rendering、Suspense 等多个高级主题",
        difficulty="hard",
        estimated_hours=8.0,
        prerequisites=["react-hooks", "react-advanced"],
        keywords=["performance", "optimization", "ssr", "suspense", "memo"],
    )
    
    test_preferences = LearningPreferences(
        learning_goal="全面掌握 React 性能优化和SSR",
        available_hours_per_week=10,
        motivation="提升大型应用性能",
        current_level="advanced",
        career_background="高级前端工程师",
        content_preference=["visual", "text", "hands_on"],
        primary_language="zh",
    )
    
    test_context = {
        "roadmap_id": "test-roadmap-max-iter",
        "stage_name": "React 性能优化",
        "module_name": "高级性能技术",
        "content_version": 1,
    }
    
    print(f"\n✅ 测试概念: {test_concept.name}")
    print(f"✅ 难度: {test_concept.difficulty}")
    print(f"⚠️  这是一个复杂主题，可能需要多次工具调用")
    
    # 创建 Agent
    print("\n初始化 TutorialGeneratorAgent...")
    agent = TutorialGeneratorAgent()
    
    # 修改 generate 方法，使用很小的 max_iterations
    print("\n⚠️  设置 max_iterations = 3 (故意设置很小)")
    print("⚠️  预期：LLM 会在3次工具调用后被强制输出\n")
    
    # 给用户时间准备
    for i in range(3, 0, -1):
        print(f"   {i} 秒后开始...", end="\r")
        await asyncio.sleep(1)
    
    print("\n开始生成教程...\n")
    
    try:
        # 手动调用内部方法，传入小的 max_iterations
        import uuid
        from app.models.domain import TutorialGenerationInput
        
        input_data = TutorialGenerationInput(
            concept=test_concept,
            context=test_context,
            user_preferences=test_preferences,
        )
        
        # 判断场景
        is_dev_scenario = await agent._is_development_scenario(test_concept)
        print(f"✅ 场景类型: {'开发场景' if is_dev_scenario else '非开发场景'}\n")
        
        # 获取工具
        tools = await agent._get_tools(is_dev_scenario=is_dev_scenario)
        print(f"✅ 加载工具: {len(tools)} 个\n")
        
        # 生成 Prompt
        system_prompt = agent._get_system_prompt(
            concept=test_concept,
            context=test_context,
            user_preferences=test_preferences,
            is_dev_scenario=is_dev_scenario,
        )
        
        user_message = f"请为概念 '{test_concept.name}' 生成教程。"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # ⭐ 关键：使用很小的 max_iterations
        print("=" * 80)
        print("开始 ReAct 循环（max_iterations=3）")
        print("=" * 80)
        
        response = await agent._call_llm(
            messages=messages,
            tools=tools if tools else None,
            use_react=True if tools else False,
            max_iterations=3,  # 故意设置很小
        )
        
        print("\n" + "=" * 80)
        print("✅ ReAct 循环完成（未抛出异常）")
        print("=" * 80)
        
        # 检查返回结果
        content = response.choices[0].message.content
        
        if not content:
            print("\n❌ 错误：返回内容为空")
            return
        
        print(f"\n✅ 生成内容长度: {len(content)} 字符")
        print(f"\n内容预览（前500字符）：")
        print("-" * 80)
        print(content[:500])
        print("-" * 80)
        
        # 尝试解析
        try:
            tutorial_markdown, metadata = agent._parse_output(content, test_concept)
            print(f"\n✅ JSON解析成功")
            print(f"   - Markdown长度: {len(tutorial_markdown)} 字符")
            print(f"   - 元数据: {metadata}")
            print(f"\n🎉 测试成功！达到max_iterations后仍能正常生成教程！")
        except Exception as e:
            print(f"\n⚠️  JSON解析失败: {e}")
            print("   但这不影响主要测试目标（验证不会抛出异常）")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_max_iterations_graceful_degradation())

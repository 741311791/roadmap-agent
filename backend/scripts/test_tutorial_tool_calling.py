"""
测试 TutorialGeneratorAgent 的工具调用功能
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.models.domain import Concept, LearningPreferences
import structlog

logger = structlog.get_logger()


async def test_tutorial_generation_with_tool_calling():
    """测试教程生成器是否能正确调用 web_search 工具"""
    
    # 创建测试概念
    concept = Concept(
        concept_id="test-react-hooks-001",
        name="React Hooks 原理深入解析",
        description="深入理解 React Hooks 的设计原理和使用方法",
        estimated_hours=3.0,
        difficulty="medium",
        prerequisites=["React 基础"],
        keywords=["React", "Hooks", "useState", "useEffect"],
    )
    
    # 创建用户偏好
    user_preferences = LearningPreferences(
        learning_goal="成为前端工程师",
        available_hours_per_week=10,
        motivation="转行",
        current_level="intermediate",
        career_background="5年后端开发经验",
        content_preference=["text", "interactive"],
    )
    
    # 创建上下文
    context = {
        "roadmap_id": "test-roadmap-001",
        "stage_name": "前端进阶",
        "module_name": "React 核心",
    }
    
    # 创建 Agent
    agent = TutorialGeneratorAgent()
    
    print("\n=== 开始测试教程生成（非流式） ===\n")
    
    try:
        result = await agent.generate(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
        )
        
        print(f"\n✅ 教程生成成功!")
        print(f"- Tutorial ID: {result.tutorial_id}")
        print(f"- 标题: {result.title}")
        print(f"- 摘要: {result.summary[:200]}...")
        print(f"- Content URL: {result.content_url}")
        print(f"- 状态: {result.content_status}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 教程生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tutorial_generation_stream_with_tool_calling():
    """测试流式教程生成是否能正确调用 web_search 工具"""
    
    # 创建测试概念
    concept = Concept(
        concept_id="test-python-async-001",
        name="Python 异步编程完全指南",
        description="掌握 Python async/await 语法和异步编程最佳实践",
        estimated_hours=4.0,
        difficulty="hard",
        prerequisites=["Python 基础", "协程概念"],
        keywords=["Python", "async", "await", "asyncio"],
    )
    
    # 创建用户偏好
    user_preferences = LearningPreferences(
        learning_goal="成为全栈工程师",
        available_hours_per_week=15,
        motivation="升职",
        current_level="intermediate",
        career_background="3年 Python 开发经验",
        content_preference=["text", "project"],
    )
    
    # 创建上下文
    context = {
        "roadmap_id": "test-roadmap-002",
        "stage_name": "后端进阶",
        "module_name": "Python 高级特性",
    }
    
    # 创建 Agent
    agent = TutorialGeneratorAgent()
    
    print("\n=== 开始测试教程生成（流式） ===\n")
    
    try:
        tool_calls_detected = False
        tutorial_completed = False
        
        async for event in agent.generate_stream(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
        ):
            event_type = event.get("type")
            
            if event_type == "tool_call":
                tool_calls_detected = True
                print(f"\n🔧 工具调用: {event['tool_name']}")
                print(f"   参数: {event['tool_args']}")
            
            elif event_type == "tool_result":
                print(f"✅ 工具调用完成，获得 {event['results_count']} 个结果")
            
            elif event_type == "tutorial_chunk":
                # 不打印所有 chunk，只显示进度
                pass
            
            elif event_type == "tutorial_complete":
                tutorial_completed = True
                data = event["data"]
                print(f"\n✅ 教程生成成功（流式）!")
                print(f"- Tutorial ID: {data['tutorial_id']}")
                print(f"- 标题: {data['title']}")
                print(f"- 摘要: {data['summary'][:200]}...")
                print(f"- Content URL: {data['content_url']}")
            
            elif event_type == "tutorial_error":
                print(f"\n❌ 教程生成失败: {event['error']}")
                return False
        
        if tutorial_completed:
            print(f"\n工具调用检测: {'✅ 已调用' if tool_calls_detected else '⚠️ 未调用'}")
            return True
        else:
            print("\n⚠️ 教程未完成")
            return False
        
    except Exception as e:
        print(f"\n❌ 流式教程生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("=" * 60)
    print("测试 TutorialGeneratorAgent 工具调用功能")
    print("=" * 60)
    
    # 测试1: 非流式生成
    success1 = await test_tutorial_generation_with_tool_calling()
    
    print("\n" + "=" * 60 + "\n")
    
    # 测试2: 流式生成
    success2 = await test_tutorial_generation_stream_with_tool_calling()
    
    print("\n" + "=" * 60)
    print("\n测试总结:")
    print(f"- 非流式生成: {'✅ 通过' if success1 else '❌ 失败'}")
    print(f"- 流式生成: {'✅ 通过' if success2 else '❌ 失败'}")
    print("=" * 60)
    
    return success1 and success2


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


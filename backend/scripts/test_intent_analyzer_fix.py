"""
测试 IntentAnalyzer 修复后的 execute 方法
"""
import asyncio
import json
from app.agents.intent_analyzer import IntentAnalyzerAgent
from app.models.domain import UserRequest, LearningPreferences


async def test_intent_analyzer():
    """测试 IntentAnalyzer.execute 方法"""
    
    # 创建测试请求
    preferences = LearningPreferences(
        learning_goal="学习Python全栈开发，掌握Web开发核心技能",
        available_hours_per_week=10,
        motivation="转行到IT行业",
        current_level="beginner",
        career_background="市场营销3年经验",
        content_preference=["visual", "hands_on"],
        industry="互联网",
        current_role="市场专员",
        tech_stack=[],
        primary_language="zh",
        secondary_language="en",
    )
    
    user_request = UserRequest(
        user_id="test_user_001",
        session_id="test_session_001",
        preferences=preferences,
    )
    
    # 创建 Agent
    agent = IntentAnalyzerAgent()
    
    print("🚀 开始测试 IntentAnalyzer.execute 方法...")
    print(f"📝 学习目标: {preferences.learning_goal}")
    print(f"👤 用户画像: {preferences.current_role} | {preferences.industry}")
    print(f"🌐 语言偏好: 主={preferences.primary_language}, 次={preferences.secondary_language}")
    print("-" * 80)
    
    try:
        # 执行分析
        result = await agent.execute(user_request)
        
        print("✅ 分析成功完成！")
        print("-" * 80)
        print(f"🆔 Roadmap ID: {result.roadmap_id}")
        print(f"🎯 解析的目标: {result.parsed_goal}")
        print(f"🔧 关键技术栈: {', '.join(result.key_technologies[:5])}")
        print(f"📊 难度画像: {result.difficulty_profile[:100]}...")
        print(f"⏱️  时间约束: {result.time_constraint}")
        print(f"🎓 学习重点: {', '.join(result.recommended_focus[:3])}")
        print(f"👤 用户画像摘要: {result.user_profile_summary[:100]}...")
        print(f"📈 技能差距: {', '.join(result.skill_gap_analysis[:3])}")
        print(f"💡 个性化建议: {', '.join(result.personalized_suggestions[:2])}")
        print(f"🛤️  学习路径类型: {result.estimated_learning_path_type}")
        
        if result.content_format_weights:
            print(f"📺 内容格式权重: visual={result.content_format_weights.visual}, hands_on={result.content_format_weights.hands_on}")
        
        if result.language_preferences:
            print(f"🌐 语言配置: 主={result.language_preferences.primary_language}, 次={result.language_preferences.secondary_language}")
            print(f"   资源比例: 主={result.language_preferences.resource_ratio.get('primary', 1.0)}, 次={result.language_preferences.resource_ratio.get('secondary', 0.0)}")
        
        print("-" * 80)
        print("✅ Schema 验证通过！所有字段都正确解析。")
        
        # 输出完整 JSON（用于调试）
        print("\n📄 完整输出 JSON:")
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
        
        return True
        
    except ValueError as e:
        print(f"❌ Schema 验证失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 执行错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_intent_analyzer())
    
    if success:
        print("\n" + "=" * 80)
        print("🎉 测试成功！IntentAnalyzer.execute 方法已正确修复。")
        print("=" * 80)
        exit(0)
    else:
        print("\n" + "=" * 80)
        print("💔 测试失败！请检查错误信息。")
        print("=" * 80)
        exit(1)


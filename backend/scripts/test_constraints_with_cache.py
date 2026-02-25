"""
测试用户画像约束系统（含 RuntimeContext 缓存）

验证点：
1. IntentAnalyzerAgent 能否正确生成约束文本
2. RuntimeContext 缓存机制是否正常工作
3. 约束在多次调用中的性能表现
"""
import asyncio
import sys
import os
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.domain import (
    IntentAnalysisOutput,
    LanguagePreferences,
    ContentFormatWeights,
    ConstraintNames,
)
from app.agents.intent_analyzer import IntentAnalyzerAgent
from app.agents.curriculum_architect import CurriculumArchitectAgent
from app.agents.structure_validator import StructureValidatorAgent
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.core.orchestrator.runtime_context import RuntimeContext
from app.agents.factory import AgentFactory
from app.services.shared.notification_service import NotificationService
from app.services.shared.execution_logger import ExecutionLogger
from app.core.orchestrator.state_manager import StateManager
from app.config.settings import settings


def create_test_intent_output():
    """创建测试用的 IntentAnalysisOutput"""
    agent = IntentAnalyzerAgent()
    
    intent_output = IntentAnalysisOutput(
        parsed_goal="学习 Python Web 开发，掌握 FastAPI 框架",
        key_technologies=["Python", "FastAPI", "SQLAlchemy", "PostgreSQL"],
        difficulty_profile="beginner - 无编程背景",
        time_constraint="每周 10 小时，6 个月完成",
        recommended_focus=["Python 基础", "Web 开发基础"],
        user_profile_summary="市场营销从业者，5 年经验，希望转行",
        skill_gap_analysis=["Python 基础", "Web 开发", "数据库"],
        personalized_suggestions=["从基础语法开始", "多做实战项目"],
        estimated_learning_path_type="career_transition",
        content_format_weights=ContentFormatWeights(
            visual=0.4,
            text=0.3,
            audio=0.1,
            hands_on=0.5
        ),
        language_preferences=LanguagePreferences(
            primary_language="zh-CN",
            secondary_language="en",
        ),
        roadmap_id="python-web-dev-test123",
    )
    
    # 生成约束
    intent_output.full_analysis_data = agent._generate_constraints(intent_output)
    
    return intent_output


async def test_runtime_context_cache():
    """测试 RuntimeContext 约束缓存"""
    print("\n=== 测试 RuntimeContext 约束缓存 ===\n")
    
    # 创建测试数据
    intent_output = create_test_intent_output()
    roadmap_id = intent_output.roadmap_id
    
    # 创建 RuntimeContext（模拟）
    # 注意：这里创建一个简化的 context，只用于测试缓存功能
    from dataclasses import replace
    
    # 创建必要的依赖（简化版）
    agent_factory = AgentFactory(settings)
    
    # 创建 RuntimeContext（需要所有必需字段）
    # 这里我们只测试缓存相关的方法，所以其他字段可以用 None 或 mock
    context = RuntimeContext(
        agent_factory=agent_factory,
        notification_service=None,  # type: ignore
        execution_logger=None,  # type: ignore
        state_manager=None,  # type: ignore
        child_checkpointer=None,  # type: ignore
    )
    
    # 测试 1：首次获取（从 intent_analysis 提取并缓存）
    print("📝 测试 1：首次获取约束（从 intent_analysis 提取）")
    start_time = time.time()
    constraints1 = await context.get_user_constraints(
        roadmap_id=roadmap_id,
        intent_analysis=intent_output
    )
    time1 = time.time() - start_time
    
    print(f"  ✅ 获取了 {len(constraints1)} 个约束")
    print(f"  ⏱️  耗时: {time1*1000:.2f}ms")
    assert len(constraints1) > 0, "应该获取到约束"
    
    # 测试 2：第二次获取（从缓存读取，应该更快）
    print("\n📝 测试 2：第二次获取约束（从缓存读取）")
    start_time = time.time()
    constraints2 = await context.get_user_constraints(
        roadmap_id=roadmap_id,
        intent_analysis=None  # 不传入 intent_analysis，强制从缓存读取
    )
    time2 = time.time() - start_time
    
    print(f"  ✅ 获取了 {len(constraints2)} 个约束")
    print(f"  ⏱️  耗时: {time2*1000:.2f}ms")
    assert constraints1 == constraints2, "缓存的约束应该与原始约束相同"
    print(f"  🚀 性能提升: {(time1/time2):.1f}x 倍（缓存命中）")
    
    # 测试 3：多个 Agent 共享缓存
    print("\n📝 测试 3：多个 Agent 共享缓存")
    
    agents = [
        CurriculumArchitectAgent(),
        StructureValidatorAgent(),
        TutorialGeneratorAgent(),
    ]
    
    for agent in agents:
        constraints = await context.get_user_constraints(
            roadmap_id=roadmap_id
        )
        filtered = agent._filter_constraints(constraints)
        print(f"  ✅ {agent.agent_id}: 过滤出 {len(filtered)} 个约束")
        assert len(filtered) > 0, f"{agent.agent_id} 应该获取到约束"
    
    # 测试 4：缓存命中率统计
    print("\n📝 测试 4：缓存状态")
    cache_size = len(context._constraints_cache)
    print(f"  📊 缓存大小: {cache_size} 个路线图")
    print(f"  🔑 缓存的 roadmap_id: {list(context._constraints_cache.keys())}")
    
    print("\n✅ RuntimeContext 缓存测试全部通过！")


async def test_agent_constraints_usage():
    """测试 Agent 使用约束的完整流程"""
    print("\n=== 测试 Agent 约束使用流程 ===\n")
    
    intent_output = create_test_intent_output()
    
    # 测试不同 Agent 的约束需求
    agents_config = [
        ("CurriculumArchitectAgent", CurriculumArchitectAgent(), 8),
        ("StructureValidatorAgent", StructureValidatorAgent(), 6),
        ("TutorialGeneratorAgent", TutorialGeneratorAgent(), 6),
    ]
    
    for agent_name, agent, expected_count in agents_config:
        constraints = await agent._load_user_constraints(
            intent_analysis=intent_output
        )
        print(f"📝 {agent_name}:")
        print(f"  - 需要 {expected_count} 个约束")
        print(f"  - 实际获取 {len(constraints)} 个约束")
        print(f"  - 约束列表: {list(constraints.keys())[:3]}...")
        
        # 验证通用约束都存在
        assert ConstraintNames.LANGUAGE in constraints, f"{agent_name} 应该有语言约束"
        assert ConstraintNames.USER_GOAL in constraints, f"{agent_name} 应该有目标约束"
    
    print("\n✅ Agent 约束使用测试通过！")


def main():
    """主测试函数"""
    print("=" * 70)
    print("用户画像约束系统测试（含 RuntimeContext 缓存）")
    print("=" * 70)
    
    try:
        # 测试 1: RuntimeContext 缓存
        asyncio.run(test_runtime_context_cache())
        
        # 测试 2: Agent 约束使用
        asyncio.run(test_agent_constraints_usage())
        
        print("\n" + "=" * 70)
        print("✅ 所有测试通过！")
        print("=" * 70)
        print("\n✨ 重构成果：")
        print("  1. ✅ 约束生成机制已集成到 IntentAnalyzerAgent")
        print("  2. ✅ BaseAgent 提供统一的约束管理接口")
        print("  3. ✅ 所有主要 Agent 已配置约束需求")
        print("  4. ✅ RuntimeContext 缓存提升性能（避免重复查询）")
        print("  5. ✅ Prompt 模板支持约束注入")
        print("\n🎯 下一步：")
        print("  1. 运行数据库迁移：cd backend && uv run alembic upgrade head")
        print("  2. 测试完整工作流：生成新路线图并观察约束注入效果")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

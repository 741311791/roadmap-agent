"""
测试用户画像约束生成和注入机制

验证点：
1. IntentAnalyzerAgent 能否正确生成约束文本
2. BaseAgent 能否正确过滤约束
3. CurriculumArchitectAgent 能否正确使用约束
"""
import asyncio
import sys
import os

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
from app.config.settings import settings


def test_constraint_generation():
    """测试约束生成逻辑"""
    print("\n=== 测试 1: 约束生成逻辑 ===")
    
    # 创建 IntentAnalyzerAgent
    agent = IntentAnalyzerAgent()
    
    # 模拟 IntentAnalysisOutput
    intent_output = IntentAnalysisOutput(
        parsed_goal="学习 Python Web 开发，掌握 FastAPI 框架，能够开发 RESTful API",
        key_technologies=["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Docker"],
        difficulty_profile="beginner - 无编程背景，需从 Python 基础语法开始",
        time_constraint="每周可投入 10 小时，希望在 6 个月内完成基础学习",
        recommended_focus=["Python 基础", "Web 开发基础", "数据库操作", "API 设计"],
        user_profile_summary="市场营销从业者，5 年工作经验，希望转行成为后端开发工程师",
        skill_gap_analysis=["Python 编程基础", "Web 开发概念", "数据库设计", "API 开发"],
        personalized_suggestions=["建议从 Python 基础语法开始", "重点学习 FastAPI 框架", "多做实战项目"],
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
            resource_ratio={"primary": 0.6, "secondary": 0.4}
        ),
        roadmap_id="python-web-dev-test123",
    )
    
    # 生成约束
    constraints = agent._generate_constraints(intent_output)
    
    # 验证结果
    print(f"✅ 生成了 {len(constraints)} 个约束")
    print("\n约束内容：")
    for name, content in constraints.items():
        print(f"  - {name}: {content}")
    
    # 验证必需约束
    assert ConstraintNames.LANGUAGE in constraints, "缺少生成语言约束"
    assert ConstraintNames.USER_GOAL in constraints, "缺少用户目标约束"
    assert ConstraintNames.USER_PROFILE in constraints, "缺少用户画像约束"
    
    print("\n✅ 约束生成测试通过！")
    return constraints


def test_constraint_filtering():
    """测试约束过滤逻辑"""
    print("\n=== 测试 2: 约束过滤逻辑 ===")
    
    # 模拟完整的约束字典
    all_constraints = {
        ConstraintNames.LANGUAGE: "请使用简体中文生成响应内容",
        ConstraintNames.USER_GOAL: "用户学习目标：学习 Python Web 开发",
        ConstraintNames.USER_PROFILE: "用户画像：市场营销从业者，5 年工作经验",
        ConstraintNames.DIFFICULTY: "用户难度画像：beginner",
        ConstraintNames.TIME_CONSTRAINT: "时间约束：每周 10 小时",
        ConstraintNames.SKILL_GAP: "技能差距：Python 基础、Web 开发",
        ConstraintNames.CONTENT_FORMAT_PREFERENCE: "用户偏好：视觉化内容、实践性内容",
    }
    
    # 创建 CurriculumArchitectAgent
    agent = CurriculumArchitectAgent()
    
    # 过滤约束
    filtered = agent._filter_constraints(all_constraints)
    
    print(f"✅ 原始约束：{len(all_constraints)} 个")
    print(f"✅ 过滤后约束：{len(filtered)} 个")
    print("\n过滤后的约束：")
    for name, content in filtered.items():
        print(f"  - {name}: {content}")
    
    # 验证过滤结果
    assert ConstraintNames.LANGUAGE in filtered, "通用约束应该被保留"
    assert ConstraintNames.USER_GOAL in filtered, "通用约束应该被保留"
    assert ConstraintNames.DIFFICULTY in filtered, "特定约束应该被保留"
    
    print("\n✅ 约束过滤测试通过！")
    return filtered


async def test_constraint_loading():
    """测试约束加载逻辑"""
    print("\n=== 测试 3: 约束加载逻辑 ===")
    
    # 创建测试用的 IntentAnalysisOutput
    intent_output = IntentAnalysisOutput(
        parsed_goal="学习 Python",
        key_technologies=["Python"],
        difficulty_profile="beginner",
        time_constraint="6 个月",
        recommended_focus=["Python 基础"],
        user_profile_summary="初学者",
        language_preferences=LanguagePreferences(primary_language="zh-CN"),
        full_analysis_data={
            ConstraintNames.LANGUAGE: "请使用简体中文生成响应内容",
            ConstraintNames.USER_GOAL: "用户学习目标：学习 Python",
            ConstraintNames.USER_PROFILE: "用户画像：初学者",
        }
    )
    
    # 创建 Agent
    agent = CurriculumArchitectAgent()
    
    # 测试从 intent_analysis 加载约束
    constraints = await agent._load_user_constraints(intent_analysis=intent_output)
    
    print(f"✅ 加载了 {len(constraints)} 个约束")
    print("\n加载的约束：")
    for name, content in constraints.items():
        print(f"  - {name}: {content}")
    
    # 验证
    assert len(constraints) > 0, "应该加载到约束"
    assert ConstraintNames.LANGUAGE in constraints, "应该包含语言约束"
    
    print("\n✅ 约束加载测试通过！")
    return constraints


def main():
    """主测试函数"""
    print("=" * 60)
    print("用户画像约束系统测试")
    print("=" * 60)
    
    try:
        # 测试 1: 约束生成
        constraints1 = test_constraint_generation()
        
        # 测试 2: 约束过滤
        constraints2 = test_constraint_filtering()
        
        # 测试 3: 约束加载
        constraints3 = asyncio.run(test_constraint_loading())
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        print("\n约束系统已成功集成到 Agent 架构中。")
        print("\n下一步：")
        print("  1. 运行数据库迁移：cd backend && uv run alembic upgrade head")
        print("  2. 测试完整的工作流：生成一个新的路线图，观察约束是否正确注入")
        print("  3. 检查日志：确认 constraints_count 和 constraint_names 被正确记录")
        
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

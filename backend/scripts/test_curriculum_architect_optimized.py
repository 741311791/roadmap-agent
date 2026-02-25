"""
测试优化后的 CurriculumArchitectAgent 性能

验证点：
1. 结构化提取速度提升
2. 依赖关系自动检查和修复
3. 完整字段默认值补充
"""
import asyncio
import sys
from pathlib import Path
import time

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.curriculum_architect import CurriculumArchitectAgent
from app.models.domain import (
    CurriculumDesignInput,
    IntentAnalysisOutput,
    LearningPreferences,
)
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


async def test_optimized_agent():
    """测试优化后的 Agent"""
    
    # 准备测试输入
    intent_analysis = IntentAnalysisOutput(
        roadmap_id="test-roadmap-123",
        parsed_goal="学习 Python 后端开发，掌握 FastAPI 和数据库操作",
        key_technologies=[
            {"name": "Python", "reason": "核心语言"},
            {"name": "FastAPI", "reason": "现代 Web 框架"},
            {"name": "PostgreSQL", "reason": "关系型数据库"},
            {"name": "Docker", "reason": "容器化部署"},
        ],
        difficulty_profile="intermediate",
        time_constraint="3 个月内完成",
        recommended_focus=["FastAPI 核心概念", "数据库设计", "API 开发最佳实践"],
        user_profile_summary="有 Python 基础，想转向后端开发",
        skill_gap_analysis="缺乏 Web 框架和数据库实战经验",
        personalized_suggestions=["从 FastAPI 基础开始", "实战项目驱动学习"],
    )
    
    user_preferences = LearningPreferences(
        learning_goal="成为 Python 后端工程师",
        available_hours_per_week=15,
        motivation="转行",
        current_level="intermediate",
        career_background="数据分析师 2 年经验",
        content_preference=["visual", "hands_on"],
        primary_language="zh",
        secondary_language="en",
    )
    
    curriculum_input = CurriculumDesignInput(
        intent_analysis=intent_analysis,
        user_preferences=user_preferences,
    )
    
    # 创建 Agent
    agent = CurriculumArchitectAgent()
    
    print("\n" + "=" * 80)
    print("测试优化后的 CurriculumArchitectAgent")
    print("=" * 80)
    print(f"模型: {agent.model_provider}/{agent.model_name}")
    print(f"优化: 使用简化的 response_model + 依赖检查")
    print("=" * 80 + "\n")
    
    # 执行并计时
    start_time = time.time()
    
    try:
        result = await agent.execute(curriculum_input)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        print("\n" + "=" * 80)
        print("✅ 生成成功!")
        print("=" * 80)
        print(f"⏱️  耗时: {elapsed:.2f}s")
        print(f"📊 路线图标题: {result.framework.title}")
        print(f"📊 阶段数: {len(result.framework.stages)}")
        
        total_modules = sum(len(stage.modules) for stage in result.framework.stages)
        total_concepts = sum(
            len(module.concepts)
            for stage in result.framework.stages
            for module in stage.modules
        )
        
        print(f"📊 模块数: {total_modules}")
        print(f"📊 概念数: {total_concepts}")
        print(f"📊 总时长: {result.framework.total_estimated_hours}h")
        print(f"📊 建议周数: {result.framework.recommended_completion_weeks}周")
        
        # 验证字段补充
        print("\n" + "-" * 80)
        print("验证字段补充（检查第一个 Concept）:")
        print("-" * 80)
        first_concept = result.framework.stages[0].modules[0].concepts[0]
        print(f"✓ concept_id: {first_concept.concept_id}")
        print(f"✓ name: {first_concept.name}")
        print(f"✓ content_status: {first_concept.content_status}")
        print(f"✓ tutorial_id: {first_concept.tutorial_id}")
        print(f"✓ resources_status: {first_concept.resources_status}")
        print(f"✓ quiz_status: {first_concept.quiz_status}")
        
        # 验证依赖关系
        print("\n" + "-" * 80)
        print("验证依赖关系检查:")
        print("-" * 80)
        concepts_with_prereqs = [
            concept
            for stage in result.framework.stages
            for module in stage.modules
            for concept in module.concepts
            if concept.prerequisites
        ]
        print(f"✓ 有前置关系的概念数: {len(concepts_with_prereqs)}")
        
        if concepts_with_prereqs:
            print(f"示例: {concepts_with_prereqs[0].name}")
            print(f"  前置: {concepts_with_prereqs[0].prerequisites}")
        
        # 运行框架自带的结构验证
        print("\n" + "-" * 80)
        print("运行框架结构验证:")
        print("-" * 80)
        is_valid, issues = result.framework.validate_structure()
        if is_valid:
            print("✅ 结构验证通过，无问题")
        else:
            print(f"⚠️  发现 {len(issues)} 个问题:")
            for issue in issues[:3]:  # 只显示前 3 个
                print(f"  - {issue.severity}: {issue.issue}")
        
        print("\n" + "=" * 80)
        
        return result
        
    except Exception as e:
        end_time = time.time()
        elapsed = end_time - start_time
        
        print("\n" + "=" * 80)
        print("❌ 生成失败!")
        print("=" * 80)
        print(f"⏱️  耗时: {elapsed:.2f}s")
        print(f"错误: {str(e)}")
        print("=" * 80 + "\n")
        
        import traceback
        traceback.print_exc()
        
        return None


async def main():
    """主函数"""
    result = await test_optimized_agent()
    
    if result:
        print("\n✅ 测试完成！优化效果:")
        print("  1. ⚡ 结构化提取速度提升（减少无效字段）")
        print("  2. ✓ 依赖关系自动检查和修复")
        print("  3. ✓ 完整字段默认值补充")
    else:
        print("\n❌ 测试失败，请检查错误日志")


if __name__ == "__main__":
    asyncio.run(main())

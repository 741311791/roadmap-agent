#!/usr/bin/env python3
"""
IntentAnalyzerAgent 测试脚本

功能：
1. 直接测试 IntentAnalyzerAgent 的执行逻辑
2. 验证输出结构的完整性和正确性
3. 测试不同场景的需求分析结果
4. 支持详细日志输出

使用方法：
    # 基础测试
    cd backend
    uv run python tests/agents/test_intent_analyzer.py

    # 详细输出模式
    cd backend
    uv run python tests/agents/test_intent_analyzer.py --verbose

    # 测试特定场景
    cd backend
    uv run python tests/agents/test_intent_analyzer.py --scenario advanced
"""
import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal

import structlog

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.agents.intent_analyzer import IntentAnalyzerAgent
from app.models.domain import (
    UserRequest,
    LearningPreferences,
    IntentAnalysisOutput,
)
from app.config.settings import settings

logger = structlog.get_logger()

# ============================================================
# 测试场景定义
# ============================================================

ScenarioType = Literal["beginner", "intermediate", "advanced", "career_switch", "bilingual"]


def get_test_scenario(scenario: ScenarioType) -> UserRequest:
    """
    获取测试场景数据
    
    Args:
        scenario: 场景类型
        
    Returns:
        UserRequest对象
    """
    scenarios = {
        "beginner": {
            "name": "初学者场景",
            "description": "零基础学习Python Web开发",
            "preferences": LearningPreferences(
                learning_goal="成为Python全栈开发工程师",
                available_hours_per_week=15,
                motivation="转行进入技术领域，希望在6个月内找到初级开发工作",
                current_level="beginner",
                career_background="市场营销3年经验，对编程有浓厚兴趣",
                content_preference=["text", "hands_on", "visual"],
                target_deadline=None,
                # 可选：用户画像
                industry=None,
                current_role=None,
                tech_stack=[],
                # 语言偏好
                preferred_language="zh-CN",  # 主要中文
            ),
            "additional_context": "希望能够掌握前后端开发技能，特别关注实战项目经验",
        },
        "intermediate": {
            "name": "中级进阶场景",
            "description": "有基础经验，想深入学习后端架构",
            "preferences": LearningPreferences(
                learning_goal="掌握分布式系统和微服务架构设计",
                available_hours_per_week=10,
                motivation="提升技术深度，晋升为高级工程师",
                current_level="intermediate",
                career_background="软件开发2年，主要做单体应用开发",
                content_preference=["text", "hands_on"],
                target_deadline=None,
                # 用户画像
                industry="互联网",
                current_role="后端开发工程师",
                tech_stack=[
                    {"technology": "Python", "proficiency": "intermediate"},
                    {"technology": "Django", "proficiency": "intermediate"},
                    {"technology": "MySQL", "proficiency": "beginner"},
                ],
                # 语言偏好
                preferred_language="zh-CN",
            ),
            "additional_context": "想学习如何设计高并发、高可用的系统架构",
        },
        "advanced": {
            "name": "高级专家场景",
            "description": "资深工程师学习前沿技术",
            "preferences": LearningPreferences(
                learning_goal="深入理解Kubernetes和云原生架构",
                available_hours_per_week=8,
                motivation="技术深度提升，成为架构师",
                current_level="advanced",
                career_background="5年后端开发经验，熟悉Docker和微服务",
                content_preference=["text", "hands_on"],
                target_deadline=None,
                # 用户画像
                industry="云计算",
                current_role="资深后端工程师",
                tech_stack=[
                    {"technology": "Python", "proficiency": "advanced"},
                    {"technology": "Go", "proficiency": "intermediate"},
                    {"technology": "Docker", "proficiency": "advanced"},
                    {"technology": "Redis", "proficiency": "advanced"},
                    {"technology": "PostgreSQL", "proficiency": "advanced"},
                ],
                # 语言偏好
                preferred_language="zh-CN",
            ),
            "additional_context": "关注Kubernetes的底层实现原理和最佳实践",
        },
        "career_switch": {
            "name": "转行场景",
            "description": "非技术背景转行做数据分析",
            "preferences": LearningPreferences(
                learning_goal="成为数据分析师，掌握Python数据分析技能",
                available_hours_per_week=20,
                motivation="职业转型，从财务分析师转为数据分析师",
                current_level="beginner",
                career_background="财务分析5年，熟悉Excel和SQL，无编程经验",
                content_preference=["text", "visual", "hands_on"],
                target_deadline=None,
                # 用户画像
                industry="金融",
                current_role="财务分析师",
                tech_stack=[
                    {"technology": "SQL", "proficiency": "intermediate"},
                    {"technology": "Excel", "proficiency": "advanced"},
                ],
                # 语言偏好
                preferred_language="zh-CN",
            ),
            "additional_context": "希望学习数据可视化和统计分析方法",
        },
        "bilingual": {
            "name": "双语学习场景",
            "description": "中英双语学习前端开发",
            "preferences": LearningPreferences(
                learning_goal="Learn React and modern frontend development",
                available_hours_per_week=12,
                motivation="Improve frontend skills and prepare for job interviews",
                current_level="intermediate",
                career_background="1年前端开发经验，主要使用jQuery",
                content_preference=["text", "hands_on", "visual"],
                target_deadline=None,
                # 用户画像
                industry="互联网",
                current_role="Junior Frontend Developer",
                tech_stack=[
                    {"technology": "JavaScript", "proficiency": "intermediate"},
                    {"technology": "HTML/CSS", "proficiency": "advanced"},
                    {"technology": "jQuery", "proficiency": "intermediate"},
                ],
                # 双语偏好
                preferred_language="en-US",  # 主要英文
                secondary_language="zh-CN",  # 次要中文
                bilingual_ratio=0.7,  # 70% 英文，30% 中文
            ),
            "additional_context": "Want to learn modern React patterns and state management",
        },
    }
    
    scenario_data = scenarios[scenario]
    
    return UserRequest(
        user_id=f"test-user-{scenario}",
        session_id=f"test-session-{scenario}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        preferences=scenario_data["preferences"],
        additional_context=scenario_data["additional_context"],
    )


# ============================================================
# 验证函数
# ============================================================

def validate_intent_analysis_output(
    result: IntentAnalysisOutput,
    scenario: ScenarioType,
    verbose: bool = False,
) -> bool:
    """
    验证 IntentAnalysisOutput 的完整性和正确性
    
    Args:
        result: Agent输出结果
        scenario: 测试场景
        verbose: 是否详细输出
        
    Returns:
        验证是否通过
    """
    print(f"\n{'='*70}")
    print(f"📊 验证输出结果")
    print(f"{'='*70}")
    
    errors = []
    warnings = []
    
    # 1. 验证必填字段
    print(f"\n1️⃣ 验证必填字段")
    required_fields = [
        ("roadmap_id", result.roadmap_id),
        ("parsed_goal", result.parsed_goal),
        ("difficulty_profile", result.difficulty_profile),
        ("time_constraint", result.time_constraint),
    ]
    
    for field_name, field_value in required_fields:
        if field_value is None:
            errors.append(f"   ❌ 必填字段 {field_name} 为空")
        else:
            print(f"   ✅ {field_name}: {field_value}")
    
    # 2. 验证 roadmap_id 格式
    print(f"\n2️⃣ 验证 roadmap_id 格式")
    if result.roadmap_id:
        if "-" not in result.roadmap_id:
            errors.append(f"   ❌ roadmap_id 格式错误（应包含连字符）: {result.roadmap_id}")
        elif len(result.roadmap_id.split("-")[-1]) != 8:
            errors.append(f"   ❌ roadmap_id 后缀不是8位: {result.roadmap_id}")
        else:
            print(f"   ✅ roadmap_id 格式正确: {result.roadmap_id}")
    
    # 3. 验证关键技术栈
    print(f"\n3️⃣ 验证关键技术栈")
    if not result.key_technologies:
        warnings.append(f"   ⚠️ key_technologies 为空")
    else:
        print(f"   ✅ 提取了 {len(result.key_technologies)} 个关键技术:")
        for tech in result.key_technologies:
            print(f"      - {tech}")
    
    # 4. 验证语言偏好
    print(f"\n4️⃣ 验证语言偏好")
    if not result.language_preferences:
        errors.append(f"   ❌ language_preferences 为空")
    else:
        lang_prefs = result.language_preferences
        print(f"   ✅ 主要语言: {lang_prefs.primary_language}")
        if lang_prefs.secondary_language:
            print(f"   ✅ 次要语言: {lang_prefs.secondary_language}")
        if lang_prefs.resource_ratio:
            print(f"   ✅ 资源比例: {lang_prefs.resource_ratio}")
    
    # 5. 验证用户画像
    print(f"\n5️⃣ 验证用户画像")
    if result.user_profile_summary:
        print(f"   ✅ 用户画像摘要: {result.user_profile_summary[:100]}...")
    else:
        warnings.append(f"   ⚠️ user_profile_summary 为空")
    
    if result.skill_gap_analysis:
        print(f"   ✅ 技能差距分析: {len(result.skill_gap_analysis)} 项")
        for i, gap in enumerate(result.skill_gap_analysis[:3], 1):
            print(f"      {i}. {gap}")
    else:
        warnings.append(f"   ⚠️ skill_gap_analysis 为空")
    
    # 6. 验证学习建议
    print(f"\n6️⃣ 验证学习建议")
    if result.personalized_suggestions:
        print(f"   ✅ 个性化建议: {len(result.personalized_suggestions)} 项")
        for i, suggestion in enumerate(result.personalized_suggestions[:3], 1):
            print(f"      {i}. {suggestion}")
    else:
        warnings.append(f"   ⚠️ personalized_suggestions 为空")
    
    # 7. 验证 full_analysis_data（约束文本字典）
    print(f"\n7️⃣ 验证 full_analysis_data")
    if not result.full_analysis_data:
        errors.append(f"   ❌ full_analysis_data 为空（必填字段）")
    else:
        print(f"   ✅ 包含 {len(result.full_analysis_data)} 个分析维度:")
        for key in result.full_analysis_data.keys():
            print(f"      - {key}")
    
    # 8. 详细输出（可选）
    if verbose:
        print(f"\n{'='*70}")
        print(f"📝 详细输出")
        print(f"{'='*70}")
        print(f"\n完整结果 JSON:")
        import json
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    
    # 9. 汇总验证结果
    print(f"\n{'='*70}")
    print(f"✅ 验证汇总")
    print(f"{'='*70}")
    
    if errors:
        print(f"\n❌ 发现 {len(errors)} 个错误:")
        for error in errors:
            print(error)
    
    if warnings:
        print(f"\n⚠️ 发现 {len(warnings)} 个警告:")
        for warning in warnings:
            print(warning)
    
    if not errors and not warnings:
        print(f"\n🎉 所有验证通过！")
    elif not errors:
        print(f"\n✅ 验证通过（有警告）")
    
    return len(errors) == 0


# ============================================================
# 主测试函数
# ============================================================

async def test_intent_analyzer(
    scenario: ScenarioType = "beginner",
    verbose: bool = False,
):
    """
    测试 IntentAnalyzerAgent
    
    Args:
        scenario: 测试场景
        verbose: 是否详细输出
    """
    print(f"\n{'#'*70}")
    print(f"# IntentAnalyzerAgent 测试脚本")
    print(f"# 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# 测试场景: {scenario}")
    print(f"# 模型提供商: {settings.ANALYZER_PROVIDER}")
    print(f"# 模型名称: {settings.ANALYZER_MODEL}")
    print(f"{'#'*70}")
    
    try:
        # 步骤1: 准备测试数据
        print(f"\n{'='*70}")
        print(f"📝 步骤1: 准备测试数据")
        print(f"{'='*70}")
        
        user_request = get_test_scenario(scenario)
        prefs = user_request.preferences
        
        print(f"   场景名称: {scenario}")
        print(f"   学习目标: {prefs.learning_goal}")
        print(f"   当前水平: {prefs.current_level}")
        print(f"   每周时间: {prefs.available_hours_per_week}小时")
        print(f"   主要语言: {prefs.preferred_language}")
        if prefs.secondary_language:
            print(f"   次要语言: {prefs.secondary_language}")
        if prefs.tech_stack:
            print(f"   已有技术栈: {len(prefs.tech_stack)} 项")
        
        # 步骤2: 创建Agent实例
        print(f"\n{'='*70}")
        print(f"🤖 步骤2: 创建 IntentAnalyzerAgent 实例")
        print(f"{'='*70}")
        
        agent = IntentAnalyzerAgent()
        print(f"   ✅ Agent 初始化成功")
        print(f"   Agent ID: {agent.agent_id}")
        print(f"   Model: {agent.model_name}")
        print(f"   Provider: {agent.model_provider}")
        
        # 步骤3: 执行Agent
        print(f"\n{'='*70}")
        print(f"⚙️ 步骤3: 执行 Agent")
        print(f"{'='*70}")
        print(f"   正在分析用户需求...")
        print(f"   提示: 预计耗时 30-60 秒...")
        
        start_time = datetime.now()
        
        try:
            result = await agent.execute(user_request)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            print(f"   ✅ 分析完成")
            print(f"   耗时: {elapsed:.2f}秒")
            
            if elapsed > 60:
                print(f"   ⚠️ 警告: 执行时间超过 60 秒")
            
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"   ❌ Agent 执行失败")
            print(f"   耗时: {elapsed:.2f}秒")
            print(f"   错误类型: {type(e).__name__}")
            print(f"   错误信息: {str(e)}")
            
            # 打印详细的堆栈跟踪
            import traceback
            print(f"\n   详细堆栈跟踪:")
            traceback.print_exc()
            
            raise
        
        # 步骤4: 验证输出
        try:
            validation_passed = validate_intent_analysis_output(result, scenario, verbose)
        except Exception as e:
            print(f"\n{'='*70}")
            print(f"❌ 验证过程中发生错误")
            print(f"{'='*70}")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            
            import traceback
            traceback.print_exc()
            
            # 即使验证失败，也打印已有的结果
            print(f"\n{'='*70}")
            print(f"📊 部分结果输出（验证前）")
            print(f"{'='*70}")
            
            try:
                import json
                print(f"\n完整结果 JSON:")
                print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
            except Exception as json_error:
                print(f"无法序列化结果: {json_error}")
            
            validation_passed = False
        
        # 步骤5: 显示结果摘要
        print(f"\n{'='*70}")
        print(f"📊 步骤4: 结果摘要")
        print(f"{'='*70}")
        
        print(f"\n✅ 基本信息:")
        print(f"   Roadmap ID: {result.roadmap_id}")
        print(f"   解析目标: {result.parsed_goal}")
        print(f"   难度画像: {result.difficulty_profile}")
        
        if result.key_technologies:
            print(f"\n✅ 关键技术栈 ({len(result.key_technologies)} 项):")
            for i, tech in enumerate(result.key_technologies[:5], 1):
                print(f"   {i}. {tech}")
            if len(result.key_technologies) > 5:
                print(f"   ... 还有 {len(result.key_technologies) - 5} 项")
        
        if result.skill_gap_analysis:
            print(f"\n✅ 技能差距 ({len(result.skill_gap_analysis)} 项):")
            for i, gap in enumerate(result.skill_gap_analysis[:3], 1):
                print(f"   {i}. {gap}")
            if len(result.skill_gap_analysis) > 3:
                print(f"   ... 还有 {len(result.skill_gap_analysis) - 3} 项")
        
        if result.time_constraint:
            print(f"\n✅ 时间约束:")
            print(f"   {result.time_constraint}")
        
        # 最终状态
        print(f"\n{'#'*70}")
        if validation_passed:
            print(f"# ✅ 测试通过")
        else:
            print(f"# ❌ 测试失败（验证未通过）")
        print(f"# 总耗时: {elapsed:.2f}秒")
        print(f"{'#'*70}\n")
        
        return 0 if validation_passed else 1
        
    except Exception as e:
        print(f"\n{'='*70}")
        print(f"❌ 测试过程中发生错误")
        print(f"{'='*70}")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print(f"{'='*70}\n")
        
        import traceback
        traceback.print_exc()
        
        return 1


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="IntentAnalyzerAgent 测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 测试初学者场景（默认）
  uv run python tests/agents/test_intent_analyzer.py
  
  # 测试中级进阶场景
  uv run python tests/agents/test_intent_analyzer.py --scenario intermediate
  
  # 测试高级场景
  uv run python tests/agents/test_intent_analyzer.py --scenario advanced
  
  # 测试转行场景
  uv run python tests/agents/test_intent_analyzer.py --scenario career_switch
  
  # 测试双语场景
  uv run python tests/agents/test_intent_analyzer.py --scenario bilingual
  
  # 详细输出模式
  uv run python tests/agents/test_intent_analyzer.py --scenario beginner --verbose
        """
    )
    parser.add_argument(
        "--scenario",
        type=str,
        choices=["beginner", "intermediate", "advanced", "career_switch", "bilingual"],
        default="beginner",
        help="测试场景类型",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="详细输出模式（显示完整JSON）",
    )
    
    args = parser.parse_args()
    
    # 运行测试
    exit_code = asyncio.run(test_intent_analyzer(
        scenario=args.scenario,
        verbose=args.verbose,
    ))
    
    sys.exit(exit_code)

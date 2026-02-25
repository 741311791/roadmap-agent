"""
单独测试 CurriculumArchitectAgent

用法:
    # 使用默认配置（环境变量中的模型）
    python scripts/test_curriculum_architect.py
    
    # 使用 Claude 模型（推荐，处理复杂 JSON 结构效果最好）
    python scripts/test_curriculum_architect.py --claude
    
    # 使用 GPT-4 模型
    python scripts/test_curriculum_architect.py --gpt4

注意:
    - qwen-plus 等较弱的模型可能无法正确生成复杂的嵌套 JSON 结构
    - 建议使用 Claude 或 GPT-4 进行测试
    - 需要在 .env 文件中配置相应的 API Key
    
环境变量说明:
    使用 Claude 时，需要设置以下环境变量（二选一）：
    1. ARCHITECT_API_KEY=你的Anthropic_API_Key（优先）
    2. ANTHROPIC_API_KEY=你的Anthropic_API_Key（备用）
    
    重要：如果你的 ARCHITECT_BASE_URL 指向阿里云等第三方代理，
    请临时注释掉该配置，或确保该代理支持 Anthropic API。
"""
import asyncio
import sys
from pathlib import Path

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
import json

logger = structlog.get_logger()


def create_mock_intent_analysis() -> IntentAnalysisOutput:
    """创建模拟的意图分析输出"""
    return IntentAnalysisOutput(
        parsed_goal="学习 Python Web 开发，能够独立开发和部署一个完整的 Web 应用",
        key_technologies=[
            "Python",
            "FastAPI",
            "SQLAlchemy",
            "PostgreSQL",
            "Docker",
            "Redis"
        ],
        difficulty_profile="中级难度，需要扎实的 Python 基础和数据库知识",
        time_constraint="建议投入 3-6 个月学习，每周 10-15 小时",
        recommended_focus=[
            "FastAPI 框架核心特性和最佳实践",
            "数据库设计与 ORM 使用",
            "异步编程与性能优化",
            "Docker 容器化部署"
        ],
        user_profile_summary="有 2 年 Python 基础经验，做过简单的脚本开发，希望转向 Web 开发",
        skill_gap_analysis=[
            "缺乏 Web 框架实战经验",
            "数据库设计能力不足",
            "对容器化部署不熟悉"
        ],
        personalized_suggestions=[
            "从 FastAPI 快速入门开始，边学边做",
            "重点练习数据库设计和 SQL 查询",
            "通过实战项目巩固所学知识"
        ],
        roadmap_id="python-web-dev-fastapi-2024-test-001"
    )


def create_mock_learning_preferences() -> LearningPreferences:
    """创建模拟的学习偏好"""
    return LearningPreferences(
        learning_goal="成为 Python Web 开发工程师",
        available_hours_per_week=12,
        motivation="转行进入互联网行业",
        current_level="intermediate",
        career_background="2 年 Python 脚本开发经验，做过数据分析工作",
        content_preference=["visual", "hands_on"],
        primary_language="zh",
        secondary_language="en",
    )


async def test_curriculum_architect(
    use_claude: bool = False,
    use_gpt4: bool = False
):
    """
    测试课程架构师 Agent
    
    Args:
        use_claude: 是否使用 Claude 模型（推荐）
        use_gpt4: 是否使用 GPT-4 模型
    """
    print("=" * 80)
    print("开始测试 CurriculumArchitectAgent")
    print("=" * 80)
    
    # 1. 创建模拟输入数据
    print("\n[1] 创建模拟输入数据...")
    intent_analysis = create_mock_intent_analysis()
    user_preferences = create_mock_learning_preferences()
    
    input_data = CurriculumDesignInput(
        intent_analysis=intent_analysis,
        user_preferences=user_preferences
    )
    
    print(f"  ✓ 学习目标: {intent_analysis.parsed_goal}")
    print(f"  ✓ 核心技术栈: {', '.join(intent_analysis.key_technologies)}")
    print(f"  ✓ 当前水平: {user_preferences.current_level}")
    print(f"  ✓ 每周可用时间: {user_preferences.available_hours_per_week} 小时")
    print(f"  ✓ Roadmap ID: {intent_analysis.roadmap_id}")
    
    # 2. 创建 Agent 实例（可选择模型）
    print("\n[2] 创建 Agent 实例...")
    
    if use_claude:
        print("  ℹ️  使用 Claude 模型（推荐）")
        print("  ⚠️  注意: 将使用 Anthropic 官方 API endpoint，忽略自定义 base_url")
        agent = CurriculumArchitectAgent(
            model_provider="anthropic",
            model_name="claude-3-5-sonnet-20241022",
            base_url=None,  # 不使用自定义 base_url，使用官方 API
            api_key=settings.ARCHITECT_API_KEY
        )
    elif use_gpt4:
        print("  ℹ️  使用 GPT-4 模型")
        print("  ⚠️  注意: 将使用 OpenAI 官方 API endpoint，忽略自定义 base_url")
        agent = CurriculumArchitectAgent(
            model_provider="openai",
            model_name="gpt-4o",
            base_url=None,  # 不使用自定义 base_url
            api_key=settings.ANALYZER_API_KEY
        )
    else:
        print("  ℹ️  使用默认配置（环境变量）")
        print("  ⚠️  注意: 当前配置的 base_url 可能不支持 Anthropic API")
        agent = CurriculumArchitectAgent()
    
    print(f"  ✓ Agent ID: {agent.agent_id}")
    print(f"  ✓ Model Provider: {agent.model_provider}")
    print(f"  ✓ Model Name: {agent.model_name}")
    print(f"  ✓ Temperature: {agent.temperature}")
    print(f"  ✓ Max Tokens: {agent.max_tokens}")
    
    # 3. 检查渲染的 Prompt (调试用)
    print("\n[3] 检查 Prompt 渲染...")
    try:
        prompt_context = agent._prepare_prompt_context(input_data)
        rendered_prompt = agent._load_system_prompt("curriculum_architect.j2", **prompt_context)
        
        # 保存渲染后的 prompt 到文件
        prompt_file = project_root / "scripts" / "test_rendered_prompt.txt"
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(rendered_prompt)
        
        print(f"  ✓ Prompt 渲染成功")
        print(f"  ✓ Prompt 长度: {len(rendered_prompt)} 字符")
        print(f"  ✓ 已保存到: {prompt_file}")
        
        # 显示 prompt 前 500 个字符
        print(f"\n  预览（前 500 字符）:")
        print("  " + "-" * 60)
        print("  " + rendered_prompt[:500].replace("\n", "\n  "))
        print("  " + "-" * 60)
        
    except Exception as e:
        print(f"  ❌ Prompt 渲染失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 4. 执行 Agent
    print("\n[4] 执行 Agent (调用 LLM)...")
    print("  ⏳ 正在生成课程架构，请稍候...")
    
    try:
        result = await agent.execute(input_data)
        
        print("\n" + "=" * 80)
        print("✅ 课程架构生成成功！")
        print("=" * 80)
        
        # 5. 验证输出结构
        print("\n[5] 验证输出结构...")
        framework = result.framework
        
        print(f"  ✓ Roadmap ID: {framework.roadmap_id}")
        print(f"  ✓ 标题: {framework.title}")
        print(f"  ✓ Stage 数量: {len(framework.stages)}")
        
        total_modules = sum(len(stage.modules) for stage in framework.stages)
        total_concepts = sum(
            len(module.concepts)
            for stage in framework.stages
            for module in stage.modules
        )
        
        print(f"  ✓ Module 总数: {total_modules}")
        print(f"  ✓ Concept 总数: {total_concepts}")
        print(f"  ✓ 预计总学时: {framework.total_estimated_hours} 小时")
        print(f"  ✓ 建议完成周数: {framework.recommended_completion_weeks} 周")
        
        # 6. 检查结构约束
        print("\n[6] 检查结构约束...")
        issues = []
        
        if len(framework.stages) != 4:
            issues.append(f"❌ Stage 数量错误: 期望 4，实际 {len(framework.stages)}")
        else:
            print("  ✓ Stage 数量: 4 个 (符合要求)")
        
        for i, stage in enumerate(framework.stages, 1):
            if len(stage.modules) != 2:
                issues.append(f"❌ Stage {i} 的 Module 数量错误: 期望 2，实际 {len(stage.modules)}")
            
            for j, module in enumerate(stage.modules, 1):
                if len(module.concepts) != 3:
                    issues.append(f"❌ Stage {i} Module {j} 的 Concept 数量错误: 期望 3，实际 {len(module.concepts)}")
        
        if not issues:
            print("  ✓ 所有 Stage 都有 2 个 Module")
            print("  ✓ 所有 Module 都有 3 个 Concept")
            print("  ✓ 结构验证通过: 4 × 2 × 3 = 24 个 Concept ✅")
        else:
            print("\n  ⚠️  结构验证失败:")
            for issue in issues:
                print(f"    {issue}")
        
        # 7. 打印详细结构
        print("\n[7] 详细课程结构:")
        print("-" * 80)
        
        for i, stage in enumerate(framework.stages, 1):
            print(f"\n📚 Stage {i}: {stage.name}")
            print(f"   描述: {stage.description}")
            print(f"   预计时长: {stage.total_hours} 小时")
            
            for j, module in enumerate(stage.modules, 1):
                print(f"\n  📖 Module {i}.{j}: {module.name}")
                print(f"     描述: {module.description}")
                print(f"     预计时长: {module.total_hours} 小时")
                
                for k, concept in enumerate(module.concepts, 1):
                    print(f"\n    💡 Concept {i}.{j}.{k}: {concept.name}")
                    print(f"       ID: {concept.concept_id}")
                    print(f"       描述: {concept.description}")
                    print(f"       关键词: {', '.join(concept.keywords)}")
                    print(f"       预计时长: {concept.estimated_hours} 小时")
        
        # 8. 保存输出到文件
        print("\n" + "-" * 80)
        print("\n[8] 保存输出结果...")
        
        output_file = project_root / "scripts" / "test_output_curriculum.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                result.model_dump(),
                f,
                ensure_ascii=False,
                indent=2
            )
        
        print(f"  ✓ 输出已保存到: {output_file}")
        
        # 9. 测试总结
        print("\n" + "=" * 80)
        print("✅ 测试完成！")
        print("=" * 80)
        print(f"\n总结:")
        print(f"  - Roadmap ID: {framework.roadmap_id}")
        print(f"  - 标题: {framework.title}")
        print(f"  - 结构: {len(framework.stages)} Stages × {total_modules//len(framework.stages)} Modules × {total_concepts//total_modules} Concepts = {total_concepts} Concepts")
        print(f"  - 总学时: {framework.total_estimated_hours} 小时")
        print(f"  - 建议周数: {framework.recommended_completion_weeks} 周")
        
        if not issues:
            print(f"\n🎉 结构验证: 通过 ✅")
        else:
            print(f"\n⚠️  结构验证: 存在 {len(issues)} 个问题")
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ 测试失败")
        print("=" * 80)
        print(f"\n错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        
        import traceback
        print("\n详细错误堆栈:")
        print(traceback.format_exc())
        
        sys.exit(1)


def print_config_diagnostics():
    """打印配置诊断信息"""
    print("\n" + "=" * 80)
    print("配置诊断信息")
    print("=" * 80)
    
    print(f"\n课程架构师 Agent (Curriculum Architect) 配置:")
    print(f"  Provider: {settings.ARCHITECT_PROVIDER}")
    print(f"  Model: {settings.ARCHITECT_MODEL}")
    print(f"  Base URL: {settings.ARCHITECT_BASE_URL or '(使用默认)'}")
    print(f"  API Key: {'已配置' if settings.ARCHITECT_API_KEY and settings.ARCHITECT_API_KEY != 'your_anthropic_api_key_here' else '未配置'}")
    
    print(f"\n⚠️  重要提示:")
    if settings.ARCHITECT_BASE_URL:
        print(f"  - 当前配置了自定义 Base URL: {settings.ARCHITECT_BASE_URL}")
        print(f"  - 如果该 URL 不支持 Anthropic API，使用 --claude 会失败")
        print(f"  - 建议：测试 Claude 时请临时在 .env 中注释掉 ARCHITECT_BASE_URL")
    else:
        print(f"  - 未配置自定义 Base URL，将使用官方 API endpoint")
    
    print("\n" + "=" * 80)


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试 CurriculumArchitectAgent")
    parser.add_argument(
        "--claude",
        action="store_true",
        help="使用 Claude 模型（推荐，适合复杂 JSON 结构）"
    )
    parser.add_argument(
        "--gpt4",
        action="store_true",
        help="使用 GPT-4 模型"
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="只显示配置诊断信息，不执行测试"
    )
    
    args = parser.parse_args()
    
    if args.diagnose:
        print_config_diagnostics()
        return
    
    if args.claude and args.gpt4:
        print("❌ 错误: 不能同时指定 --claude 和 --gpt4")
        sys.exit(1)
    
    try:
        await test_curriculum_architect(
            use_claude=args.claude,
            use_gpt4=args.gpt4
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断测试")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

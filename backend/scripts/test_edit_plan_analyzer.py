"""
测试 EditPlanAnalyzerAgent 的功能

测试场景：
1. 明确的修改请求（简化阶段）
2. 创建新 Stage
3. 删除 Stage
4. 多 Stage 修改
5. 模糊的修改请求
"""
import asyncio
import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.edit_plan_analyzer import EditPlanAnalyzerAgent
from app.models.domain import (
    EditPlanAnalyzerInput,
    RoadmapFramework,
    Stage,
    Module,
    Concept,
    LearningPreferences,
)
from app.config.settings import settings
import structlog

# 配置日志
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

logger = structlog.get_logger()


def create_sample_roadmap() -> RoadmapFramework:
    """创建示例路线图用于测试"""
    return RoadmapFramework(
        roadmap_id="test-roadmap-001",
        title="Python 全栈开发学习路线图",
        total_estimated_hours=120.0,
        recommended_completion_weeks=8,
        stages=[
            Stage(
                stage_id="stage-1",
                name="Python 基础",
                description="学习 Python 语言基础",
                order=1,
                estimated_weeks=2,
                modules=[
                    Module(
                        module_id="mod-1-1",
                        name="Python 语法基础",
                        description="变量、数据类型、控制流",
                        concepts=[
                            Concept(
                                concept_id="c-1-1-1",
                                name="变量和数据类型",
                                description="理解 Python 的基本数据类型",
                                estimated_hours=3.0,
                                difficulty="easy",
                                keywords=["变量", "数据类型", "Python"],
                                prerequisites=[],
                            ),
                            Concept(
                                concept_id="c-1-1-2",
                                name="控制流",
                                description="if/else、循环",
                                estimated_hours=4.0,
                                difficulty="easy",
                                keywords=["if", "for", "while"],
                                prerequisites=["c-1-1-1"],
                            ),
                        ],
                    ),
                ],
            ),
            Stage(
                stage_id="stage-2",
                name="Web 开发进阶",
                description="学习 Flask 和前端基础",
                order=2,
                estimated_weeks=3,
                modules=[
                    Module(
                        module_id="mod-2-1",
                        name="Flask 框架",
                        description="Web 开发框架",
                        concepts=[
                            Concept(
                                concept_id="c-2-1-1",
                                name="Flask 路由",
                                description="路由和视图函数",
                                estimated_hours=5.0,
                                difficulty="medium",
                                keywords=["Flask", "路由", "视图"],
                                prerequisites=["c-1-1-2"],
                            ),
                            Concept(
                                concept_id="c-2-1-2",
                                name="Flask 模板",
                                description="Jinja2 模板引擎",
                                estimated_hours=4.0,
                                difficulty="medium",
                                keywords=["Jinja2", "模板"],
                                prerequisites=["c-2-1-1"],
                            ),
                            Concept(
                                concept_id="c-2-1-3",
                                name="Flask 高级特性",
                                description="蓝图、中间件、扩展",
                                estimated_hours=6.0,
                                difficulty="hard",
                                keywords=["蓝图", "中间件"],
                                prerequisites=["c-2-1-2"],
                            ),
                        ],
                    ),
                ],
            ),
            Stage(
                stage_id="stage-3",
                name="数据库和部署",
                description="数据库操作和项目部署",
                order=3,
                estimated_weeks=3,
                modules=[
                    Module(
                        module_id="mod-3-1",
                        name="数据库基础",
                        description="SQL 和 ORM",
                        concepts=[
                            Concept(
                                concept_id="c-3-1-1",
                                name="SQL 基础",
                                description="基本的 SQL 查询",
                                estimated_hours=5.0,
                                difficulty="medium",
                                keywords=["SQL", "数据库"],
                                prerequisites=["c-2-1-2"],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def create_user_preferences() -> LearningPreferences:
    """创建用户偏好"""
    return LearningPreferences(
        learning_goal="成为全栈开发工程师",
        current_level="intermediate",
        available_hours_per_week=10,
        motivation="想要转行做全栈开发",
        career_background="有2年Python基础经验",
    )


async def test_scenario_1_simplify_stage():
    """场景 1: 简化阶段"""
    logger.info("=== 测试场景 1: 简化阶段 ===")
    
    agent = EditPlanAnalyzerAgent()
    existing_framework = create_sample_roadmap()
    user_preferences = create_user_preferences()
    
    input_data = EditPlanAnalyzerInput(
        user_feedback="请把阶段2的内容改简单点，删掉高级主题",
        existing_framework=existing_framework,
        user_preferences=user_preferences,
    )
    
    try:
        result = await agent.execute(input_data)
        
        logger.info(
            "test_scenario_1_result",
            feedback_summary=result.edit_plan.feedback_summary,
            tasks_count=len(result.edit_plan.tasks),
            confidence=result.confidence,
        )
        
        for idx, task in enumerate(result.edit_plan.tasks):
            logger.info(
                f"task_{idx + 1}",
                action=task.action,
                stage_id=task.stage_id,
                instruction=task.instruction[:100] + "...",
                dependencies=task.dependencies,
            )
        
        return result
    except Exception as e:
        logger.error("test_scenario_1_failed", error=str(e))
        raise


async def test_scenario_2_create_stage():
    """场景 2: 创建新 Stage"""
    logger.info("=== 测试场景 2: 创建新 Stage ===")
    
    agent = EditPlanAnalyzerAgent()
    existing_framework = create_sample_roadmap()
    user_preferences = create_user_preferences()
    
    input_data = EditPlanAnalyzerInput(
        user_feedback="在第一阶段后加一个关于前端开发的阶段",
        existing_framework=existing_framework,
        user_preferences=user_preferences,
    )
    
    try:
        result = await agent.execute(input_data)
        
        logger.info(
            "test_scenario_2_result",
            feedback_summary=result.edit_plan.feedback_summary,
            tasks_count=len(result.edit_plan.tasks),
            confidence=result.confidence,
        )
        
        for idx, task in enumerate(result.edit_plan.tasks):
            logger.info(
                f"task_{idx + 1}",
                action=task.action,
                stage_id=task.stage_id,
                order=task.order,
                instruction=task.instruction[:100] + "...",
            )
        
        return result
    except Exception as e:
        logger.error("test_scenario_2_failed", error=str(e))
        raise


async def test_scenario_3_delete_stage():
    """场景 3: 删除 Stage"""
    logger.info("=== 测试场景 3: 删除 Stage ===")
    
    agent = EditPlanAnalyzerAgent()
    existing_framework = create_sample_roadmap()
    user_preferences = create_user_preferences()
    
    input_data = EditPlanAnalyzerInput(
        user_feedback="删掉第三阶段，太难了",
        existing_framework=existing_framework,
        user_preferences=user_preferences,
    )
    
    try:
        result = await agent.execute(input_data)
        
        logger.info(
            "test_scenario_3_result",
            feedback_summary=result.edit_plan.feedback_summary,
            tasks_count=len(result.edit_plan.tasks),
        )
        
        for idx, task in enumerate(result.edit_plan.tasks):
            logger.info(
                f"task_{idx + 1}",
                action=task.action,
                stage_id=task.stage_id,
                instruction=task.instruction[:100] + "...",
            )
        
        return result
    except Exception as e:
        logger.error("test_scenario_3_failed", error=str(e))
        raise


async def test_scenario_4_multiple_stages():
    """场景 4: 多 Stage 修改"""
    logger.info("=== 测试场景 4: 多 Stage 修改 ===")
    
    agent = EditPlanAnalyzerAgent()
    existing_framework = create_sample_roadmap()
    user_preferences = create_user_preferences()
    
    input_data = EditPlanAnalyzerInput(
        user_feedback="第二阶段改简单点，第三阶段加点实战项目",
        existing_framework=existing_framework,
        user_preferences=user_preferences,
    )
    
    try:
        result = await agent.execute(input_data)
        
        logger.info(
            "test_scenario_4_result",
            feedback_summary=result.edit_plan.feedback_summary,
            tasks_count=len(result.edit_plan.tasks),
            execution_strategy=result.edit_plan.execution_strategy,
        )
        
        for idx, task in enumerate(result.edit_plan.tasks):
            logger.info(
                f"task_{idx + 1}",
                action=task.action,
                stage_id=task.stage_id,
                instruction=task.instruction[:100] + "...",
                dependencies=task.dependencies,
            )
        
        return result
    except Exception as e:
        logger.error("test_scenario_4_failed", error=str(e))
        raise


async def test_scenario_5_ambiguous_feedback():
    """场景 5: 模糊的修改请求（现在也会给出具体方案）"""
    logger.info("=== 测试场景 5: 模糊的修改请求（测试推断能力）===")
    
    agent = EditPlanAnalyzerAgent()
    existing_framework = create_sample_roadmap()
    user_preferences = create_user_preferences()
    
    input_data = EditPlanAnalyzerInput(
        user_feedback="感觉内容太多了",
        existing_framework=existing_framework,
        user_preferences=user_preferences,
    )
    
    try:
        result = await agent.execute(input_data)
        
        logger.info(
            "test_scenario_5_result",
            feedback_summary=result.edit_plan.feedback_summary,
            tasks_count=len(result.edit_plan.tasks),
            confidence=result.confidence,
            execution_strategy=result.edit_plan.execution_strategy,
        )
        
        logger.info(
            "test_scenario_5_note",
            note="即使用户反馈模糊，也给出了具体的修改方案（不再请求澄清）"
        )
        
        for idx, task in enumerate(result.edit_plan.tasks):
            logger.info(
                f"task_{idx + 1}",
                action=task.action,
                stage_id=task.stage_id,
                instruction=task.instruction[:100] + "...",
            )
        
        return result
    except Exception as e:
        logger.error("test_scenario_5_failed", error=str(e))
        raise


async def main():
    """运行所有测试场景"""
    logger.info("开始测试 EditPlanAnalyzerAgent")
    logger.info(f"使用模型: {settings.ANALYZER_PROVIDER}/{settings.ANALYZER_MODEL}")
    
    try:
        # 场景 1: 简化阶段
        result1 = await test_scenario_1_simplify_stage()
        print("\n" + "="*80 + "\n")
        
        # 场景 2: 创建新 Stage
        result2 = await test_scenario_2_create_stage()
        print("\n" + "="*80 + "\n")
        
        # 场景 3: 删除 Stage
        result3 = await test_scenario_3_delete_stage()
        print("\n" + "="*80 + "\n")
        
        # 场景 4: 多 Stage 修改
        result4 = await test_scenario_4_multiple_stages()
        print("\n" + "="*80 + "\n")
        
        # 场景 5: 模糊的修改请求
        result5 = await test_scenario_5_ambiguous_feedback()
        print("\n" + "="*80 + "\n")
        
        logger.info("✅ 所有测试场景完成")
        
    except Exception as e:
        logger.error("❌ 测试失败", error=str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

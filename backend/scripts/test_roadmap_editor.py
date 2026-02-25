"""
测试 RoadmapEditorAgent 的功能（简化版）

测试场景：
1. UPDATE 任务（简化 Stage）
2. UPDATE 任务（删除 Stage）- 通过 instruction 描述删除
3. 多任务修改
"""
import asyncio
import sys
import logging
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.roadmap_editor import RoadmapEditorAgent
from app.models.domain import (
    RoadmapEditInput,
    EditPlan,
    StageEditTask,
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
        roadmap_id="test-roadmap-003",
        title="Python Web 开发学习路线图",
        total_estimated_hours=90.0,
        recommended_completion_weeks=6,
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
                            Concept(
                                concept_id="c-1-1-3",
                                name="函数和模块",
                                description="函数定义、模块导入",
                                estimated_hours=5.0,
                                difficulty="easy",
                                keywords=["函数", "模块", "import"],
                                prerequisites=["c-1-1-2"],
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
                                prerequisites=["c-1-1-3"],
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
                                estimated_hours=8.0,
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
                estimated_weeks=2,
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
                            Concept(
                                concept_id="c-3-1-2",
                                name="SQLAlchemy ORM",
                                description="Python ORM 框架",
                                estimated_hours=6.0,
                                difficulty="hard",
                                keywords=["ORM", "SQLAlchemy"],
                                prerequisites=["c-3-1-1"],
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
        learning_goal="成为 Python Web 开发工程师",
        current_level="intermediate",
        available_hours_per_week=10,
        motivation="转行进入 Web 开发领域",
        career_background="有2年Python基础经验，做过数据分析",
    )


async def test_scenario_1_update_stage():
    """场景 1: UPDATE 任务（简化 Stage）"""
    logger.info("=== 测试场景 1: UPDATE 任务（简化 Stage 2）===")
    
    agent = RoadmapEditorAgent()
    existing_framework = create_sample_roadmap()
    user_preferences = create_user_preferences()
    
    # 创建修改计划（极简版）
    edit_plan = EditPlan(
        feedback_summary="简化阶段2，删除高级主题",
        tasks=[
            StageEditTask(
                action="UPDATE",
                stage_id="stage-2",
                instruction="简化 Stage 2：删除 Flask 高级特性（c-2-1-3），只保留基础的路由和模板内容，降低整体难度。",
            )
        ],
    )
    
    input_data = RoadmapEditInput(
        existing_framework=existing_framework,
        user_preferences=user_preferences,
        edit_plan=edit_plan,
        modification_context="测试场景1：简化阶段2",
    )
    
    try:
        result = await agent.execute(input_data)
        
        logger.info(
            "test_scenario_1_result",
            roadmap_id=result.framework.roadmap_id,
            stages_count=len(result.framework.stages),
            total_hours_before=existing_framework.total_estimated_hours,
            total_hours_after=result.framework.total_estimated_hours,
            modified_nodes_count=len(result.modified_node_ids),
        )
        
        logger.info(
            "modification_summary",
            summary=result.modification_summary,
        )
        
        logger.info(
            "modified_node_ids",
            ids=result.modified_node_ids,
        )
        
        # 验证：Stage 2 应该被修改
        stage_2 = next((s for s in result.framework.stages if s.stage_id == "stage-2"), None)
        if stage_2:
            logger.info(
                "stage_2_after_edit",
                name=stage_2.name,
                modules_count=len(stage_2.modules),
                concepts_count=sum(len(m.concepts) for m in stage_2.modules),
            )
        
        return result
    except Exception as e:
        logger.error("test_scenario_1_failed", error=str(e))
        import traceback
        traceback.print_exc()
        raise


async def test_scenario_2_delete_stage():
    """场景 2: UPDATE 任务（删除 Stage）"""
    logger.info("=== 测试场景 2: UPDATE 任务（删除 Stage 3）===")
    
    agent = RoadmapEditorAgent()
    existing_framework = create_sample_roadmap()
    user_preferences = create_user_preferences()
    
    # 创建修改计划
    edit_plan = EditPlan(
        feedback_summary="删除 Stage 3（数据库内容）",
        tasks=[
            StageEditTask(
                action="UPDATE",
                stage_id="stage-3",
                instruction="将 Stage 3 完全从路线图中移除，因为用户暂时不需要学习数据库内容。删除后，路线图只保留 Stage 1 和 Stage 2。",
            )
        ],
    )
    
    input_data = RoadmapEditInput(
        existing_framework=existing_framework,
        user_preferences=user_preferences,
        edit_plan=edit_plan,
        modification_context="测试场景2：删除Stage",
    )
    
    try:
        result = await agent.execute(input_data)
        
        logger.info(
            "test_scenario_2_result",
            stages_count_before=len(existing_framework.stages),
            stages_count_after=len(result.framework.stages),
            modified_nodes_count=len(result.modified_node_ids),
        )
        
        logger.info(
            "modification_summary",
            summary=result.modification_summary,
        )
        
        # 验证：stage-3 应该被删除
        stage_ids = [s.stage_id for s in result.framework.stages]
        logger.info("remaining_stage_ids", stage_ids=stage_ids)
        
        if "stage-3" not in stage_ids:
            logger.info("delete_success", message="✅ Stage 3 成功删除")
        else:
            logger.error("delete_failed", message="❌ Stage 3 应该被删除但仍然存在")
        
        return result
    except Exception as e:
        logger.error("test_scenario_2_failed", error=str(e))
        import traceback
        traceback.print_exc()
        raise


async def test_scenario_3_multiple_tasks():
    """场景 3: 多任务修改"""
    logger.info("=== 测试场景 3: 多任务修改（简化 Stage 2 和 Stage 3）===")
    
    agent = RoadmapEditorAgent()
    existing_framework = create_sample_roadmap()
    user_preferences = create_user_preferences()
    
    # 创建修改计划
    edit_plan = EditPlan(
        feedback_summary="简化 Stage 2 和 Stage 3",
        tasks=[
            StageEditTask(
                action="UPDATE",
                stage_id="stage-2",
                instruction="简化 Stage 2：删除高级特性（c-2-1-3），只保留核心的 Flask 基础内容。",
            ),
            StageEditTask(
                action="UPDATE",
                stage_id="stage-3",
                instruction="精简 Stage 3：只保留 SQL 基础（c-3-1-1），删除 ORM 内容（c-3-1-2）。",
            ),
        ],
    )
    
    input_data = RoadmapEditInput(
        existing_framework=existing_framework,
        user_preferences=user_preferences,
        edit_plan=edit_plan,
        modification_context="测试场景3：多任务修改",
    )
    
    try:
        result = await agent.execute(input_data)
        
        logger.info(
            "test_scenario_3_result",
            tasks_count=len(edit_plan.tasks),
            modified_nodes_count=len(result.modified_node_ids),
            total_hours_before=existing_framework.total_estimated_hours,
            total_hours_after=result.framework.total_estimated_hours,
        )
        
        logger.info(
            "modification_summary",
            summary=result.modification_summary,
        )
        
        logger.info(
            "modified_stages",
            stage_2_modified="stage-2" in result.modified_node_ids,
            stage_3_modified="stage-3" in result.modified_node_ids,
        )
        
        return result
    except Exception as e:
        logger.error("test_scenario_3_failed", error=str(e))
        import traceback
        traceback.print_exc()
        raise


async def main():
    """运行所有测试场景"""
    logger.info("开始测试 RoadmapEditorAgent（简化版）")
    logger.info(f"使用模型: {settings.EDITOR_PROVIDER}/{settings.EDITOR_MODEL}")
    
    try:
        # 场景 1: UPDATE 任务（简化）
        logger.info("\n" + "="*80)
        result1 = await test_scenario_1_update_stage()
        print("\n" + "="*80 + "\n")
        
        # 场景 2: UPDATE 任务（删除）
        logger.info("\n" + "="*80)
        result2 = await test_scenario_2_delete_stage()
        print("\n" + "="*80 + "\n")
        
        # 场景 3: 多任务修改
        logger.info("\n" + "="*80)
        result3 = await test_scenario_3_multiple_tasks()
        print("\n" + "="*80 + "\n")
        
        logger.info("✅ 所有测试场景完成")
        
        # 保存测试输出
        output_dir = Path(__file__).parent
        with open(output_dir / "test_output_editor_simplified.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "scenario_1_update": result1.model_dump(),
                    "scenario_2_delete": result2.model_dump(),
                    "scenario_3_multiple": result3.model_dump(),
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        logger.info("测试输出已保存到 test_output_editor_simplified.json")
        
    except Exception as e:
        logger.error("❌ 测试失败", error=str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

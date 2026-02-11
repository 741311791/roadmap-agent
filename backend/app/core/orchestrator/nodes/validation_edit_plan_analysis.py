"""
验证结果修改计划分析节点（验证失败触发）（纯函数）

职责：
- 调用EditPlanAnalyzerAgent基于验证结果生成修改计划
- 返回纯数据（不保存数据库）
"""
import structlog
from langchain_core.runnables import RunnableConfig

from app.core.orchestrator.base import RoadmapState
from app.core.orchestrator.runtime_context import RuntimeContext
from app.services.shared.execution_logger import execution_logger, LogCategory

logger = structlog.get_logger()


async def validation_edit_plan_analysis_node(
    state: RoadmapState,
    config: RunnableConfig,
) -> dict:
    """
    验证结果修改计划分析节点（纯函数）
    
    基于验证结果生成结构化的修改计划。
    数据库保存由ValidationEditPlanHandler处理。
    
    Args:
        state: 工作流状态
        config: 运行时配置（包含RuntimeContext）
    
    Returns:
        状态更新字典：
        - edit_plan: EditPlan对象
        - current_step: 当前步骤
        - edit_source: 编辑来源（"validation_failed"）
    """
    # 从config获取依赖
    ctx: RuntimeContext = config["configurable"]["runtime_context"]
    
    task_id = state["task_id"]
    roadmap_id = state.get("roadmap_id")
    validation_result = state.get("validation_result")
    framework = state["roadmap_framework"]
    
    logger.info(
        "validation_edit_plan_analysis_node_start",
        task_id=task_id,
        roadmap_id=roadmap_id,
        has_validation_result=validation_result is not None,
    )
    
    # 创建Agent
    agent = ctx.agent_factory.create_edit_plan_analyzer()
    
    # 构造基于验证结果的反馈
    feedback = f"Validation failed with score {validation_result.overall_score}. "
    if validation_result.issues:
        feedback += f"Issues: {', '.join([issue.issue for issue in validation_result.issues[:3]])}"
    
    # 准备输入数据
    from app.models.domain import EditPlanAnalyzerInput
    analyzer_input = EditPlanAnalyzerInput(
        user_feedback=feedback,
        existing_framework=framework,
        user_preferences=state["user_request"].preferences,
    )
    
    # 执行分析
    analysis_output = await agent.execute(analyzer_input)
    
    # 提取edit_plan
    edit_plan = analysis_output.edit_plan
    
    logger.info(
        "validation_edit_plan_analysis_node_completed",
        task_id=task_id,
        roadmap_id=roadmap_id,
        has_edit_plan=edit_plan is not None,
    )
    
    # 记录详细输出日志
    await execution_logger.info(
        task_id=task_id,
        category=LogCategory.AGENT,
        step="validation_edit_plan_analysis",
        agent_name="EditPlanAnalyzerAgent",
        roadmap_id=roadmap_id,
        message="✅ Edit plan generated from validation results",
        details={
            "log_type": "edit_plan_output",
            "source": "validation_failed",
            "validation_score": validation_result.overall_score if validation_result else None,
        },
    )
    
    # 返回纯数据（不保存数据库）
    # ⚠️ 必须包含 Handler 需要的所有字段
    return {
        "edit_plan": edit_plan,
        "validation_result": validation_result,  # ✅ Handler 需要
        "roadmap_id": state.get("roadmap_id"),   # ✅ Handler 需要
        "current_step": "validation_edit_plan_analysis",
        "edit_source": "validation_failed",
        "execution_history": ["修改计划分析完成（验证失败触发）"],
    }


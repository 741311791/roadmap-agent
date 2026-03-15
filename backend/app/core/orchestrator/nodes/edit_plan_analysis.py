"""
修改计划分析节点（人工审核触发）（纯函数）

职责：
- 调用EditPlanAnalyzerAgent解析用户反馈
- 返回纯数据（不保存数据库）
"""
import structlog
import time
from langchain_core.runnables import RunnableConfig

from app.core.orchestrator.base import INTERNAL_NODE_DURATION_MS_KEY, RoadmapState
from app.core.orchestrator.runtime_context import RuntimeContext
from app.services.shared.execution_logger import execution_logger, LogCategory

logger = structlog.get_logger()


async def edit_plan_analysis_node(
    state: RoadmapState,
    config: RunnableConfig,
) -> dict:
    """
    编辑计划分析节点（纯函数，共享节点）
    
    解析用户反馈或验证问题，生成结构化的修改计划。
    
    触发来源（由edit_source区分）：
    1. structure_validation失败 → edit_source="validation_failed"
    2. human_review拒绝 → edit_source="human_review"
    
    数据库保存由EditPlanHandler处理。
    
    Args:
        state: 工作流状态
        config: 运行时配置（包含RuntimeContext）
    
    Returns:
        状态更新字典：
        - edit_plan: EditPlan对象
        - current_step: 当前步骤
        - edit_source: 编辑来源（从state继承或默认为human_review）
    """
    # 从config获取依赖
    ctx: RuntimeContext = config["configurable"]["runtime_context"]
    node_started_at = time.perf_counter()
    
    task_id = state["task_id"]
    roadmap_id = state.get("roadmap_id")
    framework = state["roadmap_framework"]
    
    # ✅ 从state获取edit_source，如果不存在则默认为human_review
    edit_source = state.get("edit_source", "human_review")
    
    # ✅ 根据edit_source获取不同的输入数据
    if edit_source == "validation_failed":
        # 验证失败触发：使用validation_result作为输入
        validation_result = state.get("validation_result")
        if validation_result:
            # ValidationOutput是Pydantic对象，使用属性访问
            user_feedback = validation_result.validation_summary
        else:
            user_feedback = ""
    else:
        # human_review触发：使用user_feedback
        user_feedback = state.get("user_feedback", "")
    
    logger.info(
        "edit_plan_analysis_node_start",
        task_id=task_id,
        roadmap_id=roadmap_id,
        edit_source=edit_source,
        has_feedback=bool(user_feedback),
    )
    
    # 创建Agent
    agent = ctx.agent_factory.create_edit_plan_analyzer()
    
    # 准备输入数据
    from app.models.domain import EditPlanAnalyzerInput
    analyzer_input = EditPlanAnalyzerInput(
        user_feedback=user_feedback,
        existing_framework=framework,
        user_preferences=state["user_request"].preferences,
    )
    
    # 执行分析
    analysis_output = await agent.execute(analyzer_input)
    
    logger.info(
        "edit_plan_analysis_node_completed",
        task_id=task_id,
        roadmap_id=roadmap_id,
        has_edit_plan=analysis_output.edit_plan is not None,
        confidence=analysis_output.confidence,
    )
    
    # 记录详细输出日志
    await execution_logger.info(
        task_id=task_id,
        category=LogCategory.AGENT,
        step="edit_plan_analysis",
        agent_name="EditPlanAnalyzerAgent",
        roadmap_id=roadmap_id,
        message=f"✅ Edit plan generated (source: {edit_source})",
        details={
            "log_type": "edit_plan_output",
            "edit_source": edit_source,  # ✅ 修复：使用edit_source字段名（与前端保持一致）
            "confidence": analysis_output.confidence,
        },
    )
    
    # ✅ 根据edit_source计算不同的轮次
    if edit_source == "validation_failed":
        # 验证失败触发：使用modification_count
        modification_count = state.get("modification_count", 0) + 1
        round_number = modification_count
        trigger_message = f"验证失败触发，第{round_number}次修改"
    else:
        # human_review触发：使用review_round
        review_round = state.get("review_round", 0) + 1
        round_number = review_round
        trigger_message = f"人工审核触发，第{round_number}轮"
    
    # 返回纯数据（不保存数据库）
    # ⚠️ 必须包含 Handler 需要的所有字段
    return {
        "edit_plan": analysis_output,  # ✅ 返回完整的 EditPlanAnalyzerOutput
        "user_feedback": user_feedback,    # ✅ Handler 需要
        "roadmap_id": state.get("roadmap_id"),  # ✅ Handler 需要
        "user_id": state["user_request"].user_id,  # ✅ Handler 需要
        "approved": False,  # ✅ 始终为False（human_review拒绝或validation_failed都是"未批准"）
        "roadmap_version_snapshot": framework.model_dump(),  # ✅ Handler 需要
        "review_round": review_round if edit_source == "human_review" else state.get("review_round", 0),
        "modification_count": modification_count if edit_source == "validation_failed" else state.get("modification_count", 0),
        "current_step": "edit_plan_analysis",
        "edit_source": edit_source,  # ✅ 保持edit_source
        "execution_history": [f"修改计划分析完成（{trigger_message}）"],
        INTERNAL_NODE_DURATION_MS_KEY: int((time.perf_counter() - node_started_at) * 1000),
    }


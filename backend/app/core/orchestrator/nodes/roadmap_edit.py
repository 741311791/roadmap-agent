"""
路线图编辑节点（纯函数）

职责：
- 调用RoadmapEditorAgent执行编辑
- 返回纯数据（不保存数据库）
"""
import structlog
from langchain_core.runnables import RunnableConfig

from app.core.orchestrator.base import RoadmapState
from app.core.orchestrator.runtime_context import RuntimeContext
from app.services.shared.execution_logger import execution_logger, LogCategory

logger = structlog.get_logger()


async def roadmap_edit_node(
    state: RoadmapState,
    config: RunnableConfig,
) -> dict:
    """
    路线图编辑节点（纯函数）
    
    从config获取依赖，执行Agent，返回纯数据。
    数据库保存由EditorHandler处理。
    
    Args:
        state: 工作流状态
        config: 运行时配置（包含RuntimeContext）
    
    Returns:
        状态更新字典：
        - roadmap_framework: 修改后的框架
        - origin_framework: 原始框架（用于对比）
        - current_step: 当前步骤
        - modification_count: 修改次数
    """
    # 从config获取依赖
    ctx: RuntimeContext = config["configurable"]["runtime_context"]
    
    task_id = state["task_id"]
    roadmap_id = state.get("roadmap_id")
    origin_framework = state["roadmap_framework"]
    edit_plan_output = state.get("edit_plan")  # EditPlanAnalyzerOutput | None
    # ✅ 只读取 modification_count，不再累加（累加逻辑在 edit_plan_analysis_node）
    modification_count = state.get("modification_count", 0)
    
    # 提取实际的修改计划（EditPlan）
    edit_plan = edit_plan_output.edit_plan if edit_plan_output else None
    
    logger.info(
        "roadmap_edit_node_start",
        task_id=task_id,
        roadmap_id=roadmap_id,
        modification_count=modification_count,
        has_edit_plan=edit_plan is not None,
        confidence=edit_plan_output.confidence if edit_plan_output else None,
    )
    
    # 创建Agent
    agent = ctx.agent_factory.create_roadmap_editor()
    
    # 准备输入数据
    from app.models.domain import RoadmapEditInput
    edit_input = RoadmapEditInput(
        existing_framework=origin_framework,
        user_preferences=state["user_request"].preferences,
        edit_plan=edit_plan,
        modification_context=f"第 {modification_count} 轮修改",
    )
    
    # 执行编辑
    edit_output = await agent.execute(edit_input)
    
    # 提取修改后的框架
    modified_framework = edit_output.framework
    
    # 计算修改的节点ID（用于前端高亮显示）
    modified_node_ids = _compute_modified_node_ids(origin_framework, modified_framework)
    
    logger.info(
        "roadmap_edit_node_completed",
        task_id=task_id,
        roadmap_id=roadmap_id,
        modification_count=modification_count,
        modified_nodes_count=len(modified_node_ids),
    )
    
    # 获取edit_source（用于前端分支判断）
    edit_source = state.get("edit_source", "unknown")
    
    # 记录详细输出日志
    await execution_logger.info(
        task_id=task_id,
        category=LogCategory.AGENT,
        step="roadmap_edit",
        agent_name="RoadmapEditorAgent",
        roadmap_id=roadmap_id,
        message=f"✅ Roadmap edited: modification #{modification_count} (source: {edit_source})",
        details={
            "log_type": "roadmap_edit_output",
            "edit_source": edit_source,  # ✅ 添加：记录edit_source（与前端保持一致）
            "modification_count": modification_count,
            "modified_nodes_count": len(modified_node_ids),
        },
    )
    
    # 返回纯数据（不保存数据库）
    # ⚠️ 必须包含 Handler 需要的所有字段
    return {
        "roadmap_framework": modified_framework,  # ✅ 更新主 State
        "modified_framework": modified_framework,  # ✅ Handler 需要（EditorHandlerInput）
        "origin_framework": origin_framework,
        "roadmap_id": roadmap_id,             # ✅ Handler 需要
        "user_id": state["user_request"].user_id,  # ✅ Handler 需要
        "current_step": "roadmap_edit",
        "modification_count": modification_count,
        "edit_round": modification_count,
        "edit_source": edit_source,  # ✅ 添加：传递edit_source给前端
        "modified_node_ids": modified_node_ids,  # ✅ 添加：传递modified_node_ids给前端
        "execution_history": [f"路线图编辑完成（第 {modification_count} 轮）"],
    }


def _compute_modified_node_ids(
    origin_framework,
    modified_framework,
) -> list[str]:
    """
    计算修改过的节点ID
    
    Args:
        origin_framework: 原始框架
        modified_framework: 修改后的框架
    
    Returns:
        修改过的concept_id列表
    """
    if not origin_framework:
        # 如果没有原始框架，返回所有节点
        modified_ids = []
        for stage in modified_framework.stages:
            for module in stage.modules:
                modified_ids.extend([c.concept_id for c in module.concepts])
        return modified_ids
    
    # 使用简单的ID对比（与EditorHandler保持一致）
    from app.services.roadmaps.roadmap_comparison_service import (
        RoadmapComparisonService
    )
    
    comparison_service = RoadmapComparisonService()
    modified_ids = comparison_service.get_modified_node_ids_simple(
        origin_framework,
        modified_framework,
    )
    
    return modified_ids


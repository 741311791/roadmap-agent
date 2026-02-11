"""
课程设计节点（纯函数）

职责：
- 调用CurriculumArchitectAgent执行课程设计
- 返回纯数据（不保存数据库）
"""
import structlog
from langchain_core.runnables import RunnableConfig

from app.core.orchestrator.base import RoadmapState
from app.core.orchestrator.runtime_context import RuntimeContext
from app.services.shared.execution_logger import execution_logger, LogCategory

logger = structlog.get_logger()


async def curriculum_design_node(
    state: RoadmapState,
    config: RunnableConfig,
) -> dict:
    """
    课程设计节点（纯函数）
    
    从config获取依赖，执行Agent，返回纯数据。
    数据库保存由CurriculumDesignHandler处理。
    
    Args:
        state: 工作流状态
        config: 运行时配置（包含RuntimeContext）
    
    Returns:
        状态更新字典：
        - roadmap_framework: RoadmapFramework
        - current_step: 当前步骤
    """
    # 从config获取依赖
    ctx: RuntimeContext = config["configurable"]["runtime_context"]
    
    task_id = state["task_id"]
    intent_analysis = state["intent_analysis"]
    user_request = state["user_request"]
    
    logger.info(
        "curriculum_design_node_start",
        task_id=task_id,
        roadmap_id=state.get("roadmap_id"),
    )
    
    # 创建Agent
    agent = ctx.agent_factory.create_curriculum_architect()
    
    # 执行设计（传递3个独立参数）
    design_output = await agent.design(
        intent_analysis=intent_analysis,
        user_preferences=user_request.preferences,
        roadmap_id=state["roadmap_id"],
    )
    
    # 提取framework
    framework = design_output.framework
    
    logger.info(
        "curriculum_design_node_completed",
        task_id=task_id,
        roadmap_id=state.get("roadmap_id"),
        stages_count=len(framework.stages),
    )
    
    # 记录详细输出日志
    await execution_logger.info(
        task_id=task_id,
        category=LogCategory.AGENT,
        step="curriculum_design",
        agent_name="CurriculumArchitectAgent",
        roadmap_id=state.get("roadmap_id"),
        message=f"✅ Curriculum design completed: {len(framework.stages)} stages",
        details={
            "log_type": "curriculum_design_output",
            "stages_count": len(framework.stages),
            "title": framework.title,
        },
    )
    
    # 返回纯数据（不保存数据库）
    # ⚠️ 必须包含 Handler 需要的所有字段
    return {
        "roadmap_framework": framework,
        "roadmap_id": state["roadmap_id"],  # ✅ Handler 需要
        "user_id": user_request.user_id,     # ✅ Handler 需要
        "current_step": "curriculum_design",
        "execution_history": ["课程设计完成"],
    }


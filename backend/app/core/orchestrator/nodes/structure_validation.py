"""
结构验证节点（纯函数）

职责：
- 调用StructureValidatorAgent执行验证
- 返回纯数据（不保存数据库）
"""
import structlog
from langchain_core.runnables import RunnableConfig

from app.core.orchestrator.base import RoadmapState
from app.core.orchestrator.runtime_context import RuntimeContext
from app.services.shared.execution_logger import execution_logger, LogCategory

logger = structlog.get_logger()


async def structure_validation_node(
    state: RoadmapState,
    config: RunnableConfig,
) -> dict:
    """
    结构验证节点（纯函数）
    
    从config获取依赖，执行Agent，返回纯数据。
    数据库保存由ValidationHandler处理。
    
    Args:
        state: 工作流状态
        config: 运行时配置（包含RuntimeContext）
    
    Returns:
        状态更新字典：
        - validation_result: ValidationOutput
        - current_step: 当前步骤
        - validation_round: 验证轮次
    """
    # 从config获取依赖
    ctx: RuntimeContext = config["configurable"]["runtime_context"]
    
    task_id = state["task_id"]
    roadmap_id = state.get("roadmap_id")
    framework = state["roadmap_framework"]
    validation_round = state.get("validation_round", 0) + 1
    
    logger.info(
        "structure_validation_node_start",
        task_id=task_id,
        roadmap_id=roadmap_id,
        validation_round=validation_round,
    )
    
    # 创建Agent
    agent = ctx.agent_factory.create_structure_validator()
    
    # 执行验证（需要传递2个参数）
    validation_result = await agent.validate(
        framework=framework,
        user_preferences=state["user_request"].preferences,
    )
    
    logger.info(
        "structure_validation_node_completed",
        task_id=task_id,
        roadmap_id=roadmap_id,
        validation_round=validation_round,
        is_valid=validation_result.is_valid,
        overall_score=validation_result.overall_score,
    )
    
    # 记录详细输出日志
    await execution_logger.info(
        task_id=task_id,
        category=LogCategory.AGENT,
        step="structure_validation",
        agent_name="StructureValidatorAgent",
        roadmap_id=roadmap_id,
        message=f"✅ Validation completed: {'PASS' if validation_result.is_valid else 'FAIL'} (score: {validation_result.overall_score})",
        details={
            "log_type": "validation_output",
            "is_valid": validation_result.is_valid,
            "overall_score": validation_result.overall_score,
            "issues_count": len(validation_result.issues),
            "validation_round": validation_round,
        },
    )
    
    # 返回纯数据（不保存数据库）
    # ⚠️ 必须包含 Handler 需要的所有字段
    return {
        "validation_result": validation_result,
        "roadmap_id": state.get("roadmap_id"),  # ✅ Handler 需要
        "current_step": "structure_validation",
        "validation_round": validation_round,
        # ✅ 如果验证失败，设置edit_source为validation_failed（供edit_plan_analysis使用）
        "edit_source": "validation_failed" if not validation_result.is_valid else state.get("edit_source"),
        "execution_history": [f"结构验证完成（第 {validation_round} 轮）"],
    }


"""
意图分析节点（纯函数）

职责：
- 调用IntentAnalyzerAgent执行意图分析
- 返回纯数据（不保存数据库）
"""
import structlog
from langchain_core.runnables import RunnableConfig

from app.core.orchestrator.base import RoadmapState
from app.core.orchestrator.runtime_context import RuntimeContext
from app.services.shared.execution_logger import execution_logger, LogCategory

logger = structlog.get_logger()


async def intent_analysis_node(
    state: RoadmapState,
    config: RunnableConfig,
) -> dict:
    """
    意图分析节点（纯函数）
    
    从config获取依赖，执行Agent，返回纯数据。
    数据库保存由IntentAnalysisHandler处理。
    
    Args:
        state: 工作流状态
        config: 运行时配置（包含RuntimeContext）
    
    Returns:
        状态更新字典：
        - intent_analysis: IntentAnalysisOutput
        - roadmap_id: 路线图ID
        - current_step: 当前步骤
        - user_id: 用户ID（用于后续保存）
    """
    # 从config获取依赖
    ctx: RuntimeContext = config["configurable"]["runtime_context"]
    
    task_id = state["task_id"]
    user_request = state["user_request"]
    
    logger.info(
        "intent_analysis_node_start",
        task_id=task_id,
        user_id=user_request.user_id,
    )
    
    # 创建Agent
    agent = ctx.agent_factory.create_intent_analyzer()
    
    # 执行分析
    result = await agent.execute(user_request)
    
    logger.info(
        "intent_analysis_node_completed",
        task_id=task_id,
        roadmap_id=result.roadmap_id,
        key_technologies_count=len(result.key_technologies),
    )
    
    # 记录详细的分析输出日志（用于前端展示）
    await execution_logger.info(
        task_id=task_id,
        category=LogCategory.AGENT,
        step="intent_analysis",
        agent_name="IntentAnalyzerAgent",
        roadmap_id=result.roadmap_id,
        message=f"✅ Intent analysis completed: {result.parsed_goal[:80]}{'...' if len(result.parsed_goal) > 80 else ''}",
        details={
            "log_type": "intent_analysis_output",
            "output_summary": {
                "parsed_goal": result.parsed_goal,
                "key_technologies": result.key_technologies,
                "difficulty_profile": result.difficulty_profile,
                "time_constraint": result.time_constraint,
            },
        },
    )
    
    # 返回纯数据（不保存数据库）
    return {
        "intent_analysis": result,
        "roadmap_id": result.roadmap_id,
        "current_step": "intent_analysis",
        "user_id": user_request.user_id,
        "execution_history": ["需求分析完成"],
    }


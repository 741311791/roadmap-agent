"""
内容生成子图（外层编排）

使用两层 Fan-Out/Fan-In 架构实现多 Concept 的内容生成：
- 外层 Fan-Out：为每个 Concept 创建子图实例
- 外层 Reduce：自动汇总所有子图结果
- 最终汇总：检查并更新 Framework

架构设计：
1. 外层 Fan-Out：为每个 Concept 创建独立的单 Concept 子图实例
2. 并行执行：所有单 Concept 子图并行运行
3. 外层 Reduce：LangGraph 自动汇总所有子图结果
4. 最终汇总：批量更新 Framework 和 Task 状态

迁移说明：
- 共享的内容生成函数位于 content_generation_shared.py
- 新架构支持更细粒度的状态管理和独立测试
"""
from typing import TypedDict, Annotated
import operator
import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send, Command

from app.models.domain import (
    Concept,
    LearningPreferences,
)
from app.core.orchestrator.runtime_context import RuntimeContext
from app.core.orchestrator.handlers.content_handler import ContentHandler
from .single_concept_content_generation import build_single_concept_subgraph

logger = structlog.get_logger()


class ContentGenState(TypedDict):
    """
    外层子图状态
    
    注意：
    - 此状态用于外层子图编排
    - 管理多个 Concept 的并行生成
    - 使用 Reducer 自动汇总所有子图结果
    """
    # 输入数据
    roadmap_id: str
    concepts: list[Concept]
    user_preferences: LearningPreferences
    task_id: str
    
    # 单个 Concept 的输入（用于 Send API）
    concept: Concept | None
    
    # 汇总结果（使用 Reducer 自动累加）
    concept_results: Annotated[list[dict], operator.add]


def outer_fan_out(state: ContentGenState) -> Command:
    """
    外层 Fan-Out：为每个 Concept 创建子图实例
    
    使用 Send API 为每个 Concept 创建独立的单 Concept 子图实例。
    每个子图实例负责：
    - 并发生成 Tutorial、Resource、Quiz
    - Fan-In 收集并保存元数据
    - 返回该 Concept 的保存状态
    
    Args:
        state: 外层子图状态，包含所有 Concept 列表
        
    Returns:
        Command 对象，包含 N 个 Send 任务（N = Concept 数量）
    """
    concepts = state["concepts"]
    roadmap_id = state["roadmap_id"]
    user_preferences = state["user_preferences"]
    task_id = state["task_id"]
    
    logger.info(
        "outer_fan_out_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_count=len(concepts),
    )
    
    sends = []
    for concept in concepts:
        # 为每个 Concept 创建子图实例
        sends.append(Send("single_concept_subgraph", {
            "concept": concept,
            "roadmap_id": roadmap_id,
            "user_preferences": user_preferences,
            "task_id": task_id,
            "tutorial": None,
            "resource": None,
            "quiz": None,
            "errors": [],
            "save_status": {},
        }))
    
    logger.info(
        "outer_fan_out_completed",
        task_id=task_id,
        subgraph_instances=len(sends),
    )
    
    return Command(goto=sends)


async def single_concept_subgraph_wrapper(
    state: dict,
    config: RunnableConfig,
) -> dict:
    """
    单 Concept 子图包装器
    
    执行单 Concept 子图并返回结果。
    子图内部会：
    1. 并发生成 Tutorial、Resource、Quiz
    2. Fan-In 收集结果并保存元数据
    3. 返回保存状态
    
    Args:
        state: 单 Concept 状态（由 Send 传递）
        config: 运行时配置
        
    Returns:
        状态更新字典，包含该 Concept 的结果
    """
    task_id = state["task_id"]
    concept = state["concept"]
    
    logger.info(
        "single_concept_subgraph_executing",
        task_id=task_id,
        concept_id=concept.concept_id,
        concept_name=concept.name,
    )
    
    # 构建并执行单 Concept 子图
    subgraph = build_single_concept_subgraph()
    result = await subgraph.ainvoke(state, config)
    
    logger.info(
        "single_concept_subgraph_completed",
        task_id=task_id,
        concept_id=concept.concept_id,
        save_status=result.get("save_status", {}),
    )
    
    # 返回结果到 Reducer（只返回可序列化的字段，避免Celery序列化失败）
    serializable_result = {
        "concept_id": concept.concept_id,
        "save_status": result.get("save_status", {}),
        # 不返回完整的 Concept 对象，只返回基本信息
        "concept_name": concept.name,
    }
    
    return {
        "concept_results": [serializable_result],
    }


async def final_aggregation(
    state: ContentGenState,
    config: RunnableConfig,
) -> dict:
    """
    最终汇总节点
    
    职责：
    1. 检查所有 Concept 的元数据是否保存成功
    2. 统一更新整个 Framework（批量）
    3. 更新 Task 最终状态
    4. 发送工作流完成通知
    
    注意：
    - 此节点不保存单个元数据（已在各子图的 Fan-In 中完成）
    - 只负责批量更新 Framework 和最终状态
    
    Args:
        state: 外层子图状态，包含所有 Concept 的结果
        config: 运行时配置
        
    Returns:
        状态更新字典
    """
    ctx: RuntimeContext = config["configurable"]["runtime_context"]
    
    concept_results = state["concept_results"]
    roadmap_id = state["roadmap_id"]
    task_id = state["task_id"]
    
    logger.info(
        "final_aggregation_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        total_concepts=len(concept_results),
    )
    
    # 检查元数据保存状态
    all_saved = all(
        result.get("save_status", {}).get("metadata_saved", False)
        for result in concept_results
    )
    
    failed_concepts = [
        result.get("save_status", {}).get("concept_id")
        for result in concept_results
        if not result.get("save_status", {}).get("metadata_saved", False)
    ]
    
    logger.info(
        "final_aggregation_metadata_check",
        task_id=task_id,
        all_saved=all_saved,
        failed_count=len(failed_concepts),
        failed_concepts=failed_concepts,
    )
    
    # 创建 Handler 并批量更新 Framework
    # ⚠️ NodeOutputHandler 只接受 state_manager 参数
    handler = ContentHandler(
        state_manager=ctx.state_manager,
    )
    
    # ✅ 修复：使用 Celery 专用 Session（避免跨进程连接池问题）
    from app.db.celery_session import get_celery_session
    
    async with get_celery_session() as session:
        # 批量更新 Framework
        await handler.update_framework_batch(
            session=session,
            roadmap_id=roadmap_id,
            concept_results=concept_results,
        )
        
        # 更新 Task 最终状态
        final_status = "completed" if all_saved else "partial_failure"
        await handler.update_task_final_status(
            session=session,
            task_id=task_id,
            status=final_status,
        )
        
        # ✅ get_celery_session() 使用 .begin()，自动 commit/rollback
    
    # 发送工作流完成通知
    await ctx.notification_service.publish_completed(
        task_id=task_id,
        roadmap_id=roadmap_id,
        tutorials_count=len([
            r for r in concept_results
            if r.get("save_status", {}).get("tutorial") == "success"
        ]),
        failed_count=len(failed_concepts),
    )
    
    logger.info(
        "final_aggregation_completed",
        task_id=task_id,
        roadmap_id=roadmap_id,
        final_status=final_status,
    )
    
    return {
        "all_concepts_saved": all_saved,
        "failed_concepts": failed_concepts,
    }


def build_content_generation_subgraph(checkpointer=None):
    """
    构建外层内容生成子图（双 Checkpointer 架构）
    
    架构：
    1. START → outer_fan_out（外层 Fan-Out）
    2. outer_fan_out → single_concept_subgraph（N 个并行子图实例）
    3. single_concept_subgraph → 自动 Reduce（LangGraph 自动汇总）
    4. Reduce → final_aggregation（最终汇总）
    5. final_aggregation → END
    
    双 Checkpointer 架构：
    - 子图使用独立的 checkpointer（命名空间：child_graph）
    - 与父图共享 thread_id，实现逻辑关联
    - 子图可以独立记录并发任务进度，支持细粒度断点续传
    
    Args:
        checkpointer: 子图专用的 checkpointer（独立于父图）
    
    Returns:
        编译后的子图
    """
    builder = StateGraph(ContentGenState)
    
    # 添加外层 Fan-Out 节点
    builder.add_node("outer_fan_out", outer_fan_out)
    
    # 添加单 Concept 子图包装器节点（无需 RetryPolicy，子图内部已有）
    builder.add_node("single_concept_subgraph", single_concept_subgraph_wrapper)
    
    # 添加最终汇总节点
    builder.add_node("final_aggregation", final_aggregation)
    
    # 定义流程
    builder.add_edge(START, "outer_fan_out")
    # outer_fan_out 返回 Command，LangGraph 自动路由到 single_concept_subgraph
    # 所有子图完成后，Reducer 自动汇总结果
    builder.add_edge("single_concept_subgraph", "final_aggregation")
    builder.add_edge("final_aggregation", END)
    
    # ✅ 编译子图时传入独立的 checkpointer（双 Checkpointer 架构）
    subgraph = builder.compile(checkpointer=checkpointer)
    
    logger.info(
        "content_generation_subgraph_built_v3_dual_checkpointer",
        has_checkpointer=checkpointer is not None,
        namespace="child_graph" if checkpointer else None,
        architecture="dual_checkpointer",
    )
    
    return subgraph


# ========== 向后兼容：导出旧版本的生成函数 ==========
# 这些函数已移至 content_generation_shared.py
# 为了保持向后兼容，从共享模块导出

from .content_generation_shared import (
    generate_tutorial_for_concept,
    generate_resource_for_concept,
    generate_quiz_for_concept,
    ContentGenState as LegacyContentGenState,
)

__all__ = [
    "build_content_generation_subgraph",
    "ContentGenState",
    "generate_tutorial_for_concept",
    "generate_resource_for_concept",
    "generate_quiz_for_concept",
]

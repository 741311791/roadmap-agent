"""
单 Concept 内容生成子图

使用两层 Fan-Out/Fan-In 架构实现细粒度的内容生成：
- 内层 Fan-Out：并发生成 Tutorial、Resource、Quiz
- Fan-In：收集结果并保存元数据
- 支持独立调用，不依赖主图

架构优势：
- 细粒度 Checkpoint：每个 Concept 独立保存状态
- 单独重试：Tutorial 失败不影响 Resource 和 Quiz
- 独立测试：可脱离主图单独调用
- 清晰职责：每个 Concept 完成后立即保存元数据
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
    TutorialGenerationOutput,
    ResourceRecommendationOutput,
    QuizGenerationOutput,
)
from app.core.orchestrator.runtime_context import RuntimeContext
from app.core.orchestrator.handlers.concept_content_handler import ConceptContentHandler
from ..retry_policies import LLM_RETRY_POLICY, TAVILY_RETRY_POLICY
from .content_generation_legacy import (
    generate_tutorial_for_concept as _generate_tutorial_base,
    generate_resource_for_concept as _generate_resource_base,
    generate_quiz_for_concept as _generate_quiz_base,
)

logger = structlog.get_logger()


class SingleConceptState(TypedDict):
    """
    单 Concept 子图状态
    
    注意：
    - 此状态与外层子图状态隔离
    - 仅处理单个 Concept 的内容生成
    - 使用 Reducer 支持并行累加结果
    """
    # 输入数据
    concept: Concept
    roadmap_id: str
    user_preferences: LearningPreferences
    task_id: str
    
    # 并发生成的输出（使用 Reducer）
    tutorial: TutorialGenerationOutput | None
    resource: ResourceRecommendationOutput | None
    quiz: QuizGenerationOutput | None
    
    # 错误追踪（使用 Reducer）
    errors: Annotated[list[dict], operator.add]
    
    # Fan-In 保存结果
    save_status: dict  # {"tutorial": "success", "resource": "failed", ...}


def inner_fan_out(state: SingleConceptState) -> Command:
    """
    内层 Fan-Out：为单个 Concept 创建 3 个并行任务
    
    使用 Send API 动态创建并行任务：
    - generate_tutorial
    - generate_resource
    - generate_quiz
    
    Args:
        state: 单 Concept 子图状态
        
    Returns:
        Command 对象，包含 3 个 Send 任务
    """
    concept = state["concept"]
    task_id = state["task_id"]
    
    logger.info(
        "inner_fan_out_started",
        task_id=task_id,
        concept_id=concept.concept_id,
        concept_name=concept.name,
    )
    
    # 构造上下文信息
    context = {
        "roadmap_id": state["roadmap_id"],
        "stage_name": getattr(concept, "stage_name", "Unknown"),
        "module_name": getattr(concept, "module_name", "Unknown"),
    }
    
    # 为单个 Concept 创建 3 个并行任务
    sends = [
        Send("generate_tutorial", {
            "concept": concept,
            "context": context,
            "roadmap_id": state["roadmap_id"],
            "user_preferences": state["user_preferences"],
            "task_id": task_id,
        }),
        Send("generate_resource", {
            "concept": concept,
            "context": context,
            "roadmap_id": state["roadmap_id"],
            "user_preferences": state["user_preferences"],
            "task_id": task_id,
        }),
        Send("generate_quiz", {
            "concept": concept,
            "context": context,
            "roadmap_id": state["roadmap_id"],
            "user_preferences": state["user_preferences"],
            "task_id": task_id,
        }),
    ]
    
    logger.info(
        "inner_fan_out_completed",
        task_id=task_id,
        concept_id=concept.concept_id,
        parallel_tasks=len(sends),
    )
    
    return Command(goto=sends)


async def generate_tutorial_wrapper(
    state: dict,
    config: RunnableConfig,
) -> dict:
    """
    教程生成包装器
    
    适配现有的生成函数到新的状态结构。
    """
    # 转换状态格式（适配现有函数）
    adapted_state = {
        "concept": state["concept"],
        "context": state.get("context", {}),
        "user_preferences": state["user_preferences"],
        "roadmap_id": state["roadmap_id"],
        "task_id": state["task_id"],
    }
    
    # 调用现有的生成函数
    result = await _generate_tutorial_base(adapted_state, config)
    
    # 提取教程对象
    if "tutorials" in result and result["tutorials"]:
        return {"tutorial": result["tutorials"][0]}
    elif "errors" in result:
        return {"errors": result["errors"]}
    
    return {}


async def generate_resource_wrapper(
    state: dict,
    config: RunnableConfig,
) -> dict:
    """
    资源推荐包装器
    
    适配现有的生成函数到新的状态结构。
    """
    adapted_state = {
        "concept": state["concept"],
        "context": state.get("context", {}),
        "user_preferences": state["user_preferences"],
        "roadmap_id": state["roadmap_id"],
        "task_id": state["task_id"],
    }
    
    result = await _generate_resource_base(adapted_state, config)
    
    if "resources" in result and result["resources"]:
        return {"resource": result["resources"][0]}
    elif "errors" in result:
        return {"errors": result["errors"]}
    
    return {}


async def generate_quiz_wrapper(
    state: dict,
    config: RunnableConfig,
) -> dict:
    """
    测验生成包装器
    
    适配现有的生成函数到新的状态结构。
    """
    adapted_state = {
        "concept": state["concept"],
        "context": state.get("context", {}),
        "user_preferences": state["user_preferences"],
        "roadmap_id": state["roadmap_id"],
        "task_id": state["task_id"],
    }
    
    result = await _generate_quiz_base(adapted_state, config)
    
    if "quizzes" in result and result["quizzes"]:
        return {"quiz": result["quizzes"][0]}
    elif "errors" in result:
        return {"errors": result["errors"]}
    
    return {}


async def fan_in_and_save(
    state: SingleConceptState,
    config: RunnableConfig,
) -> dict:
    """
    Fan-In 收集器：收集并保存该 Concept 的元数据
    
    职责：
    1. 等待 Tutorial、Resource、Quiz 三个并发任务完成
    2. 收集生成结果
    3. 调用 ConceptContentHandler 保存元数据
    4. 记录保存状态
    
    注意：
    - 不管成功或失败，都会保存已生成的内容
    - 保存状态记录在 save_status 中
    - 不更新 Framework（由外层最终汇总节点处理）
    
    Args:
        state: 单 Concept 子图状态
        config: 运行时配置（包含 RuntimeContext）
        
    Returns:
        状态更新字典，包含 save_status
    """
    ctx: RuntimeContext = config["configurable"]["runtime_context"]
    
    concept = state["concept"]
    concept_id = concept.concept_id
    roadmap_id = state["roadmap_id"]
    task_id = state["task_id"]
    
    tutorial = state.get("tutorial")
    resource = state.get("resource")
    quiz = state.get("quiz")
    errors = state.get("errors", [])
    
    logger.info(
        "fan_in_and_save_started",
        task_id=task_id,
        concept_id=concept_id,
        has_tutorial=tutorial is not None,
        has_resource=resource is not None,
        has_quiz=quiz is not None,
        error_count=len(errors),
    )
    
    # 创建 Handler 并保存元数据
    handler = ConceptContentHandler()
    
    # ✅ 修复：使用 Celery 专用 Session（避免跨进程连接池问题）
    from app.db.celery_session import get_celery_session
    from app.schemas.handler_io import ConceptContentSaveResult
    
    async with get_celery_session() as session:
        save_result: ConceptContentSaveResult = await handler.save_concept_content(
            session=session,
            concept_id=concept_id,
            roadmap_id=roadmap_id,
            tutorial=tutorial,
            resource=resource,
            quiz=quiz,
        )
        # ✅ get_celery_session() 使用 .begin()，自动 commit/rollback
    
    # ✅ 记录执行日志：Concept 内容保存完成
    await ctx.execution_logger.info(
        task_id=task_id,
        category="content",
        step="content_generation",
        message=f"Concept 内容保存完成: {concept.name}",
        concept_id=concept_id,
        roadmap_id=roadmap_id,
        details={
            "concept_name": concept.name,
            "tutorial_status": save_result.tutorial,
            "resource_status": save_result.resource,
            "quiz_status": save_result.quiz,
            "metadata_saved": save_result.metadata_saved,
        },
    )
    
    # 发送 Concept 完成通知
    await ctx.notification_service.publish_concept_complete(
        task_id=task_id,
        concept_id=concept_id,
        concept_name=concept.name,
        content_type="all",  # 表示整个 Concept 完成
    )
    
    logger.info(
        "fan_in_and_save_completed",
        task_id=task_id,
        concept_id=concept_id,
        save_status=save_result.model_dump(),
    )
    
    # ✅ 返回 dict（LangGraph 兼容）
    return {
        "save_status": save_result.model_dump(),
    }


def build_single_concept_subgraph():
    """
    构建单 Concept 内容生成子图
    
    架构：
    1. START → inner_fan_out（内层 Fan-Out）
    2. inner_fan_out → [generate_tutorial, generate_resource, generate_quiz]（并行执行）
    3. [并行节点] → fan_in_and_save（Fan-In 收集并保存）
    4. fan_in_and_save → END
    
    Returns:
        编译后的子图
    """
    builder = StateGraph(SingleConceptState)
    
    # 添加内层 Fan-Out 节点
    builder.add_node("inner_fan_out", inner_fan_out)
    
    # 添加并行生成节点（含 RetryPolicy）
    builder.add_node(
        "generate_tutorial",
        generate_tutorial_wrapper,
        retry_policy=LLM_RETRY_POLICY,
    )
    builder.add_node(
        "generate_resource",
        generate_resource_wrapper,
        retry_policy=TAVILY_RETRY_POLICY,
    )
    builder.add_node(
        "generate_quiz",
        generate_quiz_wrapper,
        retry_policy=LLM_RETRY_POLICY,
    )
    
    # 添加 Fan-In 节点
    builder.add_node("fan_in_and_save", fan_in_and_save)
    
    # 定义流程
    builder.add_edge(START, "inner_fan_out")
    
    # 并行节点完成后流向 Fan-In
    builder.add_edge("generate_tutorial", "fan_in_and_save")
    builder.add_edge("generate_resource", "fan_in_and_save")
    builder.add_edge("generate_quiz", "fan_in_and_save")
    
    # Fan-In 完成后流向 END
    builder.add_edge("fan_in_and_save", END)
    
    # 编译子图
    subgraph = builder.compile()
    
    logger.info("single_concept_subgraph_built")
    
    return subgraph


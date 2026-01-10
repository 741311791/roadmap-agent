"""
内容生成子图

使用 LangGraph 1.0 子图模式和 Send API 实现内容生成的并行处理。

架构优势：
- 细粒度 Checkpoint：每个 Concept 的内容生成独立保存状态
- 单独重试：Tutorial 失败不影响 Resource 和 Quiz
- 动态并行：使用 Send API 根据 Concept 数量动态创建并行任务
- 统一容错：Node 级 RetryPolicy 自动处理失败
"""
from typing import TypedDict, Annotated, TYPE_CHECKING, Any
import operator
import structlog
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from app.models.domain import (
    Concept,
    LearningPreferences,
    TutorialGenerationInput,
    TutorialGenerationOutput,
    ResourceRecommendationInput,
    ResourceRecommendationOutput,
    QuizGenerationInput,
    QuizGenerationOutput,
)
from app.core.agent_factory import AgentFactory
from ..retry_policies import LLM_RETRY_POLICY, TAVILY_RETRY_POLICY
from .content_generation_types import (
    ContentType,
    NodeName,
    StateKey,
    ContextKey,
    ContentError,
)

if TYPE_CHECKING:
    from app.core.orchestrator.workflow_brain import WorkflowBrain

logger = structlog.get_logger()


class ContentGenState(TypedDict):
    """
    内容生成子图状态
    
    注意：
    - 子图状态与主图状态是隔离的
    - 仅通过调用时的参数传递数据
    - 使用 Reducer 支持并行累加结果
    """
    # 输入数据（由主图传入）
    roadmap_id: str
    concepts: list[Concept]
    user_preferences: LearningPreferences
    task_id: str  # 用于日志追踪
    
    # WorkflowBrain 和 AgentFactory（新增）
    brain: Any  # WorkflowBrain 实例（用于进度通知）
    agent_factory: Any  # AgentFactory 实例（用于创建 Agent）
    
    # 单个 Concept 的输入（用于 Send API）
    concept: Concept | None
    context: dict | None
    
    # 输出数据（使用 Reducer 累加）
    tutorials: Annotated[list[TutorialGenerationOutput], operator.add]
    resources: Annotated[list[ResourceRecommendationOutput], operator.add]
    quizzes: Annotated[list[QuizGenerationOutput], operator.add]
    
    # 错误追踪
    errors: Annotated[list[dict], operator.add]


async def generate_tutorial_for_concept(state: ContentGenState) -> dict:
    """
    为单个 Concept 生成教程（集成 WorkflowBrain）
    
    此函数会被 Send API 动态调用多次（每个 Concept 一次）
    
    职责：
    1. 调用 TutorialGeneratorAgent 生成教程
    2. 使用 WorkflowBrain 发送进度通知
    3. 返回生成结果（不保存数据库，由 ContentRunner 批量保存）
    
    Args:
        state: 子图状态，包含单个 Concept 的数据
        
    Returns:
        dict: 包含生成的教程或错误信息
    """
    concept = state[StateKey.CONCEPT.value]
    context = state.get(StateKey.CONTEXT.value, {})
    user_preferences = state[StateKey.USER_PREFERENCES.value]
    brain = state["brain"]
    agent_factory = state["agent_factory"]
    
    # 构造子状态用于 brain.node_execution()
    sub_node_state = {
        "task_id": state[StateKey.TASK_ID.value],
        "roadmap_id": state[StateKey.ROADMAP_ID.value],
        "current_step": f"tutorial_{concept.concept_id[:8]}",
    }
    
    # 使用 WorkflowBrain 的上下文管理器（用于进度通知）
    async with brain.node_execution(f"generate_tutorial_{concept.concept_id[:8]}", sub_node_state):
        try:
            # 创建 Agent（使用传入的 factory）
            tutorial_agent = agent_factory.create_tutorial_generator()
            
            # 构造输入
            tutorial_input = TutorialGenerationInput(
                concept=concept,
                context=context,
                user_preferences=user_preferences,
            )
            
            # 执行生成
            tutorial = await tutorial_agent.generate(tutorial_input)
            
            logger.info(
                "tutorial_generation_completed",
                task_id=state[StateKey.TASK_ID.value],
                concept_id=concept.concept_id,
                tutorial_id=tutorial.tutorial_id,
            )
            
            # 仅返回结果，不保存数据库（由 ContentRunner 批量保存）
            return {StateKey.TUTORIALS.value: [tutorial]}
            
        except Exception as e:
            logger.error(
                "tutorial_generation_failed",
                task_id=state[StateKey.TASK_ID.value],
                concept_id=concept.concept_id,
                error=str(e),
                exc_info=True,
            )
            # 使用 Pydantic 模型确保结构一致
            error = ContentError(
                type=ContentType.TUTORIAL,
                concept_id=concept.concept_id,
                concept_name=concept.name,
                error=str(e),
            )
            return {StateKey.ERRORS.value: [error.model_dump()]}


async def generate_resource_for_concept(state: ContentGenState) -> dict:
    """
    为单个 Concept 推荐资源（集成 WorkflowBrain）
    
    此函数会被 Send API 动态调用多次（每个 Concept 一次）
    
    职责：
    1. 调用 ResourceRecommenderAgent 推荐资源
    2. 使用 WorkflowBrain 发送进度通知
    3. 返回推荐结果（不保存数据库，由 ContentRunner 批量保存）
    
    Args:
        state: 子图状态，包含单个 Concept 的数据
        
    Returns:
        dict: 包含推荐的资源或错误信息
    """
    concept = state[StateKey.CONCEPT.value]
    context = state.get(StateKey.CONTEXT.value, {})
    user_preferences = state[StateKey.USER_PREFERENCES.value]
    brain = state["brain"]
    agent_factory = state["agent_factory"]
    
    # 构造子状态用于 brain.node_execution()
    sub_node_state = {
        "task_id": state[StateKey.TASK_ID.value],
        "roadmap_id": state[StateKey.ROADMAP_ID.value],
        "current_step": f"resource_{concept.concept_id[:8]}",
    }
    
    # 使用 WorkflowBrain 的上下文管理器（用于进度通知）
    async with brain.node_execution(f"generate_resource_{concept.concept_id[:8]}", sub_node_state):
        try:
            # 创建 Agent（使用传入的 factory）
            resource_agent = agent_factory.create_resource_recommender()
            
            # 构造输入
            resource_input = ResourceRecommendationInput(
                concept=concept,
                context=context,
                user_preferences=user_preferences,
            )
            
            # 执行推荐
            resources = await resource_agent.recommend(resource_input)
            
            logger.info(
                "resource_recommendation_completed",
                task_id=state[StateKey.TASK_ID.value],
                concept_id=concept.concept_id,
                resource_count=len(resources.resources),
            )
            
            # 仅返回结果，不保存数据库
            return {StateKey.RESOURCES.value: [resources]}
        
        except Exception as e:
            logger.error(
                "resource_recommendation_failed",
                task_id=state[StateKey.TASK_ID.value],
                concept_id=concept.concept_id,
                error=str(e),
                exc_info=True,
            )
            # 使用 Pydantic 模型确保结构一致
            error = ContentError(
                type=ContentType.RESOURCE,
                concept_id=concept.concept_id,
                concept_name=concept.name,
                error=str(e),
            )
            return {StateKey.ERRORS.value: [error.model_dump()]}


async def generate_quiz_for_concept(state: ContentGenState) -> dict:
    """
    为单个 Concept 生成测验（集成 WorkflowBrain）
    
    此函数会被 Send API 动态调用多次（每个 Concept 一次）
    
    职责：
    1. 调用 QuizGeneratorAgent 生成测验
    2. 使用 WorkflowBrain 发送进度通知
    3. 返回生成结果（不保存数据库，由 ContentRunner 批量保存）
    
    Args:
        state: 子图状态，包含单个 Concept 的数据
        
    Returns:
        dict: 包含生成的测验或错误信息
    """
    concept = state[StateKey.CONCEPT.value]
    context = state.get(StateKey.CONTEXT.value, {})
    user_preferences = state[StateKey.USER_PREFERENCES.value]
    brain = state["brain"]
    agent_factory = state["agent_factory"]
    
    # 构造子状态用于 brain.node_execution()
    sub_node_state = {
        "task_id": state[StateKey.TASK_ID.value],
        "roadmap_id": state[StateKey.ROADMAP_ID.value],
        "current_step": f"quiz_{concept.concept_id[:8]}",
    }
    
    # 使用 WorkflowBrain 的上下文管理器（用于进度通知）
    async with brain.node_execution(f"generate_quiz_{concept.concept_id[:8]}", sub_node_state):
        try:
            # 创建 Agent（使用传入的 factory）
            quiz_agent = agent_factory.create_quiz_generator()
            
            # 执行生成
            quiz = await quiz_agent.generate(
                concept=concept,
                context=context,
                user_preferences=user_preferences,
            )
            
            logger.info(
                "quiz_generation_completed",
                task_id=state[StateKey.TASK_ID.value],
                concept_id=concept.concept_id,
                quiz_id=quiz.quiz_id,
                question_count=len(quiz.questions),
            )
            
            # 仅返回结果，不保存数据库
            return {StateKey.QUIZZES.value: [quiz]}
        
        except Exception as e:
            logger.error(
                "quiz_generation_failed",
                task_id=state[StateKey.TASK_ID.value],
                concept_id=concept.concept_id,
                error=str(e),
                exc_info=True,
            )
            # 使用 Pydantic 模型确保结构一致
            error = ContentError(
                type=ContentType.QUIZ,
                concept_id=concept.concept_id,
                concept_name=concept.name,
                error=str(e),
            )
            return {StateKey.ERRORS.value: [error.model_dump()]}


def fan_out_concepts(state: ContentGenState) -> list[Send]:
    """
    Map 阶段：为每个 Concept 动态创建并行任务
    
    使用 LangGraph 1.0 的 Send API，为每个 Concept 创建 3 个并行任务：
    - generate_tutorial
    - generate_resource
    - generate_quiz
    
    Args:
        state: 子图状态，包含所有 Concept 列表
        
    Returns:
        Send 对象列表，每个 Send 指定目标节点和传递的状态
    """
    concepts = state[StateKey.CONCEPTS.value]
    roadmap_id = state[StateKey.ROADMAP_ID.value]
    user_preferences = state[StateKey.USER_PREFERENCES.value]
    task_id = state[StateKey.TASK_ID.value]
    
    logger.info(
        "fan_out_concepts_started",
        task_id=task_id,
        concept_count=len(concepts),
    )
    
    sends = []
    for concept in concepts:
        # 构造上下文信息（包含所属阶段和模块）
        context = {
            ContextKey.ROADMAP_ID.value: roadmap_id,
            ContextKey.STAGE_NAME.value: getattr(concept, "stage_name", "Unknown"),
            ContextKey.MODULE_NAME.value: getattr(concept, "module_name", "Unknown"),
        }
        
        # 为每个 Concept 创建 3 个并行任务（使用枚举确保节点名称正确）
        concept_state = {
            StateKey.CONCEPT.value: concept,
            StateKey.CONTEXT.value: context,
            StateKey.ROADMAP_ID.value: roadmap_id,
            StateKey.USER_PREFERENCES.value: user_preferences,
            StateKey.TASK_ID.value: task_id,
            StateKey.TUTORIALS.value: [],
            StateKey.RESOURCES.value: [],
            StateKey.QUIZZES.value: [],
            StateKey.ERRORS.value: [],
        }
        
        sends.append(Send(NodeName.GENERATE_TUTORIAL.value, concept_state))
        sends.append(Send(NodeName.GENERATE_RESOURCE.value, concept_state))
        sends.append(Send(NodeName.GENERATE_QUIZ.value, concept_state))
    
    logger.info(
        "fan_out_concepts_completed",
        task_id=task_id,
        total_sends=len(sends),
    )
    
    return sends


def build_content_generation_subgraph():
    """
    构建内容生成子图
    
    架构：
    1. fan_out 节点：动态创建并行任务（Send API）
    2. generate_tutorial/resource/quiz：并行执行（含 RetryPolicy）
    3. 自动合并结果（Reducer）
    
    Returns:
        编译后的子图
    """
    builder = StateGraph(ContentGenState)
    
    # 添加 fan_out 节点（不需要 RetryPolicy）
    builder.add_node(NodeName.FAN_OUT.value, fan_out_concepts)
    
    # 添加并行执行节点（含 RetryPolicy）
    builder.add_node(
        NodeName.GENERATE_TUTORIAL.value,
        generate_tutorial_for_concept,
        retry=LLM_RETRY_POLICY,  # Tutorial 生成使用 LLM
    )
    builder.add_node(
        NodeName.GENERATE_RESOURCE.value,
        generate_resource_for_concept,
        retry=TAVILY_RETRY_POLICY,  # Resource 推荐使用 Tavily 搜索
    )
    builder.add_node(
        NodeName.GENERATE_QUIZ.value,
        generate_quiz_for_concept,
        retry=LLM_RETRY_POLICY,  # Quiz 生成使用 LLM
    )
    
    # 定义边：START -> fan_out -> 动态并行节点 -> END
    builder.add_edge(START, NodeName.FAN_OUT.value)
    builder.add_conditional_edges(NodeName.FAN_OUT.value, fan_out_concepts)
    
    # 所有并行节点完成后自动流向 END
    builder.add_edge(NodeName.GENERATE_TUTORIAL.value, END)
    builder.add_edge(NodeName.GENERATE_RESOURCE.value, END)
    builder.add_edge(NodeName.GENERATE_QUIZ.value, END)
    
    # 编译子图（不传递 checkpointer，会自动继承父图的）
    subgraph = builder.compile()
    
    logger.info("content_generation_subgraph_built")
    
    return subgraph


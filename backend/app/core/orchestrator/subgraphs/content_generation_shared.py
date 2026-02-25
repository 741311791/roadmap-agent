"""
内容生成共享函数

为单个 Concept 生成教程、资源和测验的纯函数实现。
这些函数被多个子图使用，提取到独立模块以便维护。
"""
import structlog
from langchain_core.runnables import RunnableConfig

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
from app.core.orchestrator.runtime_context import RuntimeContext
from .content_generation_types import (
    ContentType,
    StateKey,
    ContentError,
)

logger = structlog.get_logger()


async def generate_tutorial_for_concept(
    state: dict,
    config: RunnableConfig,
) -> dict:
    """
    为单个 Concept 生成教程（纯函数）
    
    此函数会被 Send API 动态调用多次（每个 Concept 一次）
    
    职责：
    1. 调用 TutorialGeneratorAgent 生成教程
    2. 返回生成结果（不保存数据库，由 ContentHandler 批量保存）
    
    Args:
        state: 子图状态，包含单个 Concept 的数据
        config: 运行时配置（包含 RuntimeContext）
        
    Returns:
        dict: 包含生成的教程或错误信息
    """
    # 从 config 获取依赖
    ctx: RuntimeContext = config["configurable"]["runtime_context"]
    
    concept = state[StateKey.CONCEPT.value]
    context = state.get(StateKey.CONTEXT.value, {})
    user_preferences = state[StateKey.USER_PREFERENCES.value]
    task_id = state[StateKey.TASK_ID.value]
    roadmap_id = state[StateKey.ROADMAP_ID.value]
    
    try:
        # 创建 Agent
        tutorial_agent = ctx.agent_factory.create_tutorial_generator()
        
        # 构造输入
        tutorial_input = TutorialGenerationInput(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
        )
        
        # 执行生成（使用统一的 execute 方法）
        tutorial = await tutorial_agent.execute(tutorial_input)
        
        logger.info(
            "content_generation_completed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept.concept_id,
            tutorial_id=tutorial.tutorial_id,
        )
        
        # 发送进度通知（直接使用 notification_service）
        await ctx.notification_service.publish_concept_complete(
            task_id=task_id,
            concept_id=concept.concept_id,
            concept_name=concept.name,
            content_type="tutorial",
        )
        
        # 返回结果
        return {StateKey.TUTORIALS.value: [tutorial]}
        
    except Exception as e:
        logger.error(
            "content_generation_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept.concept_id,
            error=str(e),
            exc_info=True,
        )
        
        # 发送失败通知
        await ctx.notification_service.publish_concept_failed(
            task_id=task_id,
            concept_id=concept.concept_id,
            concept_name=concept.name,
            content_type="tutorial",
            error=str(e),
        )
        
        # 返回错误
        error = ContentError(
            type=ContentType.TUTORIAL,
            concept_id=concept.concept_id,
            concept_name=concept.name,
            error=str(e),
        )
        return {StateKey.ERRORS.value: [error.model_dump()]}


async def generate_resource_for_concept(
    state: dict,
    config: RunnableConfig,
) -> dict:
    """
    为单个 Concept 推荐资源（纯函数）
    
    此函数会被 Send API 动态调用多次（每个 Concept 一次）
    
    职责：
    1. 调用 ResourceRecommenderAgent 推荐资源
    2. 返回推荐结果（不保存数据库，由 ContentHandler 批量保存）
    
    Args:
        state: 子图状态，包含单个 Concept 的数据
        config: 运行时配置（包含 RuntimeContext）
        
    Returns:
        dict: 包含推荐的资源或错误信息
    """
    # 从 config 获取依赖
    ctx: RuntimeContext = config["configurable"]["runtime_context"]
    
    concept = state[StateKey.CONCEPT.value]
    context = state.get(StateKey.CONTEXT.value, {})
    user_preferences = state[StateKey.USER_PREFERENCES.value]
    task_id = state[StateKey.TASK_ID.value]
    roadmap_id = state[StateKey.ROADMAP_ID.value]
    
    try:
        # 创建 Agent
        resource_agent = ctx.agent_factory.create_resource_recommender()
        
        # 构造输入
        resource_input = ResourceRecommendationInput(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
        )
        
        # 执行推荐（使用统一的 execute 方法）
        resource = await resource_agent.execute(resource_input)
        
        logger.info(
            "resource_recommendation_completed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept.concept_id,
            resource_count=len(resource.resources),
        )
        
        # 发送进度通知
        # 注意：使用 "resources" 而非 "resource"，与前端 WSConceptCompleteEvent.content_type 定义一致
        await ctx.notification_service.publish_concept_complete(
            task_id=task_id,
            concept_id=concept.concept_id,
            concept_name=concept.name,
            content_type="resources",
        )
        
        # 返回结果
        return {StateKey.RESOURCES.value: [resource]}
        
    except Exception as e:
        logger.error(
            "resource_recommendation_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept.concept_id,
            error=str(e),
            exc_info=True,
        )
        
        # 发送失败通知
        await ctx.notification_service.publish_concept_failed(
            task_id=task_id,
            concept_id=concept.concept_id,
            concept_name=concept.name,
            content_type="resources",
            error=str(e),
        )
        
        # 返回错误
        error = ContentError(
            type=ContentType.RESOURCE,
            concept_id=concept.concept_id,
            concept_name=concept.name,
            error=str(e),
        )
        return {StateKey.ERRORS.value: [error.model_dump()]}


async def generate_quiz_for_concept(
    state: dict,
    config: RunnableConfig,
) -> dict:
    """
    为单个 Concept 生成测验（纯函数）
    
    此函数会被 Send API 动态调用多次（每个 Concept 一次）
    
    职责：
    1. 调用 QuizGeneratorAgent 生成测验
    2. 返回生成结果（不保存数据库，由 ContentHandler 批量保存）
    
    Args:
        state: 子图状态，包含单个 Concept 的数据
        config: 运行时配置（包含 RuntimeContext）
        
    Returns:
        dict: 包含生成的测验或错误信息
    """
    # 从 config 获取依赖
    ctx: RuntimeContext = config["configurable"]["runtime_context"]
    
    concept = state[StateKey.CONCEPT.value]
    context = state.get(StateKey.CONTEXT.value, {})
    user_preferences = state[StateKey.USER_PREFERENCES.value]
    task_id = state[StateKey.TASK_ID.value]
    roadmap_id = state[StateKey.ROADMAP_ID.value]
    
    try:
        # 创建 Agent
        quiz_agent = ctx.agent_factory.create_quiz_generator()
        
        # 构造输入
        quiz_input = QuizGenerationInput(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
        )
        
        # 执行生成（使用统一的 execute 方法）
        quiz = await quiz_agent.execute(quiz_input)
        
        logger.info(
            "quiz_generation_completed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept.concept_id,
            quiz_id=quiz.quiz_id,
            question_count=len(quiz.questions),
        )
        
        # 发送进度通知
        await ctx.notification_service.publish_concept_complete(
            task_id=task_id,
            concept_id=concept.concept_id,
            concept_name=concept.name,
            content_type="quiz",
        )
        
        # 返回结果
        return {StateKey.QUIZZES.value: [quiz]}
        
    except Exception as e:
        logger.error(
            "quiz_generation_failed",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept.concept_id,
            error=str(e),
            exc_info=True,
        )
        
        # 发送失败通知
        await ctx.notification_service.publish_concept_failed(
            task_id=task_id,
            concept_id=concept.concept_id,
            concept_name=concept.name,
            content_type="quiz",
            error=str(e),
        )
        
        # 返回错误
        error = ContentError(
            type=ContentType.QUIZ,
            concept_id=concept.concept_id,
            concept_name=concept.name,
            error=str(e),
        )
        return {StateKey.ERRORS.value: [error.model_dump()]}


# 为了向后兼容，导出 ContentGenState
# 注意：这个类型只在 legacy 代码中使用
from typing import TypedDict, Annotated
import operator

class ContentGenState(TypedDict):
    """
    内容生成子图状态（向后兼容）
    """
    roadmap_id: str
    concepts: list[Concept]
    user_preferences: LearningPreferences
    task_id: str
    concept: Concept | None
    context: dict | None
    tutorials: Annotated[list[TutorialGenerationOutput], operator.add]
    resources: Annotated[list[ResourceRecommendationOutput], operator.add]
    quizzes: Annotated[list[QuizGenerationOutput], operator.add]
    errors: Annotated[list[dict], operator.add]

"""
内容重新生成 API 端点

提供教程、资源、测验的重新生成功能。

重构变更：
- ✅ 从 content.py 拆分出重新生成相关接口
- ✅ 使用CurrentSessionTransaction（写操作）
- ✅ 使用统一响应格式（ResponseSchemaModel）

注意：
这不属于Retry功能，而是Concept编辑服务的一部分。
- Retry：使用checkpoint恢复整个workflow
- Regenerate：直接调用Agent重新生成单个内容
"""
from typing import Annotated
from fastapi import APIRouter, Depends
import structlog

from app.api.v1.deps import CurrentContentService, CurrentSessionTransaction
from app.core.response_schema import ResponseSchemaModel, response_base
from app.schemas.generation import RetryContentRequest, RetryContentResponse
from app.models.database import User
from app.core.auth.deps import current_active_user

router = APIRouter(prefix="/content", tags=["content-regenerate"])
logger = structlog.get_logger()


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/tutorial/regenerate",
    response_model=ResponseSchemaModel[RetryContentResponse],
    summary="重新生成教程",
    description="""
    重新生成单个Concept的教程内容。
    
    这是Concept编辑功能的一部分，不属于Retry（checkpoint恢复）功能。
    直接调用TutorialGeneratorAgent重新生成，不使用LangGraph checkpoint机制。
    
    适用场景：
    - 单个教程质量不满意
    - 需要不同风格的教程
    - 调整教程详细度
    """,
)
async def regenerate_tutorial(
    roadmap_id: str,
    concept_id: str,
    request: RetryContentRequest,
    content_service: CurrentContentService,
    session: CurrentSessionTransaction,
    current_user: User = Depends(current_active_user),
) -> ResponseSchemaModel[RetryContentResponse]:
    """
    重新生成单个Concept的教程内容
    
    这是Concept编辑功能，不属于Retry（checkpoint恢复）功能。
    
    Args:
        roadmap_id: 路线图ID
        concept_id: 概念ID
        request: 重新生成请求（包含用户反馈）
        content_service: 内容服务
        session: 数据库会话
        current_user: 当前用户
        
    Returns:
        重新生成的教程内容
    """
    from app.schemas.generation import ConceptRetryRequest
    
    logger.info(
        "regenerate_tutorial_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        user_id=current_user.id,
    )
    
    # 转换请求格式
    retry_request = ConceptRetryRequest(
        user_feedback=request.user_feedback or "重试教程生成"
    )
    
    # 调用ContentService
    result = await content_service.retry_content(
        session=session,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type="tutorial",
        request=retry_request,
    )
    
    # 转换响应格式
    response = RetryContentResponse(
        success=result.success,
        concept_id=result.concept_id,
        content_type=result.content_type,
        message=result.message,
        new_content=result.data if result.success else None,
    )
    
    return response_base.success(data=response)


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/resources/regenerate",
    response_model=ResponseSchemaModel[RetryContentResponse],
    summary="重新生成资源推荐",
    description="""
    重新生成单个Concept的资源推荐内容。
    
    这是Concept编辑功能的一部分，不属于Retry功能。
    """,
)
async def regenerate_resources(
    roadmap_id: str,
    concept_id: str,
    request: RetryContentRequest,
    content_service: CurrentContentService,
    session: CurrentSessionTransaction,
    current_user: User = Depends(current_active_user),
) -> ResponseSchemaModel[RetryContentResponse]:
    """
    重新生成单个Concept的资源推荐内容
    
    这是Concept编辑功能，不属于Retry功能。
    """
    from app.schemas.generation import ConceptRetryRequest
    
    logger.info(
        "regenerate_resources_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        user_id=current_user.id,
    )
    
    retry_request = ConceptRetryRequest(
        user_feedback=request.user_feedback or "重试资源推荐生成"
    )
    
    result = await content_service.retry_content(
        session=session,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type="resources",
        request=retry_request,
    )
    
    response = RetryContentResponse(
        success=result.success,
        concept_id=result.concept_id,
        content_type=result.content_type,
        message=result.message,
        new_content=result.data if result.success else None,
    )
    
    return response_base.success(data=response)


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/quiz/regenerate",
    response_model=ResponseSchemaModel[RetryContentResponse],
    summary="重新生成测验",
    description="""
    重新生成单个Concept的测验内容。
    
    这是Concept编辑功能的一部分，不属于Retry功能。
    """,
)
async def regenerate_quiz(
    roadmap_id: str,
    concept_id: str,
    request: RetryContentRequest,
    content_service: CurrentContentService,
    session: CurrentSessionTransaction,
    current_user: User = Depends(current_active_user),
) -> ResponseSchemaModel[RetryContentResponse]:
    """
    重新生成单个Concept的测验内容
    
    这是Concept编辑功能，不属于Retry功能。
    """
    from app.schemas.generation import ConceptRetryRequest
    
    logger.info(
        "regenerate_quiz_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        user_id=current_user.id,
    )
    
    retry_request = ConceptRetryRequest(
        user_feedback=request.user_feedback or "重试测验生成"
    )
    
    result = await content_service.retry_content(
        session=session,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type="quiz",
        request=retry_request,
    )
    
    response = RetryContentResponse(
        success=result.success,
        concept_id=result.concept_id,
        content_type=result.content_type,
        message=result.message,
        new_content=result.data if result.success else None,
    )
    
    return response_base.success(data=response)


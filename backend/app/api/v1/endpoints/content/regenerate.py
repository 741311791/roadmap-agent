"""
内容重新生成 API 端点

提供教程、资源、测验的重新生成功能。

架构：
- 端点只负责参数校验、创建 RoadmapTask 追踪记录、派发 Celery 任务后立即返回。
- 实际的 Agent 调用在 content_generation 队列的 Celery Worker 中执行，
  不占用主应用进程。
- 前端通过 WebSocket 订阅 task_id 接收生成进度和结果通知。
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from app.api.v1.deps import CurrentContentService, CurrentSessionTransaction
from app.core.response_schema import ResponseSchemaModel, response_base
from app.schemas.generation import RetryContentRequest, RetryContentResponse
from app.models.database import User
from app.core.auth.deps import current_active_user
from app.crud.crud_task import get_task_crud

router = APIRouter(prefix="/content", tags=["content-regenerate"])
logger = structlog.get_logger()

_CONTENT_TYPE_LABEL = {
    "tutorial": "教程",
    "resources": "资源推荐",
    "quiz": "测验",
}


async def _dispatch_regenerate_task(
    roadmap_id: str,
    concept_id: str,
    content_type: str,
    user_id: str,
    session,
    content_service,
) -> RetryContentResponse:
    """
    通用内容重新生成派发逻辑

    1. 验证概念存在
    2. 创建 RoadmapTask 记录（status=processing，current_step=content_generation）
    3. 派发到 content_generation Celery 队列
    4. 返回 task_id（前端通过 WebSocket 订阅进度）

    端点本身只做 DB 写入和任务入队，不执行任何 LLM 调用。
    """
    # 1. 验证概念存在于路线图中
    concept, _, _ = await content_service.concept_service.get_concept_from_roadmap(
        session, roadmap_id, concept_id
    )
    if not concept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Concept {concept_id} not found in roadmap {roadmap_id}",
        )

    # 2. 预分配 Celery task ID，在创建 RoadmapTask 时一并写入。
    #    这样僵尸状态检测能立即看到 celery_task_id，消除"任务刚派发但
    #    Worker 尚未启动"窗口期内被误判为僵尸的竞态条件。
    task_id = f"regen-{uuid.uuid4().hex[:12]}"
    celery_task_id = str(uuid.uuid4())

    task_crud = get_task_crud()
    await task_crud.create(session, obj_in={
        "task_id": task_id,
        "user_id": user_id,
        "roadmap_id": roadmap_id,
        "concept_id": concept_id,
        "content_type": content_type,
        "task_type": f"regenerate_{content_type}",
        "status": "processing",
        "current_step": "content_generation",
        "celery_task_id": celery_task_id,
        "user_request": {
            "type": f"regenerate_{content_type}",
            "roadmap_id": roadmap_id,
            "concept_id": concept_id,
            "content_type": content_type,
        },
    })
    await session.flush()

    # 3. 派发到 content_generation 队列，并指定预分配的 celery_task_id
    from app.tasks.content_generation_tasks import regenerate_single_content_task
    regenerate_single_content_task.apply_async(
        args=[task_id, roadmap_id, concept_id, content_type],
        task_id=celery_task_id,
        queue="content_generation",
    )

    logger.info(
        "regenerate_content_task_dispatched",
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type=content_type,
        user_id=user_id,
    )

    label = _CONTENT_TYPE_LABEL.get(content_type, content_type)
    return RetryContentResponse(
        success=True,
        concept_id=concept_id,
        content_type=content_type,
        message=f"{label}重新生成任务已提交，正在 content_generation Worker 中处理",
        data={"task_id": task_id},
    )


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/tutorial/regenerate",
    response_model=ResponseSchemaModel[RetryContentResponse],
    summary="重新生成教程",
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
    异步重新生成单个 Concept 的教程内容

    任务被派发到 content_generation Celery 队列，立即返回 task_id。
    前端通过 WebSocket 订阅该 task_id 接收完成或失败通知。
    """
    logger.info(
        "regenerate_tutorial_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        user_id=current_user.id,
    )
    response = await _dispatch_regenerate_task(
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type="tutorial",
        user_id=current_user.id,
        session=session,
        content_service=content_service,
    )
    return response_base.success(data=response)


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/resources/regenerate",
    response_model=ResponseSchemaModel[RetryContentResponse],
    summary="重新生成资源推荐",
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
    异步重新生成单个 Concept 的资源推荐内容

    任务被派发到 content_generation Celery 队列，立即返回 task_id。
    """
    logger.info(
        "regenerate_resources_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        user_id=current_user.id,
    )
    response = await _dispatch_regenerate_task(
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type="resources",
        user_id=current_user.id,
        session=session,
        content_service=content_service,
    )
    return response_base.success(data=response)


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/quiz/regenerate",
    response_model=ResponseSchemaModel[RetryContentResponse],
    summary="重新生成测验",
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
    异步重新生成单个 Concept 的测验内容

    任务被派发到 content_generation Celery 队列，立即返回 task_id。
    """
    logger.info(
        "regenerate_quiz_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        user_id=current_user.id,
    )
    response = await _dispatch_regenerate_task(
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type="quiz",
        user_id=current_user.id,
        session=session,
        content_service=content_service,
    )
    return response_base.success(data=response)

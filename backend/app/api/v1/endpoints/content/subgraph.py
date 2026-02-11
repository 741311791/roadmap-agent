"""
内容生成子图独立 API

支持子图脱离主图单独调用，用于：
- 重新生成单个 Concept 的内容
- 测试子图逻辑
- 手动触发内容生成
- 调试和开发

架构说明：
- API 层：只负责 HTTP 适配和 Celery 任务分发
- Task 层：Celery 异步任务执行
- Service 层：业务逻辑实现
- 遵循分层架构设计规范
"""
import structlog
from fastapi import APIRouter, HTTPException, status

from app.core.response_schema import ResponseModel, response_base
from app.api.v1.deps import CurrentUser
from app.schemas.content import GenerateSingleConceptRequest, ContentGenerationTaskResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/subgraph", tags=["Content Subgraph"])


@router.post("/generate-single-concept")
async def generate_single_concept_content(
    request: GenerateSingleConceptRequest,
    user: CurrentUser,
) -> ResponseModel:
    """
    独立调用单 Concept 子图生成内容（Celery 异步任务）
    
    此接口允许单独重新生成某个 Concept 的内容，不依赖完整的工作流。
    任务将分发到 Celery Worker 执行，FastAPI 进程立即返回任务 ID。
    
    架构说明：
    - ✅ API 层只负责 HTTP 适配和 Celery 任务分发
    - ✅ 任务在独立的 Worker 进程中执行
    - ✅ 通过 WebSocket 推送任务进度和结果
    - ✅ 遵循分层架构设计规范
    
    Args:
        request: 请求参数
        user: 当前用户
    
    Returns:
        Celery 任务 ID 和任务状态
    
    Raises:
        500: 任务分发失败
    
    使用流程：
    1. 调用此接口获取 celery_task_id
    2. 通过 WebSocket 订阅 `roadmap:{roadmap_id}` 频道
    3. 接收实时进度通知和最终结果
    """
    from app.tasks.content_generation_tasks import generate_single_concept_content_task
    
    try:
        # ✅ 分发 Celery 任务（异步执行）
        celery_task = generate_single_concept_content_task.delay(
            roadmap_id=request.roadmap_id,
            concept_id=request.concept_id,
            user_id=user.id,
            force_regenerate=request.force_regenerate,
        )
        
        logger.info(
            "content_generation_task_dispatched",
            roadmap_id=request.roadmap_id,
            concept_id=request.concept_id,
            celery_task_id=celery_task.id,
            user_id=user.id,
        )
        
        return response_base.success(
            data=ContentGenerationTaskResponse(
                celery_task_id=celery_task.id,
                roadmap_id=request.roadmap_id,
                concept_id=request.concept_id,
                status="pending",
                message="内容生成任务已提交，正在队列中等待执行",
            )
        )
        
    except Exception as e:
        logger.error(
            "content_generation_task_dispatch_failed",
            roadmap_id=request.roadmap_id,
            concept_id=request.concept_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch content generation task: {str(e)}",
        )


@router.get("/task/{celery_task_id}/status")
async def get_task_status(celery_task_id: str) -> ResponseModel:
    """
    查询 Celery 任务状态
    
    Args:
        celery_task_id: Celery 任务 ID
        
    Returns:
        任务状态信息
    """
    from celery.result import AsyncResult
    from app.core.celery_app import celery_app
    
    try:
        task_result = AsyncResult(celery_task_id, app=celery_app)
        
        response_data = {
            "celery_task_id": celery_task_id,
            "status": task_result.state,
            "result": None,
        }
        
        # 如果任务已完成，返回结果
        if task_result.ready():
            if task_result.successful():
                response_data["result"] = task_result.result
            elif task_result.failed():
                response_data["error"] = str(task_result.info)
        
        return response_base.success(data=response_data)
        
    except Exception as e:
        logger.error(
            "get_task_status_failed",
            celery_task_id=celery_task_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}",
        )


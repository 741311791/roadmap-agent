"""
失败重试相关端点（简化版 - 符合架构规范）

包含以下功能：
- 重试失败的内容生成
- 重新生成特定概念的内容
- 通过 task_id 重试任务
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import structlog

from app.models.domain import LearningPreferences
from app.api.v1.deps import get_current_session
from app.services.retry_service_new import RetryService, get_retry_service

router = APIRouter(prefix="/roadmaps", tags=["retry"])
tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = structlog.get_logger()

# 依赖注入
CurrentRetryService = Annotated[RetryService, Depends(get_retry_service)]


class RetryFailedRequest(BaseModel):
    """重试失败内容请求"""
    user_id: str = Field(..., description="用户ID")
    content_types: list[str] = Field(
        default=["tutorial", "resources", "quiz"],
        description="要重试的内容类型列表"
    )
    preferences: LearningPreferences = Field(..., description="用户学习偏好")


class RegenerateContentRequest(BaseModel):
    """重新生成内容请求"""
    preferences: LearningPreferences = Field(..., description="用户学习偏好")


@router.post("/{roadmap_id}/retry-failed")
async def retry_failed_content(
    roadmap_id: str,
    request: RetryFailedRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentRetryService = None,
):
    """
    断点续传：重新生成失败的内容
    
    Args:
        roadmap_id: 路线图 ID
        request: 包含用户偏好和要重试的内容类型
        background_tasks: FastAPI后台任务
        session: 数据库会话
        service: 重试服务
        
    Returns:
        task_id 用于 WebSocket 订阅进度
    """
    logger.info(
        "retry_failed_content_requested",
        roadmap_id=roadmap_id,
        user_id=request.user_id,
        content_types=request.content_types,
    )
    
    # 调用Service层准备数据
    try:
        retry_data = await service.prepare_retry_failed_content(
            session, roadmap_id, request.content_types
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    if retry_data["total_items"] == 0:
        return {
            "status": "no_failed_items",
            "message": "没有需要重试的失败项目",
            "failed_counts": retry_data["failed_counts"],
        }
    
    # 启动后台重试任务
    from app.services.retry_service import execute_retry_failed_task
    background_tasks.add_task(
        execute_retry_failed_task,
        retry_task_id=retry_data["retry_task_id"],
        roadmap_id=roadmap_id,
        items_to_retry=retry_data["items_to_retry"],
        user_preferences=request.preferences,
        user_id=request.user_id,
    )
    
    return {
        "task_id": retry_data["retry_task_id"],
        "roadmap_id": roadmap_id,
        "status": "processing",
        "items_to_retry": {
            content_type: len(items) 
            for content_type, items in retry_data["items_to_retry"].items()
        },
        "total_items": retry_data["total_items"],
        "message": f"开始重试 {retry_data['total_items']} 个失败项目",
    }


@router.post("/{roadmap_id}/concepts/{concept_id}/regenerate")
async def regenerate_concept_content(
    roadmap_id: str,
    concept_id: str,
    request: RegenerateContentRequest,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentRetryService = None,
):
    """
    重新生成指定概念的所有内容（教程+资源+测验）
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 包含学习偏好
        session: 数据库会话
        service: 重试服务
        
    Returns:
        重新生成的结果
        
    Raises:
        HTTPException: 404 - 路线图或概念不存在
    """
    logger.info(
        "regenerate_concept_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
    )
    
    # 调用Service层
    try:
        result = await service.prepare_regenerate_content(session, roadmap_id, concept_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # TODO: 实现完整的重新生成逻辑
    return {
        "success": True,
        "concept_id": concept_id,
        "message": "内容重新生成功能正在开发中",
    }


@tasks_router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    user_id: str = Query(..., description="用户ID"),
    force_checkpoint: bool = Query(False, description="强制使用 checkpoint 恢复"),
    session: AsyncSession = Depends(get_current_session),
    service: CurrentRetryService = None,
):
    """
    智能重试失败的任务（Celery 异步）
    
    两种重试策略：
    1. **Checkpoint 恢复**：从 LangGraph checkpoint 恢复
    2. **内容重试**：只重新生成失败的 Concept 内容
    
    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        force_checkpoint: 强制使用 checkpoint 恢复
        session: 数据库会话
        service: 重试服务
        
    Returns:
        重试任务的信息
        
    Raises:
        HTTPException: 404 - 任务不存在
        HTTPException: 400 - 无法重试
    """
    from app.tasks.workflow_resume_tasks import resume_from_checkpoint
    from app.tasks.content_generation_tasks import retry_failed_content_task
    
    logger.info(
        "retry_task_requested",
        task_id=task_id,
        user_id=user_id,
        force_checkpoint=force_checkpoint,
    )
    
    # 调用Service层判断重试策略
    try:
        retry_strategy = await service.prepare_retry_task(session, task_id, force_checkpoint)
    except ValueError as e:
        logger.warning("retry_task_preparation_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    
    # 策略 1：从 Checkpoint 恢复
    if retry_strategy["strategy"] == "checkpoint":
        logger.info(
            "using_checkpoint_recovery",
            task_id=task_id,
            checkpoint_step=retry_strategy.get("checkpoint_step"),
        )
        
        celery_task = resume_from_checkpoint.delay(task_id=task_id)
        
        logger.info(
            "checkpoint_recovery_dispatched",
            task_id=task_id,
            celery_task_id=celery_task.id,
        )
        
        task = retry_strategy["task"]
        return {
            "success": True,
            "recovery_type": "checkpoint",
            "task_id": task_id,
            "roadmap_id": task.roadmap_id,
            "checkpoint_step": retry_strategy.get("checkpoint_step"),
            "status": "recovering",
            "message": f"正在从 checkpoint 恢复（步骤：{retry_strategy.get('checkpoint_step')}）",
        }
    
    # 策略 2：内容重试
    else:
        task = retry_strategy["task"]
        failed_items = retry_strategy["failed_items"]
        
        # 筛选要重试的类型
        content_types = ["tutorial", "resources", "quiz"]
        items_to_retry = {}
        total_items = 0
        for content_type in content_types:
            if content_type in failed_items and failed_items[content_type]:
                items_to_retry[content_type] = failed_items[content_type]
                total_items += len(failed_items[content_type])
        
        if total_items == 0:
            raise HTTPException(
                status_code=400,
                detail="没有需要重试的失败项目，且 checkpoint 不可用"
            )
        
        logger.info(
            "using_content_retry",
            task_id=task_id,
            roadmap_id=task.roadmap_id,
            total_items=total_items,
        )
        
        # 分发 Celery 任务进行内容重试
        celery_task = retry_failed_content_task.delay(
            task_id=task_id,
            roadmap_id=task.roadmap_id,
            items_to_retry=items_to_retry,
            user_id=user_id,
        )
        
        logger.info(
            "content_retry_dispatched",
            task_id=task_id,
            celery_task_id=celery_task.id,
        )
        
        return {
            "success": True,
            "recovery_type": "content_retry",
            "task_id": task_id,
            "roadmap_id": task.roadmap_id,
            "items_to_retry": {
                content_type: len(items) for content_type, items in items_to_retry.items()
            },
            "total_items": total_items,
            "status": "retrying",
            "message": f"正在重试 {total_items} 个失败项目",
        }


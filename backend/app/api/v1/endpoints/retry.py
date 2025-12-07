"""
失败重试相关端点

包含以下功能：
- 重试失败的内容生成
- 重新生成特定概念的内容
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import structlog
import uuid

from app.models.domain import LearningPreferences
from app.db.session import get_db
from app.db.repositories.roadmap_repo import RoadmapRepository
from .utils import get_failed_content_items

router = APIRouter(prefix="/roadmaps", tags=["retry"])
logger = structlog.get_logger()


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
    user_id: str = Field(..., description="用户ID")
    preferences: LearningPreferences = Field(..., description="用户学习偏好")


@router.post("/{roadmap_id}/retry-failed")
async def retry_failed_content(
    roadmap_id: str,
    request: RetryFailedRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    断点续传：重新生成失败的内容
    
    精确到内容类型粒度，只重跑失败的部分：
    - content_status='failed' 的教程
    - resources_status='failed' 的资源推荐
    - quiz_status='failed' 的测验
    
    Args:
        roadmap_id: 路线图 ID
        request: 包含用户偏好和要重试的内容类型
        background_tasks: FastAPI后台任务
        db: 数据库会话
        
    Returns:
        task_id 用于 WebSocket 订阅进度
        
    Example:
        ```json
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "roadmap_id": "python-web-dev-2024",
            "status": "processing",
            "items_to_retry": {
                "tutorial": 3,
                "resources": 2,
                "quiz": 1
            },
            "total_items": 6,
            "message": "开始重试 6 个失败项目"
        }
        ```
    """
    logger.info(
        "retry_failed_content_requested",
        roadmap_id=roadmap_id,
        user_id=request.user_id,
        content_types=request.content_types,
    )
    
    repo = RoadmapRepository(db)
    
    # 1. 检查路线图是否存在
    roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
    if not roadmap_metadata:
        raise HTTPException(status_code=404, detail=f"路线图 {roadmap_id} 不存在")
    
    # 2. 获取失败的内容项目
    failed_items = get_failed_content_items(roadmap_metadata.framework_data)
    
    # 3. 根据请求筛选要重试的类型
    items_to_retry = {}
    total_items = 0
    for content_type in request.content_types:
        if content_type in failed_items and failed_items[content_type]:
            items_to_retry[content_type] = failed_items[content_type]
            total_items += len(failed_items[content_type])
    
    if total_items == 0:
        return {
            "status": "no_failed_items",
            "message": "没有需要重试的失败项目",
            "failed_counts": {
                "tutorial": len(failed_items["tutorial"]),
                "resources": len(failed_items["resources"]),
                "quiz": len(failed_items["quiz"]),
            }
        }
    
    # 4. 创建重试任务
    retry_task_id = str(uuid.uuid4())
    
    # 5. 启动后台重试任务（具体实现在roadmap_service中）
    from app.services.roadmap_service import execute_retry_failed_task
    background_tasks.add_task(
        execute_retry_failed_task,
        retry_task_id=retry_task_id,
        roadmap_id=roadmap_id,
        items_to_retry=items_to_retry,
        user_preferences=request.preferences,
    )
    
    return {
        "task_id": retry_task_id,
        "roadmap_id": roadmap_id,
        "status": "processing",
        "items_to_retry": {
            content_type: len(items) for content_type, items in items_to_retry.items()
        },
        "total_items": total_items,
        "message": f"开始重试 {total_items} 个失败项目",
    }


@router.post("/{roadmap_id}/concepts/{concept_id}/regenerate")
async def regenerate_concept_content(
    roadmap_id: str,
    concept_id: str,
    request: RegenerateContentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    重新生成指定概念的所有内容（教程+资源+测验）
    
    用于用户不满意当前内容，想要完全重新生成的场景
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 包含用户 ID 和学习偏好
        db: 数据库会话
        
    Returns:
        重新生成的结果
        
    Raises:
        HTTPException: 404 - 路线图或概念不存在
        
    Example:
        ```json
        {
            "success": true,
            "concept_id": "flask-basics",
            "regenerated": {
                "tutorial": true,
                "resources": true,
                "quiz": true
            },
            "message": "内容重新生成成功"
        }
        ```
    """
    logger.info(
        "regenerate_concept_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        user_id=request.user_id,
    )
    
    # 实现逻辑：调用service层进行重新生成
    # 这里是简化版本，完整实现在roadmap_service中
    repo = RoadmapRepository(db)
    roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
    
    if not roadmap_metadata:
        raise HTTPException(status_code=404, detail=f"路线图 {roadmap_id} 不存在")
    
    # TODO: 实现完整的重新生成逻辑
    # 当前返回占位响应
    return {
        "success": True,
        "concept_id": concept_id,
        "message": "内容重新生成功能正在开发中",
    }

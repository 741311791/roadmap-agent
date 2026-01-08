"""
路线图查询相关端点

重构说明：
- ✅ 使用CurrentSession（只读操作）
- ✅ 使用自定义异常替代HTTPException
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from typing import Annotated, Dict, Any
from fastapi import APIRouter, Depends
import structlog

from app.api.v1.deps import CurrentSession
from app.services.retrieval_service import RetrievalService, get_retrieval_service
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base

router = APIRouter(prefix="/roadmaps", tags=["retrieval"])
logger = structlog.get_logger()

# 依赖注入
CurrentRetrievalService = Annotated[RetrievalService, Depends(get_retrieval_service)]


@router.get("/{roadmap_id}", response_model=ResponseSchemaModel[Dict[str, Any]])
async def get_roadmap(
    roadmap_id: str,
    db: CurrentSession,  # ✅ 只读操作使用CurrentSession
    service: CurrentRetrievalService = None,
) -> ResponseSchemaModel[Dict[str, Any]]:
    """
    获取完整的路线图数据
    
    Args:
        roadmap_id: 路线图ID
        db: 数据库会话
        service: 检索服务
        
    Returns:
        - 如果路线图存在，返回完整的路线图框架数据
        - 如果路线图不存在但有活跃任务，返回生成中状态
        - 如果都不存在，返回 404
        
    Raises:
        NotFoundError: 路线图不存在
    """
    # 调用Service层获取路线图
    roadmap = await service.get_roadmap_with_status(db, roadmap_id)
    
    if not roadmap:
        # 检查是否有活跃任务正在生成这个路线图
        active_task = await service.get_active_task_by_roadmap(db, roadmap_id)
        
        if active_task:
            # 路线图正在生成中
            return response_base.success(data={
                "status": "processing",
                "task_id": active_task.task_id,
                "current_step": active_task.current_step,
                "message": "路线图正在生成中",
                "created_at": active_task.created_at.isoformat() if active_task.created_at else None,
                "updated_at": active_task.updated_at.isoformat() if active_task.updated_at else None,
            })
        
        # 路线图不存在且没有活跃任务
        raise errors.NotFoundError(msg="路线图不存在")
    
    return response_base.success(data=roadmap)

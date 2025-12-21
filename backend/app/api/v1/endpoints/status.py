"""
路线图状态查询 API 端点

提供路线图运行时状态的查询功能，用于前端轮询和状态监控。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.repositories.roadmap_repo import RoadmapRepository

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])


@router.get("/{roadmap_id}/active-task")
async def get_active_task(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取路线图当前的活跃任务
    
    用于前端轮询：查询该路线图是否有正在进行的任务
    - 如果有正在进行的任务，返回 task_id 和状态
    - 如果没有，返回 null
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话
        
    Returns:
        活跃任务信息或 null
        
    Example:
        ```json
        {
            "has_active_task": true,
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "processing",
            "current_step": "tutorial_generation",
            "task_type": "roadmap_creation",
            "concept_id": "concept-123",
            "content_type": "tutorial",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:01:00Z"
        }
        ```
    """
    repo = RoadmapRepository(db)
    
    # 直接通过 roadmap_id 查询活跃任务
    task = await repo.get_active_task_by_roadmap_id(roadmap_id)
    
    # 只有当任务状态为 processing 或 human_review_pending 时才算活跃
    if task and task.status in ['processing', 'human_review_pending']:
        return {
            "has_active_task": True,
            "task_id": task.task_id,
            "status": task.status,
            "current_step": task.current_step,
            "task_type": task.task_type,
            "concept_id": task.concept_id,
            "content_type": task.content_type,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }
    else:
        return {
            "has_active_task": False,
            "task_id": None,
            "status": None,
            "current_step": None,
        }


@router.get("/{roadmap_id}/active-retry-task")
async def get_active_retry_task(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取路线图当前正在进行的重试任务
    
    用于前端检测是否有正在进行的重试任务：
    - 用户切换 tab 返回时，检查是否有正在进行的重试任务
    - 如果有，前端可以用返回的 task_id 重新订阅 WebSocket
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话
        
    Returns:
        正在进行的重试任务信息，包含：
        - has_active_retry_task: 是否有正在进行的重试任务
        - task_id: 重试任务 ID（用于 WebSocket 订阅）
        - status: 任务状态
        - current_step: 当前执行步骤
        - items_to_retry: 正在重试的内容类型及数量
        - content_types: 正在重试的内容类型列表
        - created_at: 任务创建时间
        - updated_at: 任务更新时间
        
    Raises:
        HTTPException: 404 - 路线图不存在
        
    Example:
        ```json
        {
            "has_active_retry_task": true,
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "processing",
            "current_step": "tutorial_regeneration",
            "items_to_retry": {
                "concept-123": ["tutorial", "quiz"]
            },
            "content_types": ["tutorial", "quiz"],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:01:00Z"
        }
        ```
    """
    repo = RoadmapRepository(db)
    
    # 检查路线图是否存在
    metadata = await repo.get_roadmap_metadata(roadmap_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    
    # 获取正在进行的重试任务
    retry_task = await repo.get_active_retry_task_by_roadmap_id(roadmap_id)
    
    if retry_task:
        # 从 user_request 中提取重试信息
        user_request = retry_task.user_request or {}
        items_to_retry = user_request.get("items_to_retry", {})
        content_types = user_request.get("content_types", [])
        
        return {
            "has_active_retry_task": True,
            "task_id": retry_task.task_id,
            "status": retry_task.status,
            "current_step": retry_task.current_step,
            "items_to_retry": items_to_retry,
            "content_types": content_types,
            "created_at": retry_task.created_at.isoformat() if retry_task.created_at else None,
            "updated_at": retry_task.updated_at.isoformat() if retry_task.updated_at else None,
        }
    else:
        return {
            "has_active_retry_task": False,
            "task_id": None,
            "status": None,
            "current_step": None,
            "items_to_retry": None,
            "content_types": None,
        }


@router.get("/{roadmap_id}/status-check")
async def check_status_quick(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    快速检查路线图状态，用于检测僵尸状态
    
    检测逻辑：
    1. 获取路线图的所有活跃任务
    2. 如果有活跃任务，返回任务信息（正常状态）
    3. 如果没有活跃任务，检查概念状态是否为 pending/generating（僵尸状态）
    
    僵尸状态：任务不在运行，但概念状态仍为 pending/generating
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话
        
    Returns:
        {
            "roadmap_id": str,
            "has_active_task": bool,
            "active_tasks": [
                {
                    "task_id": str,
                    "task_type": "roadmap_creation" | "content_retry",
                    "status": "processing" | "human_review_pending",
                    "current_step": str,
                    "concept_id": str | None,
                    "content_type": "tutorial" | "resources" | "quiz" | None
                }
            ],
            "stale_concepts": [
                {
                    "concept_id": str,
                    "concept_name": str,
                    "content_type": "tutorial" | "resources" | "quiz",
                    "current_status": "pending" | "generating"
                }
            ]
        }
        
    Raises:
        HTTPException: 404 - 路线图不存在
        
    Example (Normal state):
        ```json
        {
            "roadmap_id": "roadmap-123",
            "has_active_task": true,
            "active_tasks": [
                {
                    "task_id": "task-456",
                    "task_type": "roadmap_creation",
                    "status": "processing",
                    "current_step": "tutorial_generation",
                    "concept_id": "concept-789",
                    "content_type": "tutorial"
                }
            ],
            "stale_concepts": []
        }
        ```
        
    Example (Stale state):
        ```json
        {
            "roadmap_id": "roadmap-123",
            "has_active_task": false,
            "active_tasks": [],
            "stale_concepts": [
                {
                    "concept_id": "concept-789",
                    "concept_name": "Introduction to Python",
                    "content_type": "tutorial",
                    "current_status": "generating"
                }
            ]
        }
        ```
    """
    repo = RoadmapRepository(db)
    
    # 获取路线图元数据
    metadata = await repo.get_roadmap_metadata(roadmap_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    
    # 获取所有活跃任务（包括创建任务和重试任务）
    active_tasks = await repo.get_active_tasks_by_roadmap_id(roadmap_id)
    has_active_task = len(active_tasks) > 0
    
    # 如果有活跃任务，说明正在正常生成，不是僵尸状态
    if has_active_task:
        return {
            "roadmap_id": roadmap_id,
            "has_active_task": True,
            "active_tasks": [
                {
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "status": task.status,
                    "current_step": task.current_step,
                    "concept_id": task.concept_id,
                    "content_type": task.content_type,
                }
                for task in active_tasks
            ],
            "stale_concepts": [],
        }
    
    # 检查是否有僵尸状态的概念
    framework_data = metadata.framework_data
    stale_concepts = []
    
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept in module.get("concepts", []):
                concept_id = concept.get("concept_id")
                concept_name = concept.get("name")
                
                # 检查三种内容类型的状态
                checks = [
                    ("tutorial", "content_status"),
                    ("resources", "resources_status"),
                    ("quiz", "quiz_status"),
                ]
                
                for content_type, status_key in checks:
                    status = concept.get(status_key)
                    
                    # pending 或 generating 但没有活跃任务 → 僵尸状态
                    if status in ["pending", "generating"]:
                        stale_concepts.append({
                            "concept_id": concept_id,
                            "concept_name": concept_name,
                            "content_type": content_type,
                            "current_status": status,
                        })
    
    return {
        "roadmap_id": roadmap_id,
        "has_active_task": False,
        "active_tasks": [],
        "stale_concepts": stale_concepts,
    }

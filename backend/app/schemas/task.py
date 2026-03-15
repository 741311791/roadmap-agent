"""
任务相关Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any


class TaskStatusDetailResponse(BaseModel):
    """任务状态详情（用于 Service 层返回）"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    current_step: Optional[str] = Field(None, description="当前步骤")
    roadmap_id: Optional[str] = Field(None, description="路线图ID")
    created_at: Optional[str] = Field(None, description="创建时间（ISO格式）")
    updated_at: Optional[str] = Field(None, description="更新时间（ISO格式）")
    error_message: Optional[str] = Field(None, description="错误信息")
    turbo_mode: Optional[bool] = Field(None, description="是否为极速模式（跳过结构验证）")
    user_request: Optional[Dict[str, Any]] = Field(None, description="任务发起时的原始 user_request")
    queue_ahead_count: Optional[int] = Field(None, description="前方排队任务数")
    queue_position: Optional[int] = Field(None, description="当前任务在队列中的位置（从1开始）")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "current_step": "curriculum_design",
                "roadmap_id": "python-web-xxx",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:01:00Z",
                "error_message": None,
                "queue_ahead_count": 3,
                "queue_position": 4,
            }
        }
    )


class TaskItemResponse(BaseModel):
    """任务列表项"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    current_step: Optional[str] = Field(None, description="当前步骤")
    title: Optional[str] = Field(None, description="路线图标题")
    created_at: str = Field(..., description="创建时间（ISO格式）")
    updated_at: str = Field(..., description="更新时间（ISO格式）")
    completed_at: Optional[str] = Field(None, description="完成时间（ISO格式）")
    error_message: Optional[str] = Field(None, description="错误信息")
    roadmap_id: Optional[str] = Field(None, description="路线图ID")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "human_review_pending",
                "current_step": "human_review",
                "title": "Python Web Development",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:01:00Z",
                "completed_at": None,
                "error_message": None,
                "roadmap_id": "python-guide-xxx"
            }
        }
    )


class TaskListResponse(BaseModel):
    """任务列表响应（包含统计信息）"""
    tasks: List[TaskItemResponse] = Field(..., description="任务列表")
    total: int = Field(..., description="总任务数")
    pending_count: int = Field(0, description="待处理任务数")
    processing_count: int = Field(0, description="处理中任务数")
    completed_count: int = Field(0, description="已完成任务数")
    failed_count: int = Field(0, description="失败任务数")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tasks": [
                    {
                        "task_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "human_review_pending",
                        "current_step": "human_review",
                        "title": "Python Web Development",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:01:00Z",
                        "completed_at": None,
                        "error_message": None,
                        "roadmap_id": "python-guide-xxx"
                    }
                ],
                "total": 1,
                "pending_count": 0,
                "processing_count": 1,
                "completed_count": 5,
                "failed_count": 0
            }
        }
    )


class ContentGenerationStatusResponse(BaseModel):
    """内容生成状态响应"""
    task_id: str = Field(..., description="任务ID")
    celery_task_id: Optional[str] = Field(None, description="Celery任务ID")
    status: str = Field(..., description="Celery任务状态")
    progress: Optional[dict] = Field(None, description="进度信息")
    message: Optional[str] = Field(None, description="状态消息")
    result: Optional[dict] = Field(None, description="任务结果")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "celery_task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "status": "PROGRESS",
                "progress": {
                    "current": 15,
                    "total": 30,
                    "percentage": 50.0
                },
                "message": "正在生成教程内容",
                "result": None
            }
        }
    )


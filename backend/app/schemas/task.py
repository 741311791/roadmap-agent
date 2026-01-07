"""
任务相关Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class TaskStatusDetailResponse(BaseModel):
    """任务状态详情（用于 Service 层返回）"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    current_step: Optional[str] = Field(None, description="当前步骤")
    roadmap_id: Optional[str] = Field(None, description="路线图ID")
    created_at: Optional[str] = Field(None, description="创建时间（ISO格式）")
    updated_at: Optional[str] = Field(None, description="更新时间（ISO格式）")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "current_step": "curriculum_design",
                "roadmap_id": "python-web-xxx",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:01:00Z",
                "error_message": None
            }
        }
    )


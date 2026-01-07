"""
封面图相关Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal


class CoverImageStatusResponse(BaseModel):
    """封面图状态响应"""
    status: Literal["not_started", "processing", "completed", "failed"] = Field(
        ..., 
        description="封面图生成状态"
    )
    url: Optional[str] = Field(None, description="封面图URL")
    error: Optional[str] = Field(None, description="错误信息")
    retry_count: Optional[int] = Field(0, description="重试次数")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "completed",
                "url": "https://cdn.example.com/cover.jpg",
                "error": None,
                "retry_count": 0
            }
        }
    )


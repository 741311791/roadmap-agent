"""
内容重试相关Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal, Any


class ContentRetryResult(BaseModel):
    """内容重试结果"""
    success: bool = Field(..., description="是否成功")
    content_type: str = Field(..., description="内容类型")
    concept_id: str = Field(..., description="概念ID")
    result: Optional[Any] = Field(None, description="生成结果")
    error: Optional[str] = Field(None, description="错误信息")
    skipped: Optional[bool] = Field(False, description="是否跳过（已存在）")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "content_type": "tutorial",
                "concept_id": "concept-123",
                "result": {"tutorial_id": "tut-456"},
                "error": None,
                "skipped": False
            }
        }
    )


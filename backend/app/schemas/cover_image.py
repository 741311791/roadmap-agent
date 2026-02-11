"""
封面图相关Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List


class CoverImageStatusResponse(BaseModel):
    """封面图状态响应"""
    status: str = Field(..., description="封面图生成状态: not_started/pending/generating/success/failed")
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


class CoverImageResponse(BaseModel):
    """
    封面图响应模型
    
    用于单个路线图封面图查询。
    """
    roadmap_id: str = Field(..., description="路线图 ID")
    cover_image_url: Optional[str] = Field(None, description="封面图 URL")
    status: str = Field(..., description="状态: not_started/pending/generating/success/failed")
    error: Optional[str] = Field(None, description="错误信息")
    retry_count: Optional[int] = Field(None, description="重试次数")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "roadmap_id": "roadmap-123",
                "cover_image_url": "https://cdn.example.com/cover.jpg",
                "status": "success",
                "error": None,
                "retry_count": 0
            }
        }
    )


class GenerateCoverImageRequest(BaseModel):
    """
    生成封面图请求模型
    
    用于触发封面图生成。
    """
    roadmap_id: str = Field(..., description="路线图 ID")
    prompt: Optional[str] = Field(None, description="可选的图片生成提示词")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "roadmap_id": "roadmap-123",
                "prompt": "Modern learning roadmap cover"
            }
        }
    )


class BatchGenerateRequest(BaseModel):
    """
    批量生成封面图请求模型
    
    用于批量触发多个路线图的封面图生成。
    """
    roadmap_ids: List[str] = Field(..., description="路线图 ID 列表")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "roadmap_ids": ["roadmap-123", "roadmap-456", "roadmap-789"]
            }
        }
    )


class BatchGetCoverImagesRequest(BaseModel):
    """
    批量获取封面图请求模型
    
    用于批量查询多个路线图的封面图状态。
    """
    roadmap_ids: List[str] = Field(..., description="路线图 ID 列表")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "roadmap_ids": ["roadmap-123", "roadmap-456"]
            }
        }
    )


class BatchCoverImageResponse(BaseModel):
    """
    批量封面图响应模型
    
    用于批量查询结果。
    """
    roadmap_id: str = Field(..., description="路线图 ID")
    cover_image_url: Optional[str] = Field(None, description="封面图 URL")
    status: str = Field(..., description="状态: not_started/pending/generating/success/failed")
    error: Optional[str] = Field(None, description="错误信息")
    retry_count: Optional[int] = Field(None, description="重试次数")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "roadmap_id": "roadmap-123",
                "cover_image_url": "https://cdn.example.com/cover.jpg",
                "status": "success",
                "error": None,
                "retry_count": 0
            }
        }
    )


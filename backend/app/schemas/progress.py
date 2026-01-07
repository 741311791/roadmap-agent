"""
进度相关Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

# ===== 请求模型 =====

class ProgressCreate(BaseModel):
    """进度创建Schema"""
    user_id: str = Field(..., description="用户ID")
    concept_id: str = Field(..., description="概念ID")
    status: str = Field(..., description="状态: not_started/in_progress/completed")

class ProgressUpdate(BaseModel):
    """进度更新Schema"""
    status: Optional[str] = Field(None, description="状态")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

# ===== 响应模型 =====

class ProgressDetail(BaseModel):
    """进度详情"""
    id: int
    user_id: str
    concept_id: str
    status: str
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class RoadmapProgressSummary(BaseModel):
    """路线图进度摘要"""
    roadmap_id: str = Field(..., description="路线图ID")
    total_concepts: int = Field(..., description="总概念数")
    completed_concepts: int = Field(..., description="已完成概念数")
    in_progress_concepts: int = Field(..., description="进行中概念数")
    progress_percentage: int = Field(..., ge=0, le=100, description="完成百分比")
    last_accessed_at: Optional[datetime] = Field(None, description="最后访问时间")


"""
概念相关Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

# ===== 请求模型 =====

class ConceptCreate(BaseModel):
    """概念创建Schema"""
    concept_id: str = Field(..., description="概念ID")
    roadmap_id: str = Field(..., description="所属路线图ID")
    title: str = Field(..., description="概念标题")
    description: Optional[str] = Field(None, description="概念描述")
    order_index: int = Field(..., description="排序索引")

class ConceptUpdate(BaseModel):
    """概念更新Schema"""
    title: Optional[str] = Field(None, description="概念标题")
    description: Optional[str] = Field(None, description="概念描述")
    order_index: Optional[int] = Field(None, description="排序索引")

# ===== 响应模型 =====

class ConceptDetail(BaseModel):
    """概念详情"""
    concept_id: str
    roadmap_id: str
    title: str
    description: Optional[str] = None
    order_index: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ConceptSummary(BaseModel):
    """概念摘要"""
    concept_id: str = Field(..., description="概念ID")
    title: str = Field(..., description="标题")
    description: Optional[str] = Field(None, description="描述")
    order_index: int = Field(..., description="排序索引")
    is_completed: bool = Field(default=False, description="是否已完成")
    
    model_config = ConfigDict(from_attributes=True)


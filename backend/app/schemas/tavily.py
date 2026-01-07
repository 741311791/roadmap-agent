"""
Tavily API Key 分配相关Schemas
"""
from pydantic import BaseModel, Field, ConfigDict


class TavilyAllocationStats(BaseModel):
    """Tavily Key 分配统计"""
    total_concepts: int = Field(..., description="总概念数")
    concepts_with_keys: int = Field(..., description="分配到 Key 的概念数")
    concepts_without_keys: int = Field(..., description="未分配 Key 的概念数")
    unique_keys_used: int = Field(..., description="使用的唯一 Key 数量")
    allocation_rate: str = Field(..., description="分配率（百分比）")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_concepts": 10,
                "concepts_with_keys": 8,
                "concepts_without_keys": 2,
                "unique_keys_used": 2,
                "allocation_rate": "80.0%"
            }
        }
    )


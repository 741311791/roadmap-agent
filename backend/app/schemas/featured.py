"""
精选路线图 API Schema

包含精选路线图列表的响应模型
"""
from pydantic import BaseModel
from typing import List, Optional


# ============================================================
# 精选路线图相关
# ============================================================

class StageSummary(BaseModel):
    """阶段摘要信息"""
    name: str
    description: Optional[str] = None
    order: int


class FeaturedRoadmapItem(BaseModel):
    """精选路线图条目"""
    roadmap_id: str
    title: str
    created_at: str
    total_concepts: int
    completed_concepts: int = 0
    topic: Optional[str] = None
    status: str = "completed"
    stages: Optional[List[StageSummary]] = None


class FeaturedRoadmapsResponse(BaseModel):
    """精选路线图列表响应"""
    roadmaps: List[FeaturedRoadmapItem]
    total: int
    featured_user_id: str
    featured_user_email: str


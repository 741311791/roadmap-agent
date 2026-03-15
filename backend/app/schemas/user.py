"""
用户相关Schemas

包含用户认证、画像、路线图历史、任务列表等
"""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime


# ============================================================
# 用户认证相关（原有）
# ============================================================

class UserCreate(BaseModel):
    """用户创建Schema"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=8, description="密码")
    full_name: Optional[str] = Field(None, description="全名")


class UserUpdate(BaseModel):
    """用户更新Schema"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    full_name: Optional[str] = Field(None, description="全名")
    avatar_url: Optional[str] = Field(None, description="头像URL")


class UserLogin(BaseModel):
    """用户登录Schema"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserLoginResponse(BaseModel):
    """用户登录响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    user: UserResponse = Field(..., description="用户信息")


class UserProfile(BaseModel):
    """用户资料"""
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    total_roadmaps: int = Field(default=0, description="路线图总数")
    completed_concepts: int = Field(default=0, description="已完成概念数")
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# 用户画像相关（新增）
# ============================================================

class TechStackItem(BaseModel):
    """技术栈项"""
    technology: str = Field(..., description="技术名称")
    proficiency: str = Field(..., description="熟练程度: beginner, intermediate, expert")
    capability_analysis: Optional[dict] = Field(None, description="能力分析结果（可选）")


class UserProfileRequest(BaseModel):
    """用户画像请求体"""
    # 职业背景
    industry: Optional[str] = Field(None, description="所属行业")
    current_role: Optional[str] = Field(None, description="当前职位")
    # 技术栈
    tech_stack: List[TechStackItem] = Field(default=[], description="技术栈列表")
    # 语言偏好
    primary_language: str = Field(default="zh", description="主要语言")
    secondary_language: Optional[str] = Field(None, description="次要语言")
    # 学习习惯
    weekly_commitment_hours: int = Field(default=10, ge=1, le=168, description="每周学习时间")
    learning_style: List[str] = Field(default=[], description="学习风格: visual, text, audio, hands_on")
    # AI 个性化
    ai_personalization: bool = Field(default=True, description="是否启用 AI 个性化")


class UserProfileResponse(BaseModel):
    """用户画像响应体"""
    user_id: str
    industry: Optional[str] = None
    current_role: Optional[str] = None
    tech_stack: List[dict] = []
    primary_language: str = "zh"
    secondary_language: Optional[str] = None
    weekly_commitment_hours: int = 10
    learning_style: List[str] = []
    ai_personalization: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ============================================================
# 路线图历史相关（新增）
# ============================================================

class StageSummary(BaseModel):
    """Stage 摘要信息，用于卡片展示"""
    name: str
    description: Optional[str] = None
    order: int


class RoadmapHistoryItem(BaseModel):
    """路线图历史项"""
    roadmap_id: str
    title: str
    created_at: str
    cover_image_url: Optional[str] = None
    total_concepts: int
    completed_concepts: int
    topic: Optional[str] = None
    status: Optional[str] = None
    # Stages 摘要信息
    stages: Optional[List[StageSummary]] = None
    # 新增字段：用于支持未完成路线图的恢复
    task_id: Optional[str] = None
    task_status: Optional[str] = None  # processing, pending, human_review_pending 等
    current_step: Optional[str] = None  # intent_analysis, curriculum_design 等
    # 软删除相关字段
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None


class RoadmapHistoryResponse(BaseModel):
    """用户路线图历史响应"""
    roadmaps: List[RoadmapHistoryItem]
    total: int
    # 新增字段：进行中的任务数量
    in_progress_count: int = 0


# ============================================================
# 任务列表相关（新增）
# ============================================================

class TaskListItem(BaseModel):
    """任务列表项"""
    task_id: str
    status: str  # pending, processing, completed, failed
    current_step: str
    title: str  # 从 user_request 提取
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    roadmap_id: Optional[str] = None  # 如果任务成功，关联的路线图ID
    queue_ahead_count: Optional[int] = None
    queue_position: Optional[int] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskListItem]
    total: int
    pending_count: int
    processing_count: int
    completed_count: int
    failed_count: int


# ============================================================
# 已删除路线图相关（新增）
# ============================================================

class DeletedRoadmapsResponse(BaseModel):
    """已删除路线图响应（回收站）"""
    roadmaps: List[RoadmapHistoryItem]
    total: int
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "roadmaps": [
                    {
                        "roadmap_id": "python-web-xxx",
                        "title": "Python Web Development",
                        "created_at": "2024-01-01T00:00:00Z",
                        "deleted_at": "2024-01-15T00:00:00Z",
                        "total_concepts": 20,
                        "completed_concepts": 5,
                        "topic": "python web development",
                        "status": "deleted"
                    }
                ],
                "total": 1
            }
        }
    )


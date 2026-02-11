"""
路线图相关Schemas
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Literal
from datetime import datetime

from app.models.domain import LearningPreferences

# ===== 请求模型 =====

class RoadmapGenerateRequest(BaseModel):
    """路线图生成请求"""
    user_id: str = Field(..., description="用户ID")
    preferences: LearningPreferences = Field(..., description="学习偏好")
    
    model_config = {"json_schema_extra": {
        "example": {
            "user_id": "user-123",
            "preferences": {
                "learning_goal": "成为全栈开发工程师",
                "current_level": "beginner",
                "time_commitment": "10小时/周",
            }
        }
    }}

class RoadmapUpdateRequest(BaseModel):
    """路线图更新请求"""
    title: Optional[str] = Field(None, description="路线图标题")
    description: Optional[str] = Field(None, description="路线图描述")
    is_public: Optional[bool] = Field(None, description="是否公开")

class RoadmapCreate(BaseModel):
    """路线图创建Schema"""
    roadmap_id: str = Field(..., description="路线图ID")
    user_id: str = Field(..., description="用户ID")
    title: Optional[str] = Field(None, description="标题")
    description: Optional[str] = Field(None, description="描述")
    cover_image_url: Optional[str] = Field(None, description="封面图URL")
    framework_data: dict = Field(default_factory=dict, description="路线图框架数据")

class RoadmapUpdate(BaseModel):
    """路线图更新Schema"""
    title: Optional[str] = Field(None, description="标题")
    description: Optional[str] = Field(None, description="描述")
    cover_image_url: Optional[str] = Field(None, description="封面图URL")
    framework_data: Optional[dict] = Field(None, description="路线图框架数据")
    is_public: Optional[bool] = Field(None, description="是否公开")

# ===== 内容重试请求（通用基类）=====

class ConceptRetryRequest(BaseModel):
    """概念内容重试请求（通用基类）"""
    preferences: LearningPreferences = Field(..., description="用户偏好")
    retry_reason: Optional[str] = Field(None, description="重试原因")
    force_regenerate: bool = Field(False, description="是否强制重新生成")

class TutorialRetryRequest(ConceptRetryRequest):
    """教程重试请求"""
    include_code_examples: bool = Field(True, description="是否包含代码示例")

class ResourceRetryRequest(ConceptRetryRequest):
    """资源推荐重试请求"""
    max_resources: int = Field(5, ge=1, le=10, description="最大资源数量")

class QuizRetryRequest(ConceptRetryRequest):
    """测验重试请求"""
    question_count: int = Field(5, ge=3, le=10, description="问题数量")

# ===== 响应模型 =====

class RoadmapGenerateResponse(BaseModel):
    """路线图生成响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="提示消息")
    estimated_time: Optional[int] = Field(None, description="预计完成时间（秒）")

class ConceptRetryResponse(BaseModel):
    """概念内容重试响应（通用）"""
    success: bool = Field(..., description="是否成功")
    concept_id: str = Field(..., description="概念ID")
    content_type: Literal["tutorial", "resources", "quiz"] = Field(..., description="内容类型")
    message: str = Field(..., description="提示消息")
    task_id: Optional[str] = Field(None, description="异步任务ID（如果是异步）")
    data: Optional[dict] = Field(None, description="生成结果（同步时返回）")

# ===== 任务状态查询 =====

class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str = Field(..., description="任务ID")
    status: Literal["pending", "processing", "completed", "failed", "cancelled"] = Field(..., description="任务状态")
    progress: Optional[int] = Field(None, ge=0, le=100, description="进度百分比")
    message: Optional[str] = Field(None, description="状态消息")
    result: Optional[dict] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


# ===== 流式生成相关 =====

class ChatModificationRequest(BaseModel):
    """
    聊天修改请求
    
    用于流式修改路线图的聊天式交互。
    """
    user_message: str = Field(..., description="用户的自然语言修改意见")
    context: Optional[dict] = Field(None, description="当前上下文（如正在查看的 concept_id）")
    user_id: str = Field(..., description="用户 ID")
    preferences: LearningPreferences = Field(..., description="用户学习偏好")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "user_message": "请增加更多关于 Python 面向对象编程的内容",
                "context": {"concept_id": "concept-123"},
                "user_id": "user-456",
                "preferences": {
                    "learning_goal": "Learn Python",
                    "current_level": "intermediate",
                }
            }
        }
    }

class RoadmapSummary(BaseModel):
    """路线图摘要（列表展示）"""
    roadmap_id: str = Field(..., description="路线图ID")
    title: str = Field(..., description="标题")
    description: Optional[str] = Field(None, description="描述")
    cover_image_url: Optional[str] = Field(None, description="封面图URL")
    progress: int = Field(..., ge=0, le=100, description="学习进度")
    total_concepts: int = Field(..., ge=0, description="总概念数")
    completed_concepts: int = Field(..., ge=0, description="已完成概念数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    model_config = ConfigDict(from_attributes=True)

class RoadmapDetail(BaseModel):
    """路线图详情（包含完整框架）"""
    roadmap_id: str
    title: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    framework_data: dict = Field(..., description="路线图框架数据")
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ===== 列表响应 =====

class RoadmapListResponse(BaseModel):
    """路线图列表响应"""
    roadmaps: list[RoadmapSummary]
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")


# ===== 路线图详情和操作响应 =====

class RoadmapDetailResponse(BaseModel):
    """路线图详情响应"""
    roadmap_id: str = Field(..., description="路线图ID")
    user_id: str = Field(..., description="用户ID")
    learning_goal: str = Field(..., description="学习目标")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    
    # ✅ framework 改为可选，生成中时为 None
    framework: Optional[dict] = Field(None, description="路线图框架数据（生成中时为None）")
    
    status: str = Field(..., description="路线图状态")
    title: Optional[str] = Field(None, description="标题")
    description: Optional[str] = Field(None, description="描述")
    
    # ✅ 新增任务相关字段（用于生成中状态）
    task_id: Optional[str] = Field(None, description="任务ID（生成中时有值）")
    current_step: Optional[str] = Field(None, description="当前步骤（生成中时有值）")
    message: Optional[str] = Field(None, description="状态消息（生成中时有值）")


class RoadmapDeleteResponse(BaseModel):
    """删除路线图响应（软删除）"""
    message: str = Field(..., description="操作结果消息")
    roadmap_id: str = Field(..., description="路线图ID")


class RoadmapRestoreResponse(BaseModel):
    """恢复路线图响应"""
    message: str = Field(..., description="操作结果消息")
    roadmap_id: str = Field(..., description="路线图ID")


class RoadmapPermanentDeleteResponse(BaseModel):
    """永久删除路线图响应"""
    message: str = Field(..., description="操作结果消息")
    roadmap_id: str = Field(..., description="路线图ID")


class RoadmapStatusResponse(BaseModel):
    """路线图状态响应"""
    roadmap_id: str = Field(..., description="路线图ID")
    status: str = Field(..., description="路线图状态")
    task_id: Optional[str] = Field(None, description="关联任务ID")


class RoadmapStatusQuickResponse(BaseModel):
    """快速检查路线图状态响应"""
    roadmap_id: str = Field(..., description="路线图ID")
    status: str = Field(..., description="路线图状态")
    has_active_task: bool = Field(..., description="是否有活跃任务")
    active_task_id: Optional[str] = Field(None, description="活跃任务ID")
    zombie_concepts: Optional[list[str]] = Field(None, description="僵尸概念ID列表")
    zombie_count: int = Field(0, description="僵尸概念数量")


"""
用户反馈相关 Schema。
"""
from enum import Enum

from pydantic import BaseModel, Field


class FeedbackCategory(str, Enum):
    """反馈分类枚举。"""

    BUG = "bug"
    IMPROVEMENT = "improvement"
    QUESTION = "question"
    NEW_FEATURE = "new_feature"


class FeedbackContextType(str, Enum):
    """反馈触发场景枚举。"""

    MANUAL = "manual"
    GENERATION_COMPLETED = "generation_completed"
    CONCEPT_COMPLETED = "concept_completed"


class UserFeedbackCreatePayload(BaseModel):
    """
    用户反馈创建载荷。

    Args:
        rating: 用户评分，范围 1-5。
        category: 反馈分类。
        summary: 反馈标题摘要。
        details: 反馈详细描述或复现步骤。
        page_url: 提交反馈时所在页面 URL。
        context_type: 反馈触发场景。
        roadmap_id: 关联的路线图 ID。
        concept_id: 关联的 Concept ID。
        task_id: 关联的任务 ID。

    Returns:
        None

    Raises:
        ValueError: 当字段不满足校验约束时抛出。
    """

    rating: int = Field(..., ge=1, le=5, description="用户评分")
    category: FeedbackCategory = Field(..., description="反馈分类")
    summary: str = Field(..., min_length=1, max_length=200, description="反馈标题")
    details: str = Field(..., min_length=2, max_length=5000, description="详细反馈或复现步骤")
    page_url: str = Field(..., min_length=1, max_length=2000, description="页面 URL")
    context_type: FeedbackContextType = Field(..., description="触发场景")
    roadmap_id: str | None = Field(default=None, max_length=255, description="路线图 ID")
    concept_id: str | None = Field(default=None, max_length=255, description="Concept ID")
    task_id: str | None = Field(default=None, max_length=255, description="任务 ID")


class UserFeedbackSubmitResponse(BaseModel):
    """
    用户反馈提交结果。

    Args:
        feedback_id: 本地反馈记录 ID。
        linear_issue_id: Linear Issue UUID。
        linear_issue_identifier: Linear Issue 短标识。
        linear_issue_url: Linear Issue 链接。

    Returns:
        None

    Raises:
        ValueError: 当字段不满足校验约束时抛出。
    """

    feedback_id: str = Field(..., description="本地反馈记录 ID")
    linear_issue_id: str = Field(..., description="Linear Issue ID")
    linear_issue_identifier: str = Field(..., description="Linear Issue 标识")
    linear_issue_url: str | None = Field(default=None, description="Linear Issue 链接")

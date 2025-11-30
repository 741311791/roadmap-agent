"""
数据库模型（SQLModel）

时间处理说明：
- 所有时间字段统一使用北京时间 (UTC+8)
- 使用 TIMESTAMP WITHOUT TIME ZONE 存储，避免 PostgreSQL 自动转换为 UTC
- beijing_now() 返回无时区信息的北京时间
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import Text, DateTime
import uuid

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now() -> datetime:
    """
    获取当前北京时间（无时区信息）
    
    返回的 datetime 对象不包含时区信息，但值是北京时间。
    这样存入 PostgreSQL 的 TIMESTAMP WITHOUT TIME ZONE 时不会被转换。
    """
    # 获取 UTC 时间，加上 8 小时，然后移除时区信息
    utc_now = datetime.now(timezone.utc)
    beijing_time = utc_now + timedelta(hours=8)
    return beijing_time.replace(tzinfo=None)


class User(SQLModel, table=True):
    """用户表"""
    __tablename__ = "users"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    email: str = Field(unique=True, index=True)
    username: str
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))  # 无时区，直接存储北京时间
    )


class RoadmapTask(SQLModel, table=True):
    """路线图生成任务表"""
    __tablename__ = "roadmap_tasks"
    
    task_id: str = Field(primary_key=True)
    # 移除外键约束，user_id 可能来自外部身份验证服务
    user_id: str = Field(index=True)
    
    # 状态跟踪
    status: str = Field(default="pending")  # pending, processing, completed, failed
    current_step: str = Field(default="init")
    
    # 输入/输出
    user_request: dict = Field(sa_column=Column(JSON))
    roadmap_id: Optional[str] = Field(default=None)
    
    # 元数据（所有时间字段使用北京时间）
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))  # 无时区，直接存储北京时间
    )
    updated_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))  # 无时区，直接存储北京时间
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True)  # 无时区，直接存储北京时间
    )
    
    # 错误信息
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))


class RoadmapMetadata(SQLModel, table=True):
    """路线图元数据表（存储轻量级框架，不包含详细内容）"""
    __tablename__ = "roadmap_metadata"
    
    roadmap_id: str = Field(primary_key=True)
    # 移除外键约束，user_id 可能来自外部身份验证服务
    user_id: str = Field(index=True)
    task_id: str = Field(index=True)
    
    title: str
    total_estimated_hours: float
    recommended_completion_weeks: int
    
    # 完整框架数据（JSON 格式）
    framework_data: dict = Field(sa_column=Column(JSON))
    
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))  # 无时区，直接存储北京时间
    )


class TutorialMetadata(SQLModel, table=True):
    """
    教程元数据表（仅存储引用和摘要）
    
    版本管理说明：
    - content_version: 版本号，从 1 开始递增
    - is_latest: 标记是否为当前最新版本
    - 重新生成教程时，旧版本的 is_latest 设为 False，新版本设为 True
    - tutorial_id 格式：UUID（确保全局唯一，避免跨 roadmap 冲突）
    """
    __tablename__ = "tutorial_metadata"
    
    tutorial_id: str = Field(primary_key=True)  # UUID 格式，确保全局唯一
    concept_id: str = Field(index=True)
    roadmap_id: str = Field(foreign_key="roadmap_metadata.roadmap_id", index=True)
    
    title: str
    summary: str = Field(sa_column=Column(Text))
    
    # S3 存储引用（包含版本号）
    # 格式：{roadmap_id}/concepts/{concept_id}/v{version}.md
    content_url: str
    content_status: str = Field(default="pending")  # pending, completed, failed
    
    # 版本管理
    content_version: int = Field(default=1, description="内容版本号，从 1 开始")
    is_latest: bool = Field(default=True, index=True, description="是否为最新版本")
    
    estimated_completion_time: int  # 分钟
    generated_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))  # 无时区，直接存储北京时间
    )


class IntentAnalysisMetadata(SQLModel, table=True):
    """需求分析结果元数据表（A1: 需求分析师产出）"""
    __tablename__ = "intent_analysis_metadata"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    task_id: str = Field(foreign_key="roadmap_tasks.task_id", index=True)
    
    # 分析结果
    parsed_goal: str = Field(sa_column=Column(Text))
    key_technologies: list = Field(sa_column=Column(JSON))  # List[str]
    difficulty_profile: str = Field(sa_column=Column(Text))
    time_constraint: str = Field(sa_column=Column(Text))
    recommended_focus: list = Field(sa_column=Column(JSON))  # List[str]
    
    # 完整分析数据（JSON 格式，用于恢复）
    full_analysis_data: dict = Field(sa_column=Column(JSON))
    
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))
    )


class ResourceRecommendationMetadata(SQLModel, table=True):
    """资源推荐元数据表（A5: 资源推荐师产出）"""
    __tablename__ = "resource_recommendation_metadata"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    concept_id: str = Field(index=True)
    roadmap_id: str = Field(foreign_key="roadmap_metadata.roadmap_id", index=True)
    
    # 推荐资源列表（JSON 格式）
    resources: list = Field(sa_column=Column(JSON))  # List[Resource]
    resources_count: int = Field(default=0)
    
    # 搜索查询记录
    search_queries_used: list = Field(sa_column=Column(JSON))  # List[str]
    
    generated_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))
    )


class QuizMetadata(SQLModel, table=True):
    """测验元数据表（A6: 测验生成器产出）"""
    __tablename__ = "quiz_metadata"
    
    quiz_id: str = Field(primary_key=True)  # UUID 格式，确保全局唯一
    concept_id: str = Field(index=True)
    roadmap_id: str = Field(foreign_key="roadmap_metadata.roadmap_id", index=True)
    
    # 测验题目（JSON 格式）
    questions: list = Field(sa_column=Column(JSON))  # List[QuizQuestion]
    total_questions: int = Field(default=0)
    
    # 难度分布统计
    easy_count: int = Field(default=0)
    medium_count: int = Field(default=0)
    hard_count: int = Field(default=0)
    
    generated_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))
    )


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
    
    # 失败概念列表（JSON 格式，包含 concept_id, reason, timestamp）
    failed_concepts: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="失败概念的详细信息：{concept_id: {reason, content_type, timestamp}}"
    )
    
    # 执行摘要（JSON 格式，包含总数、成功数、失败数等）
    execution_summary: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="执行摘要：{total, completed, failed, skipped, duration_seconds}"
    )


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
    """需求分析结果元数据表（A1: 需求分析师产出，增强版）"""
    __tablename__ = "intent_analysis_metadata"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    task_id: str = Field(foreign_key="roadmap_tasks.task_id", index=True)
    
    # 路线图ID（在需求分析完成后生成）
    roadmap_id: Optional[str] = Field(default=None, index=True, description="路线图唯一标识")
    
    # 原有分析结果字段
    parsed_goal: str = Field(sa_column=Column(Text))
    key_technologies: list = Field(sa_column=Column(JSON))  # List[str]
    difficulty_profile: str = Field(sa_column=Column(Text))
    time_constraint: str = Field(sa_column=Column(Text))
    recommended_focus: list = Field(sa_column=Column(JSON))  # List[str]
    
    # 新增分析维度字段
    user_profile_summary: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    skill_gap_analysis: list = Field(default=[], sa_column=Column(JSON))  # List[str]
    personalized_suggestions: list = Field(default=[], sa_column=Column(JSON))  # List[str]
    estimated_learning_path_type: Optional[str] = Field(default=None)  # quick_start, deep_dive, career_transition, skill_upgrade
    content_format_weights: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))  # {visual, text, audio, hands_on}
    
    # 语言偏好（新增）
    language_preferences: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))  # LanguagePreferences
    
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


class UserProfile(SQLModel, table=True):
    """
    用户画像表
    
    存储用户的个人偏好设置，用于个性化路线图生成。
    """
    __tablename__ = "user_profiles"
    
    user_id: str = Field(primary_key=True)
    
    # 职业背景
    industry: Optional[str] = Field(default=None, description="所属行业")
    current_role: Optional[str] = Field(default=None, description="当前职位")
    
    # 技术栈 (JSON: [{technology: str, proficiency: str}])
    tech_stack: list = Field(default=[], sa_column=Column(JSON))
    
    # 语言偏好
    primary_language: str = Field(default="zh", description="主要语言")
    secondary_language: Optional[str] = Field(default=None, description="次要语言")
    
    # 学习习惯
    weekly_commitment_hours: int = Field(default=10, description="每周学习时间（小时）")
    # 学习风格 (JSON: ['visual', 'text', 'audio', 'hands_on'])
    learning_style: list = Field(default=[], sa_column=Column(JSON))
    
    # AI 个性化开关
    ai_personalization: bool = Field(default=True, description="是否启用 AI 个性化")
    
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))
    )
    updated_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))
    )


class ExecutionLog(SQLModel, table=True):
    """
    执行日志表
    
    记录工作流执行过程中的关键事件，用于：
    - 通过 trace_id 追踪请求完整生命周期
    - 聚合错误报告
    - 性能分析和问题定位
    
    日志级别：
    - debug: 调试信息（开发环境）
    - info: 正常执行信息
    - warning: 警告（可恢复的问题）
    - error: 错误（导致失败的问题）
    """
    __tablename__ = "execution_logs"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    
    # 关联字段
    trace_id: str = Field(index=True, description="追踪 ID，对应 task_id")
    roadmap_id: Optional[str] = Field(default=None, index=True, description="路线图 ID")
    concept_id: Optional[str] = Field(default=None, index=True, description="概念 ID")
    
    # 日志分类
    level: str = Field(default="info", index=True, description="日志级别: debug, info, warning, error")
    category: str = Field(index=True, description="日志分类: workflow, agent, tool, database")
    step: Optional[str] = Field(default=None, index=True, description="当前步骤")
    agent_name: Optional[str] = Field(default=None, index=True, description="Agent 名称")
    
    # 日志内容
    message: str = Field(sa_column=Column(Text), description="日志消息")
    details: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="详细数据（如输入输出、错误堆栈等）"
    )
    
    # 性能指标
    duration_ms: Optional[int] = Field(default=None, description="执行耗时（毫秒）")
    
    # 时间戳
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))
    )


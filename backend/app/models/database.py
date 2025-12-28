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
from sqlalchemy import Text, DateTime, UniqueConstraint, String, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from fastapi_users.db import SQLAlchemyBaseUserTable
import uuid


# SQLAlchemy Base 用于 User 表（FastAPI Users 要求）
class Base(DeclarativeBase):
    pass

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


class User(SQLAlchemyBaseUserTable[str], Base):
    """
    用户表
    
    继承 FastAPI Users 的 SQLAlchemyBaseUserTable，提供：
    - id: str (主键，UUID 字符串)
    - email: str (唯一索引)
    - hashed_password: str (密码哈希)
    - is_active: bool (是否激活)
    - is_superuser: bool (是否超级管理员)
    - is_verified: bool (是否已验证邮箱)
    
    自定义字段：
    - username: str (用户名)
    - password_expires_at: Optional[datetime] (临时密码过期时间)
    - created_at: datetime (创建时间)
    """
    __tablename__ = "users"
    
    # 重写 id 字段，使用 str 类型的 UUID
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    # 自定义字段
    username: Mapped[str] = mapped_column(String(100), nullable=False, default="", server_default="")
    
    # 临时密码过期时间（用于内测邀请）
    password_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        default=None,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=beijing_now,
        server_default=text("CURRENT_TIMESTAMP"),
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
    
    # 任务类型信息（用于区分创建任务和重试任务）
    task_type: Optional[str] = Field(default=None)  # 'creation', 'retry_tutorial', 'retry_resources', 'retry_quiz', 'retry_batch'
    concept_id: Optional[str] = Field(default=None)  # 单 Concept 重试时的概念 ID
    content_type: Optional[str] = Field(default=None)  # 'tutorial', 'resources', 'quiz'（单 Concept 重试时）
    
    # Celery 任务 ID（用于查询内容生成任务状态）
    celery_task_id: Optional[str] = Field(
        default=None,
        description="Celery 任务 ID，用于查询内容生成任务状态或取消任务"
    )
    
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
    
    title: str
    total_estimated_hours: float
    recommended_completion_weeks: int
    
    # 完整框架数据（JSON 格式）
    framework_data: dict = Field(sa_column=Column(JSON))
    
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))  # 无时区，直接存储北京时间
    )
    
    # 软删除字段
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
        description="软删除时间，None 表示未删除"
    )
    deleted_by: Optional[str] = Field(
        default=None,
        description="删除操作的用户 ID"
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
    task_id: str = Field(
        foreign_key="roadmap_tasks.task_id",
        index=True,
        unique=True,  # 确保每个任务只有一个需求分析记录
    )
    
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


class TechStackAssessment(SQLModel, table=True):
    """技术栈能力测试表"""
    __tablename__ = "tech_stack_assessments"
    
    assessment_id: str = Field(primary_key=True)
    technology: str = Field(index=True, description="技术栈名称 (python, react等)")
    proficiency_level: str = Field(index=True, description="能力级别 (beginner, intermediate, expert)")
    
    # 题目列表（每个题目不再包含difficulty字段）
    questions: list = Field(sa_column=Column(JSON), description="题目列表")
    total_questions: int = Field(default=20, description="题目总数")
    
    # 考察内容规划（用于审计和调试）
    examination_plan: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="考察内容规划（topics）"
    )
    
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
    
    # 技术栈 (JSON: [{technology: str, proficiency: str, capability_analysis: dict}])
    # capability_analysis 包含：overall_assessment, strengths, weaknesses, 
    # knowledge_gaps, learning_suggestions, proficiency_verification, score_breakdown
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
    - 通过 task_id 追踪请求完整生命周期
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
    task_id: str = Field(index=True, description="任务 ID")
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


class ConceptProgress(SQLModel, table=True):
    """Concept 学习进度表"""
    __tablename__ = "concept_progress"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(index=True, description="用户 ID")
    roadmap_id: str = Field(foreign_key="roadmap_metadata.roadmap_id", index=True)
    concept_id: str = Field(index=True, description="概念 ID（来自框架数据）")
    
    is_completed: bool = Field(default=False, description="是否完成")
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
        description="完成时间（北京时间）"
    )
    
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))
    )
    updated_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))
    )
    
    # 唯一约束：每个用户对每个Concept只有一条记录
    __table_args__ = (
        UniqueConstraint('user_id', 'roadmap_id', 'concept_id', name='uq_user_concept'),
    )


class QuizAttempt(SQLModel, table=True):
    """Quiz 答题记录表"""
    __tablename__ = "quiz_attempts"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(index=True, description="用户 ID")
    roadmap_id: str = Field(foreign_key="roadmap_metadata.roadmap_id", index=True)
    concept_id: str = Field(index=True, description="概念 ID")
    quiz_id: str = Field(foreign_key="quiz_metadata.quiz_id", index=True)
    
    # 答题详情
    total_questions: int = Field(description="总题数")
    correct_answers: int = Field(description="正确题数")
    score_percentage: float = Field(description="得分百分比（0-100）")
    incorrect_question_indices: list = Field(
        default=[],
        sa_column=Column(JSON),
        description="答错题目的序号列表（从0开始）"
    )
    
    # 时间记录
    attempted_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False)),
        description="答题时间（北京时间）"
    )


# ============================================================
# 路线图验证和编辑记录表
# ============================================================

class StructureValidationRecord(SQLModel, table=True):
    """
    结构验证记录表
    
    存储每次 structure_validation 的验证结果，支持查看历史验证记录。
    
    新版本字段说明:
    - dimension_scores: 5个维度的评分（知识完整性、知识进阶性、阶段连贯性、模块清晰度、用户匹配度）
    - improvement_suggestions: 结构化的改进建议（包含 action, target_location, content, reason）
    - validation_summary: 验证摘要（总体评价）
    """
    __tablename__ = "structure_validation_records"
    
    # 主键
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="记录唯一标识"
    )
    
    # 关联字段
    task_id: str = Field(
        foreign_key="roadmap_tasks.task_id",
        index=True,
        description="关联的任务 ID"
    )
    roadmap_id: str = Field(
        index=True,
        description="关联的路线图 ID"
    )
    
    # 验证结果
    is_valid: bool = Field(description="验证是否通过")
    overall_score: float = Field(description="总体评分 0-100")
    
    # 问题详情（JSON）- 只包含 critical 和 warning
    issues: dict = Field(
        sa_column=Column(JSON),
        description="验证问题列表（severity: critical/warning, category, location, issue, suggestion）"
    )
    
    # 维度评分（JSON）
    dimension_scores: dict = Field(
        sa_column=Column(JSON),
        description="5个维度的评分：knowledge_completeness, knowledge_progression, stage_coherence, module_clarity, user_alignment"
    )
    
    # 改进建议（JSON）
    improvement_suggestions: dict = Field(
        sa_column=Column(JSON),
        description="结构化改进建议列表（action, target_location, content, reason）"
    )
    
    # 验证摘要
    validation_summary: str = Field(
        sa_column=Column(Text),
        description="验证摘要：总体评价"
    )
    
    # 验证轮次
    validation_round: int = Field(
        default=1,
        description="第几轮验证（每次 edit 后重新验证时递增）"
    )
    
    # 统计数据
    critical_count: int = Field(default=0, description="严重问题数量")
    warning_count: int = Field(default=0, description="警告问题数量")
    suggestion_count: int = Field(default=0, description="改进建议数量（来自 improvement_suggestions）")
    
    # 时间戳
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False)),
        description="创建时间（北京时间）"
    )


class RoadmapEditRecord(SQLModel, table=True):
    """
    路线图编辑记录表
    
    存储每次 roadmap_edit 的编辑前后数据，用于对比和节点差异标记。
    """
    __tablename__ = "roadmap_edit_records"
    
    # 主键
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="记录唯一标识"
    )
    
    # 关联字段
    task_id: str = Field(
        foreign_key="roadmap_tasks.task_id",
        index=True,
        description="关联的任务 ID"
    )
    roadmap_id: str = Field(
        index=True,
        description="关联的路线图 ID"
    )
    
    # 编辑前后的框架数据
    origin_framework_data: dict = Field(
        sa_column=Column(JSON),
        description="编辑前的完整框架数据"
    )
    modified_framework_data: dict = Field(
        sa_column=Column(JSON),
        description="编辑后的完整框架数据"
    )
    
    # 差异摘要（由 Agent 或后端计算）
    modification_summary: str = Field(
        sa_column=Column(Text),
        description="修改摘要描述"
    )
    
    # 修改的节点 ID 列表
    modified_node_ids: list = Field(
        sa_column=Column(JSON),
        description="修改过的 concept_id 列表（用于前端高亮）"
    )
    
    # 编辑轮次
    edit_round: int = Field(
        default=1,
        description="第几轮编辑"
    )
    
    # 时间戳
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False)),
        description="创建时间（北京时间）"
    )


class HumanReviewFeedback(SQLModel, table=True):
    """
    人工审核反馈记录表
    
    存储 human_review 节点中用户提交的审核反馈，用于追溯和分析用户需求。
    """
    __tablename__ = "human_review_feedbacks"
    
    # 主键
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="反馈记录唯一标识"
    )
    
    # 关联字段
    task_id: str = Field(
        foreign_key="roadmap_tasks.task_id",
        index=True,
        description="关联的任务 ID"
    )
    roadmap_id: str = Field(
        index=True,
        description="关联的路线图 ID"
    )
    user_id: str = Field(
        index=True,
        description="用户 ID"
    )
    
    # 审核结果
    approved: bool = Field(
        description="是否批准：True=批准通过，False=拒绝并要求修改"
    )
    feedback_text: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="用户反馈文本（拒绝时必填）"
    )
    
    # 关联上下文
    roadmap_version_snapshot: dict = Field(
        sa_column=Column(JSON),
        description="审核时的路线图框架快照（用于追溯）"
    )
    
    # 审核轮次（同一任务可能有多轮审核）
    review_round: int = Field(
        default=1,
        index=True,
        description="第几轮审核"
    )
    
    # 时间戳
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False)),
        description="反馈提交时间（北京时间）"
    )


class EditPlanRecord(SQLModel, table=True):
    """
    修改计划记录表
    
    存储 EditPlanAnalyzerAgent 解析用户反馈后生成的结构化修改计划。
    """
    __tablename__ = "edit_plan_records"
    
    # 主键
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="修改计划唯一标识"
    )
    
    # 关联字段
    task_id: str = Field(
        foreign_key="roadmap_tasks.task_id",
        index=True,
        description="关联的任务 ID"
    )
    roadmap_id: str = Field(
        index=True,
        description="关联的路线图 ID"
    )
    feedback_id: str = Field(
        foreign_key="human_review_feedbacks.id",
        index=True,
        description="关联的用户反馈记录 ID"
    )
    
    # 修改计划内容（JSON 格式）
    feedback_summary: str = Field(
        sa_column=Column(Text),
        description="反馈摘要"
    )
    scope_analysis: str = Field(
        sa_column=Column(Text),
        description="修改范围分析"
    )
    intents: list = Field(
        sa_column=Column(JSON),
        description="修改意图列表（EditIntent 对象列表）"
    )
    preservation_requirements: list = Field(
        sa_column=Column(JSON),
        description="需保持不变的部分列表"
    )
    
    # 完整计划数据（JSON 格式，用于恢复 EditPlan 对象）
    full_plan_data: dict = Field(
        sa_column=Column(JSON),
        description="完整的 EditPlan 数据"
    )
    
    # 分析结果元数据
    confidence: Optional[str] = Field(
        default=None,
        description="解析置信度：high, medium, low"
    )
    needs_clarification: bool = Field(
        default=False,
        description="是否需要用户澄清"
    )
    clarification_questions: Optional[list] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="需要澄清的问题列表"
    )
    
    # 执行状态
    execution_status: str = Field(
        default="pending",
        index=True,
        description="执行状态：pending, executing, completed, failed"
    )
    
    # 时间戳
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False)),
        description="创建时间（北京时间）"
    )


# ============================================================
# 伴学Agent相关表
# ============================================================

class ChatSession(SQLModel, table=True):
    """
    聊天会话表
    
    存储用户与伴学Agent的对话会话，支持多轮对话和历史追踪。
    """
    __tablename__ = "chat_sessions"
    
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="会话唯一标识"
    )
    user_id: str = Field(index=True, description="用户 ID")
    roadmap_id: str = Field(index=True, description="关联的路线图 ID")
    concept_id: Optional[str] = Field(
        default=None, 
        index=True,
        description="当前聚焦的概念 ID（可选）"
    )
    
    # 会话元数据
    title: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="会话标题，如'React Hooks 学习讨论'"
    )
    message_count: int = Field(default=0, description="消息数量")
    last_message_preview: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="最后一条消息预览（截断）"
    )
    
    # 时间戳
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))
    )
    updated_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))
    )


class ChatMessage(SQLModel, table=True):
    """
    聊天消息表
    
    存储每一条对话消息，支持流式输出后的完整消息存储。
    """
    __tablename__ = "chat_messages"
    
    message_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="消息唯一标识"
    )
    session_id: str = Field(
        foreign_key="chat_sessions.session_id",
        index=True,
        description="关联的会话 ID"
    )
    
    # 消息内容
    role: str = Field(description="消息角色: user, assistant, system")
    content: str = Field(sa_column=Column(Text), description="消息内容")
    
    # 元数据
    intent_type: Optional[str] = Field(
        default=None,
        description="意图类型: qa, quiz_request, note_record, explanation, analogy"
    )
    message_metadata: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="额外元数据：工具调用记录、引用的概念等"
    )
    
    # 时间戳
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))
    )


class LearningNote(SQLModel, table=True):
    """
    学习笔记表
    
    存储用户的学习笔记，支持AI自动生成和手动记录。
    """
    __tablename__ = "learning_notes"
    
    note_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="笔记唯一标识"
    )
    user_id: str = Field(index=True, description="用户 ID")
    roadmap_id: str = Field(index=True, description="关联的路线图 ID")
    concept_id: str = Field(index=True, description="关联的概念 ID")
    
    # 笔记内容
    title: Optional[str] = Field(
        default=None,
        description="笔记标题"
    )
    content: str = Field(
        sa_column=Column(Text),
        description="笔记内容（Markdown格式）"
    )
    source: str = Field(
        default="manual",
        description="笔记来源: manual, ai_generated, chat_extracted"
    )
    tags: list = Field(
        default=[],
        sa_column=Column(JSON),
        description="标签列表"
    )
    
    # 时间戳
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))
    )
    updated_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False))
    )


# ============================================================
# Waitlist 相关表
# ============================================================

class WaitlistEmail(SQLModel, table=True):
    """
    候补名单邮箱表
    
    存储 Join Waitlist 用户的邮箱，用于内测邀请。
    """
    __tablename__ = "waitlist_emails"
    
    email: str = Field(
        primary_key=True,
        description="用户邮箱（主键）"
    )
    source: str = Field(
        default="landing_page",
        description="来源标记：landing_page, referral 等"
    )
    invited: bool = Field(
        default=False,
        description="是否已发送邀请"
    )
    invited_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
        description="邀请发送时间"
    )
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False)),
        description="加入候补名单时间"
    )
    
    # 邀请凭证字段（管理员发送邀请时生成）
    username: Optional[str] = Field(
        default=None,
        description="生成的用户名（从邮箱提取）"
    )
    password: Optional[str] = Field(
        default=None,
        description="临时密码（明文存储用于邮件发送）"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=False), nullable=True),
        description="密码过期时间"
    )
    sent_content: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="发送历史记录（JSON 格式）"
    )


# ============================================================
# 路线图封面图表
# ============================================================

class RoadmapCoverImage(SQLModel, table=True):
    """
    路线图封面图表
    
    存储路线图的封面图片URL，由外部图片生成服务生成。
    每个路线图对应一个封面图记录。
    """
    __tablename__ = "roadmap_cover_images"
    
    roadmap_id: str = Field(
        primary_key=True,
        description="路线图ID（主键，关联 roadmap_metadata.roadmap_id）"
    )
    cover_image_url: Optional[str] = Field(
        default=None,
        description="封面图URL"
    )
    generation_status: str = Field(
        default="pending",
        description="生成状态：pending, generating, success, failed"
    )
    error_message: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="生成失败时的错误信息"
    )
    retry_count: int = Field(
        default=0,
        description="重试次数"
    )
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False)),
        description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False)),
        description="更新时间"
    )


# ============================================================
# Tavily API Key 配额表
# ============================================================

class TavilyAPIKey(SQLModel, table=True):
    """
    Tavily API Key 配额表
    
    存储 Tavily API Key 的配额信息，由外部项目定时更新。
    本项目仅读取该表以选择剩余配额最多的 Key。
    """
    __tablename__ = "tavily_api_keys"
    
    api_key: str = Field(
        primary_key=True,
        description="Tavily API Key"
    )
    plan_limit: int = Field(
        description="计划总配额（每月总请求数）"
    )
    remaining_quota: int = Field(
        description="剩余配额（当前剩余可用请求数）"
    )
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(
            DateTime(timezone=False),
            server_default=text("CURRENT_TIMESTAMP")
        ),
        description="录入时间"
    )
    updated_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(
            DateTime(timezone=False),
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=beijing_now
        ),
        description="最后更新时间"
    )


"""
业务领域模型（Pydantic）

按时序图，保留以下角色相关的模型：
- A1: 需求分析师 (IntentAnalysis*)
- A2: 课程架构师 (CurriculumDesign*)
- A2E: 路线图编辑师 (RoadmapEdit*)
- A3: 结构审查员 (Validation*)
- A4: 教程生成器 (TutorialGeneration*)
- A5: 资源推荐师 (ResourceRecommendation*)
- A6: 测验生成器 (QuizGeneration*)
"""
from pydantic import BaseModel, Field, field_serializer
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime


# ============================================================
# 1. 用户输入模型
# ============================================================

class LearningPreferences(BaseModel):
    """学习偏好配置"""
    learning_goal: str = Field(..., description="学习目标，如'成为全栈工程师'")
    available_hours_per_week: int = Field(..., ge=1, le=168, description="每周可投入小时数")
    motivation: str = Field(..., description="学习动机，如'转行'、'升职'、'兴趣'")
    current_level: Literal["beginner", "intermediate", "advanced"] = Field(
        ..., description="当前掌握程度"
    )
    career_background: str = Field(..., description="职业背景，如'市场营销 5 年经验'")
    content_preference: List[Literal["video", "text", "interactive", "project"]] = Field(
        default=["text", "interactive"], description="偏好的内容类型"
    )
    target_deadline: Optional[datetime] = Field(None, description="期望完成时间")
    
    @field_serializer('target_deadline')
    def serialize_deadline(self, value: Optional[datetime], _info) -> Optional[str]:
        """将 datetime 序列化为 ISO 格式字符串"""
        return value.isoformat() if value else None


class UserRequest(BaseModel):
    """系统输入：用户请求"""
    user_id: str
    session_id: str
    preferences: LearningPreferences
    additional_context: Optional[str] = Field(None, description="额外补充信息")


# ============================================================
# 2. 路线图框架模型 (Stage -> Module -> Concept)
# ============================================================

class Concept(BaseModel):
    """第三层：概念/知识点（轻量级结构，不嵌套详细内容）"""
    concept_id: str
    name: str = Field(..., description="概念名称，如 'React Hooks 原理'")
    description: str = Field(..., description="简短描述（1-2 句话）")
    estimated_hours: float = Field(..., ge=0.5, description="预估学习时长（小时）")
    prerequisites: List[str] = Field(default=[], description="前置概念 ID 列表")
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    keywords: List[str] = Field(default=[], description="关键词标签")
    
    # 教程内容引用（结构与内容解耦）
    content_status: Literal["pending", "generating", "completed", "failed"] = Field(
        default="pending", 
        description="教程内容生成状态"
    )
    content_ref: Optional[str] = Field(
        None, 
        description="指向 S3 Key 或内容 API 的 ID，如 's3://bucket/{roadmap_id}/concepts/{concept_id}/v1.md'"
    )
    content_version: str = Field(default="v1", description="内容版本号")
    content_summary: Optional[str] = Field(
        None, 
        max_length=300, 
        description="教程摘要（用于前端预览，避免加载完整内容）"
    )
    
    # 资源推荐引用（A5: 资源推荐师产出）
    resources_status: Literal["pending", "generating", "completed", "failed"] = Field(
        default="pending",
        description="资源推荐生成状态"
    )
    resources_id: Optional[str] = Field(None, description="资源推荐记录 ID（UUID 格式，关联 resource_recommendation_metadata 表）")
    resources_count: int = Field(default=0, description="推荐资源数量")
    
    # 测验引用（A6: 测验生成器产出）
    quiz_status: Literal["pending", "generating", "completed", "failed"] = Field(
        default="pending",
        description="测验生成状态"
    )
    quiz_id: Optional[str] = Field(None, description="测验 ID（UUID 格式）")
    quiz_questions_count: int = Field(default=0, description="测验题目数量")


class Module(BaseModel):
    """第二层：模块"""
    module_id: str
    name: str = Field(..., description="模块名称，如 'React 核心'")
    description: str
    concepts: List[Concept] = Field(..., min_length=1)

    @property
    def total_hours(self) -> float:
        return sum(c.estimated_hours for c in self.concepts)


class Stage(BaseModel):
    """第一层：阶段"""
    stage_id: str
    name: str = Field(..., description="阶段名称，如 '前端基础'")
    description: str
    order: int = Field(..., ge=1, description="阶段顺序")
    modules: List[Module] = Field(..., min_length=1)

    @property
    def total_hours(self) -> float:
        return sum(m.total_hours for m in self.modules)


class RoadmapFramework(BaseModel):
    """完整的三层路线图框架"""
    roadmap_id: str
    title: str = Field(..., description="路线图标题，如 '全栈开发学习路线'")
    stages: List[Stage] = Field(..., min_length=1)
    total_estimated_hours: float
    recommended_completion_weeks: int

    def validate_structure(self) -> bool:
        """验证结构完整性（所有前置关系是否有效）"""
        all_concept_ids = {
            c.concept_id
            for stage in self.stages
            for module in stage.modules
            for c in module.concepts
        }
        for stage in self.stages:
            for module in stage.modules:
                for concept in module.concepts:
                    for prereq in concept.prerequisites:
                        if prereq not in all_concept_ids:
                            return False
        return True


# ============================================================
# 3. 详细教程模型（独立存储，不嵌套在 Roadmap 中）
# ============================================================

class TutorialSection(BaseModel):
    """教程的一个章节"""
    section_id: str
    title: str
    content: str = Field(..., description="Markdown 格式内容")
    content_type: Literal["theory", "example", "exercise", "quiz"]
    estimated_minutes: int


class Tutorial(BaseModel):
    """
    单个 Concept 的详细教程（大文本对象）
    
    存储策略：
    - 生成后直接存入 S3/OSS 作为 Markdown 或 JSON 文件
    - Concept 对象只保留 content_ref 指向此文件
    - 前端按需加载，避免一次性传输所有教程内容
    """
    tutorial_id: str
    concept_id: str
    title: str
    summary: str = Field(..., max_length=500, description="教程摘要")
    sections: List[TutorialSection]
    recommended_resources: List[Dict[str, str]] = Field(
        default=[],
        description="推荐资源，格式: [{title, url, type}]"
    )
    exercises: List[str] = Field(default=[], description="实战练习题")
    estimated_completion_time: int = Field(..., description="完成时长（分钟）")
    
    # 元数据（用于追踪和版本管理）
    version: str = Field(default="v1", description="教程版本")
    generated_at: datetime = Field(default_factory=datetime.now)
    storage_url: Optional[str] = Field(None, description="存储位置的完整 URL")


# ============================================================
# 4. Agent 输入/输出接口
# ============================================================

# --- A1: Intent Analyzer (需求分析师) ---
class IntentAnalysisInput(BaseModel):
    user_request: UserRequest


class IntentAnalysisOutput(BaseModel):
    parsed_goal: str = Field(..., description="结构化的学习目标")
    key_technologies: List[str] = Field(..., description="提取的关键技术栈")
    difficulty_profile: str = Field(..., description="难度画像分析")
    time_constraint: str = Field(..., description="时间约束分析")
    recommended_focus: List[str] = Field(..., description="建议的学习重点")


# --- A2: Curriculum Architect (课程架构师) ---
class CurriculumDesignInput(BaseModel):
    intent_analysis: IntentAnalysisOutput
    user_preferences: LearningPreferences


class CurriculumDesignOutput(BaseModel):
    framework: RoadmapFramework
    design_rationale: str = Field(..., description="设计理由说明")


# --- A2E: Roadmap Editor (路线图编辑师) ---
class RoadmapEditInput(BaseModel):
    """路线图编辑输入"""
    existing_framework: RoadmapFramework = Field(..., description="现有路线图框架")
    validation_issues: List["ValidationIssue"] = Field(..., description="验证发现的问题列表")
    user_preferences: LearningPreferences = Field(..., description="用户偏好")
    modification_context: Optional[str] = Field(
        None, 
        description="修改上下文说明（如：第2次修改，主要解决前置关系问题）"
    )


class RoadmapEditOutput(BaseModel):
    """路线图编辑输出"""
    framework: RoadmapFramework = Field(..., description="修改后的路线图框架")
    modification_summary: str = Field(..., description="修改说明：解决了哪些问题，做了哪些调整")
    preserved_elements: List[str] = Field(
        default=[], 
        description="保留的原有元素（如：保留了Stage 1的完整结构）"
    )


# --- A3: Structure Validator (结构审查员) ---
class ValidationInput(BaseModel):
    framework: RoadmapFramework
    user_preferences: LearningPreferences


class ValidationIssue(BaseModel):
    severity: Literal["critical", "warning", "suggestion"]
    location: str = Field(..., description="问题位置，如 'Stage 2 > Module 1'")
    issue: str
    suggestion: str


class ValidationOutput(BaseModel):
    is_valid: bool
    issues: List[ValidationIssue] = []
    overall_score: float = Field(..., ge=0, le=100, description="结构质量评分")


# --- A4: Tutorial Generator (教程生成器) ---
class TutorialGenerationInput(BaseModel):
    concept: Concept
    context: Dict[str, Any] = Field(
        default={},
        description="上下文信息：前置概念、所属模块等"
    )
    user_preferences: LearningPreferences


class TutorialGenerationOutput(BaseModel):
    """
    教程生成器的输出（轻量级）
    
    注意：不直接返回完整 Tutorial 对象，而是返回引用信息
    
    版本管理说明：
    - content_version: 内容版本号，从 1 开始
    - tutorial_id 格式：UUID（全局唯一）
    - content_url 格式：{roadmap_id}/concepts/{concept_id}/v{version}.md
    """
    concept_id: str
    tutorial_id: str = Field(..., description="教程 ID（UUID 格式，确保全局唯一）")
    title: str
    summary: str = Field(..., max_length=500, description="教程摘要（用于预览）")
    content_url: str = Field(..., description="S3 存储地址或 CDN URL")
    content_status: Literal["completed", "failed"] = "completed"
    content_version: int = Field(default=1, description="内容版本号，从 1 开始")
    estimated_completion_time: int
    generated_at: datetime = Field(default_factory=datetime.now)


# --- A5: Resource Recommender (资源推荐师) ---
class Resource(BaseModel):
    """单个学习资源"""
    title: str = Field(..., description="资源标题")
    url: str = Field(..., description="资源 URL")
    type: Literal["article", "video", "book", "course", "documentation", "tool"] = Field(
        ..., description="资源类型"
    )
    description: str = Field(..., description="资源简介")
    relevance_score: float = Field(..., ge=0, le=1, description="相关性评分（0-1）")


class ResourceRecommendationInput(BaseModel):
    """资源推荐师的输入"""
    concept: Concept
    context: Dict[str, Any] = Field(
        default={},
        description="上下文信息：所属阶段、模块等"
    )
    user_preferences: LearningPreferences


class ResourceRecommendationOutput(BaseModel):
    """资源推荐师的输出"""
    id: str = Field(..., description="资源推荐记录 ID（UUID 格式）")
    concept_id: str
    resources: List[Resource] = Field(..., description="推荐的学习资源列表")
    search_queries_used: List[str] = Field(
        default=[],
        description="使用的搜索查询（用于追踪）"
    )
    generated_at: datetime = Field(default_factory=datetime.now)


# --- A6: Quiz Generator (测验生成器) ---
class QuizQuestion(BaseModel):
    """单个测验题目"""
    question_id: str = Field(..., description="题目唯一标识")
    question_type: Literal["single_choice", "multiple_choice", "true_false", "fill_blank"] = Field(
        ..., description="题目类型"
    )
    question: str = Field(..., description="题目内容")
    options: List[str] = Field(default=[], description="选项列表（选择题适用）")
    correct_answer: List[int] = Field(
        ..., 
        description="正确答案索引列表（单选题为单元素列表，多选题为多元素列表）"
    )
    explanation: str = Field(..., description="答案解析")
    difficulty: Literal["easy", "medium", "hard"] = Field(
        default="medium", description="题目难度"
    )


class QuizGenerationInput(BaseModel):
    """测验生成器的输入"""
    concept: Concept
    context: Dict[str, Any] = Field(
        default={},
        description="上下文信息：所属阶段、模块等"
    )
    user_preferences: LearningPreferences


class QuizGenerationOutput(BaseModel):
    """测验生成器的输出"""
    concept_id: str
    quiz_id: str = Field(..., description="测验唯一标识（UUID 格式，确保全局唯一）")
    questions: List[QuizQuestion] = Field(..., description="测验题目列表")
    total_questions: int = Field(..., description="题目总数")
    generated_at: datetime = Field(default_factory=datetime.now)


# ============================================================
# 5. Tool Interface Models
# ============================================================

class SearchQuery(BaseModel):
    """Web 搜索查询"""
    query: str = Field(..., description="搜索查询字符串")
    search_type: Literal["web", "academic", "video"] = Field(default="web", description="搜索类型")
    max_results: int = Field(default=5, ge=1, le=20, description="最大结果数量")


class SearchResult(BaseModel):
    """Web 搜索结果"""
    results: List[Dict[str, str]] = Field(
        ...,
        description="搜索结果列表，格式: [{title, url, snippet, published_date}]"
    )
    total_found: int = Field(..., description="找到的结果总数")


class S3UploadRequest(BaseModel):
    """S3 对象存储上传请求"""
    key: str = Field(..., description="对象存储路径，如 'roadmaps/{id}/concepts/{cid}/v1.md'")
    content: str = Field(..., description="要上传的内容（文本或 base64 编码）")
    content_type: str = Field(default="text/markdown", description="MIME 类型")
    bucket: Optional[str] = Field(None, description="存储桶名称（默认使用配置）")


class S3UploadResult(BaseModel):
    """S3 上传结果"""
    success: bool = Field(..., description="上传是否成功")
    url: str = Field(..., description="对象的访问 URL（可能是预签名 URL）")
    key: str = Field(..., description="存储的对象 Key")
    size_bytes: int = Field(..., description="上传的文件大小")
    etag: Optional[str] = Field(None, description="对象的 ETag")


class S3DownloadRequest(BaseModel):
    """S3 对象存储下载请求"""
    key: str = Field(..., description="对象存储路径，如 'roadmaps/{id}/concepts/{cid}/v1.md'")
    bucket: Optional[str] = Field(None, description="存储桶名称（默认使用配置）")


class S3DownloadResult(BaseModel):
    """S3 下载结果"""
    success: bool = Field(..., description="下载是否成功")
    content: str = Field(..., description="下载的文本内容")
    key: str = Field(..., description="对象的 Key")
    size_bytes: int = Field(..., description="下载的文件大小")
    content_type: Optional[str] = Field(None, description="对象的 Content-Type")
    etag: Optional[str] = Field(None, description="对象的 ETag")
    last_modified: Optional[datetime] = Field(None, description="对象的最后修改时间")


# ============================================================
# 6. 内容修改相关模型（Modifier Agents）
# ============================================================

from enum import Enum


class ModificationType(str, Enum):
    """修改目标类型"""
    TUTORIAL = "tutorial"
    RESOURCES = "resources"
    QUIZ = "quiz"
    CONCEPT = "concept"


class SingleModificationIntent(BaseModel):
    """单个修改意图"""
    modification_type: ModificationType = Field(..., description="修改目标类型")
    target_id: str = Field(..., description="目标 ID（concept_id）")
    target_name: str = Field(..., description="目标名称，便于展示")
    specific_requirements: List[str] = Field(..., description="具体修改要求列表")
    priority: Literal["high", "medium", "low"] = Field(
        default="medium", description="优先级"
    )


class ModificationAnalysisInput(BaseModel):
    """修改意图分析输入"""
    user_message: str = Field(..., description="用户的自然语言修改意见")
    roadmap_id: str = Field(..., description="路线图 ID")
    current_context: Optional[Dict[str, Any]] = Field(
        None, 
        description="当前上下文（如用户正在查看的 concept_id）"
    )


class ModificationAnalysisOutput(BaseModel):
    """修改意图分析输出（支持多目标）"""
    intents: List[SingleModificationIntent] = Field(
        ..., description="识别出的所有修改意图"
    )
    overall_confidence: float = Field(
        ..., ge=0, le=1, description="整体置信度"
    )
    needs_clarification: bool = Field(
        default=False, description="是否需要向用户澄清"
    )
    clarification_questions: List[str] = Field(
        default=[], description="如果需要澄清，要问用户的问题"
    )
    analysis_reasoning: str = Field(..., description="分析推理过程")


# --- Tutorial Modifier Agent ---

class TutorialModificationInput(BaseModel):
    """教程修改输入"""
    concept: Concept = Field(..., description="要修改教程的概念")
    context: Dict[str, Any] = Field(
        default={}, description="上下文信息：所属阶段、模块等"
    )
    user_preferences: LearningPreferences = Field(..., description="用户偏好")
    existing_content_url: str = Field(..., description="现有教程内容的 S3 URL")
    modification_requirements: List[str] = Field(
        ..., description="具体修改要求列表"
    )


class TutorialModificationOutput(BaseModel):
    """教程修改输出"""
    concept_id: str = Field(..., description="概念 ID")
    tutorial_id: str = Field(..., description="新教程 ID（UUID 格式）")
    title: str = Field(..., description="教程标题")
    summary: str = Field(..., max_length=500, description="教程摘要")
    content_url: str = Field(..., description="新版本的 S3 URL")
    content_version: int = Field(..., description="新版本号")
    modification_summary: str = Field(..., description="修改说明")
    changes_made: List[str] = Field(..., description="具体修改点列表")
    estimated_completion_time: int = Field(..., description="预估完成时间（分钟）")
    generated_at: datetime = Field(default_factory=datetime.now)


# --- Resource Modifier Agent ---

class ResourceModificationInput(BaseModel):
    """资源修改输入"""
    concept: Concept = Field(..., description="要修改资源的概念")
    context: Dict[str, Any] = Field(
        default={}, description="上下文信息：所属阶段、模块等"
    )
    user_preferences: LearningPreferences = Field(..., description="用户偏好")
    existing_resources: List[Resource] = Field(..., description="现有资源列表")
    modification_requirements: List[str] = Field(
        ..., description="具体修改要求列表"
    )


class ResourceModificationOutput(BaseModel):
    """资源修改输出"""
    id: str = Field(..., description="新资源推荐记录 ID（UUID 格式）")
    concept_id: str = Field(..., description="概念 ID")
    resources: List[Resource] = Field(..., description="修改后的资源列表")
    modification_summary: str = Field(..., description="修改说明")
    changes_made: List[str] = Field(..., description="具体修改点列表")
    search_queries_used: List[str] = Field(
        default=[], description="使用的搜索查询"
    )
    generated_at: datetime = Field(default_factory=datetime.now)


# --- Quiz Modifier Agent ---

class QuizModificationInput(BaseModel):
    """测验修改输入"""
    concept: Concept = Field(..., description="要修改测验的概念")
    context: Dict[str, Any] = Field(
        default={}, description="上下文信息：所属阶段、模块等"
    )
    user_preferences: LearningPreferences = Field(..., description="用户偏好")
    existing_questions: List[QuizQuestion] = Field(..., description="现有题目列表")
    modification_requirements: List[str] = Field(
        ..., description="具体修改要求列表"
    )


class QuizModificationOutput(BaseModel):
    """测验修改输出"""
    concept_id: str = Field(..., description="概念 ID")
    quiz_id: str = Field(..., description="新测验 ID（UUID 格式）")
    questions: List[QuizQuestion] = Field(..., description="修改后的题目列表")
    total_questions: int = Field(..., description="题目总数")
    modification_summary: str = Field(..., description="修改说明")
    changes_made: List[str] = Field(..., description="具体修改点列表")
    generated_at: datetime = Field(default_factory=datetime.now)


# --- 批量修改结果 ---

class SingleModificationResult(BaseModel):
    """单个修改结果"""
    modification_type: ModificationType = Field(..., description="修改类型")
    target_id: str = Field(..., description="目标 ID")
    target_name: str = Field(..., description="目标名称")
    success: bool = Field(..., description="是否成功")
    modification_summary: str = Field(..., description="修改摘要")
    new_version: Optional[int] = Field(None, description="新版本号（如果支持版本管理）")
    error_message: Optional[str] = Field(None, description="错误信息（如果失败）")


class BatchModificationResult(BaseModel):
    """批量修改结果"""
    results: List[SingleModificationResult] = Field(..., description="各项修改结果")
    overall_success: bool = Field(..., description="是否全部成功")
    partial_success: bool = Field(..., description="是否部分成功")
    summary: str = Field(..., description="整体修改摘要")

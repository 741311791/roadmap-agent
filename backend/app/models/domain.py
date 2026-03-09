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
from typing import List, Optional, Literal, Dict, Any, Tuple
from datetime import datetime

# 导入项目统一的时间函数（北京时间，无时区信息）
from app.models.database import beijing_now


# ============================================================
# 1. 用户输入模型
# ============================================================

class LanguagePreferences(BaseModel):
    """
    语言偏好配置
    
    用于指导内容生成和资源推荐的语言分布：
    - primary_language: 主要语言（教程、路线图的主要语言）
    - secondary_language: 次要语言（资源推荐的补充语言）
    - resource_ratio: 资源推荐的语言分配比例
    """
    primary_language: str = Field(default="zh", description="主要语言代码（如 'zh', 'en'）")
    secondary_language: Optional[str] = Field(None, description="次要语言代码（如 'en', 'zh'）")
    resource_ratio: Dict[str, float] = Field(
        default={"primary": 1.0, "secondary": 0.0},
        description="资源推荐的语言分配比例（如 {'primary': 0.6, 'secondary': 0.4}）"
    )
    
    def get_effective_ratio(self) -> Dict[str, float]:
        """
        获取有效的资源分配比例
        
        规则：
        - 如果 secondary_language 为空或与 primary_language 相同，则 100% 使用主语言
        - 否则按 60%/40% 分配
        """
        if not self.secondary_language or self.secondary_language == self.primary_language:
            return {"primary": 1.0, "secondary": 0.0}
        return {"primary": 0.6, "secondary": 0.4}


class LearningPreferences(BaseModel):
    """学习偏好配置"""
    learning_goal: str = Field(..., description="学习目标，如'成为全栈工程师'")
    available_hours_per_week: int = Field(..., ge=1, le=168, description="每周可投入小时数")
    motivation: str = Field(..., description="学习动机，如'转行'、'升职'、'兴趣'")
    current_level: Literal["beginner", "intermediate", "advanced"] = Field(
        ..., description="当前掌握程度"
    )
    career_background: str = Field(..., description="职业背景，如'市场营销 5 年经验'")
    # 内容偏好类型：visual(视觉类), text(文本类), audio(音频类), hands_on(实操类)
    content_preference: List[Literal["visual", "text", "audio", "hands_on"]] = Field(
        default=["visual", "text"], description="偏好的内容类型"
    )
    target_deadline: Optional[datetime] = Field(None, description="期望完成时间")
    
    # 来自用户画像的扩展信息（可选）
    industry: Optional[str] = Field(None, description="所属行业")
    current_role: Optional[str] = Field(None, description="当前职位")
    tech_stack: Optional[List[Dict[str, Any]]] = Field(None, description="技术栈列表")
    
    # 语言偏好（向后兼容：保留 preferred_language，新增双语支持）
    preferred_language: Optional[str] = Field(None, description="偏好的学习语言（向后兼容）")
    primary_language: str = Field(default="zh", description="主要语言（教程、路线图语言）")
    secondary_language: Optional[str] = Field(None, description="次要语言（资源推荐补充语言）")
    
    @field_serializer('target_deadline')
    def serialize_deadline(self, value: Optional[datetime], _info) -> Optional[str]:
        """将 datetime 序列化为 ISO 格式字符串"""
        return value.isoformat() if value else None
    
    def get_language_preferences(self) -> LanguagePreferences:
        """
        获取语言偏好配置对象
        
        向后兼容逻辑：
        - 如果设置了 primary_language，使用它
        - 否则使用 preferred_language（如果有）
        - 默认为 'zh'
        """
        primary = self.primary_language or self.preferred_language or "zh"
        return LanguagePreferences(
            primary_language=primary,
            secondary_language=self.secondary_language,
        )


class UserRequest(BaseModel):
    """系统输入：用户请求"""
    user_id: str
    session_id: str
    preferences: LearningPreferences
    additional_context: Optional[str] = Field(None, description="额外补充信息")
    turbo_mode: bool = Field(True, description="极速模式：跳过结构验证节点，Curriculum Design 后直接进入 Human Review")


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
    tutorial_id: Optional[str] = Field(None, description="教程 ID（UUID 格式，关联 tutorial_metadata 表）")
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
    stages: List[Stage] = Field(default_factory=list, description="路线图阶段列表")
    total_estimated_hours: float
    recommended_completion_weeks: int

    def validate_structure(self) -> Tuple[bool, List["ValidationIssue"]]:
        """
        执行硬性结构检查
        
        Returns:
            (是否通过, 问题列表)
        """
        issues = []
        
        # 1. 检查前置关系有效性
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
                            issues.append(ValidationIssue(
                                severity="critical",
                                category="structural_flaw",
                                location=f"Stage {stage.order} > {module.name} > {concept.name}",
                                issue=f"前置概念 '{prereq}' 不存在于路线图中",
                                suggestion="移除无效的前置关系或添加缺失的概念"
                            ))
        
        # 2. 检查循环依赖（使用 DFS）
        cycles = self._detect_cycles()
        for cycle in cycles:
            cycle_str = " → ".join(cycle)
            issues.append(ValidationIssue(
                severity="critical",
                category="structural_flaw",
                location="多个 Concepts",
                issue=f"检测到循环依赖：{cycle_str}",
                suggestion="移除循环中的某个前置关系"
            ))
        
        # 3. 检查 Stage/Module 是否为空
        for stage in self.stages:
            if not stage.modules:
                issues.append(ValidationIssue(
                    severity="critical",
                    category="structural_flaw",
                    location=f"Stage {stage.order}: {stage.name}",
                    issue="阶段不包含任何模块",
                    suggestion="添加至少一个模块或删除该阶段"
                ))
            else:
                for module in stage.modules:
                    if not module.concepts:
                        issues.append(ValidationIssue(
                            severity="critical",
                            category="structural_flaw",
                            location=f"Stage {stage.order} > {module.name}",
                            issue="模块不包含任何概念",
                            suggestion="添加至少一个概念或删除该模块"
                        ))
        
        # 判断是否通过：没有 critical 问题
        is_valid = len([i for i in issues if i.severity == "critical"]) == 0
        
        return (is_valid, issues)
    
    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """
        构建概念依赖图
        
        Returns:
            概念 ID -> 依赖它的概念 ID 列表
        """
        graph = {}
        
        for stage in self.stages:
            for module in stage.modules:
                for concept in module.concepts:
                    if concept.concept_id not in graph:
                        graph[concept.concept_id] = []
                    
                    for prereq in concept.prerequisites:
                        if prereq not in graph:
                            graph[prereq] = []
                        # prereq -> concept (concept 依赖 prereq)
                        graph[prereq].append(concept.concept_id)
        
        return graph
    
    def _detect_cycles(self) -> List[List[str]]:
        """
        使用 DFS 检测循环依赖
        
        Returns:
            循环列表，每个循环是一个概念 ID 列表
        """
        # 构建依赖图（反向：concept -> prerequisites）
        graph = {}
        for stage in self.stages:
            for module in stage.modules:
                for concept in module.concepts:
                    graph[concept.concept_id] = concept.prerequisites
        
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> bool:
            """DFS 检测循环，返回 True 表示发现循环"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            if node in graph:
                for neighbor in graph[node]:
                    if neighbor not in visited:
                        if dfs(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        # 发现循环
                        cycle_start = path.index(neighbor)
                        cycle = path[cycle_start:] + [neighbor]
                        cycles.append(cycle)
                        return True
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        for concept_id in graph:
            if concept_id not in visited:
                dfs(concept_id)
        
        return cycles


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
    created_at: datetime = Field(default_factory=beijing_now, description="创建时间")
    storage_url: Optional[str] = Field(None, description="存储位置的完整 URL")


# ============================================================
# 4. Agent 输入/输出接口
# ============================================================

# --- A1: Intent Analyzer (需求分析师) ---
class IntentAnalysisInput(BaseModel):
    user_request: UserRequest


class ContentFormatWeights(BaseModel):
    """内容格式权重分配"""
    visual: float = Field(default=0.25, ge=0.0, le=1.0, description="视觉类内容权重")
    text: float = Field(default=0.25, ge=0.0, le=1.0, description="文本类内容权重")
    audio: float = Field(default=0.25, ge=0.0, le=1.0, description="音频类内容权重")
    hands_on: float = Field(default=0.25, ge=0.0, le=1.0, description="实操类内容权重")


# ============================================================
# 约束系统（用户画像约束）
# ============================================================

# 约束文本字典类型
UserConstraints = Dict[str, str]  # {"约束名称": "约束内容"}


class ConstraintNames:
    """约束名称常量"""
    # 通用约束（所有 Agent）
    LANGUAGE = "生成语言约束"
    USER_GOAL = "用户目标约束"
    USER_PROFILE = "用户画像约束"
    
    # 特定约束
    DIFFICULTY = "难度约束"
    TIME_CONSTRAINT = "时间约束"
    LEARNING_PATH_TYPE = "学习路径类型约束"
    SKILL_GAP = "技能差距约束"
    RECOMMENDED_FOCUS = "推荐重点约束"
    CONTENT_FORMAT_PREFERENCE = "内容格式偏好约束"
    LANGUAGE_RESOURCE_ALLOCATION = "语言资源分配约束"
    KEY_TECHNOLOGIES = "技术栈约束"
    PERSONALIZED_SUGGESTIONS = "个性化建议约束"


class IntentAnalysisOutput(BaseModel):
    """需求分析输出（增强版）"""
    # 原有字段
    parsed_goal: str = Field(..., description="结构化的学习目标")
    key_technologies: List[str] = Field(..., description="需要学习的关键技术栈")
    difficulty_profile: str = Field(..., description="难度画像分析")
    time_constraint: str = Field(..., description="时间约束分析")
    recommended_focus: List[str] = Field(..., description="建议的学习重点")
    
    # 新增分析维度
    user_profile_summary: str = Field(
        default="", 
        description="用户画像摘要，包括职业背景和技能基础"
    )
    skill_gap_analysis: List[str] = Field(
        default=[], 
        description="技能差距分析，列出需要重点提升的方面"
    )
    personalized_suggestions: List[str] = Field(
        default=[], 
        description="基于用户画像的个性化建议"
    )
    estimated_learning_path_type: Literal[
        "quick_start", "deep_dive", "career_transition", "skill_upgrade"
    ] = Field(
        default="deep_dive",
        description="学习路径类型"
    )
    content_format_weights: Optional[ContentFormatWeights] = Field(
        default=None,
        description="基于用户偏好的内容格式权重分配"
    )
    
    # 语言偏好分析
    language_preferences: Optional[LanguagePreferences] = Field(
        default=None,
        description="语言偏好配置（包含主语言、次语言和资源分配比例）"
    )
    
    # 路线图ID（在需求分析完成后生成）
    roadmap_id: Optional[str] = Field(
        default=None,
        description="路线图唯一标识（有语义的英文短语 + 唯一后缀）"
    )
    
    # 约束文本字典（新增）
    full_analysis_data: UserConstraints = Field(
        default_factory=dict,
        description="约束文本字典，格式：{'约束名称': '约束内容'}"
    )


# --- A2: Curriculum Architect (课程架构师) ---
class CurriculumDesignInput(BaseModel):
    intent_analysis: IntentAnalysisOutput
    user_preferences: LearningPreferences


# --- 简化模型（用于第一阶段 LLM 结构化提取）---

class SimplifiedConcept(BaseModel):
    """
    简化的 Concept 模型（仅第一阶段需要的字段）
    
    用于 LLM 结构化提取，减少嵌套深度和无效字段，提升响应速度。
    """
    concept_id: str
    name: str = Field(..., description="概念名称，如 'React Hooks 原理'")
    description: str = Field(..., description="简短描述（1-2 句话）")
    estimated_hours: float = Field(..., ge=0.5, description="预估学习时长（小时）")
    prerequisites: List[str] = Field(default=[], description="前置概念 ID 列表")
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    keywords: List[str] = Field(default=[], description="关键词标签")


class SimplifiedModule(BaseModel):
    """简化的 Module 模型（仅第一阶段需要的字段）"""
    module_id: str
    name: str = Field(..., description="模块名称，如 'React 核心'")
    description: str
    concepts: List[SimplifiedConcept] = Field(..., min_length=1)


class SimplifiedStage(BaseModel):
    """简化的 Stage 模型（仅第一阶段需要的字段）"""
    stage_id: str
    name: str = Field(..., description="阶段名称，如 '前端基础'")
    description: str
    order: int = Field(..., ge=1, description="阶段顺序")
    modules: List[SimplifiedModule] = Field(..., min_length=1)


class SimplifiedRoadmapFramework(BaseModel):
    """
    简化的路线图框架（仅第一阶段需要的字段）
    
    用于 LLM 结构化提取，提升响应速度。
    转换为完整 RoadmapFramework 时会补充其他字段的默认值。
    """
    roadmap_id: str
    title: str = Field(..., description="路线图标题，如 '全栈开发学习路线'")
    stages: List[SimplifiedStage] = Field(default_factory=list, description="路线图阶段列表")
    total_estimated_hours: float
    recommended_completion_weeks: int


class CurriculumDesignOutput(BaseModel):
    """
    课程架构师输出
    
    重构说明:
    - 移除 design_rationale 字段,只保留核心的 framework
    - 设计理由通过日志记录,不作为输出结构的一部分
    """
    framework: RoadmapFramework


# --- A2E: Roadmap Editor (路线图编辑师) ---

class StageEditTask(BaseModel):
    """
    Stage 级别的修改任务（极简版）
    
    重构说明（第三版）：
    - 移除所有工程化设计（dependencies、order、priority）
    - 只保留核心字段：action、stage_id、instruction
    - 完全依赖 LLM 的语义理解能力
    """
    action: Literal["CREATE", "UPDATE", "REGENERATE"] = Field(
        ..., description="动作类型：CREATE（创建新Stage）、UPDATE（修改现有Stage，包括增删改模块/概念）、REGENERATE（重建整个路线图）"
    )
    stage_id: Optional[str] = Field(
        None, description="目标 Stage ID（UPDATE 时必需，CREATE/REGENERATE 时为 None）"
    )
    instruction: str = Field(
        ..., description="清晰的自然语言指令，描述该 Stage 需要如何调整（LLM 会理解并执行）"
    )


class EditPlan(BaseModel):
    """
    路线图修改计划（极简版）
    
    重构说明（第三版）：
    - 移除所有工程化字段（execution_strategy、preservation_requirements）
    - 只保留核心：feedback_summary + tasks
    - LLM 会根据 tasks 自己判断如何修改、保留什么
    """
    feedback_summary: str = Field(
        ..., description="用户反馈的简明摘要"
    )
    tasks: List[StageEditTask] = Field(
        ..., description="Stage 级别的修改任务列表"
    )


class EditPlanAnalyzerInput(BaseModel):
    """修改计划分析器输入"""
    user_feedback: str = Field(..., description="用户的原始反馈文本")
    existing_framework: RoadmapFramework = Field(..., description="当前路线图框架")
    user_preferences: LearningPreferences = Field(..., description="用户偏好")


class EditPlanAnalyzerOutput(BaseModel):
    """
    修改计划分析器输出
    
    重构说明：
    - 移除 needs_clarification 和 clarification_questions
    - 即使用户反馈模糊，也需要给出具体的修改计划
    - 在输入到 EditPlanAnalyzer 之前会通过其他方式确认修改请求有效
    """
    edit_plan: EditPlan = Field(..., description="解析后的结构化修改计划")
    confidence: float = Field(
        ..., ge=0, le=1, description="解析置信度（0-1）"
    )


class RoadmapEditInput(BaseModel):
    """
    路线图编辑输入（简化版）
    
    重构说明：
    - 统一使用 EditPlan 作为修改指令来源
    - 移除了 validation_issues 和 user_feedback 字段
    - 所有修改来源（验证失败、人工反馈）都通过 EditPlanAnalyzerAgent 转换为 EditPlan
    """
    existing_framework: RoadmapFramework = Field(..., description="现有路线图框架")
    user_preferences: LearningPreferences = Field(..., description="用户偏好")
    modification_context: Optional[str] = Field(
        None, 
        description="修改上下文说明（如：第2次修改，验证问题修复）"
    )
    # 统一使用 EditPlan 作为修改指令来源
    edit_plan: EditPlan = Field(..., description="结构化的修改计划（必需，来自 EditPlanAnalyzerAgent）")


class RoadmapEditOutput(BaseModel):
    """
    路线图编辑输出
    
    重构说明：
    - 采用新旧对比引擎自动生成 modified_node_ids
    - 移除手动标注的 preserved_elements
    """
    framework: RoadmapFramework = Field(..., description="修改后的路线图框架")
    modification_summary: str = Field(..., description="修改说明：解决了哪些问题，做了哪些调整")
    modified_node_ids: List[str] = Field(
        default=[], 
        description="被修改的节点 ID 列表（通过新旧对比自动生成，包括 stage_id/module_id/concept_id）"
    )


# --- A3: Structure Validator (结构审查员) ---
class ValidationInput(BaseModel):
    framework: RoadmapFramework
    user_preferences: LearningPreferences


class DimensionScore(BaseModel):
    """单个评估维度的分数"""
    dimension: str = Field(..., description="维度名称")
    score: float = Field(..., ge=0, le=100, description="该维度得分（0-100）")
    rationale: str = Field(..., description="评分理由（50字以内）")


class StructuralSuggestion(BaseModel):
    """结构化修改建议"""
    action: Literal[
        "add_concept",
        "add_module",
        "add_stage",
        "modify_concept",
        "reorder_stage",
        "reorder_module",
        "reorder_concepts",
        "merge_modules"
    ]
    target_location: str = Field(..., description="目标位置，如 'Stage 2 > Module 1 之后'")
    content: str = Field(..., description="建议的具体内容")
    reason: str = Field(..., description="为什么需要此修改")


class ValidationIssue(BaseModel):
    """验证问题"""
    severity: Literal["critical", "warning"]  # 移除 suggestion
    category: Literal["knowledge_gap", "structural_flaw", "user_mismatch"]
    location: str = Field(..., description="问题位置，如 'Stage 2 > Module 1'")
    issue: str
    suggestion: str  # 保留描述性建议
    structural_suggestion: Optional[StructuralSuggestion] = None  # 新增：结构化建议


class ValidationOutput(BaseModel):
    """验证输出结果"""
    # === LLM 输出部分 ===
    dimension_scores: List[DimensionScore] = Field(default_factory=list, description="5个维度的独立评分")
    issues: List[ValidationIssue] = Field(default_factory=list, description="只包含 critical 和 warning")
    improvement_suggestions: List[StructuralSuggestion] = Field(default_factory=list, description="改进建议（不影响通过与否）")
    
    # === Python 计算部分 ===
    overall_score: float = Field(..., ge=0, le=100, description="加权总分（Python 计算）")
    is_valid: bool = Field(..., description="是否通过验证（Python 判定）")
    validation_summary: str = Field(..., description="验证摘要（Python 生成）")


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
    created_at: datetime = Field(default_factory=beijing_now, description="创建时间")


# --- A5: Resource Recommender (资源推荐师) ---
class Resource(BaseModel):
    """单个学习资源"""
    title: str = Field(..., description="资源标题")
    url: str = Field(..., description="资源 URL")
    type: Literal["article", "video", "book", "course", "documentation", "tool", "hands_on"] = Field(
        ..., description="资源类型"
    )
    description: str = Field(..., description="资源简介")
    relevance_score: float = Field(..., ge=0, le=1, description="相关性评分（0-1）")
    language: Optional[str] = Field(
        default=None, 
        description="资源语言代码（如 'zh', 'en'），用于语言分布追踪"
    )
    
    # 🆕 新增字段：提升资源质量
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="资源可信度评分（0-1），基于来源权威性和内容质量"
    )
    published_date: Optional[str] = Field(
        default=None,
        description="资源发布日期（ISO格式，如 '2024-01-15'），用于时效性判断"
    )


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
    created_at: datetime = Field(default_factory=beijing_now, description="创建时间")


# --- A6: Quiz Generator (测验生成器) ---
class QuizQuestion(BaseModel):
    """单个测验题目"""
    question_id: str = Field(..., description="题目唯一标识")
    question_type: Literal["single_choice", "multiple_choice", "true_false"] = Field(
        ..., description="题目类型：单选题、多选题、判断题"
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
    created_at: datetime = Field(default_factory=beijing_now, description="创建时间")


# ============================================================
# 5. Tool Interface Models
# ============================================================

class SearchQuery(BaseModel):
    """
    Web 搜索查询
    
    支持 Tavily API 的高级参数，用于精确控制搜索行为。
    """
    query: str = Field(..., description="搜索查询字符串")
    search_type: Literal["web", "academic", "video"] = Field(default="web", description="搜索类型")
    max_results: int = Field(default=5, ge=1, le=20, description="最大结果数量")
    
    # 基础参数
    language: Optional[str] = Field(None, description="搜索语言（如 'zh', 'en'），用于优化搜索结果")
    content_type: Optional[str] = Field(None, description="内容类型提示（如 'video', 'article', 'documentation'），用于优化搜索策略")
    
    # Tavily 高级参数
    search_depth: Literal["basic", "advanced"] = Field(
        default="advanced",
        description="搜索深度：basic（快速）或 advanced（高质量，推荐）"
    )
    time_range: Optional[Literal["day", "week", "month", "year"]] = Field(
        None,
        description="时间筛选：day（最近1天）、week（最近1周）、month（最近1月）、year（最近1年）"
    )
    include_domains: Optional[List[str]] = Field(
        None,
        description="优先搜索的域名列表，如 ['github.com', 'stackoverflow.com']"
    )
    exclude_domains: Optional[List[str]] = Field(
        None,
        description="排除的域名列表，如 ['medium.com']（避免低质量内容）"
    )


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
    created_at: datetime = Field(default_factory=beijing_now, description="创建时间")


# --- 批量修改结果 ---

class SingleModificationResult(BaseModel):
    """单个修改结果"""
    modification_type: Literal["tutorial", "resource", "quiz"] = Field(..., description="修改类型")
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


# ============================================================
# 学习进度相关模型
# ============================================================

class ConceptProgressUpdate(BaseModel):
    """标记/取消 Concept 完成状态请求"""
    is_completed: bool = Field(..., description="是否完成")


class ConceptProgressResponse(BaseModel):
    """Concept 进度响应"""
    concept_id: str
    is_completed: bool
    completed_at: Optional[datetime] = None


class QuizAttemptCreate(BaseModel):
    """提交 Quiz 答题记录请求"""
    quiz_id: str
    total_questions: int
    correct_answers: int
    score_percentage: float
    incorrect_question_indices: List[int] = Field(
        default=[],
        description="答错题目的序号列表（从0开始，如 [0, 2, 5] 表示第1、3、6题答错）"
    )


class QuizAttemptResponse(BaseModel):
    """Quiz 答题记录响应"""
    id: str
    quiz_id: str
    concept_id: str
    total_questions: int
    correct_answers: int
    score_percentage: float
    incorrect_question_indices: List[int]
    attempted_at: datetime


# ============================================================
# 7. 伴学Agent相关模型
# ============================================================

class ChatMessageRequest(BaseModel):
    """聊天消息请求"""
    user_id: str = Field(..., description="用户 ID")
    roadmap_id: str = Field(..., description="路线图 ID")
    concept_id: Optional[str] = Field(None, description="当前学习的概念 ID")
    message: str = Field(..., description="用户消息内容")
    session_id: Optional[str] = Field(None, description="会话 ID（新会话时为空）")


class ChatSession(BaseModel):
    """聊天会话"""
    session_id: str
    user_id: str
    roadmap_id: str
    concept_id: Optional[str] = None
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    last_message_preview: Optional[str] = None


class ChatMessage(BaseModel):
    """聊天消息"""
    message_id: str
    session_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    intent_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class LearningNoteCreate(BaseModel):
    """创建学习笔记请求"""
    user_id: str = Field(..., description="用户 ID")
    roadmap_id: str = Field(..., description="路线图 ID")
    concept_id: str = Field(..., description="概念 ID")
    title: Optional[str] = Field(None, description="笔记标题")
    content: str = Field(..., description="笔记内容（Markdown格式）")
    source: Literal["manual", "ai_generated", "chat_extracted"] = Field(
        default="manual", description="笔记来源"
    )
    tags: List[str] = Field(default=[], description="标签列表")


class LearningNote(BaseModel):
    """学习笔记"""
    note_id: str
    user_id: str
    roadmap_id: str
    concept_id: str
    title: Optional[str] = None
    content: str
    source: Literal["manual", "ai_generated", "chat_extracted"]
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime



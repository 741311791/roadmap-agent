"""
工作流基础定义

包含：
- RoadmapState: 工作流全局状态（TypedDict）
- WorkflowConfig: 工作流配置（Pydantic模型）
- merge_dicts: 字典合并reducer函数
- ensure_unique_roadmap_id: 路线图ID唯一性保证
"""
from typing import TypedDict, Annotated
from operator import add
from pydantic import BaseModel
import structlog
import uuid
import re

from app.models.domain import (
    UserRequest,
    IntentAnalysisOutput,
    RoadmapFramework,
    ValidationOutput,
    TutorialGenerationOutput,
    ResourceRecommendationOutput,
    QuizGenerationOutput,
    EditPlan,
)

logger = structlog.get_logger()


def merge_dicts(left: dict, right: dict) -> dict:
    """
    合并字典的 reducer 函数（用于 tutorial_refs、resource_refs、quiz_refs）
    
    LangGraph 最佳实践：使用 reducer 确保状态更新是合并而非覆盖
    """
    return {**left, **right}


class RoadmapState(TypedDict):
    """
    工作流全局状态
    
    LangGraph 最佳实践：
    - 使用 Annotated 配合 reducer 函数来处理列表和字典的更新
    - reducer 函数确保状态更新是追加/合并而非覆盖
    """
    # 输入
    user_request: UserRequest
    task_id: str
    
    # 路线图ID（在需求分析完成后生成）
    roadmap_id: str | None
    
    # 中间产出
    intent_analysis: IntentAnalysisOutput | None
    roadmap_framework: RoadmapFramework | None
    validation_result: ValidationOutput | None
    
    # 内容生成相关（A4: 教程生成器）
    # 使用 merge_dicts reducer 来合并教程引用
    tutorial_refs: Annotated[dict[str, TutorialGenerationOutput], merge_dicts]
    # 使用 add reducer 来追加失败的 concept_id
    failed_concepts: Annotated[list[str], add]
    
    # 资源推荐相关（A5: 资源推荐师）
    resource_refs: Annotated[dict[str, ResourceRecommendationOutput], merge_dicts]
    
    # 测验生成相关（A6: 测验生成器）
    quiz_refs: Annotated[dict[str, QuizGenerationOutput], merge_dicts]
    
    # Celery 异步内容生成状态
    content_generation_status: str | None  # "queued" 表示已发送到 Celery，"completed" 表示已完成
    celery_task_id: str | None  # Celery 任务 ID
    
    # 流程控制
    current_step: str
    modification_count: int
    human_approved: bool
    
    # 人工审核反馈（Human Review 阶段产出）
    user_feedback: str | None  # 用户拒绝时提供的修改反馈
    edit_plan: EditPlan | None  # 解析后的结构化修改计划
    review_feedback_id: str | None  # 用户审核反馈记录ID（关联 HumanReviewFeedback 表）
    edit_plan_record_id: str | None  # 修改计划记录ID（关联 EditPlanRecord 表）
    
    # 编辑来源标记（用于路由决策）
    edit_source: str | None  # "validation_failed" 或 "human_review"
    
    # 验证轮次（用于记录）
    validation_round: int
    
    # 元数据（执行历史）
    execution_history: Annotated[list[str], add]


class WorkflowConfig(BaseModel):
    """
    工作流配置
    
    支持通过环境变量跳过特定节点：
    - skip_structure_validation: 跳过结构验证和编辑循环
    - skip_human_review: 跳过人工审核
    - skip_tutorial_generation: 跳过教程生成
    - skip_resource_recommendation: 跳过资源推荐
    - skip_quiz_generation: 跳过测验生成
    """
    skip_structure_validation: bool = False
    skip_human_review: bool = False
    skip_tutorial_generation: bool = False
    skip_resource_recommendation: bool = False
    skip_quiz_generation: bool = False
    
    max_framework_retry: int = 3
    parallel_tutorial_limit: int = 5
    
    @classmethod
    def from_settings(cls) -> "WorkflowConfig":
        """从全局settings创建配置"""
        from app.config.settings import settings
        return cls(
            skip_structure_validation=settings.SKIP_STRUCTURE_VALIDATION,
            skip_human_review=settings.SKIP_HUMAN_REVIEW,
            skip_tutorial_generation=settings.SKIP_TUTORIAL_GENERATION,
            skip_resource_recommendation=settings.SKIP_RESOURCE_RECOMMENDATION,
            skip_quiz_generation=settings.SKIP_QUIZ_GENERATION,
            max_framework_retry=settings.MAX_FRAMEWORK_RETRY,
            parallel_tutorial_limit=settings.PARALLEL_TUTORIAL_LIMIT,
        )


async def ensure_unique_roadmap_id(roadmap_id: str, repo) -> str:
    """
    确保 roadmap_id 在数据库中是唯一的
    
    如果 roadmap_id 已存在，则重新生成后缀直到唯一。
    
    Args:
        roadmap_id: IntentAnalyzerAgent 生成的 roadmap_id
        repo: RoadmapRepository 实例
        
    Returns:
        唯一的 roadmap_id
    """
    # 检查是否已存在
    if not await repo.roadmap_id_exists(roadmap_id):
        logger.debug(
            "roadmap_id_unique",
            roadmap_id=roadmap_id,
        )
        return roadmap_id
    
    # 提取基础部分和后缀（假设格式为 xxx-xxx-xxxxxxxx）
    # 找到最后一个 8 位字母数字后缀
    pattern = r'^(.+)-([a-z0-9]{8})$'
    match = re.match(pattern, roadmap_id)
    
    if match:
        base_part = match.group(1)  # 例如 "python-web-development"
    else:
        # 如果格式不符合预期，使用整个 roadmap_id 作为基础
        base_part = roadmap_id.rsplit('-', 1)[0] if '-' in roadmap_id else roadmap_id
    
    # 重新生成后缀直到唯一
    max_attempts = 10
    for attempt in range(max_attempts):
        new_suffix = uuid.uuid4().hex[:8]
        new_roadmap_id = f"{base_part}-{new_suffix}"
        
        if not await repo.roadmap_id_exists(new_roadmap_id):
            logger.info(
                "roadmap_id_regenerated",
                original=roadmap_id,
                new=new_roadmap_id,
                attempt=attempt + 1,
            )
            return new_roadmap_id
    
    # 如果 10 次都失败，使用完全随机的后缀
    fallback_id = f"{base_part}-{uuid.uuid4().hex[:12]}"
    logger.warning(
        "roadmap_id_fallback",
        original=roadmap_id,
        fallback=fallback_id,
        reason="max_attempts_exceeded",
    )
    return fallback_id


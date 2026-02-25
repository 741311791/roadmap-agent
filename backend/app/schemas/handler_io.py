"""
Handler 输入输出 Schemas

定义所有 Handler 的强类型输入输出模型，提供类型安全和验证。
"""
from pydantic import BaseModel, Field
from typing import Optional
from app.models.domain import (
    IntentAnalysisOutput,
    RoadmapFramework,
    ValidationOutput,
    EditPlanAnalyzerOutput,
    RoadmapEditOutput,
    TutorialGenerationOutput,
    ResourceRecommendationOutput,
    QuizGenerationOutput,
)


# ============================================================
# Handler Input Schemas
# ============================================================


class IntentAnalysisHandlerInput(BaseModel):
    """
    意图分析 Handler 输入
    
    字段来源：intent_analysis_node 返回值
    """
    intent_analysis: IntentAnalysisOutput = Field(..., description="意图分析结果")
    roadmap_id: str = Field(..., description="路线图ID")
    user_id: str = Field(..., description="用户ID")


class CurriculumDesignHandlerInput(BaseModel):
    """
    课程设计 Handler 输入
    
    字段来源：curriculum_design_node 返回值
    """
    roadmap_framework: RoadmapFramework = Field(..., description="路线图框架")
    roadmap_id: str = Field(..., description="路线图ID")
    user_id: str = Field(..., description="用户ID")


class ValidationHandlerInput(BaseModel):
    """
    验证 Handler 输入
    
    字段来源：structure_validation_node 返回值
    """
    validation_result: ValidationOutput = Field(..., description="验证结果")
    roadmap_id: str = Field(..., description="路线图ID")
    validation_round: int = Field(default=1, description="验证轮次")


class EditPlanHandlerInput(BaseModel):
    """
    修改计划分析 Handler 输入（共享节点，支持两种触发来源）
    
    触发来源：
    1. human_review 拒绝 → edit_source="human_review"
    2. structure_validation 失败 → edit_source="validation_failed"
    
    字段来源：edit_plan_analysis_node 返回值
    """
    edit_plan: EditPlanAnalyzerOutput = Field(..., description="修改计划")
    user_feedback: Optional[str] = Field(None, description="用户反馈或验证问题摘要")
    roadmap_id: str = Field(..., description="路线图ID")
    user_id: str = Field(..., description="用户ID")
    approved: bool = Field(..., description="是否批准（始终为False，因为触发修改意味着未批准）")
    roadmap_version_snapshot: dict = Field(..., description="路线图框架快照")
    review_round: int = Field(default=1, description="审核轮次")


# ✅ 移除：ValidationEditPlanHandlerInput（使用共享的EditPlanHandlerInput）


class EditorHandlerInput(BaseModel):
    """
    编辑 Handler 输入
    
    字段来源：roadmap_edit_node 返回值
    """
    modified_framework: RoadmapFramework = Field(..., description="修改后的框架")
    origin_framework: Optional[RoadmapFramework] = Field(None, description="原始框架")
    roadmap_id: str = Field(..., description="路线图ID")
    user_id: str = Field(..., description="用户ID")
    edit_round: int = Field(default=1, description="编辑轮次")


class ReviewHandlerInput(BaseModel):
    """
    人工审核 Handler 输入
    
    字段来源：human_review_node 返回值
    """
    human_approved: bool = Field(..., description="是否批准")
    roadmap_id: str = Field(..., description="路线图ID")
    user_feedback: Optional[str] = Field(None, description="用户反馈（拒绝时）")


class ContentHandlerInput(BaseModel):
    """
    内容生成 Handler 输入（重构版 - 两层 Fan-Out/Fan-In 架构）
    
    字段来源：content_generation_node 返回值（通过子图）
    """
    concept_results: list[dict] = Field(..., description="所有 Concept 的保存结果")
    roadmap_id: str = Field(..., description="路线图ID")


# ============================================================
# Handler Output Schemas
# ============================================================


class ConceptContentSaveResult(BaseModel):
    """
    单个 Concept 内容保存结果
    
    由 ConceptContentHandler.save_concept_content 返回
    """
    concept_id: str = Field(..., description="Concept ID")
    
    # Tutorial 状态
    tutorial: str = Field(..., description="教程保存状态: success | failed | skipped")
    tutorial_output: Optional[dict] = Field(None, description="教程生成输出（序列化）")
    
    # Resource 状态
    resource: str = Field(..., description="资源保存状态: success | failed | skipped")
    resource_output: Optional[dict] = Field(None, description="资源推荐输出（序列化）")
    
    # Quiz 状态
    quiz: str = Field(..., description="测验保存状态: success | failed | skipped")
    quiz_output: Optional[dict] = Field(None, description="测验生成输出（序列化）")
    
    # 总体状态
    metadata_saved: bool = Field(..., description="是否所有元数据都已保存")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "concept_id": "roadmap-123:c-1-1-1",
                "tutorial": "success",
                "tutorial_output": {
                    "tutorial_id": "tut-456",
                    "title": "Python 基础",
                    "summary": "学习 Python 基本语法",
                },
                "resource": "success",
                "resource_output": {
                    "id": "res-789",
                    "resources": [],
                },
                "quiz": "success",
                "quiz_output": {
                    "quiz_id": "quiz-012",
                    "questions": [],
                },
                "metadata_saved": True,
            }
        }
    }


"""
技术评估相关Schemas

包含数据库CRUD Schema和API端点Schema
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================
# 数据库 CRUD Schemas（原有）
# ============================================================

class TechAssessmentCreate(BaseModel):
    """技术评估创建Schema"""
    user_id: str = Field(..., description="用户ID")
    technology: str = Field(..., description="技术名称")
    questions: list[dict] = Field(..., description="评估问题列表")


class TechAssessmentSubmit(BaseModel):
    """技术评估提交Schema"""
    assessment_id: str = Field(..., description="评估ID")
    answers: dict = Field(..., description="用户答案")


class TechAssessmentResponse(BaseModel):
    """技术评估响应"""
    assessment_id: str = Field(..., description="评估ID")
    user_id: str = Field(..., description="用户ID")
    technology: str = Field(..., description="技术名称")
    questions: list[dict] = Field(..., description="评估问题列表")
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TechAssessmentResult(BaseModel):
    """技术评估结果"""
    assessment_id: str = Field(..., description="评估ID")
    score: int = Field(..., description="分数")
    total: int = Field(..., description="总分")
    level: str = Field(..., description="水平等级: beginner/intermediate/advanced")
    feedback: dict = Field(..., description="详细反馈")
    recommendations: list[str] = Field(..., description="学习建议")
    completed_at: datetime


# ============================================================
# API 端点 Schemas（新增）
# ============================================================

class QuestionResponse(BaseModel):
    """题目响应模型"""
    question: str = Field(..., description="题目内容")
    type: str = Field(..., description="题目类型: single_choice, multiple_choice, true_false")
    options: List[str] = Field(..., description="选项列表")
    proficiency_level: Optional[str] = Field(None, description="题目来源级别: beginner, intermediate, expert")


class AssessmentResponse(BaseModel):
    """测验响应模型"""
    assessment_id: str
    technology: str
    proficiency_level: str
    questions: List[QuestionResponse]
    total_questions: int


class EvaluateRequest(BaseModel):
    """评估请求模型"""
    assessment_id: str = Field(..., description="测验ID（前端获取题目时返回的ID）")
    answers: List[str] = Field(..., description="用户的答案列表（按题目顺序）")


class EvaluationResult(BaseModel):
    """评估结果模型"""
    score: int = Field(..., description="得分")
    max_score: int = Field(..., description="总分")
    percentage: float = Field(..., description="正确率百分比")
    correct_count: int = Field(..., description="答对题数")
    total_questions: int = Field(..., description="题目总数")
    recommendation: str = Field(..., description="建议: confirmed, adjust, downgrade")
    message: str = Field(..., description="建议说明")


class KnowledgeGap(BaseModel):
    """知识缺口模型"""
    topic: str = Field(..., description="主题名称")
    description: str = Field(..., description="详细说明")
    priority: str = Field(..., description="优先级: high/medium/low")
    recommendations: List[str] = Field(..., description="学习建议列表")


class ProficiencyVerification(BaseModel):
    """能力级别验证模型"""
    claimed_level: str = Field(..., description="声称的能力级别")
    verified_level: str = Field(..., description="验证的实际能力级别")
    confidence: str = Field(..., description="置信度: high/medium/low")
    reasoning: str = Field(..., description="判定依据")


class ScoreBreakdownItem(BaseModel):
    """分数细分项"""
    correct: int = Field(..., description="答对题数")
    total: int = Field(..., description="总题数")
    percentage: float = Field(..., description="正确率百分比")


class CapabilityAnalysisResult(BaseModel):
    """能力分析结果模型"""
    technology: str = Field(..., description="技术栈名称")
    proficiency_level: str = Field(..., description="声称的能力级别")
    overall_assessment: str = Field(..., description="整体评价")
    strengths: List[str] = Field(..., description="优势领域列表")
    weaknesses: List[str] = Field(..., description="薄弱点列表")
    knowledge_gaps: List[KnowledgeGap] = Field(..., description="知识缺口列表")
    learning_suggestions: List[str] = Field(..., description="学习建议列表")
    proficiency_verification: ProficiencyVerification = Field(..., description="能力级别验证")
    score_breakdown: Dict[str, ScoreBreakdownItem] = Field(..., description="各难度得分情况")


class AnalyzeCapabilityRequest(BaseModel):
    """能力分析请求模型"""
    user_id: str = Field(..., description="用户ID")
    assessment_id: str = Field(..., description="测验ID")
    answers: List[str] = Field(..., description="用户的答案列表（按题目顺序）")
    save_to_profile: bool = Field(default=True, description="是否保存到用户画像")


class CustomTechAssessmentRequest(BaseModel):
    """自定义技能测验请求模型"""
    technology: str = Field(..., description="自定义技术栈名称")
    proficiency: str = Field(..., description="能力级别")


class CustomAssessmentResponse(BaseModel):
    """自定义测验响应模型"""
    status: str = Field(..., description="generation_started | ready")
    message: str
    assessment: Optional[AssessmentResponse] = None


class AvailableTechnologiesResponse(BaseModel):
    """可用技术栈列表响应模型"""
    technologies: List[str] = Field(..., description="技术栈名称列表")
    count: int = Field(..., description="技术栈总数")


class AnalyzeTaskResponse(BaseModel):
    """能力分析任务触发响应模型"""
    status: str = Field(..., description="任务状态: processing")
    task_id: str = Field(..., description="Celery任务ID")
    message: str = Field(..., description="提示消息")
    technology: str = Field(..., description="技术栈名称")
    proficiency: str = Field(..., description="能力级别")


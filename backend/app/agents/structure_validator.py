"""
Structure Validator Agent（结构审查员）
"""
import json
from typing import List
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent
from app.models.domain import (
    RoadmapFramework,
    LearningPreferences,
    ValidationOutput,
    ValidationInput,
    ValidationIssue,
    DimensionScore,
    StructuralSuggestion,
)
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class LLMSemanticEvaluation(BaseModel):
    """LLM 语义评估输出（中间模型）"""
    dimension_scores: List[DimensionScore] = Field(..., description="各维度评分")
    issues: List[ValidationIssue] = Field(default=[], description="发现的问题")
    improvement_suggestions: List[StructuralSuggestion] = Field(default=[], description="改进建议")


class StructureValidatorAgent(BaseAgent):
    """
    结构审查员 Agent
    
    配置从环境变量加载：
    - VALIDATOR_PROVIDER: 模型提供商（默认: openai）
    - VALIDATOR_MODEL: 模型名称（默认: gpt-4o-mini）
    - VALIDATOR_BASE_URL: 自定义 API 端点（可选）
    - VALIDATOR_API_KEY: API 密钥（必需）
    """
    
    def __init__(
        self,
        agent_id: str = "structure_validator",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.VALIDATOR_PROVIDER,
            model_name=model_name or settings.VALIDATOR_MODEL,
            base_url=base_url or settings.VALIDATOR_BASE_URL,
            api_key=api_key or settings.VALIDATOR_API_KEY,
            temperature=0.2,  # 低温度，确保审查的严谨性
            max_tokens=8000,
        )
    
    def _get_required_constraints(self) -> list[str]:
        """结构验证器需要的约束"""
        from app.models.domain import ConstraintNames
        return [
            # 通用约束
            ConstraintNames.LANGUAGE,
            ConstraintNames.USER_GOAL,
            ConstraintNames.USER_PROFILE,
            # 特定约束
            ConstraintNames.DIFFICULTY,
            ConstraintNames.TIME_CONSTRAINT,
            ConstraintNames.SKILL_GAP,
        ]
    
    async def validate(
        self,
        framework: RoadmapFramework,
        user_preferences: LearningPreferences,
    ) -> ValidationOutput:
        """
        验证路线图结构和质量
        
        流程：
        1. Python 前置检查（硬性规则）
        2. LLM 语义评估（量化打分）
        3. Python 计算总分和判定是否通过
        
        Args:
            framework: 待验证的路线图框架
            user_preferences: 用户偏好
            
        Returns:
            验证结果
        """
        # === Step 1: Python 前置检查 ===
        structure_valid, structure_issues = framework.validate_structure()
        
        # 如果结构检查失败，直接返回（不调用 LLM）
        if not structure_valid:
            logger.warning(
                "structure_validation_failed_at_python_check",
                roadmap_id=framework.roadmap_id,
                roadmap_title=framework.title,
                issues_count=len(structure_issues),
                critical_issues=[
                    {"location": issue.location, "issue": issue.issue}
                    for issue in structure_issues[:5]
                ],
            )
            
            return ValidationOutput(
                dimension_scores=[],
                issues=structure_issues,
                improvement_suggestions=[],
                overall_score=0.0,
                is_valid=False,
                validation_summary=f"Structure validation failed: {len(structure_issues)} critical issues found"
            )
        
        # === Step 2: 调用 LLM 进行语义评估 ===
        system_prompt = self._load_system_prompt(
            "structure_validator.j2",
            user_preferences=user_preferences,
            framework=framework,
        )
        
        # 构建用户消息
        user_message = f"""
请仔细审查以下学习路线图框架：

**路线图结构（完整 JSON）**:
{json.dumps(framework.model_dump(mode='json'), ensure_ascii=False, indent=2)}

请严格按照系统提示中定义的 5 个维度进行评估，并返回 JSON 格式的结果。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # 使用 instructor 调用 LLM，自动验证和重试
        logger.info(
            "llm_evaluation_started",
            roadmap_id=framework.roadmap_id,
            model=self.model_name,
        )
        
        llm_output = await self._call_llm(
            messages,
            response_model=LLMSemanticEvaluation
        )
        
        logger.info(
            "llm_evaluation_success",
            roadmap_id=framework.roadmap_id,
            dimension_scores_count=len(llm_output.dimension_scores),
            issues_count=len(llm_output.issues),
        )
        
        # === Step 3: Python 计算总分和最终判定 ===
        all_issues = structure_issues + llm_output.issues
        
        overall_score = self._calculate_overall_score(
            llm_output.dimension_scores,
            all_issues
        )
        
        is_valid = self._determine_validity(all_issues)
        
        validation_summary = self._generate_summary(
            llm_output.dimension_scores,
            all_issues,
            overall_score,
            is_valid
        )
        
        # 组装最终结果
        result = ValidationOutput(
            dimension_scores=llm_output.dimension_scores,
            issues=all_issues,
            improvement_suggestions=llm_output.improvement_suggestions,
            overall_score=overall_score,
            is_valid=is_valid,
            validation_summary=validation_summary
        )
        
        # 记录验证结果
        self._log_validation_result(framework, result)
        
        return result
    
    def _calculate_overall_score(
        self, 
        dimension_scores: List[DimensionScore],
        issues: List[ValidationIssue]
    ) -> float:
        """
        计算加权总分
        
        公式：
        1. 基础分 = 5个维度分数的加权平均
           - knowledge_completeness: 30%
           - knowledge_progression: 25%
           - stage_coherence: 20%
           - module_clarity: 15%
           - user_alignment: 10%
        2. 惩罚分 = critical问题数 * 10 + warning问题数 * 5
        3. 总分 = max(0, 基础分 - 惩罚分)
        
        Args:
            dimension_scores: 各维度评分
            issues: 问题列表
            
        Returns:
            总分（0-100）
        """
        # 如果没有维度评分（结构检查失败），返回 0
        if not dimension_scores:
            return 0.0
        
        # 维度权重
        weights = {
            "knowledge_completeness": 0.30,
            "knowledge_progression": 0.25,
            "stage_coherence": 0.20,
            "module_clarity": 0.15,
            "user_alignment": 0.10,
        }
        
        # 计算基础分
        base_score = 0.0
        for score in dimension_scores:
            weight = weights.get(score.dimension, 0.0)
            base_score += score.score * weight
        
        # 计算惩罚分
        penalty = 0.0
        for issue in issues:
            if issue.severity == "critical":
                penalty += 10.0
            elif issue.severity == "warning":
                penalty += 5.0
        
        # 计算总分
        final_score = max(0.0, base_score - penalty)
        
        return round(final_score, 1)
    
    def _determine_validity(self, issues: List[ValidationIssue]) -> bool:
        """
        判定是否通过验证
        
        规则：仅当有 critical 问题时才失败
        （warning 不影响通过与否）
        
        Args:
            issues: 问题列表
            
        Returns:
            是否通过验证
        """
        return not any(issue.severity == "critical" for issue in issues)
    
    def _generate_summary(
        self,
        dimension_scores: List[DimensionScore],
        issues: List[ValidationIssue],
        overall_score: float,
        is_valid: bool
    ) -> str:
        """
        生成人类可读的验证摘要
        
        Args:
            dimension_scores: 各维度评分
            issues: 问题列表
            overall_score: 总分
            is_valid: 是否通过
            
        Returns:
            验证摘要字符串
        """
        critical_count = sum(1 for i in issues if i.severity == "critical")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        
        if is_valid:
            if warning_count > 0:
                return f"Validation passed with score {overall_score:.1f}/100. Found {warning_count} warnings."
            else:
                return f"Validation passed with score {overall_score:.1f}/100. No issues found."
        else:
            return f"Validation failed with {critical_count} critical issues (score: {overall_score:.1f}/100)."
    
    def _log_validation_result(
        self,
        framework: RoadmapFramework,
        result: ValidationOutput
    ) -> None:
        """
        记录验证结果
        
        Args:
            framework: 路线图框架
            result: 验证结果
        """
        log_data = {
            "roadmap_id": framework.roadmap_id,
            "roadmap_title": framework.title,
            "stages_count": len(framework.stages),
            "total_hours": framework.total_estimated_hours,
            "is_valid": result.is_valid,
            "overall_score": result.overall_score,
            "issues_count": len(result.issues),
            "validation_summary": result.validation_summary,
        }
        
        # 添加维度评分
        if result.dimension_scores:
            log_data["dimension_scores"] = {
                score.dimension: score.score
                for score in result.dimension_scores
            }
        
        if result.is_valid:
            # 验证通过
            logger.info("structure_validation_completed", **log_data)
        else:
            # 验证失败：记录详细的失败原因
            critical_issues = [issue for issue in result.issues if issue.severity == "critical"]
            warning_issues = [issue for issue in result.issues if issue.severity == "warning"]
            
            log_data.update({
                "critical_issues_count": len(critical_issues),
                "warning_issues_count": len(warning_issues),
                "critical_issues": [
                    {
                        "category": issue.category,
                        "location": issue.location,
                        "issue": issue.issue[:200] + "..." if len(issue.issue) > 200 else issue.issue,
                    }
                    for issue in critical_issues[:5]  # 最多记录5个严重问题
                ],
            })
            
            logger.warning(
                "structure_validation_failed",
                **log_data,
            )
    
    async def execute(self, input_data: ValidationInput) -> ValidationOutput:
        """实现基类的抽象方法"""
        return await self.validate(
            framework=input_data.framework,
            user_preferences=input_data.user_preferences,
        )

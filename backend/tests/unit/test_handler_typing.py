"""
Handler 类型化重构单元测试

验证：
1. Handler Input Schema 验证
2. 基类自动类型转换
3. ConceptContentSaveResult 强类型返回
"""
import pytest
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock

from app.schemas.handler_io import (
    IntentAnalysisHandlerInput,
    CurriculumDesignHandlerInput,
    ValidationHandlerInput,
    EditPlanHandlerInput,
    # ✅ 移除：ValidationEditPlanHandlerInput（使用共享的EditPlanHandlerInput）
    EditorHandlerInput,
    ReviewHandlerInput,
    ContentHandlerInput,
    ConceptContentSaveResult,
)
from app.models.domain import (
    IntentAnalysisOutput,
    RoadmapFramework,
    ValidationOutput,
    EditPlanAnalyzerOutput,
    Stage,
    Module,
    Concept,
)


class TestHandlerInputValidation:
    """测试 Handler 输入验证"""
    
    def test_intent_analysis_handler_input_valid(self):
        """测试意图分析 Handler 输入验证 - 有效数据"""
        # 创建模拟的 IntentAnalysisOutput
        intent_output = IntentAnalysisOutput(
            roadmap_id="test-roadmap",
            parsed_goal="Learn Python",
            key_technologies=["Python"],
            difficulty_profile="beginner",
            time_constraint="10 hours/week",
            recommended_focus=["fundamentals", "syntax"],
        )
        
        # 验证有效输入
        input_data = {
            "intent_analysis": intent_output,
            "roadmap_id": "test-roadmap",
            "user_id": "test-user",
        }
        
        result = IntentAnalysisHandlerInput.model_validate(input_data)
        assert result.roadmap_id == "test-roadmap"
        assert result.user_id == "test-user"
        assert result.intent_analysis.parsed_goal == "Learn Python"
    
    def test_intent_analysis_handler_input_missing_field(self):
        """测试意图分析 Handler 输入验证 - 缺少必填字段"""
        intent_output = IntentAnalysisOutput(
            roadmap_id="test-roadmap",
            parsed_goal="Learn Python",
            key_technologies=["Python"],
            difficulty_profile="beginner",
            time_constraint="10 hours/week",
            recommended_focus=["fundamentals", "syntax"],
        )
        
        # 缺少 roadmap_id
        invalid_input = {
            "intent_analysis": intent_output,
            "user_id": "test-user",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            IntentAnalysisHandlerInput.model_validate(invalid_input)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("roadmap_id",) for error in errors)
    
    def test_curriculum_design_handler_input_valid(self):
        """测试课程设计 Handler 输入验证 - 有效数据"""
        framework = RoadmapFramework(
            roadmap_id="test-roadmap",
            title="Test Roadmap",
            total_estimated_hours=10.0,
            recommended_completion_weeks=2,
            stages=[
                Stage(
                    stage_id="stage-1",
                    name="Stage 1",
                    description="Test Stage",
                    order=1,
                    modules=[
                        Module(
                            module_id="module-1",
                            name="Module 1",
                            description="Test Module",
                            concepts=[
                                Concept(
                                    concept_id="concept-1",
                                    name="Concept 1",
                                    description="Test Concept",
                                    estimated_hours=2.0,
                                )
                            ],
                        )
                    ],
                )
            ],
        )
        
        input_data = {
            "roadmap_framework": framework,
            "roadmap_id": "test-roadmap",
            "user_id": "test-user",
        }
        
        result = CurriculumDesignHandlerInput.model_validate(input_data)
        assert result.roadmap_id == "test-roadmap"
        assert result.user_id == "test-user"
        assert len(result.roadmap_framework.stages) == 1
    
    def test_validation_handler_input_valid(self):
        """测试验证 Handler 输入验证 - 有效数据"""
        validation_output = ValidationOutput(
            is_valid=True,
            overall_score=90.0,
            issues=[],
            dimension_scores=[],
            improvement_suggestions=[],
            validation_summary="Valid",
        )
        
        input_data = {
            "validation_result": validation_output,
            "roadmap_id": "test-roadmap",
            "validation_round": 1,
        }
        
        result = ValidationHandlerInput.model_validate(input_data)
        assert result.roadmap_id == "test-roadmap"
        assert result.validation_round == 1
        assert result.validation_result.is_valid is True
    
    def test_validation_handler_input_default_round(self):
        """测试验证 Handler 输入验证 - 默认轮次"""
        validation_output = ValidationOutput(
            is_valid=True,
            overall_score=90.0,
            issues=[],
            dimension_scores=[],
            improvement_suggestions=[],
            validation_summary="Valid",
        )
        
        input_data = {
            "validation_result": validation_output,
            "roadmap_id": "test-roadmap",
            # validation_round 未提供，应使用默认值 1
        }
        
        result = ValidationHandlerInput.model_validate(input_data)
        assert result.validation_round == 1
    
    def test_content_handler_input_valid(self):
        """测试内容生成 Handler 输入验证 - 有效数据"""
        concept_results = [
            {
                "save_status": {
                    "concept_id": "concept-1",
                    "tutorial": "success",
                    "resource": "success",
                    "quiz": "success",
                    "metadata_saved": True,
                }
            },
            {
                "save_status": {
                    "concept_id": "concept-2",
                    "tutorial": "failed",
                    "resource": "success",
                    "quiz": "success",
                    "metadata_saved": False,
                }
            },
        ]
        
        input_data = {
            "concept_results": concept_results,
            "roadmap_id": "test-roadmap",
        }
        
        result = ContentHandlerInput.model_validate(input_data)
        assert result.roadmap_id == "test-roadmap"
        assert len(result.concept_results) == 2


class TestConceptContentSaveResult:
    """测试 ConceptContentSaveResult 强类型返回"""
    
    def test_concept_content_save_result_all_success(self):
        """测试所有内容保存成功"""
        result = ConceptContentSaveResult(
            concept_id="concept-1",
            tutorial="success",
            tutorial_output={"tutorial_id": "tut-1", "title": "Test"},
            resource="success",
            resource_output={"id": "res-1", "resources": []},
            quiz="success",
            quiz_output={"quiz_id": "quiz-1", "questions": []},
            metadata_saved=True,
        )
        
        assert result.concept_id == "concept-1"
        assert result.tutorial == "success"
        assert result.resource == "success"
        assert result.quiz == "success"
        assert result.metadata_saved is True
    
    def test_concept_content_save_result_partial_failure(self):
        """测试部分内容保存失败"""
        result = ConceptContentSaveResult(
            concept_id="concept-2",
            tutorial="failed",
            tutorial_output=None,
            resource="success",
            resource_output={"id": "res-2", "resources": []},
            quiz="success",
            quiz_output={"quiz_id": "quiz-2", "questions": []},
            metadata_saved=False,
        )
        
        assert result.tutorial == "failed"
        assert result.tutorial_output is None
        assert result.resource == "success"
        assert result.metadata_saved is False
    
    def test_concept_content_save_result_all_skipped(self):
        """测试所有内容跳过"""
        result = ConceptContentSaveResult(
            concept_id="concept-3",
            tutorial="skipped",
            tutorial_output=None,
            resource="skipped",
            resource_output=None,
            quiz="skipped",
            quiz_output=None,
            metadata_saved=False,
        )
        
        assert result.tutorial == "skipped"
        assert result.resource == "skipped"
        assert result.quiz == "skipped"
        assert result.metadata_saved is False
    
    def test_concept_content_save_result_serialization(self):
        """测试序列化为 dict"""
        result = ConceptContentSaveResult(
            concept_id="concept-4",
            tutorial="success",
            tutorial_output={"tutorial_id": "tut-4"},
            resource="success",
            resource_output={"id": "res-4"},
            quiz="success",
            quiz_output={"quiz_id": "quiz-4"},
            metadata_saved=True,
        )
        
        result_dict = result.model_dump()
        assert isinstance(result_dict, dict)
        assert result_dict["concept_id"] == "concept-4"
        assert result_dict["tutorial"] == "success"
        assert result_dict["metadata_saved"] is True


class TestHandlerInputEdgeCases:
    """测试 Handler 输入边界情况"""
    
    def test_review_handler_input_with_feedback(self):
        """测试审核 Handler - 带用户反馈"""
        input_data = {
            "human_approved": False,
            "roadmap_id": "test-roadmap",
            "user_feedback": "Please add more details",
        }
        
        result = ReviewHandlerInput.model_validate(input_data)
        assert result.human_approved is False
        assert result.user_feedback == "Please add more details"
    
    def test_review_handler_input_without_feedback(self):
        """测试审核 Handler - 无用户反馈"""
        input_data = {
            "human_approved": True,
            "roadmap_id": "test-roadmap",
            # user_feedback 为可选
        }
        
        result = ReviewHandlerInput.model_validate(input_data)
        assert result.human_approved is True
        assert result.user_feedback is None
    
    def test_editor_handler_input_default_edit_round(self):
        """测试编辑 Handler - 默认编辑轮次"""
        framework = RoadmapFramework(
            roadmap_id="test-roadmap",
            title="Test",
            stages=[],
            total_estimated_hours=10.0,
            recommended_completion_weeks=2,
        )
        
        input_data = {
            "modified_framework": framework,
            "roadmap_id": "test-roadmap",
            "user_id": "test-user",
            # edit_round 未提供，应使用默认值 1
        }
        
        result = EditorHandlerInput.model_validate(input_data)
        assert result.edit_round == 1
    
    def test_editor_handler_input_with_origin_framework(self):
        """测试编辑 Handler - 带原始框架"""
        modified_framework = RoadmapFramework(
            roadmap_id="test-roadmap",
            title="Modified",
            stages=[],
            total_estimated_hours=10.0,
            recommended_completion_weeks=2,
        )
        origin_framework = RoadmapFramework(
            roadmap_id="test-roadmap",
            title="Original",
            stages=[],
            total_estimated_hours=10.0,
            recommended_completion_weeks=2,
        )
        
        input_data = {
            "modified_framework": modified_framework,
            "origin_framework": origin_framework,
            "roadmap_id": "test-roadmap",
            "user_id": "test-user",
            "edit_round": 2,
        }
        
        result = EditorHandlerInput.model_validate(input_data)
        assert result.modified_framework.title == "Modified"
        assert result.origin_framework.title == "Original"
        assert result.edit_round == 2


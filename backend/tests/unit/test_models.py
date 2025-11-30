"""
领域模型单元测试

测试 app.models.domain 中的所有 Pydantic 模型验证逻辑。
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.domain import (
    LearningPreferences,
    UserRequest,
    Concept,
    Module,
    Stage,
    RoadmapFramework,
    IntentAnalysisOutput,
    CurriculumDesignOutput,
    ValidationInput,
    ValidationIssue,
    ValidationOutput,
    RoadmapEditInput,
    RoadmapEditOutput,
    TutorialGenerationInput,
    TutorialGenerationOutput,
    SearchQuery,
    SearchResult,
    S3UploadRequest,
    S3UploadResult,
)


class TestLearningPreferences:
    """学习偏好模型测试"""
    
    def test_valid_preferences(self):
        """测试有效的学习偏好"""
        prefs = LearningPreferences(
            learning_goal="学习 Python 编程",
            available_hours_per_week=10,
            motivation="兴趣",
            current_level="beginner",
            career_background="学生",
        )
        assert prefs.learning_goal == "学习 Python 编程"
        assert prefs.available_hours_per_week == 10
        assert prefs.current_level == "beginner"
    
    def test_hours_validation_min(self):
        """测试每周小时数最小值验证"""
        with pytest.raises(ValidationError) as exc_info:
            LearningPreferences(
                learning_goal="学习编程",
                available_hours_per_week=0,  # 小于最小值 1
                motivation="兴趣",
                current_level="beginner",
                career_background="学生",
            )
        assert "greater than or equal to 1" in str(exc_info.value)
    
    def test_hours_validation_max(self):
        """测试每周小时数最大值验证"""
        with pytest.raises(ValidationError) as exc_info:
            LearningPreferences(
                learning_goal="学习编程",
                available_hours_per_week=200,  # 大于最大值 168
                motivation="兴趣",
                current_level="beginner",
                career_background="学生",
            )
        assert "less than or equal to 168" in str(exc_info.value)
    
    def test_invalid_current_level(self):
        """测试无效的当前水平"""
        with pytest.raises(ValidationError):
            LearningPreferences(
                learning_goal="学习编程",
                available_hours_per_week=10,
                motivation="兴趣",
                current_level="expert",  # 无效值
                career_background="学生",
            )
    
    def test_datetime_serialization(self):
        """测试日期时间序列化"""
        deadline = datetime(2025, 12, 31, 23, 59, 59)
        prefs = LearningPreferences(
            learning_goal="学习编程",
            available_hours_per_week=10,
            motivation="兴趣",
            current_level="beginner",
            career_background="学生",
            target_deadline=deadline,
        )
        # 使用 model_dump(mode='json') 序列化
        data = prefs.model_dump(mode='json')
        assert data["target_deadline"] == "2025-12-31T23:59:59"


class TestConcept:
    """概念模型测试"""
    
    def test_valid_concept(self):
        """测试有效的概念"""
        concept = Concept(
            concept_id="c1",
            name="HTML 基础",
            description="学习 HTML 标签",
            estimated_hours=4.0,
        )
        assert concept.concept_id == "c1"
        assert concept.difficulty == "medium"  # 默认值
        assert concept.content_status == "pending"  # 默认值
    
    def test_estimated_hours_min(self):
        """测试预估小时数最小值"""
        with pytest.raises(ValidationError):
            Concept(
                concept_id="c1",
                name="Test",
                description="Test",
                estimated_hours=0.1,  # 小于最小值 0.5
            )
    
    def test_concept_with_prerequisites(self):
        """测试带前置概念的概念"""
        concept = Concept(
            concept_id="c2",
            name="CSS 样式",
            description="学习 CSS",
            estimated_hours=5.0,
            prerequisites=["c1"],
        )
        assert concept.prerequisites == ["c1"]
    
    def test_content_status_literal(self):
        """测试内容状态枚举"""
        concept = Concept(
            concept_id="c1",
            name="Test",
            description="Test",
            estimated_hours=1.0,
            content_status="completed",
        )
        assert concept.content_status == "completed"


class TestModule:
    """模块模型测试"""
    
    def test_valid_module(self, sample_concept):
        """测试有效的模块"""
        module = Module(
            module_id="m1",
            name="Web 基础",
            description="Web 开发基础",
            concepts=[sample_concept],
        )
        assert module.module_id == "m1"
        assert len(module.concepts) == 1
    
    def test_module_total_hours(self):
        """测试模块总小时数计算"""
        concepts = [
            Concept(concept_id="c1", name="C1", description="D1", estimated_hours=2.0),
            Concept(concept_id="c2", name="C2", description="D2", estimated_hours=3.0),
        ]
        module = Module(
            module_id="m1",
            name="Test",
            description="Test",
            concepts=concepts,
        )
        assert module.total_hours == 5.0
    
    def test_module_requires_at_least_one_concept(self):
        """测试模块至少需要一个概念"""
        with pytest.raises(ValidationError):
            Module(
                module_id="m1",
                name="Test",
                description="Test",
                concepts=[],  # 空列表
            )


class TestStage:
    """阶段模型测试"""
    
    def test_valid_stage(self, sample_module):
        """测试有效的阶段"""
        stage = Stage(
            stage_id="s1",
            name="前端基础",
            description="学习前端",
            order=1,
            modules=[sample_module],
        )
        assert stage.stage_id == "s1"
        assert stage.order == 1
    
    def test_stage_order_min(self):
        """测试阶段顺序最小值"""
        with pytest.raises(ValidationError):
            Stage(
                stage_id="s1",
                name="Test",
                description="Test",
                order=0,  # 小于最小值 1
                modules=[],
            )


class TestRoadmapFramework:
    """路线图框架模型测试"""
    
    def test_valid_framework(self, sample_roadmap_framework):
        """测试有效的路线图框架"""
        assert sample_roadmap_framework.roadmap_id == "roadmap-001"
        assert len(sample_roadmap_framework.stages) == 1
    
    def test_validate_structure_valid(self, sample_roadmap_framework):
        """测试结构验证 - 有效"""
        assert sample_roadmap_framework.validate_structure() is True
    
    def test_validate_structure_invalid_prerequisite(self):
        """测试结构验证 - 无效前置关系"""
        concept = Concept(
            concept_id="c1",
            name="Test",
            description="Test",
            estimated_hours=1.0,
            prerequisites=["non_existent"],  # 不存在的前置概念
        )
        module = Module(
            module_id="m1",
            name="Test",
            description="Test",
            concepts=[concept],
        )
        stage = Stage(
            stage_id="s1",
            name="Test",
            description="Test",
            order=1,
            modules=[module],
        )
        framework = RoadmapFramework(
            roadmap_id="r1",
            title="Test",
            stages=[stage],
            total_estimated_hours=1.0,
            recommended_completion_weeks=1,
        )
        assert framework.validate_structure() is False


class TestValidationModels:
    """验证相关模型测试"""
    
    def test_validation_issue(self):
        """测试验证问题模型"""
        issue = ValidationIssue(
            severity="critical",
            location="Stage 1",
            issue="结构问题",
            suggestion="修复建议",
        )
        assert issue.severity == "critical"
    
    def test_validation_output_score_range(self):
        """测试验证输出分数范围"""
        # 有效分数
        output = ValidationOutput(
            is_valid=True,
            issues=[],
            overall_score=85.0,
        )
        assert output.overall_score == 85.0
        
        # 无效分数 - 超出范围
        with pytest.raises(ValidationError):
            ValidationOutput(
                is_valid=True,
                issues=[],
                overall_score=150.0,  # 超过 100
            )


class TestTutorialGenerationOutput:
    """教程生成输出模型测试"""
    
    def test_valid_output(self):
        """测试有效的教程生成输出"""
        output = TutorialGenerationOutput(
            concept_id="c1",
            tutorial_id="t1",
            title="HTML 教程",
            summary="学习 HTML 基础知识",
            content_url="s3://bucket/key.md",
            estimated_completion_time=30,
        )
        assert output.content_status == "completed"  # 默认值
        assert output.generated_at is not None
    
    def test_summary_max_length(self):
        """测试摘要最大长度"""
        with pytest.raises(ValidationError):
            TutorialGenerationOutput(
                concept_id="c1",
                tutorial_id="t1",
                title="Test",
                summary="x" * 600,  # 超过 500 字符
                content_url="s3://bucket/key.md",
                estimated_completion_time=30,
            )


class TestToolModels:
    """工具接口模型测试"""
    
    def test_search_query(self):
        """测试搜索查询模型"""
        query = SearchQuery(
            query="Python tutorial",
            search_type="web",
            max_results=10,
        )
        assert query.max_results == 10
    
    def test_search_query_max_results_range(self):
        """测试搜索结果数量范围"""
        with pytest.raises(ValidationError):
            SearchQuery(
                query="test",
                max_results=50,  # 超过 20
            )
    
    def test_s3_upload_request(self):
        """测试 S3 上传请求模型"""
        request = S3UploadRequest(
            key="roadmaps/r1/c1/v1.md",
            content="# Hello World",
        )
        assert request.content_type == "text/markdown"  # 默认值
    
    def test_s3_upload_result(self):
        """测试 S3 上传结果模型"""
        result = S3UploadResult(
            success=True,
            url="https://bucket.s3.amazonaws.com/key.md",
            key="key.md",
            size_bytes=100,
        )
        assert result.etag is None  # 可选字段


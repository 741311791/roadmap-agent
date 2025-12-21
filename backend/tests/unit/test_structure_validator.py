"""
StructureValidator Agent 单元测试（重构后）

测试：
1. Python 前置检查（循环依赖检测、空 Stage/Module 检查）
2. 评分计算逻辑
3. 通过判定逻辑
"""
import pytest
from typing import List

from app.models.domain import (
    RoadmapFramework,
    Stage,
    Module,
    Concept,
    ValidationIssue,
    DimensionScore,
)
from app.agents.structure_validator import StructureValidatorAgent


class TestRoadmapStructureValidation:
    """测试 RoadmapFramework.validate_structure() 方法"""
    
    def test_valid_structure(self):
        """测试有效的路线图结构"""
        # 创建一个有效的路线图
        framework = RoadmapFramework(
            roadmap_id="test_roadmap_1",
            title="Test Roadmap",
            stages=[
                Stage(
                    stage_id="s1",
                    name="Stage 1",
                    description="First stage",
                    order=1,
                    modules=[
                        Module(
                            module_id="m1",
                            name="Module 1",
                            description="First module",
                            concepts=[
                                Concept(
                                    concept_id="c1",
                                    name="Concept 1",
                                    description="Basic concept",
                                    estimated_hours=2.0,
                                    prerequisites=[],
                                    difficulty="easy",
                                ),
                                Concept(
                                    concept_id="c2",
                                    name="Concept 2",
                                    description="Second concept",
                                    estimated_hours=3.0,
                                    prerequisites=["c1"],  # 有效的前置关系
                                    difficulty="medium",
                                ),
                            ],
                        )
                    ],
                )
            ],
            total_estimated_hours=5.0,
            recommended_completion_weeks=1,
        )
        
        is_valid, issues = framework.validate_structure()
        
        assert is_valid is True
        assert len(issues) == 0
    
    def test_invalid_prerequisite(self):
        """测试无效的前置关系"""
        framework = RoadmapFramework(
            roadmap_id="test_roadmap_2",
            title="Test Roadmap",
            stages=[
                Stage(
                    stage_id="s1",
                    name="Stage 1",
                    description="First stage",
                    order=1,
                    modules=[
                        Module(
                            module_id="m1",
                            name="Module 1",
                            description="First module",
                            concepts=[
                                Concept(
                                    concept_id="c1",
                                    name="Concept 1",
                                    description="Basic concept",
                                    estimated_hours=2.0,
                                    prerequisites=["c999"],  # 无效的前置关系
                                    difficulty="easy",
                                ),
                            ],
                        )
                    ],
                )
            ],
            total_estimated_hours=2.0,
            recommended_completion_weeks=1,
        )
        
        is_valid, issues = framework.validate_structure()
        
        assert is_valid is False
        assert len(issues) > 0
        assert any(issue.severity == "critical" for issue in issues)
        assert any("c999" in issue.issue for issue in issues)
    
    def test_circular_dependency(self):
        """测试循环依赖检测"""
        framework = RoadmapFramework(
            roadmap_id="test_roadmap_3",
            title="Test Roadmap",
            stages=[
                Stage(
                    stage_id="s1",
                    name="Stage 1",
                    description="First stage",
                    order=1,
                    modules=[
                        Module(
                            module_id="m1",
                            name="Module 1",
                            description="First module",
                            concepts=[
                                Concept(
                                    concept_id="c1",
                                    name="Concept 1",
                                    description="Concept 1",
                                    estimated_hours=2.0,
                                    prerequisites=["c2"],  # c1 依赖 c2
                                    difficulty="easy",
                                ),
                                Concept(
                                    concept_id="c2",
                                    name="Concept 2",
                                    description="Concept 2",
                                    estimated_hours=2.0,
                                    prerequisites=["c1"],  # c2 依赖 c1（循环！）
                                    difficulty="easy",
                                ),
                            ],
                        )
                    ],
                )
            ],
            total_estimated_hours=4.0,
            recommended_completion_weeks=1,
        )
        
        is_valid, issues = framework.validate_structure()
        
        assert is_valid is False
        assert len(issues) > 0
        assert any("循环依赖" in issue.issue for issue in issues)
    
    def test_empty_stage(self):
        """测试空阶段检测"""
        framework = RoadmapFramework(
            roadmap_id="test_roadmap_4",
            title="Test Roadmap",
            stages=[
                Stage(
                    stage_id="s1",
                    name="Empty Stage",
                    description="Stage with no modules",
                    order=1,
                    modules=[],  # 空的模块列表
                )
            ],
            total_estimated_hours=0.0,
            recommended_completion_weeks=1,
        )
        
        is_valid, issues = framework.validate_structure()
        
        assert is_valid is False
        assert len(issues) > 0
        assert any("不包含任何模块" in issue.issue for issue in issues)
    
    def test_empty_module(self):
        """测试空模块检测"""
        framework = RoadmapFramework(
            roadmap_id="test_roadmap_5",
            title="Test Roadmap",
            stages=[
                Stage(
                    stage_id="s1",
                    name="Stage 1",
                    description="First stage",
                    order=1,
                    modules=[
                        Module(
                            module_id="m1",
                            name="Empty Module",
                            description="Module with no concepts",
                            concepts=[],  # 空的概念列表
                        )
                    ],
                )
            ],
            total_estimated_hours=0.0,
            recommended_completion_weeks=1,
        )
        
        is_valid, issues = framework.validate_structure()
        
        assert is_valid is False
        assert len(issues) > 0
        assert any("不包含任何概念" in issue.issue for issue in issues)


class TestStructureValidatorScoring:
    """测试 StructureValidatorAgent 的评分计算逻辑"""
    
    def test_calculate_overall_score_no_issues(self):
        """测试无问题时的总分计算"""
        agent = StructureValidatorAgent()
        
        dimension_scores = [
            DimensionScore(dimension="knowledge_completeness", score=90.0, rationale="Good"),
            DimensionScore(dimension="knowledge_progression", score=85.0, rationale="Good"),
            DimensionScore(dimension="stage_coherence", score=88.0, rationale="Good"),
            DimensionScore(dimension="module_clarity", score=92.0, rationale="Good"),
            DimensionScore(dimension="user_alignment", score=87.0, rationale="Good"),
        ]
        
        issues = []
        
        overall_score = agent._calculate_overall_score(dimension_scores, issues)
        
        # 计算期望值：90*0.3 + 85*0.25 + 88*0.2 + 92*0.15 + 87*0.1
        expected = 90*0.3 + 85*0.25 + 88*0.2 + 92*0.15 + 87*0.1
        
        assert overall_score == pytest.approx(expected, rel=0.1)
    
    def test_calculate_overall_score_with_critical_issues(self):
        """测试有 critical 问题时的总分计算"""
        agent = StructureValidatorAgent()
        
        dimension_scores = [
            DimensionScore(dimension="knowledge_completeness", score=90.0, rationale="Good"),
            DimensionScore(dimension="knowledge_progression", score=85.0, rationale="Good"),
            DimensionScore(dimension="stage_coherence", score=88.0, rationale="Good"),
            DimensionScore(dimension="module_clarity", score=92.0, rationale="Good"),
            DimensionScore(dimension="user_alignment", score=87.0, rationale="Good"),
        ]
        
        issues = [
            ValidationIssue(
                severity="critical",
                category="knowledge_gap",
                location="Stage 1",
                issue="Missing fundamental concepts",
                suggestion="Add basic concepts",
            ),
            ValidationIssue(
                severity="critical",
                category="structural_flaw",
                location="Stage 2",
                issue="Empty module",
                suggestion="Add concepts to module",
            ),
        ]
        
        overall_score = agent._calculate_overall_score(dimension_scores, issues)
        
        # 基础分
        base_score = 90*0.3 + 85*0.25 + 88*0.2 + 92*0.15 + 87*0.1
        # 惩罚分：2 * 10 = 20
        expected = max(0.0, base_score - 20)
        
        assert overall_score == pytest.approx(expected, rel=0.1)
    
    def test_calculate_overall_score_with_warnings(self):
        """测试有 warning 问题时的总分计算"""
        agent = StructureValidatorAgent()
        
        dimension_scores = [
            DimensionScore(dimension="knowledge_completeness", score=80.0, rationale="Good"),
            DimensionScore(dimension="knowledge_progression", score=75.0, rationale="Good"),
            DimensionScore(dimension="stage_coherence", score=78.0, rationale="Good"),
            DimensionScore(dimension="module_clarity", score=82.0, rationale="Good"),
            DimensionScore(dimension="user_alignment", score=77.0, rationale="Good"),
        ]
        
        issues = [
            ValidationIssue(
                severity="warning",
                category="knowledge_gap",
                location="Stage 2",
                issue="Minor gap",
                suggestion="Consider adding more examples",
            ),
        ]
        
        overall_score = agent._calculate_overall_score(dimension_scores, issues)
        
        # 基础分
        base_score = 80*0.3 + 75*0.25 + 78*0.2 + 82*0.15 + 77*0.1
        # 惩罚分：1 * 5 = 5
        expected = max(0.0, base_score - 5)
        
        assert overall_score == pytest.approx(expected, rel=0.1)
    
    def test_calculate_overall_score_minimum_zero(self):
        """测试总分不会低于0"""
        agent = StructureValidatorAgent()
        
        dimension_scores = [
            DimensionScore(dimension="knowledge_completeness", score=10.0, rationale="Poor"),
            DimensionScore(dimension="knowledge_progression", score=10.0, rationale="Poor"),
            DimensionScore(dimension="stage_coherence", score=10.0, rationale="Poor"),
            DimensionScore(dimension="module_clarity", score=10.0, rationale="Poor"),
            DimensionScore(dimension="user_alignment", score=10.0, rationale="Poor"),
        ]
        
        # 大量的 critical 问题
        issues = [
            ValidationIssue(
                severity="critical",
                category="knowledge_gap",
                location=f"Stage {i}",
                issue=f"Issue {i}",
                suggestion=f"Fix {i}",
            )
            for i in range(20)  # 20个 critical 问题，惩罚分 = 200
        ]
        
        overall_score = agent._calculate_overall_score(dimension_scores, issues)
        
        assert overall_score == 0.0


class TestStructureValidatorValidity:
    """测试 StructureValidatorAgent 的通过判定逻辑"""
    
    def test_determine_validity_no_issues(self):
        """测试无问题时判定为通过"""
        agent = StructureValidatorAgent()
        
        issues = []
        
        is_valid = agent._determine_validity(issues)
        
        assert is_valid is True
    
    def test_determine_validity_only_warnings(self):
        """测试只有 warning 时判定为通过"""
        agent = StructureValidatorAgent()
        
        issues = [
            ValidationIssue(
                severity="warning",
                category="knowledge_gap",
                location="Stage 1",
                issue="Minor issue",
                suggestion="Fix it",
            ),
            ValidationIssue(
                severity="warning",
                category="structural_flaw",
                location="Stage 2",
                issue="Another minor issue",
                suggestion="Fix it too",
            ),
        ]
        
        is_valid = agent._determine_validity(issues)
        
        assert is_valid is True
    
    def test_determine_validity_with_critical(self):
        """测试有 critical 问题时判定为失败"""
        agent = StructureValidatorAgent()
        
        issues = [
            ValidationIssue(
                severity="warning",
                category="knowledge_gap",
                location="Stage 1",
                issue="Minor issue",
                suggestion="Fix it",
            ),
            ValidationIssue(
                severity="critical",
                category="structural_flaw",
                location="Stage 2",
                issue="Major issue",
                suggestion="Must fix",
            ),
        ]
        
        is_valid = agent._determine_validity(issues)
        
        assert is_valid is False


class TestStructureValidatorSummary:
    """测试 StructureValidatorAgent 的摘要生成逻辑"""
    
    def test_generate_summary_passed_no_warnings(self):
        """测试通过且无警告的摘要"""
        agent = StructureValidatorAgent()
        
        dimension_scores = []
        issues = []
        overall_score = 95.0
        is_valid = True
        
        summary = agent._generate_summary(dimension_scores, issues, overall_score, is_valid)
        
        assert "passed" in summary.lower()
        assert "95.0" in summary
        assert "no issues" in summary.lower()
    
    def test_generate_summary_passed_with_warnings(self):
        """测试通过但有警告的摘要"""
        agent = StructureValidatorAgent()
        
        dimension_scores = []
        issues = [
            ValidationIssue(
                severity="warning",
                category="knowledge_gap",
                location="Stage 1",
                issue="Minor issue",
                suggestion="Fix it",
            ),
        ]
        overall_score = 85.0
        is_valid = True
        
        summary = agent._generate_summary(dimension_scores, issues, overall_score, is_valid)
        
        assert "passed" in summary.lower()
        assert "85.0" in summary
        assert "1 warnings" in summary.lower()
    
    def test_generate_summary_failed(self):
        """测试失败的摘要"""
        agent = StructureValidatorAgent()
        
        dimension_scores = []
        issues = [
            ValidationIssue(
                severity="critical",
                category="structural_flaw",
                location="Stage 1",
                issue="Major issue",
                suggestion="Must fix",
            ),
            ValidationIssue(
                severity="critical",
                category="knowledge_gap",
                location="Stage 2",
                issue="Another major issue",
                suggestion="Must fix too",
            ),
        ]
        overall_score = 45.0
        is_valid = False
        
        summary = agent._generate_summary(dimension_scores, issues, overall_score, is_valid)
        
        assert "failed" in summary.lower()
        assert "45.0" in summary
        assert "2 critical" in summary.lower()

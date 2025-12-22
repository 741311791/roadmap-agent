"""
ValidationOutput 格式化器单元测试

测试 format_validation_to_feedback() 函数将 ValidationOutput 转换为自然语言 user_feedback
"""
import pytest
from app.models.domain import (
    ValidationOutput,
    ValidationIssue,
    DimensionScore,
    StructuralSuggestion,
)
from app.utils.validation_formatter import format_validation_to_feedback


class TestFormatValidationToFeedback:
    """测试 format_validation_to_feedback 函数"""
    
    @pytest.fixture
    def valid_validation_output(self) -> ValidationOutput:
        """验证通过的输出（无问题）"""
        return ValidationOutput(
            dimension_scores=[
                DimensionScore(dimension="knowledge_completeness", score=90.0, rationale="知识覆盖全面"),
                DimensionScore(dimension="knowledge_progression", score=88.0, rationale="难度递进合理"),
            ],
            issues=[],
            improvement_suggestions=[],
            overall_score=89.0,
            is_valid=True,
            validation_summary="验证通过，路线图结构良好",
        )
    
    @pytest.fixture
    def invalid_validation_output(self) -> ValidationOutput:
        """验证失败的输出（包含 critical 和 warning 问题）"""
        return ValidationOutput(
            dimension_scores=[
                DimensionScore(dimension="knowledge_completeness", score=65.0, rationale="缺少关键知识点"),
                DimensionScore(dimension="knowledge_progression", score=70.0, rationale="难度跳跃过大"),
            ],
            issues=[
                ValidationIssue(
                    severity="critical",
                    category="structural_flaw",
                    location="Stage 2 > Module 1 > Concept 3",
                    issue="前置概念 'c-1-2-1' 不存在于路线图中",
                    suggestion="移除无效的前置关系或添加缺失的概念",
                ),
                ValidationIssue(
                    severity="critical",
                    category="structural_flaw",
                    location="Stage 1",
                    issue="检测到循环依赖: c-1-1-1 → c-1-1-2 → c-1-1-1",
                    suggestion="打破循环依赖链",
                ),
                ValidationIssue(
                    severity="warning",
                    category="knowledge_gap",
                    location="Stage 3 > Module 2",
                    issue="缺少实战练习环节",
                    suggestion="添加项目实践或练习题",
                ),
            ],
            improvement_suggestions=[
                StructuralSuggestion(
                    action="add_concept",
                    target_location="Stage 2 > Module 1 之后",
                    content="添加 Docker 容器化概念",
                    reason="补充云原生知识",
                ),
            ],
            overall_score=55.0,
            is_valid=False,
            validation_summary="验证未通过，存在2个严重问题和1个警告",
        )
    
    def test_format_valid_output(self, valid_validation_output: ValidationOutput):
        """测试格式化验证通过的输出"""
        result = format_validation_to_feedback(valid_validation_output)
        
        # 验证总体状态
        assert "验证通过" in result
        assert "89/100" in result
        
        # 验证维度评分
        assert "knowledge_completeness" in result
        assert "90/100" in result
        assert "知识覆盖全面" in result
        
        # 验证没有问题部分（因为没有问题）
        assert "必须修复的问题" not in result
        assert "建议修复的问题" not in result
    
    def test_format_invalid_output(self, invalid_validation_output: ValidationOutput):
        """测试格式化验证失败的输出"""
        result = format_validation_to_feedback(invalid_validation_output)
        
        # 验证总体状态
        assert "验证未通过" in result
        assert "55/100" in result
        
        # 验证 critical 问题
        assert "必须修复的问题" in result
        assert "前置概念 'c-1-2-1' 不存在" in result
        assert "循环依赖" in result
        
        # 验证 warning 问题
        assert "建议修复的问题" in result
        assert "缺少实战练习环节" in result
        
        # 验证改进建议
        assert "可选优化建议" in result
        assert "Docker 容器化" in result
        
        # 验证验证摘要
        assert "验证未通过，存在2个严重问题和1个警告" in result
    
    def test_format_output_with_structural_suggestion(self):
        """测试格式化包含 structural_suggestion 的问题"""
        output = ValidationOutput(
            dimension_scores=[],
            issues=[
                ValidationIssue(
                    severity="critical",
                    category="structural_flaw",
                    location="Stage 2 > Module 1",
                    issue="模块不包含任何概念",
                    suggestion="添加至少一个概念或删除该模块",
                    structural_suggestion=StructuralSuggestion(
                        action="add_concept",
                        target_location="Stage 2 > Module 1",
                        content="添加 'API 设计基础' 概念",
                        reason="补充模块内容",
                    ),
                ),
            ],
            improvement_suggestions=[],
            overall_score=40.0,
            is_valid=False,
            validation_summary="验证未通过",
        )
        
        result = format_validation_to_feedback(output)
        
        # 验证结构化建议被包含
        assert "add_concept" in result
        assert "API 设计基础" in result
    
    def test_format_output_only_warnings(self):
        """测试只有 warning 没有 critical 的情况"""
        output = ValidationOutput(
            dimension_scores=[
                DimensionScore(dimension="user_alignment", score=75.0, rationale="基本符合用户需求"),
            ],
            issues=[
                ValidationIssue(
                    severity="warning",
                    category="user_mismatch",
                    location="Stage 4",
                    issue="高级主题可能超出用户当前水平",
                    suggestion="考虑简化或标记为可选",
                ),
            ],
            improvement_suggestions=[],
            overall_score=75.0,
            is_valid=True,  # warning 不导致验证失败
            validation_summary="验证通过，但有建议",
        )
        
        result = format_validation_to_feedback(output)
        
        # 验证通过但有警告
        assert "验证通过" in result
        assert "建议修复的问题" in result
        assert "高级主题可能超出用户当前水平" in result
        
        # 没有 critical 问题部分
        assert "必须修复的问题" not in result
    
    def test_format_output_preserves_all_issues(self, invalid_validation_output: ValidationOutput):
        """测试所有问题都被保留在输出中"""
        result = format_validation_to_feedback(invalid_validation_output)
        
        # 验证所有 critical 问题都在
        assert "前置概念" in result
        assert "循环依赖" in result
        
        # 验证所有 warning 问题都在
        assert "实战练习" in result
        
        # 验证所有改进建议都在
        assert "Docker" in result


class TestFormatterEdgeCases:
    """测试边界情况"""
    
    def test_empty_issues_list(self):
        """测试空问题列表"""
        output = ValidationOutput(
            dimension_scores=[],
            issues=[],
            improvement_suggestions=[],
            overall_score=100.0,
            is_valid=True,
            validation_summary="完美通过",
        )
        
        result = format_validation_to_feedback(output)
        
        assert "验证通过" in result
        assert "100/100" in result
    
    def test_only_improvement_suggestions(self):
        """测试只有改进建议没有问题"""
        output = ValidationOutput(
            dimension_scores=[],
            issues=[],
            improvement_suggestions=[
                StructuralSuggestion(
                    action="add_module",
                    target_location="Stage 1 之后",
                    content="添加实战项目模块",
                    reason="增强动手能力",
                ),
            ],
            overall_score=85.0,
            is_valid=True,
            validation_summary="验证通过，有优化建议",
        )
        
        result = format_validation_to_feedback(output)
        
        assert "可选优化建议" in result
        assert "add_module" in result
        assert "实战项目模块" in result


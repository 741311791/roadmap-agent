"""
测试单 Concept 子图逻辑

验证两层 Fan-Out/Fan-In 架构中的单 Concept 子图：
- 内层 Fan-Out 创建 3 个并行任务
- Tutorial、Resource、Quiz 并发生成
- Fan-In 收集并保存元数据
- 错误处理和部分失败场景
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.orchestrator.subgraphs.single_concept_content_generation import (
    build_single_concept_subgraph,
    inner_fan_out,
    fan_in_and_save,
)
from app.models.domain import (
    Concept,
    LearningPreferences,
    TutorialGenerationOutput,
    ResourceRecommendationOutput,
    QuizGenerationOutput,
)


class TestSingleConceptSubgraph:
    """测试单 Concept 子图"""
    
    @pytest.fixture
    def sample_concept(self):
        """示例 Concept"""
        return Concept(
            concept_id="test-concept-1",
            name="Python Basics",
            description="Learn Python fundamentals",
            estimated_hours=10,
            key_points=["Variables", "Functions", "Classes"],
        )
    
    @pytest.fixture
    def sample_preferences(self):
        """示例 LearningPreferences"""
        return LearningPreferences(
            learning_goal="Learn Python",
            available_hours_per_week=10,
            motivation="Career",
            current_level="beginner",
            career_background="Student",
        )
    
    @pytest.fixture
    def sample_state(self, sample_concept, sample_preferences):
        """示例状态"""
        return {
            "concept": sample_concept,
            "roadmap_id": "test-roadmap-1",
            "user_preferences": sample_preferences,
            "task_id": "test-task-1",
            "tutorial": None,
            "resource": None,
            "quiz": None,
            "errors": [],
            "save_status": {},
        }
    
    def test_inner_fan_out_creates_three_sends(self, sample_state):
        """测试内层 Fan-Out 创建 3 个 Send 任务"""
        result = inner_fan_out(sample_state)
        
        # 验证返回 Command 对象
        assert hasattr(result, 'goto')
        assert isinstance(result.goto, list)
        
        # 验证创建了 3 个 Send 任务
        assert len(result.goto) == 3
        
        # 验证每个 Send 的目标节点
        target_nodes = [send.node for send in result.goto]
        assert "generate_tutorial" in target_nodes
        assert "generate_resource" in target_nodes
        assert "generate_quiz" in target_nodes
    
    @pytest.mark.asyncio
    async def test_fan_in_and_save_all_success(self, sample_state, sample_concept):
        """测试 Fan-In 节点：所有内容生成成功"""
        # 准备成功的结果
        tutorial = TutorialGenerationOutput(
            concept_id=sample_concept.concept_id,
            tutorial_id="tutorial-1",
            content_url="https://example.com/tutorial",
            summary="Tutorial summary",
            sections=[],
        )
        
        resource = ResourceRecommendationOutput(
            concept_id=sample_concept.concept_id,
            id="resource-1",
            resources=[],
        )
        
        quiz = QuizGenerationOutput(
            concept_id=sample_concept.concept_id,
            quiz_id="quiz-1",
            questions=[],
            total_questions=5,
        )
        
        sample_state["tutorial"] = tutorial
        sample_state["resource"] = resource
        sample_state["quiz"] = quiz
        
        # Mock RuntimeContext 和 DB
        mock_runtime_context = MagicMock()
        mock_db_factory = MagicMock()
        mock_session = AsyncMock()
        mock_db_factory.get_session.return_value.__aenter__.return_value = mock_session
        mock_db_factory.get_session.return_value.__aexit__.return_value = None
        mock_runtime_context.db_factory = mock_db_factory
        mock_runtime_context.notification_service = AsyncMock()
        
        config = {
            "configurable": {
                "runtime_context": mock_runtime_context,
            }
        }
        
        # Mock ConceptContentHandler
        with patch("app.core.orchestrator.subgraphs.single_concept_content_generation.ConceptContentHandler") as MockHandler:
            mock_handler = MockHandler.return_value
            mock_handler.save_concept_content = AsyncMock(return_value={
                "concept_id": sample_concept.concept_id,
                "tutorial": "success",
                "resource": "success",
                "quiz": "success",
                "metadata_saved": True,
            })
            
            # 执行 Fan-In
            result = await fan_in_and_save(sample_state, config)
            
            # 验证返回结果
            assert "save_status" in result
            assert result["save_status"]["metadata_saved"] is True
            assert result["save_status"]["tutorial"] == "success"
            assert result["save_status"]["resource"] == "success"
            assert result["save_status"]["quiz"] == "success"
            
            # 验证调用了 save_concept_content
            mock_handler.save_concept_content.assert_called_once()
            
            # 验证发送了通知
            mock_runtime_context.notification_service.publish_concept_complete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fan_in_and_save_partial_failure(self, sample_state, sample_concept):
        """测试 Fan-In 节点：部分内容生成失败"""
        # 只有 Tutorial 和 Quiz 成功，Resource 失败
        tutorial = TutorialGenerationOutput(
            concept_id=sample_concept.concept_id,
            tutorial_id="tutorial-1",
            content_url="https://example.com/tutorial",
            summary="Tutorial summary",
            sections=[],
        )
        
        quiz = QuizGenerationOutput(
            concept_id=sample_concept.concept_id,
            quiz_id="quiz-1",
            questions=[],
            total_questions=5,
        )
        
        sample_state["tutorial"] = tutorial
        sample_state["resource"] = None  # Resource 失败
        sample_state["quiz"] = quiz
        sample_state["errors"] = [{"concept_id": sample_concept.concept_id, "type": "resource", "error": "API failed"}]
        
        # Mock RuntimeContext 和 DB
        mock_runtime_context = MagicMock()
        mock_db_factory = MagicMock()
        mock_session = AsyncMock()
        mock_db_factory.get_session.return_value.__aenter__.return_value = mock_session
        mock_db_factory.get_session.return_value.__aexit__.return_value = None
        mock_runtime_context.db_factory = mock_db_factory
        mock_runtime_context.notification_service = AsyncMock()
        
        config = {
            "configurable": {
                "runtime_context": mock_runtime_context,
            }
        }
        
        # Mock ConceptContentHandler
        with patch("app.core.orchestrator.subgraphs.single_concept_content_generation.ConceptContentHandler") as MockHandler:
            mock_handler = MockHandler.return_value
            mock_handler.save_concept_content = AsyncMock(return_value={
                "concept_id": sample_concept.concept_id,
                "tutorial": "success",
                "resource": "skipped",  # Resource 跳过
                "quiz": "success",
                "metadata_saved": True,  # 仍然认为保存成功（部分成功）
            })
            
            # 执行 Fan-In
            result = await fan_in_and_save(sample_state, config)
            
            # 验证返回结果
            assert "save_status" in result
            assert result["save_status"]["tutorial"] == "success"
            assert result["save_status"]["resource"] == "skipped"
            assert result["save_status"]["quiz"] == "success"
            
            # 验证发送了通知
            mock_runtime_context.notification_service.publish_concept_complete.assert_called_once()
    
    def test_build_single_concept_subgraph(self):
        """测试子图构建"""
        subgraph = build_single_concept_subgraph()
        
        # 验证子图已编译
        assert subgraph is not None
        
        # 验证子图包含正确的节点（如果可以访问）
        if hasattr(subgraph, 'nodes'):
            assert "inner_fan_out" in subgraph.nodes
            assert "generate_tutorial" in subgraph.nodes
            assert "generate_resource" in subgraph.nodes
            assert "generate_quiz" in subgraph.nodes
            assert "fan_in_and_save" in subgraph.nodes


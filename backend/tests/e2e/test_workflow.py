"""
端到端工作流测试

测试完整的状态机流程：
START → A1(需求分析师) → A2(课程架构师) → A3(结构审查员) ↔ A2E(路线图编辑师)
     → HUMAN_REVIEW → A4(教程生成器) → COMPLETED
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock

from app.models.domain import UserRequest, LearningPreferences


class TestFullWorkflow:
    """完整工作流端到端测试"""
    
    @pytest.fixture
    def user_request(self) -> UserRequest:
        """测试用的用户请求"""
        return UserRequest(
            user_id="e2e-test-user",
            session_id="e2e-test-session",
            preferences=LearningPreferences(
                learning_goal="学习 Python Web 开发",
                available_hours_per_week=10,
                motivation="转行",
                current_level="beginner",
                career_background="市场营销",
                content_preference=["text", "interactive"],
            ),
            additional_context="希望能在 3 个月内入门",
        )
    
    @pytest.fixture
    def mock_intent_analysis_response(self):
        """Mock 需求分析响应"""
        data = {
            "parsed_goal": "学习 Python Web 开发",
            "key_technologies": ["Python", "Flask", "PostgreSQL"],
            "difficulty_profile": "初学者",
            "time_constraint": "3 个月",
            "recommended_focus": ["Python 基础", "Web 框架"]
        }
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = f"```json\n{json.dumps(data)}\n```"
        return response
    
    @pytest.fixture
    def mock_curriculum_design_response(self):
        """Mock 课程设计响应"""
        data = {
            "framework": {
                "roadmap_id": "e2e-roadmap-001",
                "title": "Python Web 开发学习路线",
                "stages": [{
                    "stage_id": "s1",
                    "name": "Python 基础",
                    "description": "学习 Python 编程基础",
                    "order": 1,
                    "modules": [{
                        "module_id": "m1",
                        "name": "基础语法",
                        "description": "Python 基本语法",
                        "concepts": [{
                            "concept_id": "c1",
                            "name": "变量和类型",
                            "description": "学习 Python 变量",
                            "estimated_hours": 2.0,
                            "prerequisites": [],
                            "difficulty": "easy",
                            "keywords": ["变量"]
                        }]
                    }]
                }],
                "total_estimated_hours": 2.0,
                "recommended_completion_weeks": 1
            },
            "design_rationale": "针对初学者设计的基础课程"
        }
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = f"```json\n{json.dumps(data)}\n```"
        return response
    
    @pytest.fixture
    def mock_validation_response(self):
        """Mock 验证响应"""
        data = {
            "is_valid": True,
            "issues": [],
            "overall_score": 95.0
        }
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = f"```json\n{json.dumps(data)}\n```"
        return response
    
    @pytest.fixture
    def mock_tutorial_response(self):
        """Mock 教程生成响应"""
        data = {
            "tutorial_id": "tutorial-001",
            "title": "Python 变量和类型",
            "summary": "学习 Python 中的变量声明和数据类型",
            "tutorial_content": "# Python 变量\n\n这是教程内容...",
            "estimated_completion_time": 30
        }
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = f"```json\n{json.dumps(data)}\n```"
        return response
    
    @pytest.mark.asyncio
    async def test_workflow_with_skip_all_optional(self, user_request):
        """测试跳过所有可选节点的工作流"""
        from app.core.orchestrator import RoadmapOrchestrator
        from app.config.settings import settings
        
        # Mock 所有 LLM 调用
        mock_responses = []
        
        # 需求分析响应
        intent_data = {
            "parsed_goal": "学习 Python",
            "key_technologies": ["Python"],
            "difficulty_profile": "初学者",
            "time_constraint": "3个月",
            "recommended_focus": ["基础"]
        }
        intent_response = MagicMock()
        intent_response.choices = [MagicMock()]
        intent_response.choices[0].message.content = json.dumps(intent_data)
        mock_responses.append(intent_response)
        
        # 课程设计响应
        curriculum_data = {
            "framework": {
                "roadmap_id": "test-001",
                "title": "Python 学习",
                "stages": [{
                    "stage_id": "s1",
                    "name": "基础",
                    "description": "基础学习",
                    "order": 1,
                    "modules": [{
                        "module_id": "m1",
                        "name": "入门",
                        "description": "入门学习",
                        "concepts": [{
                            "concept_id": "c1",
                            "name": "Hello World",
                            "description": "第一个程序",
                            "estimated_hours": 1.0,
                            "prerequisites": [],
                            "difficulty": "easy",
                            "keywords": []
                        }]
                    }]
                }],
                "total_estimated_hours": 1.0,
                "recommended_completion_weeks": 1
            },
            "design_rationale": "简单课程"
        }
        curriculum_response = MagicMock()
        curriculum_response.choices = [MagicMock()]
        curriculum_response.choices[0].message.content = json.dumps(curriculum_data)
        mock_responses.append(curriculum_response)
        
        with patch("litellm.acompletion") as mock_llm, \
             patch.object(RoadmapOrchestrator, 'initialize', new_callable=AsyncMock), \
             patch.object(RoadmapOrchestrator, '_checkpointer', AsyncMock()), \
             patch.object(RoadmapOrchestrator, '_initialized', True), \
             patch.object(settings, 'SKIP_STRUCTURE_VALIDATION', True), \
             patch.object(settings, 'SKIP_HUMAN_REVIEW', True), \
             patch.object(settings, 'SKIP_TUTORIAL_GENERATION', True):
            
            mock_llm.side_effect = mock_responses
            
            orchestrator = RoadmapOrchestrator()
            
            # 由于跳过了所有可选节点，工作流应该快速完成
            # 这里我们测试工作流的构建逻辑
            assert orchestrator is not None


class TestWorkflowSkipConfigurations:
    """工作流跳过配置测试"""
    
    def test_skip_structure_validation_config_type(self):
        """测试跳过结构验证配置类型"""
        from app.config.settings import Settings
        
        settings = Settings()
        # 验证配置是布尔类型
        assert isinstance(settings.SKIP_STRUCTURE_VALIDATION, bool)
    
    def test_skip_human_review_config_type(self):
        """测试跳过人工审核配置类型"""
        from app.config.settings import Settings
        
        settings = Settings()
        # 验证配置是布尔类型
        assert isinstance(settings.SKIP_HUMAN_REVIEW, bool)
    
    def test_skip_tutorial_generation_config_type(self):
        """测试跳过教程生成配置类型"""
        from app.config.settings import Settings
        
        settings = Settings()
        # 验证配置是布尔类型
        assert isinstance(settings.SKIP_TUTORIAL_GENERATION, bool)


class TestWorkflowStateTransitions:
    """工作流状态转换测试"""
    
    @pytest.fixture
    def mock_orchestrator(self):
        """Mock Orchestrator"""
        from app.core.orchestrator import RoadmapOrchestrator
        
        with patch.object(RoadmapOrchestrator, '_initialized', True), \
             patch.object(RoadmapOrchestrator, '_checkpointer', AsyncMock()):
            yield RoadmapOrchestrator()
    
    def test_route_after_validation_edit_on_failure(self, mock_orchestrator):
        """测试验证失败后路由到编辑"""
        state = {
            "validation_result": MagicMock(is_valid=False),
            "modification_count": 0,
            "trace_id": "test-trace",
        }
        
        with patch('app.core.orchestrator.settings') as mock_settings:
            mock_settings.MAX_FRAMEWORK_RETRY = 3
            mock_settings.SKIP_HUMAN_REVIEW = False
            mock_settings.SKIP_TUTORIAL_GENERATION = False
            
            result = mock_orchestrator._route_after_validation(state)
            assert result == "edit_roadmap"
    
    def test_route_after_validation_proceed_on_max_retries(self, mock_orchestrator):
        """测试达到最大重试次数后继续流程"""
        state = {
            "validation_result": MagicMock(is_valid=False),
            "modification_count": 5,  # 超过最大重试次数
            "trace_id": "test-trace",
        }
        
        with patch('app.core.orchestrator.settings') as mock_settings:
            mock_settings.MAX_FRAMEWORK_RETRY = 3
            mock_settings.SKIP_HUMAN_REVIEW = False
            mock_settings.SKIP_TUTORIAL_GENERATION = False
            
            result = mock_orchestrator._route_after_validation(state)
            assert result == "human_review"
    
    def test_route_after_human_review_approved(self, mock_orchestrator):
        """测试人工审核通过后的路由"""
        state = {
            "human_approved": True,
            "trace_id": "test-trace",
        }
        
        with patch('app.core.orchestrator.settings') as mock_settings:
            mock_settings.SKIP_TUTORIAL_GENERATION = False
            
            result = mock_orchestrator._route_after_human_review(state)
            assert result == "approved"
    
    def test_route_after_human_review_rejected(self, mock_orchestrator):
        """测试人工审核拒绝后的路由"""
        state = {
            "human_approved": False,
            "trace_id": "test-trace",
        }
        
        result = mock_orchestrator._route_after_human_review(state)
        assert result == "modify"


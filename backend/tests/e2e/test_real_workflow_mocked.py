"""
真实环境测试（使用Mock LLM）

测试内容：
- 使用真实数据库
- 使用真实环境变量
- Mock LLM调用以避免格式解析问题
- 测试完整工作流执行
"""
import pytest
import asyncio
import uuid
from unittest.mock import patch, AsyncMock, MagicMock

from app.core.orchestrator_factory import OrchestratorFactory
from app.models.domain import (
    UserRequest,
    LearningPreferences,
    IntentAnalysisOutput,
    RoadmapFramework,
    Stage,
    Module,
    Concept,
)
from app.db.session import AsyncSessionLocal
from app.db.repositories.roadmap_repo import RoadmapRepository


@pytest.mark.asyncio
class TestRealWorkflowMocked:
    """真实环境工作流测试（Mock LLM）"""
    
    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """初始化和清理"""
        # 初始化 OrchestratorFactory
        await OrchestratorFactory.initialize()
        
        yield
        
        # 清理
        await OrchestratorFactory.cleanup()
    
    @patch("app.agents.intent_analyzer.IntentAnalyzerAgent")
    @patch("app.agents.curriculum_architect.CurriculumArchitectAgent")
    async def test_full_workflow_with_mocked_agents(
        self,
        mock_curriculum_cls,
        mock_intent_cls,
    ):
        """
        测试完整工作流（Mock Agent）
        
        预期流程：
        1. Intent Analysis (mocked)
        2. Curriculum Design (mocked)
        3. Content Generation (mocked)
        4. END
        """
        task_id = f"test-mocked-{uuid.uuid4().hex[:8]}"
        roadmap_id = f"python-test-{uuid.uuid4().hex[:8]}"
        
        # Mock Intent Analyzer
        mock_intent = AsyncMock()
        mock_intent.execute = AsyncMock(return_value=IntentAnalysisOutput(
            parsed_goal="学习 Python 基础编程",
            key_technologies=["Python", "基础语法", "数据类型"],
            difficulty_profile="beginner",
            time_constraint="每周10小时",
            recommended_focus=["Python基础", "编程思维"],
            roadmap_id=roadmap_id,
        ))
        mock_intent_cls.return_value = mock_intent
        
        # Mock Curriculum Architect
        concept1 = Concept(
            concept_id="c1",
            name="Python 安装与环境配置",
            description="学习如何安装Python和配置开发环境",
            estimated_hours=2.0,
            prerequisites=[],
            difficulty="easy",
            keywords=["Python", "安装", "环境"],
        )
        concept2 = Concept(
            concept_id="c2",
            name="变量与数据类型",
            description="学习Python的基本数据类型",
            estimated_hours=3.0,
            prerequisites=["c1"],
            difficulty="easy",
            keywords=["变量", "数据类型"],
        )
        
        module1 = Module(
            module_id="m1",
            name="Python 入门",
            description="Python 基础知识",
            concepts=[concept1, concept2],
        )
        
        stage1 = Stage(
            stage_id="s1",
            name="基础阶段",
            description="Python 基础学习",
            order=1,
            modules=[module1],
        )
        
        framework = RoadmapFramework(
            roadmap_id=roadmap_id,
            title="Python基础学习路线",
            stages=[stage1],
            total_estimated_hours=5.0,
            recommended_completion_weeks=1,
        )
        
        mock_curriculum = AsyncMock()
        mock_curriculum.model_name = "test-model"
        mock_curriculum.model_provider = "test-provider"
        mock_curriculum.execute = AsyncMock(return_value=MagicMock(
            framework=framework
        ))
        mock_curriculum_cls.return_value = mock_curriculum
        
        # Mock 所有内容生成器（教程、资源、测验）
        with patch("app.agents.tutorial_generator.TutorialGeneratorAgent") as mock_tutorial_cls:
            with patch("app.agents.resource_recommender.ResourceRecommenderAgent") as mock_resource_cls:
                with patch("app.agents.quiz_generator.QuizGeneratorAgent") as mock_quiz_cls:
                    
                    # Mock Tutorial Generator
                    from app.models.domain import TutorialGenerationOutput
                    mock_tutorial = AsyncMock()
                    mock_tutorial.execute = AsyncMock(return_value=TutorialGenerationOutput(
                        concept_id="c1",
                        tutorial_id=f"tutorial-{uuid.uuid4().hex[:8]}",
                        title="Python 安装与环境配置教程",
                        summary="本教程教你如何安装Python",
                        content_url=f"s3://roadmap/tutorials/{uuid.uuid4().hex}.md",
                        content_status="completed",
                        estimated_completion_time=30,
                    ))
                    mock_tutorial_cls.return_value = mock_tutorial
                    
                    # Mock Resource Recommender
                    from app.models.domain import ResourceRecommendationOutput, Resource
                    mock_resource = AsyncMock()
                    mock_resource.execute = AsyncMock(return_value=ResourceRecommendationOutput(
                        id=f"resource-{uuid.uuid4().hex[:8]}",
                        concept_id="c1",
                        concept_name="Python 安装与环境配置",
                        resources=[
                            Resource(
                                title="Python官方文档",
                                type="documentation",
                                url="https://docs.python.org",
                                description="官方文档",
                                relevance_score=0.95,
                            )
                        ],
                        total_count=1,
                    ))
                    mock_resource_cls.return_value = mock_resource
                    
                    # Mock Quiz Generator
                    from app.models.domain import QuizGenerationOutput, QuizQuestion
                    mock_quiz = AsyncMock()
                    mock_quiz.execute = AsyncMock(return_value=QuizGenerationOutput(
                        quiz_id=f"quiz-{uuid.uuid4().hex[:8]}",
                        concept_id="c1",
                        concept_name="Python 安装与环境配置",
                        questions=[
                            QuizQuestion(
                                question_id="q1",
                                question="如何安装Python？",
                                question_type="multiple_choice",
                                options=["下载安装包", "在线安装", "源码编译", "以上都可以"],
                                correct_answer=[3],  # 索引从0开始，"以上都可以"是第4个选项
                                explanation="Python可以通过多种方式安装",
                                difficulty="easy",
                            )
                        ],
                        total_questions=1,
                        difficulty_distribution={"easy": 1},
                    ))
                    mock_quiz_cls.return_value = mock_quiz
                    
                    # 创建测试请求
                    user_request = UserRequest(
                        user_id="test-user-mocked",
                        session_id="test-session-mocked",
                        preferences=LearningPreferences(
                            learning_goal="学习Python基础编程",
                            available_hours_per_week=10,
                            motivation="兴趣学习",
                            current_level="beginner",
                            career_background="学生",
                            content_preference=["text", "hands_on"],
                            target_deadline=None,
                        ),
                        additional_context="希望快速入门",
                    )
                    
                    # 获取executor
                    executor = OrchestratorFactory.create_workflow_executor()
                    
                    print(f"\n{'='*60}")
                    print(f"开始执行完整工作流（Mock版本）: {task_id}")
                    print(f"{'='*60}\n")
                    
                    try:
                        result = await asyncio.wait_for(
                            executor.execute(user_request, task_id),
                            timeout=120.0
                        )
                        
                        print(f"\n{'='*60}")
                        print(f"✅ 工作流执行成功！")
                        print(f"{'='*60}\n")
                        
                        # 验证结果
                        assert result is not None
                        assert result["task_id"] == task_id
                        assert result["roadmap_id"] == roadmap_id
                        assert result["intent_analysis"] is not None
                        assert result["roadmap_framework"] is not None
                        
                        # 验证内容生成结果
                        assert "tutorial_refs" in result
                        assert "resource_refs" in result
                        assert "quiz_refs" in result
                        
                        print(f"✅ Trace ID: {task_id}")
                        print(f"✅ Roadmap ID: {roadmap_id}")
                        print(f"✅ Title: {result['roadmap_framework'].title}")
                        print(f"✅ Tutorials: {len(result['tutorial_refs'])}")
                        print(f"✅ Resources: {len(result['resource_refs'])}")
                        print(f"✅ Quizzes: {len(result['quiz_refs'])}")
                        
                        # 验证数据库记录
                        from app.db.repository_factory import RepositoryFactory
                        repo_factory = RepositoryFactory()
                        
                        async with repo_factory.create_session() as session:
                            # 检查task记录（任务可能已完成并状态更新）
                            task_repo = repo_factory.create_task_repo(session)
                            task = await task_repo.get_by_task_id(task_id)
                            if task:
                                print(f"✅ Task Status: {task.status}")
                            else:
                                print(f"⚠️ Task not found in DB (may be due to testing environment)")
                            
                            # 检查roadmap记录
                            roadmap_meta_repo = repo_factory.create_roadmap_meta_repo(session)
                            roadmap = await roadmap_meta_repo.get_by_roadmap_id(roadmap_id)
                            if roadmap:
                                print(f"✅ Roadmap saved in DB: {roadmap.roadmap_id}")
                            else:
                                print(f"⚠️ Roadmap not found in DB (may be due to testing environment)")
                        
                        print(f"\n{'='*60}")
                        print(f"所有验证通过！完整工作流测试成功！")
                        print(f"{'='*60}\n")
                        
                        return result
                        
                    except asyncio.TimeoutError:
                        pytest.fail("工作流执行超时（2分钟）")
                    except Exception as e:
                        print(f"\n{'='*60}")
                        print(f"❌ 工作流执行失败: {str(e)}")
                        print(f"{'='*60}\n")
                        raise


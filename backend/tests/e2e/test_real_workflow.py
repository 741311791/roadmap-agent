"""
真实环境的端到端工作流测试

测试内容：
- 使用真实数据库
- 使用真实环境变量
- 测试完整工作流执行
"""
import pytest
import asyncio
import uuid
from datetime import datetime

from app.core.orchestrator_factory import OrchestratorFactory
from app.models.domain import UserRequest, LearningPreferences
from app.db.session import AsyncSessionLocal
from app.db.repositories.roadmap_repo import RoadmapRepository


@pytest.mark.asyncio
class TestRealWorkflow:
    """真实环境工作流测试"""
    
    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """初始化和清理"""
        # 初始化 OrchestratorFactory
        await OrchestratorFactory.initialize()
        
        yield
        
        # 清理
        await OrchestratorFactory.cleanup()
    
    async def test_minimal_workflow_with_all_skip(self):
        """
        测试最小工作流（跳过所有可选步骤）
        
        预期流程：
        1. Intent Analysis
        2. Curriculum Design
        3. END (跳过所有可选步骤)
        """
        # 创建测试请求
        task_id = f"test-real-{uuid.uuid4().hex[:8]}"
        user_request = UserRequest(
            user_id="test-user-real",
            session_id="test-session-real",
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
        
        # 创建task记录（工作流需要已存在的task）
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            await repo.create_task(
                task_id=task_id,
                user_id=user_request.user_id,
                user_request=user_request.model_dump(),
            )
            await session.commit()
            print(f"✅ Task record created: {task_id}")
        
        # 获取executor
        executor = OrchestratorFactory.create_workflow_executor()
        
        # 执行工作流
        print(f"\n{'='*60}")
        print(f"开始执行工作流: {task_id}")
        print(f"{'='*60}\n")
        
        try:
            result = await asyncio.wait_for(
                executor.execute(user_request, task_id),
                timeout=120.0  # 2分钟超时
            )
            
            print(f"\n{'='*60}")
            print(f"工作流执行成功！")
            print(f"{'='*60}\n")
            
            # 验证结果
            assert result is not None
            assert result["task_id"] == task_id
            assert result["roadmap_id"] is not None
            assert result["intent_analysis"] is not None
            assert result["roadmap_framework"] is not None
            
            # 验证roadmap_framework结构
            framework = result["roadmap_framework"]
            assert framework.roadmap_id is not None
            assert framework.title
            assert len(framework.stages) > 0
            
            # 打印结果
            print(f"✅ Trace ID: {task_id}")
            print(f"✅ Roadmap ID: {framework.roadmap_id}")
            print(f"✅ Title: {framework.title}")
            print(f"✅ Stages: {len(framework.stages)}")
            
            total_concepts = sum(
                len(module.concepts)
                for stage in framework.stages
                for module in stage.modules
            )
            print(f"✅ Total Concepts: {total_concepts}")
            
            # 验证数据库记录
            async with AsyncSessionLocal() as session:
                repo = RoadmapRepository(session)
                
                # 检查task记录
                task = await repo.get_task(task_id)
                assert task is not None
                # 接受 completed 或 partial_failure（部分概念生成失败是正常的）
                assert task.status in ["completed", "partial_failure"]
                print(f"✅ Task Status: {task.status}")
                if task.failed_concepts:
                    print(f"⚠️  Failed Concepts: {task.failed_concepts.get('count', 0)}")
                
                # 检查roadmap记录
                roadmap = await repo.get_roadmap_metadata(framework.roadmap_id)
                assert roadmap is not None
                assert roadmap.roadmap_id == framework.roadmap_id
                print(f"✅ Roadmap saved in DB: {roadmap.roadmap_id}")
            
            print(f"\n{'='*60}")
            print(f"所有验证通过！")
            print(f"{'='*60}\n")
            
            return result
            
        except asyncio.TimeoutError:
            pytest.fail("工作流执行超时（2分钟）")
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"❌ 工作流执行失败: {str(e)}")
            print(f"{'='*60}\n")
            raise
    
    async def test_workflow_with_validation(self):
        """
        测试包含结构验证的工作流
        
        预期流程：
        1. Intent Analysis
        2. Curriculum Design
        3. Structure Validation
        4. Human Review (会被interrupt，这里我们直接跳过)
        """
        # 创建测试请求
        task_id = f"test-validation-{uuid.uuid4().hex[:8]}"
        user_request = UserRequest(
            user_id="test-user-validation",
            session_id="test-session-validation",
            preferences=LearningPreferences(
                learning_goal="深入学习Web前端开发",
                available_hours_per_week=20,
                motivation="职业发展",
                current_level="intermediate",
                career_background="后端开发2年",
                content_preference=["text", "hands_on", "visual"],
                target_deadline=None,
            ),
            additional_context="希望系统学习现代前端技术栈",
        )
        
        # 获取executor
        executor = OrchestratorFactory.create_workflow_executor()
        
        print(f"\n{'='*60}")
        print(f"开始执行包含验证的工作流: {task_id}")
        print(f"{'='*60}\n")
        
        try:
            # 注意：这个测试会在human_review处中断
            # 因为LangGraph的interrupt()会抛出GraphInterrupt
            from langgraph.errors import GraphInterrupt
            
            with pytest.raises(GraphInterrupt):
                await asyncio.wait_for(
                    executor.execute(user_request, task_id),
                    timeout=120.0
                )
            
            print(f"\n{'='*60}")
            print(f"✅ 工作流正确在人工审核处中断")
            print(f"{'='*60}\n")
            
            # 验证数据库中的状态
            async with AsyncSessionLocal() as session:
                repo = RoadmapRepository(session)
                task = await repo.get_task_by_id(task_id)
                
                assert task is not None
                assert task.roadmap_id is not None
                print(f"✅ Task created: {task_id}")
                print(f"✅ Roadmap ID: {task.roadmap_id}")
                print(f"✅ Current Step: {task.current_step}")
                print(f"✅ Task Status: {task.status}")
                
        except asyncio.TimeoutError:
            pytest.fail("工作流执行超时（2分钟）")
        except GraphInterrupt:
            # 预期的中断
            pass
        except Exception as e:
            print(f"\n❌ 意外错误: {str(e)}")
            raise
    
    async def test_state_manager_checkpointer(self):
        """测试 StateManager 的 checkpointer 功能"""
        # checkpointer 由 OrchestratorFactory 管理
        checkpointer = OrchestratorFactory.get_checkpointer()
        
        assert checkpointer is not None
        print(f"✅ Checkpointer initialized: {type(checkpointer).__name__}")
        
        # 测试 checkpointer 的基本功能
        # 注意：这里只验证checkpointer存在且可用
        # 完整的checkpoint功能由LangGraph管理
    
    async def test_live_step_tracking(self):
        """测试 live_step 追踪功能"""
        state_manager = OrchestratorFactory.get_state_manager()
        
        test_task_id = f"test-live-{uuid.uuid4().hex[:8]}"
        
        # 设置步骤
        state_manager.set_live_step(test_task_id, "intent_analysis")
        assert state_manager.get_live_step(test_task_id) == "intent_analysis"
        
        state_manager.set_live_step(test_task_id, "curriculum_design")
        assert state_manager.get_live_step(test_task_id) == "curriculum_design"
        
        # 清除
        state_manager.clear_live_step(test_task_id)
        assert state_manager.get_live_step(test_task_id) is None
        
        print(f"✅ Live step tracking working correctly")


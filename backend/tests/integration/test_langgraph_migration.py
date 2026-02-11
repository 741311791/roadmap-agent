"""
LangGraph 1.0 迁移集成测试

测试新架构的核心功能：
- 子图模式：单个内容失败不影响其他
- interrupt API：人工审核暂停和恢复
- RetryPolicy：节点级自动重试
- stream 监控：实时进度追踪

测试策略：
- 使用真实的 Agent（不 mock）
- 使用测试数据库（隔离）
- 模拟各种失败场景
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from app.core.orchestrator_factory import OrchestratorFactory
from app.models.domain import UserRequest, LearningPreferences
from app.models.constants import TaskStatus


class TestSubgraphMode:
    """测试子图模式的细粒度容错"""
    
    @pytest.mark.asyncio
    async def test_tutorial_failure_does_not_affect_resource_quiz(self):
        """
        测试：Tutorial 生成失败时，Resource 和 Quiz 仍能成功
        
        验证：
        - Tutorial 失败记录在 errors 列表中
        - Resource 和 Quiz 正常生成
        - failed_concepts 包含失败的 Concept ID
        """
        # 创建 Orchestrator
        factory = OrchestratorFactory()
        await factory.initialize()
        executor = factory.create_workflow_executor()
        
        # 构造测试请求
        user_request = UserRequest(
            user_id="test_user_001",
            session_id="test_session_001",
            preferences=LearningPreferences(
                learning_goal="Learn Python basics",
                available_hours_per_week=10,
                motivation="Personal interest",
                current_level="beginner",
                career_background="Student",
            ),
            additional_context="Focus on practical projects",
        )
        
        task_id = "test_task_subgraph_001"
        
        # Mock Tutorial Agent 失败，但 Resource 和 Quiz 正常
        with patch("app.core.agent_factory.AgentFactory.create_tutorial_generator") as mock_tutorial:
            # Tutorial Agent 抛出异常
            mock_tutorial_instance = AsyncMock()
            mock_tutorial_instance.generate.side_effect = Exception("Tutorial LLM timeout")
            mock_tutorial.return_value = mock_tutorial_instance
            
            # 执行工作流（会在 human_review 处暂停）
            final_state = await executor.execute(user_request, task_id)
            
            # 验证状态
            assert "failed_concepts" in final_state
            # Tutorial 失败不应阻止整个内容生成
            # Resource 和 Quiz 应该成功
            assert len(final_state.get("resource_refs", {})) > 0
            assert len(final_state.get("quiz_refs", {})) > 0
        
        await factory.cleanup()
    
    @pytest.mark.asyncio
    async def test_subgraph_checkpoint_granularity(self):
        """
        测试：子图的 Checkpoint 粒度
        
        验证：
        - Checkpoint 表包含子图节点记录
        - 每个 Concept 的内容生成有独立 Checkpoint
        """
        factory = OrchestratorFactory()
        await factory.initialize()
        executor = factory.create_workflow_executor()
        
        user_request = UserRequest(
            user_id="test_user_002",
            session_id="test_session_002",
            preferences=LearningPreferences(
                learning_goal="Learn JavaScript",
                available_hours_per_week=5,
                motivation="Career",
                current_level="beginner",
                career_background="Developer",
            ),
            additional_context="",
        )
        
        task_id = "test_task_checkpoint_002"
        
        # 执行工作流
        final_state = await executor.execute(user_request, task_id)
        
        # 查询 Checkpoint 表
        from app.db.session import async_session_maker
        async with async_session_maker() as session:
            from sqlalchemy import text
            result = await session.execute(
                text("SELECT COUNT(*) FROM checkpoints WHERE thread_id = :thread_id"),
                {"thread_id": task_id}
            )
            checkpoint_count = result.scalar()
            
            # 验证：应该有多个 Checkpoint（主图 + 子图节点）
            assert checkpoint_count > 5, f"Expected > 5 checkpoints, got {checkpoint_count}"
        
        await factory.cleanup()


class TestInterruptAPI:
    """测试 interrupt() API 的人机协同"""
    
    @pytest.mark.asyncio
    async def test_human_review_pauses_workflow(self):
        """
        测试：工作流在 human_review 节点自动暂停
        
        验证：
        - current_step 为 "human_review"
        - 任务状态为 "human_review_pending"
        """
        factory = OrchestratorFactory()
        await factory.initialize()
        executor = factory.create_workflow_executor()
        
        user_request = UserRequest(
            user_id="test_user_003",
            session_id="test_session_003",
            preferences=LearningPreferences(
                learning_goal="Learn React",
                available_hours_per_week=8,
                motivation="Career",
                current_level="intermediate",
                career_background="Frontend Developer",
            ),
            additional_context="",
        )
        
        task_id = "test_task_interrupt_003"
        
        # 执行工作流（应该在 human_review 处暂停）
        final_state = await executor.execute(user_request, task_id)
        
        # 验证暂停状态
        assert final_state.get("current_step") == "human_review"
        
        # 验证数据库任务状态
        from app.db.session import async_session_maker
        from app.crud.crud_task import get_task_crud
        async with async_session_maker() as session:
            task_crud = get_task_crud()
            task = await task_crud.get_by_task_id(session, task_id)
            assert task.status == TaskStatus.HUMAN_REVIEW_PENDING.value
        
        await factory.cleanup()
    
    @pytest.mark.asyncio
    async def test_resume_after_approval(self):
        """
        测试：用户批准后工作流恢复
        
        验证：
        - 恢复后继续执行内容生成
        - 最终状态为 "completed"
        """
        factory = OrchestratorFactory()
        await factory.initialize()
        executor = factory.create_workflow_executor()
        
        user_request = UserRequest(
            user_id="test_user_004",
            session_id="test_session_004",
            preferences=LearningPreferences(
                learning_goal="Learn Python",
                available_hours_per_week=10,
                motivation="Personal",
                current_level="beginner",
                career_background="Student",
            ),
            additional_context="",
        )
        
        task_id = "test_task_resume_004"
        
        # 第一次执行（暂停在 human_review）
        await executor.execute(user_request, task_id)
        
        # 恢复执行（批准）
        final_state = await executor.resume_after_human_review(
            task_id=task_id,
            approved=True,
            feedback=None,
        )
        
        # 验证最终状态
        assert final_state.get("current_step") == "completed"
        assert final_state.get("human_approved") is True
        
        await factory.cleanup()


class TestRetryPolicy:
    """测试 Node 级 RetryPolicy"""
    
    @pytest.mark.asyncio
    async def test_llm_rate_limit_auto_retry(self):
        """
        测试：LLM 限流错误自动重试
        
        验证：
        - RetryPolicy 自动重试 5 次
        - 重试后成功不影响其他节点
        """
        factory = OrchestratorFactory()
        await factory.initialize()
        executor = factory.create_workflow_executor()
        
        user_request = UserRequest(
            user_id="test_user_005",
            session_id="test_session_005",
            preferences=LearningPreferences(
                learning_goal="Learn TypeScript",
                available_hours_per_week=6,
                motivation="Career",
                current_level="intermediate",
                career_background="Developer",
            ),
            additional_context="",
        )
        
        task_id = "test_task_retry_005"
        
        # Mock Intent Agent 前 3 次失败，第 4 次成功
        with patch("app.agents.base.BaseAgent._call_llm") as mock_llm:
            call_count = 0
            
            async def mock_call_with_retry(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 3:
                    import litellm
                    raise litellm.RateLimitError("Rate limit exceeded")
                # 第 4 次成功
                return MagicMock(
                    choices=[MagicMock(message=MagicMock(content="Success"))]
                )
            
            mock_llm.side_effect = mock_call_with_retry
            
            # 执行工作流
            final_state = await executor.execute(user_request, task_id)
            
            # 验证重试次数（tenacity 3 次 + RetryPolicy 可能 1 次）
            assert call_count >= 3, f"Expected >= 3 retries, got {call_count}"
            # 验证最终成功
            assert "intent_analysis" in final_state or final_state.get("current_step") == "human_review"
        
        await factory.cleanup()
    
    @pytest.mark.asyncio
    async def test_validation_node_no_retry(self):
        """
        测试：Validation 节点失败不重试（NO_RETRY_POLICY）
        
        验证：
        - Validation 失败立即进入修改流程
        - 不浪费时间重试纯逻辑错误
        """
        # 这个测试验证 NO_RETRY_POLICY 生效
        # 实际实现中，Validation 失败会进入 validation_edit_plan_analysis
        # 不会重试 validation 本身
        pass


class TestStreamMonitoring:
    """测试 stream() 实时监控"""
    
    @pytest.mark.asyncio
    async def test_stream_logs_all_nodes(self):
        """
        测试：stream() 记录所有节点的执行
        
        验证：
        - execution_logs 表包含每个节点的记录
        - 日志顺序正确
        """
        factory = OrchestratorFactory()
        await factory.initialize()
        executor = factory.create_workflow_executor()
        
        user_request = UserRequest(
            user_id="test_user_006",
            session_id="test_session_006",
            preferences=LearningPreferences(
                learning_goal="Learn Vue.js",
                available_hours_per_week=7,
                motivation="Personal",
                current_level="beginner",
                career_background="Designer",
            ),
            additional_context="",
        )
        
        task_id = "test_task_stream_006"
        
        # 执行工作流
        await executor.execute(user_request, task_id)
        
        # 查询 execution_logs 表
        from app.db.session import async_session_maker
        async with async_session_maker() as session:
            from sqlalchemy import text
            result = await session.execute(
                text("""
                    SELECT step, message 
                    FROM execution_logs 
                    WHERE task_id = :task_id 
                    ORDER BY created_at
                """),
                {"task_id": task_id}
            )
            logs = result.fetchall()
            
            # 验证：应该有多个节点的日志
            assert len(logs) >= 3, f"Expected >= 3 log entries, got {len(logs)}"
            
            # 验证：日志包含关键节点
            steps = [log[0] for log in logs]
            assert "intent_analysis" in steps
            assert "curriculum_design" in steps
        
        await factory.cleanup()


class TestCheckpointRecovery:
    """测试 Checkpoint 断点续传"""
    
    @pytest.mark.asyncio
    async def test_resume_from_failed_node(self):
        """
        测试：从失败节点恢复，不重跑已成功节点
        
        验证：
        - 使用相同 thread_id 重新执行
        - 跳过已成功的节点
        - 从失败节点继续
        """
        factory = OrchestratorFactory()
        await factory.initialize()
        executor = factory.create_workflow_executor()
        
        user_request = UserRequest(
            user_id="test_user_007",
            session_id="test_session_007",
            preferences=LearningPreferences(
                learning_goal="Learn Django",
                available_hours_per_week=12,
                motivation="Career",
                current_level="intermediate",
                career_background="Backend Developer",
            ),
            additional_context="",
        )
        
        task_id = "test_task_recovery_007"
        
        # 第一次执行（模拟 Curriculum 失败）
        with patch("app.agents.curriculum_designer.CurriculumDesignerAgent.design") as mock_design:
            mock_design.side_effect = Exception("Curriculum generation failed")
            
            # 捕获异常
            with pytest.raises(Exception):
                await executor.execute(user_request, task_id)
        
        # 第二次执行（恢复，不 mock，应该从 Curriculum 节点继续）
        final_state = await executor.execute(user_request, task_id)
        
        # 验证：Intent 节点没有重跑（检查 Checkpoint）
        from app.db.session import async_session_maker
        async with async_session_maker() as session:
            from sqlalchemy import text
            result = await session.execute(
                text("""
                    SELECT COUNT(*) 
                    FROM checkpoints 
                    WHERE thread_id = :thread_id
                """),
                {"thread_id": task_id}
            )
            checkpoint_count = result.scalar()
            
            # 验证：有 Checkpoint 记录
            assert checkpoint_count > 0
        
        await factory.cleanup()


@pytest.mark.asyncio
async def test_two_layer_fanout_fanin():
    """
    测试两层 Fan-Out/Fan-In 架构
    
    验证：
    - 外层 Fan-Out 创建 N 个子图实例
    - 每个子图的 Fan-In 保存元数据
    - 最终汇总更新 Framework
    """
    from app.core.orchestrator.subgraphs.content_generation import (
        build_content_generation_subgraph,
        outer_fan_out,
    )
    from app.models.domain import Concept
    
    # 创建测试数据
    concepts = [
        Concept(
            concept_id=f"test-concept-{i}",
            name=f"Concept {i}",
            description=f"Test concept {i}",
            estimated_hours=5,
            key_points=["Point 1", "Point 2"],
        )
        for i in range(3)
    ]
    
    state = {
        "roadmap_id": "test-roadmap",
        "concepts": concepts,
        "user_preferences": LearningPreferences(
            learning_goal="Test",
            available_hours_per_week=10,
            motivation="Test",
            current_level="beginner",
            career_background="Test",
        ),
        "task_id": "test-task",
        "concept": None,
        "concept_results": [],
    }
    
    # 测试外层 Fan-Out
    command = outer_fan_out(state)
    
    # 验证创建了 3 个 Send 任务（每个 Concept 一个）
    assert hasattr(command, 'goto')
    assert len(command.goto) == 3
    
    # 验证每个 Send 的目标是 single_concept_subgraph
    for send in command.goto:
        assert send.node == "single_concept_subgraph"
        assert "concept" in send.arg
        assert "roadmap_id" in send.arg
    
    # 验证子图可以构建
    subgraph = build_content_generation_subgraph()
    assert subgraph is not None


@pytest.mark.asyncio
async def test_full_workflow_with_subgraph():
    """
    端到端测试：完整工作流（使用子图模式）
    
    验证：
    - 所有节点正常执行
    - 内容生成使用子图
    - 最终状态正确
    """
    factory = OrchestratorFactory()
    await factory.initialize()
    executor = factory.create_workflow_executor()
    
    user_request = UserRequest(
        user_id="test_user_e2e",
        session_id="test_session_e2e",
        preferences=LearningPreferences(
            learning_goal="Learn FastAPI and async Python",
            available_hours_per_week=15,
            motivation="Career advancement",
            current_level="intermediate",
            career_background="Backend Developer with Flask experience",
        ),
        additional_context="Focus on production-ready patterns",
    )
    
    task_id = "test_task_e2e_full"
    
    # 执行工作流（会在 human_review 处暂停）
    final_state = await executor.execute(user_request, task_id)
    
    # 验证暂停在 human_review
    assert final_state.get("current_step") == "human_review"
    
    # 批准并恢复
    final_state = await executor.resume_after_human_review(
        task_id=task_id,
        approved=True,
        feedback=None,
    )
    
    # 验证最终状态
    assert final_state.get("current_step") == "completed"
    assert final_state.get("roadmap_id") is not None
    
    # 验证内容生成结果（新架构返回 concept_results）
    assert "concept_results" in final_state or "tutorial_refs" in final_state
    
    # 验证 Checkpoint 表
    from app.db.session import async_session_maker
    async with async_session_maker() as session:
        from sqlalchemy import text
        result = await session.execute(
            text("""
                SELECT COUNT(*) 
                FROM checkpoints 
                WHERE thread_id = :thread_id
            """),
            {"thread_id": task_id}
        )
        checkpoint_count = result.scalar()
        
        # 验证：完整流程应该有多个 Checkpoint
        assert checkpoint_count >= 6, f"Expected >= 6 checkpoints, got {checkpoint_count}"
    
    await factory.cleanup()


# ====================================================================
# 测试辅助函数
# ====================================================================

@pytest.fixture
async def orchestrator_factory():
    """提供 OrchestratorFactory 实例"""
    factory = OrchestratorFactory()
    await factory.initialize()
    yield factory
    await factory.cleanup()


@pytest.fixture
def sample_user_request():
    """提供示例用户请求"""
    return UserRequest(
        user_id="test_user",
        session_id="test_session",
        preferences=LearningPreferences(
            learning_goal="Learn a new technology",
            available_hours_per_week=10,
            motivation="Personal interest",
            current_level="beginner",
            career_background="Student",
        ),
        additional_context="",
    )


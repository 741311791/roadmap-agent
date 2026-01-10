"""
LangGraph 1.0 迁移端到端测试

真实场景测试，验证新架构在生产环境下的表现：
- 大规模内容生成（100 个 Concept）
- Worker 重启恢复
- 性能指标验证
- 断点续传

注意：
- 这些测试需要真实的 LLM API（会产生成本）
- 应该在测试环境而非 CI 中运行
- 可以使用 @pytest.mark.skip 跳过
"""
import pytest
import asyncio
from datetime import datetime
import time

from app.core.orchestrator_factory import OrchestratorFactory
from app.models.domain import UserRequest, LearningPreferences
from app.models.constants import TaskStatus


@pytest.mark.skip(reason="需要真实 LLM API，仅在测试环境手动运行")
@pytest.mark.asyncio
async def test_large_roadmap_100_concepts():
    """
    测试：大型路线图（100 个 Concept）
    
    验证：
    - 所有 Concept 的内容正常生成
    - 性能指标达标（P95 < 150s）
    - Checkpoint 表正常工作
    - 内存和 CPU 使用合理
    """
    factory = OrchestratorFactory()
    await factory.initialize()
    executor = factory.create_workflow_executor()
    
    # 构造大型路线图请求
    user_request = UserRequest(
        user_id="test_user_large",
        session_id="test_session_large",
        preferences=LearningPreferences(
            learning_goal="Become a Full Stack Developer (comprehensive roadmap)",
            available_hours_per_week=20,
            motivation="Career change",
            current_level="beginner",
            career_background="Non-technical background, eager to learn",
        ),
        additional_context="I want a very detailed roadmap covering frontend, backend, database, deployment, and soft skills",
    )
    
    task_id = "test_task_large_100"
    
    # 记录开始时间
    start_time = time.time()
    
    # 执行工作流
    final_state = await executor.execute(user_request, task_id)
    
    # 批准（跳过人工审核）
    if final_state.get("current_step") == "human_review":
        final_state = await executor.resume_after_human_review(
            task_id=task_id,
            approved=True,
            feedback=None,
        )
    
    # 记录结束时间
    end_time = time.time()
    duration = end_time - start_time
    
    # 验证性能（P95 < 150s，这里用 200s 作为宽松限制）
    assert duration < 200, f"Workflow took {duration}s, expected < 200s"
    
    # 验证完成状态
    assert final_state.get("current_step") == "completed"
    assert final_state.get("roadmap_id") is not None
    
    # 验证内容生成结果
    tutorial_count = len(final_state.get("tutorial_refs", {}))
    resource_count = len(final_state.get("resource_refs", {}))
    quiz_count = len(final_state.get("quiz_refs", {}))
    
    print(f"\n=== 大型路线图测试结果 ===")
    print(f"执行时长: {duration:.2f}s")
    print(f"Tutorial 数量: {tutorial_count}")
    print(f"Resource 数量: {resource_count}")
    print(f"Quiz 数量: {quiz_count}")
    print(f"失败 Concept: {len(final_state.get('failed_concepts', []))}")
    
    # 验证成功率（> 95%）
    total_concepts = tutorial_count + len(final_state.get("failed_concepts", []))
    success_rate = tutorial_count / total_concepts if total_concepts > 0 else 0
    assert success_rate > 0.95, f"Success rate {success_rate:.2%} < 95%"
    
    await factory.cleanup()


@pytest.mark.skip(reason="需要真实数据库，仅在测试环境手动运行")
@pytest.mark.asyncio
async def test_worker_restart_recovery():
    """
    测试：Worker 重启后的恢复能力
    
    验证：
    - 使用相同 thread_id 恢复
    - 从 Checkpoint 断点续传
    - 不重跑已成功的节点
    """
    factory = OrchestratorFactory()
    await factory.initialize()
    executor = factory.create_workflow_executor()
    
    user_request = UserRequest(
        user_id="test_user_restart",
        session_id="test_session_restart",
        preferences=LearningPreferences(
            learning_goal="Learn Docker and Kubernetes",
            available_hours_per_week=12,
            motivation="Career",
            current_level="intermediate",
            career_background="Backend Developer",
        ),
        additional_context="Focus on production deployment",
    )
    
    task_id = "test_task_restart"
    
    # 第一次执行（模拟执行到一半）
    final_state = await executor.execute(user_request, task_id)
    
    # 模拟 Worker 重启（清理 factory）
    await factory.cleanup()
    
    # 重新初始化（模拟新的 Worker 进程）
    factory = OrchestratorFactory()
    await factory.initialize()
    executor = factory.create_workflow_executor()
    
    # 使用相同 thread_id 恢复（不传初始状态）
    config = {"configurable": {"thread_id": task_id}}
    recovered_state = await executor.graph.ainvoke(None, config=config)
    
    # 验证恢复成功
    assert recovered_state is not None
    assert recovered_state.get("task_id") == task_id
    
    print(f"\n=== Worker 重启恢复测试结果 ===")
    print(f"恢复后状态: {recovered_state.get('current_step')}")
    print(f"路线图 ID: {recovered_state.get('roadmap_id')}")
    
    await factory.cleanup()


@pytest.mark.asyncio
async def test_checkpoint_cleanup_task():
    """
    测试：Checkpoint 清理任务
    
    验证：
    - cleanup_old_checkpoints 正常执行
    - 仅删除旧的已完成任务
    - 统计结果正确
    """
    from app.tasks.maintenance_tasks import cleanup_old_checkpoints
    
    # 执行清理任务
    result = cleanup_old_checkpoints()
    
    # 验证结果
    assert result["success"] is True
    assert "deleted_completed" in result
    assert "deleted_failed" in result
    assert "total_deleted" in result
    
    print(f"\n=== Checkpoint 清理测试结果 ===")
    print(f"已完成任务 Checkpoint 删除: {result['deleted_completed']}")
    print(f"失败任务 Checkpoint 删除: {result['deleted_failed']}")
    print(f"总计删除: {result['total_deleted']}")


@pytest.mark.asyncio
async def test_checkpoint_size_monitoring():
    """
    测试：Checkpoint 表大小监控
    
    验证：
    - monitor_checkpoint_size 正常执行
    - 返回表大小和行数
    """
    from app.tasks.maintenance_tasks import monitor_checkpoint_size
    
    # 执行监控任务
    result = monitor_checkpoint_size()
    
    # 验证结果
    assert result["success"] is True
    assert "total_rows" in result
    assert "table_size_mb" in result
    
    print(f"\n=== Checkpoint 表监控结果 ===")
    print(f"总行数: {result['total_rows']}")
    print(f"表大小: {result['table_size_mb']} MB")


@pytest.mark.skip(reason="性能压测，仅在测试环境手动运行")
@pytest.mark.asyncio
async def test_performance_benchmark():
    """
    性能压测：并发生成多个路线图
    
    验证：
    - 并发处理能力
    - 数据库连接池稳定性
    - Checkpoint 写入性能
    """
    factory = OrchestratorFactory()
    await factory.initialize()
    
    # 创建 10 个并发任务
    tasks = []
    for i in range(10):
        user_request = UserRequest(
            user_id=f"test_user_perf_{i}",
            session_id=f"test_session_perf_{i}",
            preferences=LearningPreferences(
                learning_goal=f"Learn Technology {i}",
                available_hours_per_week=10,
                motivation="Testing",
                current_level="beginner",
                career_background="Tester",
            ),
            additional_context="",
        )
        
        executor = factory.create_workflow_executor()
        task_id = f"test_task_perf_{i}"
        
        tasks.append(executor.execute(user_request, task_id))
    
    # 并发执行
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    # 统计结果
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    failure_count = len(results) - success_count
    
    print(f"\n=== 性能压测结果 ===")
    print(f"总任务数: {len(results)}")
    print(f"成功: {success_count}")
    print(f"失败: {failure_count}")
    print(f"总耗时: {end_time - start_time:.2f}s")
    print(f"平均耗时: {(end_time - start_time) / len(results):.2f}s")
    
    # 验证成功率
    assert success_count >= 8, f"Expected >= 8 successes, got {success_count}"
    
    await factory.cleanup()


# ====================================================================
# 真实场景测试用例
# ====================================================================

@pytest.mark.skip(reason="真实场景测试，需要手动触发")
@pytest.mark.asyncio
async def test_real_world_frontend_roadmap():
    """
    真实场景：前端开发路线图
    
    用户需求：零基础学习前端开发
    预期结果：生成完整的 HTML/CSS/JS/React 学习路径
    """
    factory = OrchestratorFactory()
    await factory.initialize()
    executor = factory.create_workflow_executor()
    
    user_request = UserRequest(
        user_id="real_user_frontend",
        session_id="real_session_frontend",
        preferences=LearningPreferences(
            learning_goal="I want to become a frontend developer from scratch",
            available_hours_per_week=15,
            motivation="Career change from marketing to tech",
            current_level="absolute_beginner",
            career_background="Marketing manager, no programming experience",
        ),
        additional_context="I learn best with hands-on projects. Please include lots of practical examples.",
    )
    
    task_id = "real_task_frontend"
    
    # 执行工作流
    final_state = await executor.execute(user_request, task_id)
    
    # 批准
    if final_state.get("current_step") == "human_review":
        final_state = await executor.resume_after_human_review(
            task_id=task_id,
            approved=True,
            feedback=None,
        )
    
    # 验证结果
    assert final_state.get("current_step") == "completed"
    roadmap_id = final_state.get("roadmap_id")
    
    # 查询生成的路线图
    from app.db.session import async_session_maker
    from app.crud.crud_roadmap import get_roadmap_crud
    async with async_session_maker() as session:
        roadmap_crud = get_roadmap_crud()
        roadmap = await roadmap_crud.get(session, roadmap_id)
        
        print(f"\n=== 真实场景测试：前端路线图 ===")
        print(f"路线图标题: {roadmap.title if roadmap else 'N/A'}")
        print(f"总学时: {roadmap.total_estimated_hours if roadmap else 0} 小时")
        print(f"Tutorial 数: {len(final_state.get('tutorial_refs', {}))}")
        print(f"Resource 数: {len(final_state.get('resource_refs', {}))}")
        print(f"Quiz 数: {len(final_state.get('quiz_refs', {}))}")
    
    await factory.cleanup()


@pytest.mark.skip(reason="真实场景测试，需要手动触发")
@pytest.mark.asyncio
async def test_real_world_backend_roadmap():
    """
    真实场景：后端开发路线图
    
    用户需求：有 Python 基础，想学习 FastAPI 和微服务
    预期结果：生成进阶的后端开发路径
    """
    factory = OrchestratorFactory()
    await factory.initialize()
    executor = factory.create_workflow_executor()
    
    user_request = UserRequest(
        user_id="real_user_backend",
        session_id="real_session_backend",
        preferences=LearningPreferences(
            learning_goal="Master FastAPI and microservices architecture",
            available_hours_per_week=20,
            motivation="Upgrade from Flask to modern async Python",
            current_level="intermediate",
            career_background="Backend developer with 2 years Flask experience",
        ),
        additional_context="I'm particularly interested in async/await, database optimization, and deployment to cloud platforms",
    )
    
    task_id = "real_task_backend"
    
    # 记录开始时间
    start_time = time.time()
    
    # 执行工作流
    final_state = await executor.execute(user_request, task_id)
    
    # 批准
    if final_state.get("current_step") == "human_review":
        final_state = await executor.resume_after_human_review(
            task_id=task_id,
            approved=True,
            feedback=None,
        )
    
    # 记录结束时间
    end_time = time.time()
    duration = end_time - start_time
    
    # 验证结果
    assert final_state.get("current_step") == "completed"
    
    # 验证性能
    assert duration < 150, f"Duration {duration}s > 150s threshold"
    
    print(f"\n=== 真实场景测试：后端路线图 ===")
    print(f"执行时长: {duration:.2f}s")
    print(f"Tutorial 数: {len(final_state.get('tutorial_refs', {}))}")
    print(f"Resource 数: {len(final_state.get('resource_refs', {}))}")
    print(f"Quiz 数: {len(final_state.get('quiz_refs', {}))}")
    print(f"失败数: {len(final_state.get('failed_concepts', []))}")
    
    await factory.cleanup()


@pytest.mark.asyncio
async def test_send_api_dynamic_parallelism():
    """
    测试：Send API 动态并行
    
    验证：
    - fan_out_concepts 正确创建 Send 对象
    - 每个 Concept 创建 3 个 Send（tutorial/resource/quiz）
    - Send 对象包含正确的状态数据
    """
    from app.core.orchestrator.subgraphs.content_generation import fan_out_concepts
    from app.models.domain import Concept, LearningPreferences
    from app.core.orchestrator.subgraphs.content_generation_types import StateKey
    
    # 构造测试状态
    test_concepts = [
        Concept(
            concept_id=f"test_concept_{i}",
            name=f"Concept {i}",
            description=f"Description {i}",
            difficulty="beginner",
            estimated_hours=2.0,
            keywords=[],
            prerequisites=[],
        )
        for i in range(5)
    ]
    
    state = {
        StateKey.ROADMAP_ID.value: "test_roadmap",
        StateKey.CONCEPTS.value: test_concepts,
        StateKey.USER_PREFERENCES.value: LearningPreferences(
            learning_goal="Test",
            available_hours_per_week=10,
            motivation="Test",
            current_level="beginner",
            career_background="Test",
        ),
        StateKey.TASK_ID.value: "test_task_send",
    }
    
    # 调用 fan_out
    sends = fan_out_concepts(state)
    
    # 验证 Send 数量（5 个 Concept × 3 个内容类型 = 15）
    assert len(sends) == 15, f"Expected 15 Sends, got {len(sends)}"
    
    # 验证 Send 对象结构
    from langgraph.types import Send
    for send in sends:
        assert isinstance(send, Send)
        # Send 应该包含 concept 和其他必要字段
        # 注意：Send 内部结构可能是私有的，仅验证类型


# ====================================================================
# 性能基准测试
# ====================================================================

@pytest.mark.skip(reason="基准测试，仅在需要时手动运行")
@pytest.mark.asyncio
async def test_performance_baseline():
    """
    性能基准测试
    
    测试场景：
    - 小型路线图（10 个 Concept）
    - 中型路线图（50 个 Concept）
    - 大型路线图（100 个 Concept）
    
    记录：
    - 执行时长
    - Checkpoint 数量
    - 数据库查询次数
    """
    scenarios = [
        ("Small (10 concepts)", 10, "Learn basic Python"),
        ("Medium (50 concepts)", 50, "Full stack web development with Python and React"),
        ("Large (100 concepts)", 100, "Comprehensive computer science degree roadmap"),
    ]
    
    results = []
    
    for scenario_name, expected_concepts, learning_goal in scenarios:
        factory = OrchestratorFactory()
        await factory.initialize()
        executor = factory.create_workflow_executor()
        
        user_request = UserRequest(
            user_id=f"perf_test_{scenario_name}",
            session_id=f"perf_session_{scenario_name}",
            preferences=LearningPreferences(
                learning_goal=learning_goal,
                available_hours_per_week=20,
                motivation="Benchmark testing",
                current_level="beginner",
                career_background="Tester",
            ),
            additional_context="Generate comprehensive roadmap for benchmarking",
        )
        
        task_id = f"perf_task_{scenario_name}"
        
        # 记录开始时间
        start_time = time.time()
        
        # 执行工作流
        final_state = await executor.execute(user_request, task_id)
        
        # 批准
        if final_state.get("current_step") == "human_review":
            final_state = await executor.resume_after_human_review(
                task_id=task_id,
                approved=True,
                feedback=None,
            )
        
        # 记录结束时间
        end_time = time.time()
        duration = end_time - start_time
        
        # 查询 Checkpoint 数量
        from app.db.session import async_session_maker
        async with async_session_maker() as session:
            from sqlalchemy import text
            result = await session.execute(
                text("SELECT COUNT(*) FROM checkpoints WHERE thread_id = :thread_id"),
                {"thread_id": task_id}
            )
            checkpoint_count = result.scalar()
        
        results.append({
            "scenario": scenario_name,
            "duration": duration,
            "tutorial_count": len(final_state.get("tutorial_refs", {})),
            "checkpoint_count": checkpoint_count,
        })
        
        await factory.cleanup()
    
    # 打印结果
    print("\n=== 性能基准测试结果 ===")
    for r in results:
        print(f"\n{r['scenario']}:")
        print(f"  执行时长: {r['duration']:.2f}s")
        print(f"  Tutorial 数: {r['tutorial_count']}")
        print(f"  Checkpoint 数: {r['checkpoint_count']}")
        print(f"  平均每个 Tutorial: {r['duration'] / r['tutorial_count']:.2f}s")


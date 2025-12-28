"""
Celery 日志集成测试

测试场景：
1. 完整工作流中的日志写入
2. 重试场景中的日志写入
3. 高并发场景下的连接池占用
4. Celery Worker 真实执行任务

注意：这些测试需要 Redis 和 Celery Worker 运行。
"""
import pytest
import asyncio
from unittest.mock import patch
from app.services.execution_logger import execution_logger, LogCategory
from app.models.database import ExecutionLog
from app.db.session import safe_session
from sqlalchemy import select


@pytest.mark.integration
class TestCeleryLogIntegration:
    """Celery 日志集成测试"""
    
    @pytest.mark.asyncio
    async def test_log_written_to_database(self):
        """测试：日志最终写入数据库"""
        task_id = "integration-test-1"
        
        # 写入日志
        await execution_logger.info(
            task_id=task_id,
            category=LogCategory.WORKFLOW,
            message="集成测试日志",
        )
        
        # 手动刷新
        await execution_logger.flush()
        
        # 等待 Celery Worker 处理
        await asyncio.sleep(3)
        
        # 验证数据库中有日志
        async with safe_session() as session:
            result = await session.execute(
                select(ExecutionLog).where(ExecutionLog.task_id == task_id)
            )
            logs = result.scalars().all()
            
            assert len(logs) > 0
            assert logs[0].message == "集成测试日志"
            assert logs[0].category == LogCategory.WORKFLOW
    
    @pytest.mark.asyncio
    async def test_batch_logs_written_together(self):
        """测试：批量日志一起写入"""
        task_id = "integration-test-2"
        
        # 写入多条日志
        for i in range(10):
            await execution_logger.info(
                task_id=task_id,
                category=LogCategory.AGENT,
                message=f"批量日志 {i}",
                details={"index": i},
            )
        
        # 手动刷新
        await execution_logger.flush()
        
        # 等待 Celery Worker 处理
        await asyncio.sleep(3)
        
        # 验证数据库中有所有日志
        async with safe_session() as session:
            result = await session.execute(
                select(ExecutionLog)
                .where(ExecutionLog.task_id == task_id)
                .order_by(ExecutionLog.created_at)
            )
            logs = result.scalars().all()
            
            assert len(logs) == 10
            for i, log in enumerate(logs):
                assert log.message == f"批量日志 {i}"
                assert log.details["index"] == i
    
    @pytest.mark.asyncio
    async def test_high_concurrency_logging(self):
        """测试：高并发日志写入"""
        task_id = "integration-test-3"
        
        async def write_logs(batch_id: int):
            """写入一批日志"""
            for i in range(20):
                await execution_logger.info(
                    task_id=task_id,
                    category=LogCategory.AGENT,
                    message=f"并发日志 batch={batch_id} i={i}",
                    details={"batch_id": batch_id, "index": i},
                )
        
        # 并发写入 10 批日志（共 200 条）
        await asyncio.gather(*[write_logs(i) for i in range(10)])
        
        # 手动刷新
        await execution_logger.flush()
        
        # 等待 Celery Worker 处理
        await asyncio.sleep(5)
        
        # 验证数据库中有所有日志
        async with safe_session() as session:
            result = await session.execute(
                select(ExecutionLog).where(ExecutionLog.task_id == task_id)
            )
            logs = result.scalars().all()
            
            assert len(logs) == 200
    
    @pytest.mark.asyncio
    async def test_workflow_complete_flow(self):
        """测试：完整工作流日志记录"""
        task_id = "integration-test-4"
        roadmap_id = "roadmap-test-1"
        
        # 模拟工作流各阶段
        await execution_logger.log_workflow_start(
            task_id=task_id,
            step="intent_analysis",
            message="开始需求分析",
            roadmap_id=roadmap_id,
        )
        
        await execution_logger.log_agent_start(
            task_id=task_id,
            agent_name="IntentAnalyzer",
            message="开始执行 IntentAnalyzer",
        )
        
        await execution_logger.log_agent_complete(
            task_id=task_id,
            agent_name="IntentAnalyzer",
            message="IntentAnalyzer 执行完成",
            duration_ms=1500,
        )
        
        await execution_logger.log_workflow_complete(
            task_id=task_id,
            step="intent_analysis",
            message="需求分析完成",
            duration_ms=2000,
            roadmap_id=roadmap_id,
        )
        
        # 手动刷新
        await execution_logger.flush()
        
        # 等待 Celery Worker 处理
        await asyncio.sleep(3)
        
        # 验证数据库中有完整日志
        async with safe_session() as session:
            result = await session.execute(
                select(ExecutionLog)
                .where(ExecutionLog.task_id == task_id)
                .order_by(ExecutionLog.created_at)
            )
            logs = result.scalars().all()
            
            assert len(logs) == 4
            assert logs[0].step == "intent_analysis"
            assert "开始需求分析" in logs[0].message
            assert logs[1].agent_name == "IntentAnalyzer"
            assert logs[2].duration_ms == 1500
            assert logs[3].duration_ms == 2000
    
    @pytest.mark.asyncio
    async def test_retry_scenario_logging(self):
        """测试：重试场景日志记录"""
        task_id = "integration-test-5"
        roadmap_id = "roadmap-test-2"
        
        # 模拟重试场景
        await execution_logger.log_retry_start(
            task_id=task_id,
            message="开始重试任务",
            roadmap_id=roadmap_id,
            details={"retry_count": 1, "reason": "超时"},
        )
        
        await execution_logger.log_agent_error(
            task_id=task_id,
            agent_name="TutorialGenerator",
            message="教程生成失败",
            error="TimeoutError: 生成超时",
        )
        
        await execution_logger.log_retry_complete(
            task_id=task_id,
            message="重试完成",
            duration_ms=5000,
            roadmap_id=roadmap_id,
            details={"success": False},
        )
        
        # 手动刷新
        await execution_logger.flush()
        
        # 等待 Celery Worker 处理
        await asyncio.sleep(3)
        
        # 验证数据库中有重试日志
        async with safe_session() as session:
            result = await session.execute(
                select(ExecutionLog)
                .where(ExecutionLog.task_id == task_id)
                .order_by(ExecutionLog.created_at)
            )
            logs = result.scalars().all()
            
            assert len(logs) == 3
            assert logs[0].category == LogCategory.RETRY
            assert logs[1].level == "error"
            assert logs[2].details["success"] is False


@pytest.mark.integration
@pytest.mark.slow
class TestCeleryPerformance:
    """Celery 性能测试"""
    
    @pytest.mark.asyncio
    async def test_connection_pool_usage_under_load(self):
        """测试：高负载下连接池占用情况"""
        from app.db.session import get_pool_status
        
        # 获取初始连接池状态
        initial_pool = get_pool_status()
        initial_connections = initial_pool["connections_in_use"]
        
        task_id = "performance-test-1"
        
        # 模拟内容生成阶段（大量并发日志写入）
        async def generate_concept_logs(concept_id: int):
            """模拟单个概念的日志写入"""
            for i in range(10):
                await execution_logger.info(
                    task_id=task_id,
                    category=LogCategory.AGENT,
                    message=f"生成教程内容 concept={concept_id} step={i}",
                    concept_id=f"concept-{concept_id}",
                )
        
        # 模拟 100 个概念的并发生成（共 1000 条日志）
        await asyncio.gather(*[generate_concept_logs(i) for i in range(100)])
        
        # 获取峰值连接池状态
        peak_pool = get_pool_status()
        peak_connections = peak_pool["connections_in_use"]
        
        # 验证：连接池占用增长不超过 5 个连接
        # （因为日志写入是异步的，不占用主应用连接池）
        assert peak_connections - initial_connections <= 5
        
        # 手动刷新
        await execution_logger.flush()
        
        # 等待 Celery Worker 处理
        await asyncio.sleep(10)
        
        # 验证所有日志都写入了
        async with safe_session() as session:
            result = await session.execute(
                select(ExecutionLog).where(ExecutionLog.task_id == task_id)
            )
            logs = result.scalars().all()
            
            assert len(logs) == 1000


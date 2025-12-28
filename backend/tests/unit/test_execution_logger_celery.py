"""
ExecutionLogger Celery 版本单元测试

测试场景：
1. 日志写入不阻塞主流程
2. 批量发送逻辑正确
3. 优雅关闭时刷新所有日志
4. Celery 任务失败时的降级处理
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.execution_logger import ExecutionLogger, LogLevel, LogCategory


class TestExecutionLoggerCelery:
    """ExecutionLogger Celery 版本测试"""
    
    @pytest.fixture
    def logger(self):
        """创建 ExecutionLogger 实例"""
        return ExecutionLogger()
    
    @pytest.mark.asyncio
    async def test_log_non_blocking(self, logger):
        """测试：日志写入不阻塞主流程"""
        # 模拟 Celery 任务
        with patch('app.services.execution_logger.batch_write_logs') as mock_task:
            mock_task.apply_async = MagicMock()
            
            # 写入一条日志
            result = await logger.info(
                task_id="test-123",
                category=LogCategory.WORKFLOW,
                message="测试日志",
            )
            
            # 验证返回对象
            assert result.task_id == "test-123"
            assert result.level == LogLevel.INFO
            assert result.category == LogCategory.WORKFLOW
            assert result.message == "测试日志"
            
            # 验证日志在缓冲区中
            assert len(logger._log_buffer) == 1
            
            # 验证没有立即发送到 Celery（因为没达到批量大小）
            mock_task.apply_async.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_batch_flush_on_size(self, logger):
        """测试：达到批量大小时自动刷新"""
        with patch('app.services.execution_logger.batch_write_logs') as mock_task:
            mock_task.apply_async = MagicMock()
            
            # 设置较小的批量大小
            logger._buffer_size = 3
            
            # 写入 3 条日志（达到批量大小）
            for i in range(3):
                await logger.info(
                    task_id=f"test-{i}",
                    category=LogCategory.WORKFLOW,
                    message=f"测试日志 {i}",
                )
            
            # 验证发送到 Celery
            mock_task.apply_async.assert_called_once()
            
            # 验证缓冲区已清空
            assert len(logger._log_buffer) == 0
    
    @pytest.mark.asyncio
    async def test_batch_flush_on_timeout(self, logger):
        """测试：超时时自动刷新"""
        with patch('app.services.execution_logger.batch_write_logs') as mock_task:
            mock_task.apply_async = MagicMock()
            
            # 设置较短的刷新间隔
            logger._flush_interval = 0.1
            
            # 写入一条日志
            await logger.info(
                task_id="test-123",
                category=LogCategory.WORKFLOW,
                message="测试日志",
            )
            
            # 等待超过刷新间隔
            await asyncio.sleep(0.2)
            
            # 再写入一条日志，触发超时检查
            await logger.info(
                task_id="test-456",
                category=LogCategory.WORKFLOW,
                message="测试日志 2",
            )
            
            # 验证发送到 Celery
            mock_task.apply_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_manual_flush(self, logger):
        """测试：手动刷新所有日志"""
        with patch('app.services.execution_logger.batch_write_logs') as mock_task:
            mock_task.apply_async = MagicMock()
            
            # 写入几条日志
            for i in range(5):
                await logger.info(
                    task_id=f"test-{i}",
                    category=LogCategory.WORKFLOW,
                    message=f"测试日志 {i}",
                )
            
            # 验证缓冲区有数据
            assert len(logger._log_buffer) == 5
            
            # 手动刷新
            await logger.flush()
            
            # 验证发送到 Celery
            mock_task.apply_async.assert_called_once()
            
            # 验证缓冲区已清空
            assert len(logger._log_buffer) == 0
    
    @pytest.mark.asyncio
    async def test_celery_send_failure_fallback(self, logger):
        """测试：Celery 发送失败时的降级处理"""
        with patch('app.services.execution_logger.batch_write_logs') as mock_task:
            # 模拟 Celery 发送失败
            mock_task.apply_async = MagicMock(side_effect=Exception("Celery 不可用"))
            
            # 设置较小的批量大小
            logger._buffer_size = 3
            
            # 写入 3 条日志（触发发送）
            for i in range(3):
                await logger.info(
                    task_id=f"test-{i}",
                    category=LogCategory.WORKFLOW,
                    message=f"测试日志 {i}",
                )
            
            # 验证尝试发送
            mock_task.apply_async.assert_called_once()
            
            # 验证日志重新放回缓冲区（降级处理）
            assert len(logger._log_buffer) == 3
    
    @pytest.mark.asyncio
    async def test_log_level_methods(self, logger):
        """测试：不同日志级别的便捷方法"""
        with patch('app.services.execution_logger.batch_write_logs'):
            # 测试 debug
            result = await logger.debug(
                task_id="test-123",
                category=LogCategory.TOOL,
                message="调试日志",
            )
            assert result.level == LogLevel.DEBUG
            
            # 测试 info
            result = await logger.info(
                task_id="test-123",
                category=LogCategory.WORKFLOW,
                message="信息日志",
            )
            assert result.level == LogLevel.INFO
            
            # 测试 warning
            result = await logger.warning(
                task_id="test-123",
                category=LogCategory.AGENT,
                message="警告日志",
            )
            assert result.level == LogLevel.WARNING
            
            # 测试 error
            result = await logger.error(
                task_id="test-123",
                category=LogCategory.DATABASE,
                message="错误日志",
            )
            assert result.level == LogLevel.ERROR
    
    @pytest.mark.asyncio
    async def test_workflow_methods(self, logger):
        """测试：工作流相关的便捷方法"""
        with patch('app.services.execution_logger.batch_write_logs'):
            # 测试 log_workflow_start
            result = await logger.log_workflow_start(
                task_id="test-123",
                step="intent_analysis",
                message="开始需求分析",
                roadmap_id="roadmap-1",
            )
            assert result.level == LogLevel.INFO
            assert result.category == LogCategory.WORKFLOW
            assert result.step == "intent_analysis"
            assert result.roadmap_id == "roadmap-1"
            
            # 测试 log_workflow_complete
            result = await logger.log_workflow_complete(
                task_id="test-123",
                step="intent_analysis",
                message="需求分析完成",
                duration_ms=1500,
                roadmap_id="roadmap-1",
            )
            assert result.level == LogLevel.INFO
            assert result.duration_ms == 1500
    
    @pytest.mark.asyncio
    async def test_agent_methods(self, logger):
        """测试：Agent 相关的便捷方法"""
        with patch('app.services.execution_logger.batch_write_logs'):
            # 测试 log_agent_start
            result = await logger.log_agent_start(
                task_id="test-123",
                agent_name="IntentAnalyzer",
                message="开始执行",
                concept_id="concept-1",
            )
            assert result.category == LogCategory.AGENT
            assert result.agent_name == "IntentAnalyzer"
            assert result.concept_id == "concept-1"
            
            # 测试 log_agent_complete
            result = await logger.log_agent_complete(
                task_id="test-123",
                agent_name="IntentAnalyzer",
                message="执行完成",
                duration_ms=2000,
                concept_id="concept-1",
            )
            assert result.duration_ms == 2000
            
            # 测试 log_agent_error
            result = await logger.log_agent_error(
                task_id="test-123",
                agent_name="IntentAnalyzer",
                message="执行失败",
                error="ValueError: 无效的输入",
                concept_id="concept-1",
            )
            assert result.level == LogLevel.ERROR
            assert result.details["error"] == "ValueError: 无效的输入"
    
    @pytest.mark.asyncio
    async def test_timed_operation_success(self, logger):
        """测试：计时上下文管理器（成功场景）"""
        with patch('app.services.execution_logger.batch_write_logs'):
            async with logger.timed_operation(
                task_id="test-123",
                category=LogCategory.AGENT,
                operation_name="TutorialGenerator",
                concept_id="concept-1",
            ) as timer:
                # 模拟操作
                await asyncio.sleep(0.1)
                timer.set_details({"title": "Python 基础教程"})
            
            # 验证记录了开始和完成日志
            assert len(logger._log_buffer) == 2
            
            # 验证开始日志
            start_log = logger._log_buffer[0]
            assert start_log["message"] == "TutorialGenerator 开始"
            assert start_log["category"] == LogCategory.AGENT
            
            # 验证完成日志
            complete_log = logger._log_buffer[1]
            assert complete_log["message"] == "TutorialGenerator 完成"
            assert complete_log["duration_ms"] >= 100  # 至少 100ms
            assert complete_log["details"]["title"] == "Python 基础教程"
    
    @pytest.mark.asyncio
    async def test_timed_operation_failure(self, logger):
        """测试：计时上下文管理器（失败场景）"""
        with patch('app.services.execution_logger.batch_write_logs'):
            with pytest.raises(ValueError):
                async with logger.timed_operation(
                    task_id="test-123",
                    category=LogCategory.AGENT,
                    operation_name="TutorialGenerator",
                    concept_id="concept-1",
                ):
                    # 模拟操作失败
                    raise ValueError("生成失败")
            
            # 验证记录了开始和错误日志
            assert len(logger._log_buffer) == 2
            
            # 验证错误日志
            error_log = logger._log_buffer[1]
            assert "失败" in error_log["message"]
            assert error_log["level"] == LogLevel.ERROR
            assert "error" in error_log["details"]


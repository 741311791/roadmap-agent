"""
Celery 任务错误端到端测试

测试 Celery 任务的错误处理机制（信号处理器）。
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock


class TestCeleryTaskFailureScenarios:
    """测试 Celery 任务失败场景"""
    
    def test_task_failure_triggers_signal_handler(self):
        """测试任务失败触发信号处理器"""
        from app.core.celery_error_handler import handle_task_failure
        
        # Mock 任务
        mock_task = type('Task', (), {'name': 'test.task.failed'})()
        test_exception = ValueError("Task execution failed")
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            # 模拟任务失败
            handle_task_failure(
                sender=mock_task,
                task_id='e2e-fail-123',
                exception=test_exception,
            )
            
            # 验证日志记录
            mock_logger.error.assert_called_once()
            call_kwargs = mock_logger.error.call_args.kwargs
            
            assert call_kwargs['task_id'] == 'e2e-fail-123'
            assert call_kwargs['task_name'] == 'test.task.failed'
            assert call_kwargs['error_type'] == 'ValueError'
            assert call_kwargs['error_message'] == 'Task execution failed'
    
    def test_database_connection_error_logged(self):
        """测试数据库连接错误被记录"""
        from app.core.celery_error_handler import handle_task_failure
        
        mock_task = type('Task', (), {'name': 'db.task'})()
        test_exception = ConnectionError("Database connection failed")
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            handle_task_failure(
                sender=mock_task,
                task_id='db-conn-fail',
                exception=test_exception,
            )
            
            call_kwargs = mock_logger.error.call_args.kwargs
            assert call_kwargs['error_type'] == 'ConnectionError'
    
    def test_timeout_error_logged(self):
        """测试超时错误被记录"""
        from app.core.celery_error_handler import handle_task_failure
        
        mock_task = type('Task', (), {'name': 'timeout.task'})()
        test_exception = TimeoutError("Task timed out after 30s")
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            handle_task_failure(
                sender=mock_task,
                task_id='timeout-task',
                exception=test_exception,
            )
            
            call_kwargs = mock_logger.error.call_args.kwargs
            assert call_kwargs['error_type'] == 'TimeoutError'


class TestCeleryTaskRetryScenarios:
    """测试 Celery 任务重试场景"""
    
    def test_task_retry_triggers_signal_handler(self):
        """测试任务重试触发信号处理器"""
        from app.core.celery_error_handler import handle_task_retry
        
        mock_task = type('Task', (), {'name': 'retry.task'})()
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            # 模拟任务重试
            handle_task_retry(
                sender=mock_task,
                task_id='retry-e2e-456',
                reason='Network connection lost',
            )
            
            # 验证日志记录
            mock_logger.info.assert_called_once()
            call_kwargs = mock_logger.info.call_args.kwargs
            
            assert call_kwargs['task_id'] == 'retry-e2e-456'
            assert call_kwargs['task_name'] == 'retry.task'
            assert call_kwargs['reason'] == 'Network connection lost'
    
    def test_exponential_backoff_calculation(self):
        """测试指数退避计算"""
        from app.core.celery_error_handler import exponential_backoff
        
        # 第一次重试：60 秒
        assert exponential_backoff(0) == 60
        
        # 第二次重试：120 秒
        assert exponential_backoff(1) == 120
        
        # 第三次重试：240 秒
        assert exponential_backoff(2) == 240


class TestTaskStatusUpdate:
    """测试任务状态更新"""
    
    @pytest.mark.asyncio
    async def test_update_task_status_to_failed(self):
        """测试更新任务状态为失败"""
        from app.core.celery_error_handler import update_task_status_failed
        
        task_id = "e2e-status-789"
        error = RuntimeError("Task processing error")
        
        # Mock 数据库会话和仓库
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.update_task_status = AsyncMock()
        
        with patch('app.core.celery_error_handler.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            with patch('app.core.celery_error_handler.RoadmapRepository') as mock_repo_class:
                mock_repo_class.return_value = mock_repo
                
                # 执行状态更新
                await update_task_status_failed(task_id, error)
                
                # 验证调用
                mock_repo.update_task_status.assert_called_once()
                call_kwargs = mock_repo.update_task_status.call_args.kwargs
                
                assert call_kwargs['task_id'] == task_id
                assert call_kwargs['status'] == 'failed'
                assert call_kwargs['current_step'] == 'failed'
                assert 'Task processing error' in call_kwargs['error_message']
                
                mock_session.commit.assert_called_once()


class TestRetryLogic:
    """测试重试逻辑"""
    
    def test_connection_error_should_retry(self):
        """测试连接错误应该重试"""
        from app.core.celery_error_handler import should_retry
        
        exc = ConnectionError("Connection refused")
        assert should_retry(exc) is True
    
    def test_timeout_error_should_retry(self):
        """测试超时错误应该重试"""
        from app.core.celery_error_handler import should_retry
        
        exc = TimeoutError("Request timeout")
        assert should_retry(exc) is True
    
    def test_value_error_should_not_retry(self):
        """测试值错误不应该重试"""
        from app.core.celery_error_handler import should_retry
        
        exc = ValueError("Invalid input data")
        assert should_retry(exc) is False
    
    def test_runtime_error_should_not_retry(self):
        """测试运行时错误不应该重试"""
        from app.core.celery_error_handler import should_retry
        
        exc = RuntimeError("Business logic error")
        assert should_retry(exc) is False


class TestCelerySignalIntegration:
    """测试 Celery 信号集成"""
    
    def test_both_signals_can_be_triggered(self):
        """测试两个信号都可以被触发"""
        from app.core.celery_error_handler import handle_task_failure, handle_task_retry
        
        mock_task = type('Task', (), {'name': 'integration.task'})()
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            # 触发重试信号
            handle_task_retry(
                sender=mock_task,
                task_id='integration-123',
                reason='First attempt',
            )
            
            # 触发失败信号
            handle_task_failure(
                sender=mock_task,
                task_id='integration-123',
                exception=RuntimeError("Final failure"),
            )
            
            # 验证两次日志调用
            assert mock_logger.info.call_count == 1
            assert mock_logger.error.call_count == 1
    
    def test_signals_work_without_task_sender(self):
        """测试信号在没有 task sender 时也能工作"""
        from app.core.celery_error_handler import handle_task_failure, handle_task_retry
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            # sender 为 None
            handle_task_failure(
                sender=None,
                task_id='no-sender-fail',
                exception=Exception("Unknown task error"),
            )
            
            handle_task_retry(
                sender=None,
                task_id='no-sender-retry',
                reason='Unknown task retry',
            )
            
            # 应该都记录了日志
            assert mock_logger.error.call_count == 1
            assert mock_logger.info.call_count == 1


class TestErrorSanitization:
    """测试错误消息清理"""
    
    @pytest.mark.asyncio
    async def test_sensitive_info_removed_from_task_status(self):
        """测试敏感信息从任务状态中移除"""
        from app.core.celery_error_handler import update_task_status_failed
        
        task_id = "sensitive-data-123"
        # 创建包含敏感信息的错误
        error = RuntimeError("Connection failed to postgresql://user:password@localhost/db")
        
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.update_task_status = AsyncMock()
        
        with patch('app.core.celery_error_handler.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            with patch('app.core.celery_error_handler.RoadmapRepository') as mock_repo_class:
                mock_repo_class.return_value = mock_repo
                
                with patch('app.core.celery_error_handler.sanitize_error_message') as mock_sanitize:
                    mock_sanitize.return_value = "An internal error occurred. Please contact support."
                    
                    await update_task_status_failed(task_id, error)
                    
                    # 验证调用了清理函数
                    mock_sanitize.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


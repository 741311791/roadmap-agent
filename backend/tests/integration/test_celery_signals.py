"""
Celery 信号处理器集成测试

测试 Celery 错误信号处理器（task_failure、task_retry）。
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from celery import Task


class TestCeleryTaskFailureSignal:
    """测试任务失败信号处理器"""
    
    def test_on_task_failure_logs_error(self):
        """测试任务失败时记录日志"""
        from app.core.celery_app import on_task_failure
        
        # Mock 任务
        mock_task = Mock(spec=Task)
        mock_task.name = "test.task"
        
        # Mock 异常
        test_exception = ValueError("Test failure")
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            # 触发信号
            on_task_failure(
                sender=mock_task,
                task_id='failure-test-123',
                exception=test_exception,
            )
            
            # 验证日志
            mock_logger.error.assert_called_once()
            call_kwargs = mock_logger.error.call_args.kwargs
            assert call_kwargs['task_id'] == 'failure-test-123'
            assert call_kwargs['task_name'] == 'test.task'
            assert call_kwargs['error_type'] == 'ValueError'
            assert call_kwargs['error_message'] == 'Test failure'
    
    def test_on_task_failure_handles_none_sender(self):
        """测试处理 sender 为 None 的情况"""
        from app.core.celery_app import on_task_failure
        
        test_exception = RuntimeError("Unknown task failed")
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            # sender 为 None
            on_task_failure(
                sender=None,
                task_id='unknown-task-456',
                exception=test_exception,
            )
            
            # 应该仍然记录日志
            mock_logger.error.assert_called_once()
            call_kwargs = mock_logger.error.call_args.kwargs
            assert call_kwargs['task_name'] == 'Unknown'
    
    def test_on_task_failure_in_production_mode(self, monkeypatch):
        """测试生产环境模式（不包含 traceback）"""
        from app.core.celery_app import on_task_failure
        
        # 设置生产环境
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "False")
        
        # 重新加载 settings
        import importlib
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        mock_task = Mock(spec=Task)
        mock_task.name = "prod.task"
        test_exception = ValueError("Production error")
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            on_task_failure(
                sender=mock_task,
                task_id='prod-123',
                exception=test_exception,
            )
            
            call_kwargs = mock_logger.error.call_args.kwargs
            # 生产环境不应包含 traceback
            assert 'traceback' not in call_kwargs or call_kwargs['traceback'] is None


class TestCeleryTaskRetrySignal:
    """测试任务重试信号处理器"""
    
    def test_on_task_retry_logs_info(self):
        """测试任务重试时记录日志"""
        from app.core.celery_app import on_task_retry
        
        mock_task = Mock(spec=Task)
        mock_task.name = "retry.task"
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            # 触发信号
            on_task_retry(
                sender=mock_task,
                task_id='retry-test-789',
                reason='Connection timeout',
            )
            
            # 验证日志
            mock_logger.info.assert_called_once()
            call_kwargs = mock_logger.info.call_args.kwargs
            assert call_kwargs['task_id'] == 'retry-test-789'
            assert call_kwargs['task_name'] == 'retry.task'
            assert call_kwargs['reason'] == 'Connection timeout'
    
    def test_on_task_retry_handles_missing_reason(self):
        """测试处理缺少 reason 参数的情况"""
        from app.core.celery_app import on_task_retry
        
        mock_task = Mock(spec=Task)
        mock_task.name = "retry.task"
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            # 不提供 reason
            on_task_retry(
                sender=mock_task,
                task_id='retry-no-reason',
            )
            
            # 应该仍然记录日志
            mock_logger.info.assert_called_once()
            call_kwargs = mock_logger.info.call_args.kwargs
            assert 'reason' in call_kwargs


class TestCelerySignalsIntegration:
    """测试 Celery 信号集成场景"""
    
    def test_signals_are_registered(self):
        """测试信号处理器已注册"""
        from celery.signals import task_failure, task_retry
        
        # 检查信号处理器是否已连接
        # 注意：这是一个基本检查，实际的信号连接由 Celery 管理
        assert len(task_failure.receivers) > 0
        assert len(task_retry.receivers) > 0
    
    def test_failure_and_retry_can_coexist(self):
        """测试失败和重试信号可以共存"""
        from app.core.celery_app import on_task_failure, on_task_retry
        
        mock_task = Mock(spec=Task)
        mock_task.name = "coexist.task"
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            # 先重试
            on_task_retry(
                sender=mock_task,
                task_id='coexist-123',
                reason='First attempt failed',
            )
            
            # 然后失败
            on_task_failure(
                sender=mock_task,
                task_id='coexist-123',
                exception=RuntimeError("Final failure"),
            )
            
            # 应该有两次日志调用
            assert mock_logger.info.call_count == 1
            assert mock_logger.error.call_count == 1


class TestSafeTaskDecorator:
    """测试 @safe_task 装饰器（概念验证）"""
    
    @pytest.mark.asyncio
    async def test_safe_task_decorator_exists(self):
        """测试 @safe_task 装饰器可导入"""
        from app.core.celery_error_handler import safe_task
        
        assert callable(safe_task)
    
    def test_safe_task_creates_celery_task(self):
        """测试 @safe_task 创建 Celery 任务"""
        from app.core.celery_error_handler import safe_task
        
        @safe_task(bind=True)
        async def test_task(self, x, y):
            return x + y
        
        # 验证是 Celery 任务
        assert hasattr(test_task, 'delay')
        assert hasattr(test_task, 'apply_async')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


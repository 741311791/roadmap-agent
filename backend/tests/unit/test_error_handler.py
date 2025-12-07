"""
测试统一错误处理器

测试 WorkflowErrorHandler 的功能和异常处理行为
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from app.core.error_handler import WorkflowErrorHandler, error_handler


@pytest.fixture
def mock_services():
    """Mock 依赖的服务"""
    with patch("app.core.error_handler.execution_logger") as mock_exec_logger, \
         patch("app.core.error_handler.notification_service") as mock_notif_service, \
         patch("app.core.error_handler.AsyncSessionLocal") as mock_session_local:
        
        # Mock execution_logger
        mock_exec_logger.error = AsyncMock()
        
        # Mock notification_service
        mock_notif_service.publish_failed = AsyncMock()
        
        # Mock database session
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.update_task_status = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        mock_session_local.return_value = mock_session
        
        # Patch RoadmapRepository
        with patch("app.core.error_handler.RoadmapRepository") as mock_repo_cls:
            mock_repo_cls.return_value = mock_repo
            
            yield {
                "exec_logger": mock_exec_logger,
                "notif_service": mock_notif_service,
                "session": mock_session,
                "repo": mock_repo,
            }


class TestWorkflowErrorHandler:
    """测试 WorkflowErrorHandler 类"""
    
    @pytest.mark.asyncio
    async def test_successful_execution(self, mock_services):
        """测试成功执行的情况"""
        handler = WorkflowErrorHandler()
        task_id = "test-trace-123"
        node_name = "test_node"
        
        async with handler.handle_node_execution(node_name, task_id) as ctx:
            # 模拟成功执行
            ctx["result"] = {"success": True, "data": "test_data"}
        
        # 验证没有调用错误处理相关的方法
        mock_services["exec_logger"].error.assert_not_called()
        mock_services["notif_service"].publish_failed.assert_not_called()
        mock_services["repo"].update_task_status.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_exception_handling(self, mock_services):
        """测试异常处理"""
        handler = WorkflowErrorHandler()
        task_id = "test-trace-456"
        node_name = "test_node"
        error_message = "Test error occurred"
        
        with pytest.raises(ValueError):
            async with handler.handle_node_execution(node_name, task_id) as ctx:
                # 模拟执行中抛出异常
                raise ValueError(error_message)
        
        # 验证错误日志记录
        mock_services["exec_logger"].error.assert_called_once()
        call_args = mock_services["exec_logger"].error.call_args
        assert call_args.kwargs["task_id"] == task_id
        assert call_args.kwargs["step"] == node_name
        assert error_message in call_args.kwargs["message"]
        
        # 验证失败通知发布
        mock_services["notif_service"].publish_failed.assert_called_once_with(
            task_id=task_id,
            error=error_message,
            step=node_name,
        )
        
        # 验证任务状态更新
        mock_services["repo"].update_task_status.assert_called_once_with(
            task_id=task_id,
            status="failed",
            current_step="failed",
            error_message=error_message[:500],
        )
        mock_services["session"].commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_exception_with_long_message(self, mock_services):
        """测试长错误消息被截断"""
        handler = WorkflowErrorHandler()
        task_id = "test-trace-789"
        node_name = "test_node"
        long_message = "X" * 1000  # 创建一个超过500字符的错误消息
        
        with pytest.raises(RuntimeError):
            async with handler.handle_node_execution(node_name, task_id) as ctx:
                raise RuntimeError(long_message)
        
        # 验证错误消息被截断到500字符
        call_args = mock_services["repo"].update_task_status.call_args
        error_msg = call_args.kwargs["error_message"]
        assert len(error_msg) == 500
        assert error_msg == long_message[:500]
    
    @pytest.mark.asyncio
    async def test_custom_step_display_name(self, mock_services):
        """测试自定义步骤显示名称"""
        handler = WorkflowErrorHandler()
        task_id = "test-trace-display"
        node_name = "intent_analysis"
        display_name = "需求分析"
        error_message = "Analysis failed"
        
        with pytest.raises(Exception):
            async with handler.handle_node_execution(
                node_name, 
                task_id, 
                step_display_name=display_name
            ) as ctx:
                raise Exception(error_message)
        
        # 验证使用了自定义显示名称
        call_args = mock_services["exec_logger"].error.call_args
        assert display_name in call_args.kwargs["message"]
    
    @pytest.mark.asyncio
    async def test_context_data_preservation(self, mock_services):
        """测试上下文数据保留"""
        handler = WorkflowErrorHandler()
        task_id = "test-trace-context"
        node_name = "test_node"
        
        async with handler.handle_node_execution(node_name, task_id) as ctx:
            ctx["intermediate_data"] = {"step1": "done"}
            ctx["result"] = {"final": "result"}
        
        # 验证上下文数据可以访问（虽然在这个测试中我们只验证了不抛异常）
        # 在实际使用中，调用方会使用 ctx["result"]
    
    @pytest.mark.asyncio
    async def test_database_update_failure_handling(self, mock_services):
        """测试数据库更新失败的处理"""
        handler = WorkflowErrorHandler()
        task_id = "test-trace-db-fail"
        node_name = "test_node"
        
        # 模拟数据库更新失败
        mock_services["repo"].update_task_status.side_effect = Exception("DB error")
        
        # 主异常仍应被抛出，数据库错误不应影响主流程
        with pytest.raises(ValueError):
            async with handler.handle_node_execution(node_name, task_id) as ctx:
                raise ValueError("Original error")
        
        # 验证尝试更新数据库
        mock_services["repo"].update_task_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_types_captured(self, mock_services):
        """测试各种错误类型都能被正确捕获"""
        handler = WorkflowErrorHandler()
        task_id = "test-trace-types"
        
        # 测试不同类型的异常
        exception_types = [
            ValueError("value error"),
            RuntimeError("runtime error"),
            KeyError("key error"),
            Exception("generic error"),
        ]
        
        for exc in exception_types:
            # 重置 mock
            for service in mock_services.values():
                if hasattr(service, "reset_mock"):
                    service.reset_mock()
            
            with pytest.raises(type(exc)):
                async with handler.handle_node_execution("test_node", task_id) as ctx:
                    raise exc
            
            # 验证错误类型被记录
            call_args = mock_services["exec_logger"].error.call_args
            assert call_args.kwargs["details"]["error_type"] == type(exc).__name__


class TestErrorHandlerSingleton:
    """测试全局错误处理器单例"""
    
    def test_global_error_handler_exists(self):
        """测试全局错误处理器实例存在"""
        from app.core.error_handler import error_handler
        assert error_handler is not None
        assert isinstance(error_handler, WorkflowErrorHandler)
    
    def test_global_error_handler_singleton(self):
        """测试全局错误处理器是单例"""
        from app.core.error_handler import error_handler as handler1
        from app.core.error_handler import error_handler as handler2
        assert handler1 is handler2


class TestErrorHandlerIntegration:
    """集成测试（模拟真实使用场景）"""
    
    @pytest.mark.asyncio
    async def test_runner_style_usage(self, mock_services):
        """测试 Runner 风格的使用方式"""
        handler = WorkflowErrorHandler()
        task_id = "integration-test-123"
        
        # 模拟 Runner 中的使用
        async def mock_agent_execute():
            """模拟 Agent 执行"""
            return {"analysis": "complete", "roadmap_id": "roadmap-123"}
        
        async with handler.handle_node_execution("intent_analysis", task_id, "需求分析") as ctx:
            # 执行 Agent
            result = await mock_agent_execute()
            
            # 处理结果
            roadmap_id = result["roadmap_id"]
            
            # 存储到上下文
            ctx["result"] = {
                "intent_analysis": result,
                "roadmap_id": roadmap_id,
                "current_step": "intent_analysis",
                "execution_history": ["需求分析完成"],
            }
        
        # 验证结果可以被访问
        assert ctx["result"]["roadmap_id"] == "roadmap-123"
        
        # 验证没有错误处理被触发
        mock_services["exec_logger"].error.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_runner_style_usage_with_failure(self, mock_services):
        """测试 Runner 风格使用时的失败情况"""
        handler = WorkflowErrorHandler()
        task_id = "integration-test-fail-456"
        
        async def mock_agent_execute_fail():
            """模拟 Agent 执行失败"""
            raise RuntimeError("LLM connection timeout")
        
        with pytest.raises(RuntimeError):
            async with handler.handle_node_execution("intent_analysis", task_id, "需求分析") as ctx:
                result = await mock_agent_execute_fail()
                ctx["result"] = result
        
        # 验证错误处理被正确触发
        mock_services["exec_logger"].error.assert_called_once()
        mock_services["notif_service"].publish_failed.assert_called_once()
        mock_services["repo"].update_task_status.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

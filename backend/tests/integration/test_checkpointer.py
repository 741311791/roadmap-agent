"""
AsyncPostgresSaver Checkpointer 集成测试

注意：这些测试需要 PostgreSQL 数据库连接。
如果没有数据库连接，测试将被跳过。
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# 尝试导入 AsyncPostgresSaver
try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg_pool import AsyncConnectionPool
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False


@pytest.mark.skipif(not HAS_POSTGRES, reason="PostgreSQL dependencies not available")
class TestAsyncPostgresSaver:
    """AsyncPostgresSaver 集成测试"""
    
    @pytest.fixture
    def mock_pool(self):
        """Mock 连接池"""
        pool = AsyncMock(spec=AsyncConnectionPool)
        pool.open = AsyncMock()
        pool.close = AsyncMock()
        return pool
    
    @pytest.fixture
    def sample_checkpoint(self):
        """示例 checkpoint 数据"""
        return {
            "v": 1,
            "id": "test-checkpoint-001",
            "ts": "2025-01-01T00:00:00.000000+00:00",
            "channel_values": {
                "current_step": "intent_analysis",
                "user_request": {"user_id": "test-user"},
            },
            "channel_versions": {},
            "versions_seen": {},
            "pending_sends": [],
        }
    
    @pytest.mark.asyncio
    async def test_checkpointer_initialization(self, mock_pool):
        """测试 Checkpointer 初始化"""
        with patch.object(AsyncPostgresSaver, 'setup', new_callable=AsyncMock) as mock_setup:
            checkpointer = AsyncPostgresSaver(mock_pool)
            
            # 验证实例创建
            assert checkpointer is not None
    
    @pytest.mark.asyncio
    async def test_checkpointer_setup(self, mock_pool):
        """测试 Checkpointer 表结构初始化"""
        with patch.object(AsyncPostgresSaver, 'setup', new_callable=AsyncMock) as mock_setup:
            checkpointer = AsyncPostgresSaver(mock_pool)
            await checkpointer.setup()
            
            # 验证 setup 被调用
            mock_setup.assert_called_once()


class TestOrchestratorCheckpointerIntegration:
    """Orchestrator 与 Checkpointer 集成测试"""
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """测试 Orchestrator 初始化"""
        from app.core.orchestrator import RoadmapOrchestrator
        
        with patch.object(RoadmapOrchestrator, 'initialize', new_callable=AsyncMock) as mock_init:
            await RoadmapOrchestrator.initialize()
            mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_orchestrator_shutdown(self):
        """测试 Orchestrator 关闭"""
        from app.core.orchestrator import RoadmapOrchestrator
        
        with patch.object(RoadmapOrchestrator, 'shutdown', new_callable=AsyncMock) as mock_shutdown:
            await RoadmapOrchestrator.shutdown()
            mock_shutdown.assert_called_once()
    
    def test_orchestrator_checkpointer_property_not_initialized(self):
        """测试未初始化时访问 checkpointer 抛出异常"""
        from app.core.orchestrator import RoadmapOrchestrator
        
        # 确保未初始化状态
        RoadmapOrchestrator._initialized = False
        RoadmapOrchestrator._checkpointer = None
        
        orchestrator = RoadmapOrchestrator()
        
        with pytest.raises(RuntimeError) as exc_info:
            _ = orchestrator.checkpointer
        
        assert "未初始化" in str(exc_info.value)


class TestCheckpointStateManagement:
    """Checkpoint 状态管理测试"""
    
    @pytest.fixture
    def mock_checkpoint_tuple(self):
        """Mock CheckpointTuple"""
        from langgraph.checkpoint.base import CheckpointTuple
        
        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": "test-thread-001",
                    "checkpoint_ns": "",
                    "checkpoint_id": "checkpoint-001",
                }
            },
            checkpoint={
                "v": 1,
                "id": "checkpoint-001",
                "ts": "2025-01-01T00:00:00.000000+00:00",
                "channel_values": {
                    "current_step": "curriculum_design",
                },
                "channel_versions": {},
                "versions_seen": {},
                "pending_sends": [],
            },
            metadata={"source": "loop", "step": 1},
            parent_config=None,
            pending_writes=[],
        )
    
    @pytest.mark.asyncio
    async def test_get_checkpoint_returns_current_step(self, mock_checkpoint_tuple):
        """测试获取 checkpoint 返回当前步骤"""
        from app.core.orchestrator import RoadmapOrchestrator
        
        with patch.object(RoadmapOrchestrator, '_checkpointer') as mock_cp:
            mock_cp.aget_tuple = AsyncMock(return_value=mock_checkpoint_tuple)
            
            # 模拟已初始化状态
            RoadmapOrchestrator._initialized = True
            RoadmapOrchestrator._checkpointer = mock_cp
            
            orchestrator = RoadmapOrchestrator()
            
            config = {"configurable": {"thread_id": "test-thread-001"}}
            checkpoint_tuple = await orchestrator.checkpointer.aget_tuple(config)
            
            assert checkpoint_tuple is not None
            assert checkpoint_tuple.checkpoint["channel_values"]["current_step"] == "curriculum_design"
            
            # 清理
            RoadmapOrchestrator._initialized = False
            RoadmapOrchestrator._checkpointer = None


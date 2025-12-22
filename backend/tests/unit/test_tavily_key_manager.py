"""
Tavily API Key Manager 单元测试

测试覆盖：
- Key 选择策略（配额感知、Round Robin 降级）
- 配额追踪（分钟级、日级）
- 健康检查逻辑
- Redis 故障降级
"""
import pytest
import asyncio
from datetime import datetime, date
from unittest.mock import AsyncMock, Mock, patch
from dataclasses import asdict

from app.tools.search.tavily_key_manager import TavilyAPIKeyManager, KeyStats
from app.config.settings import settings


@pytest.fixture
def mock_redis_client():
    """模拟 Redis 客户端"""
    mock_redis = Mock()
    mock_redis._client = Mock()
    mock_redis.connect = AsyncMock()
    
    # 模拟 Redis 客户端方法
    mock_redis._client.get = AsyncMock(return_value=None)
    mock_redis._client.set = AsyncMock()
    mock_redis._client.incr = AsyncMock(return_value=1)
    mock_redis._client.expire = AsyncMock()
    
    return mock_redis


@pytest.fixture
def sample_api_keys():
    """示例 API Keys"""
    return [
        "tvly-test-key-1-abc123",
        "tvly-test-key-2-def456",
        "tvly-test-key-3-ghi789",
    ]


@pytest.fixture
def key_manager(mock_redis_client, sample_api_keys):
    """Key Manager 实例"""
    return TavilyAPIKeyManager(
        redis_client=mock_redis_client,
        api_keys=sample_api_keys
    )


class TestKeyManagerInitialization:
    """测试 Key Manager 初始化"""
    
    def test_init_with_valid_keys(self, mock_redis_client, sample_api_keys):
        """测试使用有效 Keys 初始化"""
        manager = TavilyAPIKeyManager(mock_redis_client, sample_api_keys)
        
        assert manager.redis == mock_redis_client
        assert manager.api_keys == sample_api_keys
        assert manager._current_index == 0
    
    def test_init_with_empty_keys(self, mock_redis_client):
        """测试使用空 Keys 列表初始化（应该抛出异常）"""
        with pytest.raises(ValueError, match="至少需要提供一个"):
            TavilyAPIKeyManager(mock_redis_client, [])
    
    def test_get_key_id(self, key_manager):
        """测试 Key ID 生成（SHA256 哈希前 8 位）"""
        key_id_0 = key_manager._get_key_id(0)
        key_id_1 = key_manager._get_key_id(1)
        
        # Key ID 应该是 8 位字符串
        assert len(key_id_0) == 8
        assert len(key_id_1) == 8
        
        # 不同的 Key 应该有不同的 ID
        assert key_id_0 != key_id_1


class TestQuotaTracking:
    """测试配额追踪功能"""
    
    @pytest.mark.asyncio
    async def test_get_minute_usage(self, key_manager, mock_redis_client):
        """测试获取分钟级使用次数"""
        # 模拟 Redis 返回使用次数
        mock_redis_client._client.get.return_value = "15"
        
        usage = await key_manager._get_minute_usage(0)
        
        assert usage == 15
        assert mock_redis_client._client.get.called
    
    @pytest.mark.asyncio
    async def test_get_minute_usage_redis_failure(self, key_manager, mock_redis_client):
        """测试 Redis 失败时的降级处理"""
        # 模拟 Redis 连接失败
        mock_redis_client._client.get.side_effect = Exception("Redis connection failed")
        
        usage = await key_manager._get_minute_usage(0)
        
        # 降级：返回 0
        assert usage == 0
    
    @pytest.mark.asyncio
    async def test_get_daily_usage(self, key_manager, mock_redis_client):
        """测试获取日级使用次数"""
        mock_redis_client._client.get.return_value = "250"
        
        usage = await key_manager._get_daily_usage(0)
        
        assert usage == 250
    
    @pytest.mark.asyncio
    async def test_increment_usage(self, key_manager, mock_redis_client):
        """测试增加使用计数"""
        await key_manager._increment_usage(0)
        
        # 应该调用 incr 两次（分钟级和日级）
        assert mock_redis_client._client.incr.call_count == 2
        
        # 应该设置 TTL
        assert mock_redis_client._client.expire.call_count == 2


class TestKeyStats:
    """测试 KeyStats 数据类"""
    
    def test_success_rate_calculation(self):
        """测试成功率计算"""
        # 100% 成功率
        stats_100 = KeyStats(
            key_id="test123",
            key_index=0,
            total_calls=10,
            success_calls=10,
            failed_calls=0,
            rate_limit_errors=0,
            last_used_at=None,
            is_healthy=True,
            minute_usage=5,
            daily_usage=100,
        )
        assert stats_100.success_rate == 1.0
        
        # 50% 成功率
        stats_50 = KeyStats(
            key_id="test123",
            key_index=0,
            total_calls=10,
            success_calls=5,
            failed_calls=5,
            rate_limit_errors=2,
            last_used_at=None,
            is_healthy=True,
            minute_usage=5,
            daily_usage=100,
        )
        assert stats_50.success_rate == 0.5
        
        # 0 次调用时的成功率
        stats_zero = KeyStats(
            key_id="test123",
            key_index=0,
            total_calls=0,
            success_calls=0,
            failed_calls=0,
            rate_limit_errors=0,
            last_used_at=None,
            is_healthy=True,
            minute_usage=0,
            daily_usage=0,
        )
        assert stats_zero.success_rate == 1.0  # 默认为 100%
    
    def test_remaining_quota_calculation(self):
        """测试剩余配额计算"""
        stats = KeyStats(
            key_id="test123",
            key_index=0,
            total_calls=50,
            success_calls=45,
            failed_calls=5,
            rate_limit_errors=1,
            last_used_at=None,
            is_healthy=True,
            minute_usage=20,
            daily_usage=200,
        )
        
        # 假设配额为 100（分钟）和 1000（日）
        with patch.object(settings, 'TAVILY_MINUTE_QUOTA_PER_KEY', 100):
            assert stats.remaining_minute_quota == 80
        
        with patch.object(settings, 'TAVILY_DAILY_QUOTA_PER_KEY', 1000):
            assert stats.remaining_daily_quota == 800


class TestKeySelection:
    """测试 Key 选择策略"""
    
    @pytest.mark.asyncio
    async def test_round_robin_when_quota_tracking_disabled(
        self, key_manager, sample_api_keys
    ):
        """测试配额追踪禁用时的 Round Robin 策略"""
        with patch.object(settings, 'TAVILY_QUOTA_TRACKING_ENABLED', False):
            # 第一次选择
            key1, idx1 = await key_manager.get_best_key()
            assert idx1 == 0
            assert key1 == sample_api_keys[0]
            
            # 第二次选择
            key2, idx2 = await key_manager.get_best_key()
            assert idx2 == 1
            assert key2 == sample_api_keys[1]
            
            # 第三次选择
            key3, idx3 = await key_manager.get_best_key()
            assert idx3 == 2
            assert key3 == sample_api_keys[2]
            
            # 第四次选择（应该回到第一个）
            key4, idx4 = await key_manager.get_best_key()
            assert idx4 == 0
            assert key4 == sample_api_keys[0]
    
    @pytest.mark.asyncio
    async def test_quota_aware_selection(self, key_manager, mock_redis_client):
        """测试配额感知选择策略"""
        with patch.object(settings, 'TAVILY_QUOTA_TRACKING_ENABLED', True):
            # 模拟不同 Key 的配额使用情况
            # Key 0: 高使用率（剩余配额少）
            # Key 1: 中使用率
            # Key 2: 低使用率（剩余配额多）
            
            async def mock_get_key_stats(key_index):
                if key_index == 0:
                    return KeyStats(
                        key_id=key_manager._get_key_id(0),
                        key_index=0,
                        total_calls=100,
                        success_calls=95,
                        failed_calls=5,
                        rate_limit_errors=2,
                        last_used_at=datetime.now(),
                        is_healthy=True,
                        minute_usage=80,  # 高使用率
                        daily_usage=800,
                    )
                elif key_index == 1:
                    return KeyStats(
                        key_id=key_manager._get_key_id(1),
                        key_index=1,
                        total_calls=50,
                        success_calls=48,
                        failed_calls=2,
                        rate_limit_errors=0,
                        last_used_at=datetime.now(),
                        is_healthy=True,
                        minute_usage=40,  # 中使用率
                        daily_usage=400,
                    )
                else:  # key_index == 2
                    return KeyStats(
                        key_id=key_manager._get_key_id(2),
                        key_index=2,
                        total_calls=10,
                        success_calls=10,
                        failed_calls=0,
                        rate_limit_errors=0,
                        last_used_at=None,
                        is_healthy=True,
                        minute_usage=10,  # 低使用率
                        daily_usage=100,
                    )
            
            # 注入 mock
            key_manager.get_key_stats = mock_get_key_stats
            
            # 选择最优 Key（应该是 Key 2，因为剩余配额最多）
            best_key, best_idx = await key_manager.get_best_key()
            
            assert best_idx == 2  # Key 2 有最多剩余配额
    
    @pytest.mark.asyncio
    async def test_skip_unhealthy_keys(self, key_manager):
        """测试跳过不健康的 Keys"""
        with patch.object(settings, 'TAVILY_QUOTA_TRACKING_ENABLED', True):
            async def mock_get_key_stats(key_index):
                return KeyStats(
                    key_id=key_manager._get_key_id(key_index),
                    key_index=key_index,
                    total_calls=10,
                    success_calls=10,
                    failed_calls=0,
                    rate_limit_errors=0,
                    last_used_at=None,
                    is_healthy=(key_index != 0),  # Key 0 不健康
                    minute_usage=10,
                    daily_usage=100,
                )
            
            key_manager.get_key_stats = mock_get_key_stats
            
            # 选择最优 Key（应该跳过 Key 0）
            best_key, best_idx = await key_manager.get_best_key()
            
            assert best_idx != 0  # 不应该选择不健康的 Key 0
    
    @pytest.mark.asyncio
    async def test_skip_quota_exhausted_keys(self, key_manager):
        """测试跳过配额已用尽的 Keys"""
        with patch.object(settings, 'TAVILY_QUOTA_TRACKING_ENABLED', True):
            with patch.object(settings, 'TAVILY_MINUTE_QUOTA_PER_KEY', 100):
                async def mock_get_key_stats(key_index):
                    return KeyStats(
                        key_id=key_manager._get_key_id(key_index),
                        key_index=key_index,
                        total_calls=100,
                        success_calls=100,
                        failed_calls=0,
                        rate_limit_errors=0,
                        last_used_at=None,
                        is_healthy=True,
                        minute_usage=100 if key_index == 0 else 10,  # Key 0 配额用尽
                        daily_usage=100,
                    )
                
                key_manager.get_key_stats = mock_get_key_stats
                
                # 选择最优 Key（应该跳过 Key 0）
                best_key, best_idx = await key_manager.get_best_key()
                
                assert best_idx != 0  # 不应该选择配额用尽的 Key 0


class TestHealthCheck:
    """测试健康检查功能"""
    
    @pytest.mark.asyncio
    async def test_check_key_health_healthy(self, key_manager):
        """测试健康 Key 的检查"""
        # 模拟健康的统计信息
        async def mock_get_key_stats(key_index):
            return KeyStats(
                key_id=key_manager._get_key_id(key_index),
                key_index=key_index,
                total_calls=100,
                success_calls=95,
                failed_calls=5,
                rate_limit_errors=1,  # 少量限流错误
                last_used_at=datetime.now(),
                is_healthy=True,
                minute_usage=20,
                daily_usage=200,
            )
        
        key_manager.get_key_stats = mock_get_key_stats
        key_manager._mark_key_healthy = AsyncMock()
        
        is_healthy = await key_manager.check_key_health(0)
        
        assert is_healthy is True
        assert key_manager._mark_key_healthy.called
    
    @pytest.mark.asyncio
    async def test_check_key_health_too_many_rate_limits(self, key_manager):
        """测试限流错误过多时标记为不健康"""
        # 模拟限流错误过多
        async def mock_get_key_stats(key_index):
            return KeyStats(
                key_id=key_manager._get_key_id(key_index),
                key_index=key_index,
                total_calls=20,
                success_calls=17,
                failed_calls=3,
                rate_limit_errors=5,  # 限流错误过多
                last_used_at=datetime.now(),
                is_healthy=True,
                minute_usage=20,
                daily_usage=200,
            )
        
        key_manager.get_key_stats = mock_get_key_stats
        key_manager._mark_key_unhealthy = AsyncMock()
        
        is_healthy = await key_manager.check_key_health(0)
        
        assert is_healthy is False
        assert key_manager._mark_key_unhealthy.called
    
    @pytest.mark.asyncio
    async def test_check_key_health_low_success_rate(self, key_manager):
        """测试成功率过低时标记为不健康"""
        # 模拟成功率低于 50%
        async def mock_get_key_stats(key_index):
            return KeyStats(
                key_id=key_manager._get_key_id(key_index),
                key_index=key_index,
                total_calls=20,
                success_calls=8,  # 40% 成功率
                failed_calls=12,
                rate_limit_errors=0,
                last_used_at=datetime.now(),
                is_healthy=True,
                minute_usage=20,
                daily_usage=200,
            )
        
        key_manager.get_key_stats = mock_get_key_stats
        key_manager._mark_key_unhealthy = AsyncMock()
        
        is_healthy = await key_manager.check_key_health(0)
        
        assert is_healthy is False
        assert key_manager._mark_key_unhealthy.called


class TestMarkKeyUsed:
    """测试标记 Key 使用"""
    
    @pytest.mark.asyncio
    async def test_mark_key_used_success(self, key_manager, mock_redis_client):
        """测试标记成功使用"""
        await key_manager.mark_key_used(
            key_index=0,
            success=True,
            error_type=None
        )
        
        # 应该增加 total_calls 和 success_calls
        assert mock_redis_client._client.incr.call_count >= 3  # minute, daily, total, success
    
    @pytest.mark.asyncio
    async def test_mark_key_used_rate_limit_error(self, key_manager, mock_redis_client):
        """测试标记限流错误"""
        await key_manager.mark_key_used(
            key_index=0,
            success=False,
            error_type="rate_limit"
        )
        
        # 应该增加 rate_limit_errors
        assert mock_redis_client._client.incr.called
    
    @pytest.mark.asyncio
    async def test_mark_key_used_redis_failure(self, key_manager, mock_redis_client):
        """测试 Redis 失败时的容错处理"""
        # 模拟 Redis 失败
        mock_redis_client._client.incr.side_effect = Exception("Redis failed")
        
        # 不应该抛出异常（容错处理）
        await key_manager.mark_key_used(
            key_index=0,
            success=True,
            error_type=None
        )


class TestGetAllStats:
    """测试获取所有 Keys 的统计信息"""
    
    @pytest.mark.asyncio
    async def test_get_all_stats(self, key_manager, sample_api_keys):
        """测试获取所有统计信息"""
        # Mock get_key_stats
        async def mock_get_key_stats(key_index):
            return KeyStats(
                key_id=key_manager._get_key_id(key_index),
                key_index=key_index,
                total_calls=key_index * 10,
                success_calls=key_index * 9,
                failed_calls=key_index * 1,
                rate_limit_errors=0,
                last_used_at=None,
                is_healthy=True,
                minute_usage=key_index * 5,
                daily_usage=key_index * 50,
            )
        
        key_manager.get_key_stats = mock_get_key_stats
        
        all_stats = await key_manager.get_all_stats()
        
        assert len(all_stats) == len(sample_api_keys)
        assert all_stats[0].key_index == 0
        assert all_stats[1].key_index == 1
        assert all_stats[2].key_index == 2


"""
多 API Key 搜索集成测试

测试覆盖：
- 多 Key 搜索功能
- 限流故障转移
- Redis 集成
- 端到端工作流
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch

from app.tools.search.tavily_api_search import TavilyAPISearchTool
from app.tools.search.tavily_key_manager import TavilyAPIKeyManager
from app.models.domain import SearchQuery, SearchResult
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


class TestMultiKeySearch:
    """测试多 Key 搜索功能"""
    
    @pytest.mark.asyncio
    async def test_search_success_with_first_key(self, mock_redis_client, sample_api_keys):
        """测试使用第一个 Key 成功搜索"""
        # Mock KeyManager
        with patch('app.tools.search.tavily_api_search.get_redis_client', return_value=mock_redis_client):
            with patch.object(settings, 'get_tavily_api_keys', sample_api_keys):
                tool = TavilyAPISearchTool()
                
                # Mock get_best_key 返回第一个 Key
                tool.key_manager.get_best_key = AsyncMock(
                    return_value=(sample_api_keys[0], 0)
                )
                
                # Mock _rate_limited_request 返回成功结果
                mock_result = {
                    "results": [
                        {
                            "title": "Test Result 1",
                            "url": "https://example.com/1",
                            "content": "Test content 1",
                        },
                        {
                            "title": "Test Result 2",
                            "url": "https://example.com/2",
                            "content": "Test content 2",
                        }
                    ]
                }
                
                tool._rate_limited_request = AsyncMock(return_value=mock_result)
                tool.key_manager.mark_key_used = AsyncMock()
                
                # 执行搜索
                query = SearchQuery(query="test query", max_results=5)
                result = await tool.execute(query)
                
                # 验证结果
                assert isinstance(result, SearchResult)
                assert len(result.results) == 2
                assert result.results[0]["title"] == "Test Result 1"
                
                # 验证标记 Key 使用成功
                tool.key_manager.mark_key_used.assert_called_once_with(
                    key_index=0,
                    success=True,
                    error_type=None
                )
    
    @pytest.mark.asyncio
    async def test_search_retry_on_rate_limit(self, mock_redis_client, sample_api_keys):
        """测试遇到限流时自动重试"""
        with patch('app.tools.search.tavily_api_search.get_redis_client', return_value=mock_redis_client):
            with patch.object(settings, 'get_tavily_api_keys', sample_api_keys):
                tool = TavilyAPISearchTool()
                
                # Mock get_best_key 依次返回不同的 Key
                key_sequence = [
                    (sample_api_keys[0], 0),  # 第一次调用：Key 0
                    (sample_api_keys[1], 1),  # 第二次调用：Key 1
                ]
                tool.key_manager.get_best_key = AsyncMock(side_effect=key_sequence)
                
                # Mock _rate_limited_request：第一次限流，第二次成功
                call_count = 0
                async def mock_rate_limited(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        # 第一次调用：模拟限流错误
                        raise Exception("Rate limit exceeded (429)")
                    else:
                        # 第二次调用：成功
                        return {
                            "results": [
                                {
                                    "title": "Success Result",
                                    "url": "https://example.com/success",
                                    "content": "Success content",
                                }
                            ]
                        }
                
                tool._rate_limited_request = mock_rate_limited
                tool.key_manager.mark_key_used = AsyncMock()
                
                # 执行搜索
                query = SearchQuery(query="test query", max_results=5)
                result = await tool.execute(query)
                
                # 验证结果（应该使用第二个 Key 成功）
                assert isinstance(result, SearchResult)
                assert len(result.results) == 1
                assert result.results[0]["title"] == "Success Result"
                
                # 验证两次 get_best_key 调用
                assert tool.key_manager.get_best_key.call_count == 2
                
                # 验证两次 mark_key_used 调用
                # 第一次：Key 0 失败（rate_limit）
                # 第二次：Key 1 成功
                assert tool.key_manager.mark_key_used.call_count == 2
    
    @pytest.mark.asyncio
    async def test_search_all_keys_failed(self, mock_redis_client, sample_api_keys):
        """测试所有 Keys 都失败的情况"""
        with patch('app.tools.search.tavily_api_search.get_redis_client', return_value=mock_redis_client):
            with patch.object(settings, 'get_tavily_api_keys', sample_api_keys):
                tool = TavilyAPISearchTool()
                
                # Mock get_best_key 依次返回所有 Key
                key_sequence = [
                    (sample_api_keys[i], i) for i in range(3)
                ]
                tool.key_manager.get_best_key = AsyncMock(side_effect=key_sequence)
                
                # Mock _rate_limited_request：所有调用都限流
                async def mock_rate_limited(*args, **kwargs):
                    raise Exception("Rate limit exceeded (429)")
                
                tool._rate_limited_request = mock_rate_limited
                tool.key_manager.mark_key_used = AsyncMock()
                
                # 执行搜索（应该抛出异常）
                query = SearchQuery(query="test query", max_results=5)
                
                with pytest.raises(Exception, match="Rate limit|429"):
                    await tool.execute(query)
                
                # 验证尝试了 3 次（最多重试次数）
                assert tool.key_manager.get_best_key.call_count == 3
    
    @pytest.mark.asyncio
    async def test_search_non_rate_limit_error_no_retry(self, mock_redis_client, sample_api_keys):
        """测试非限流错误不重试"""
        with patch('app.tools.search.tavily_api_search.get_redis_client', return_value=mock_redis_client):
            with patch.object(settings, 'get_tavily_api_keys', sample_api_keys):
                tool = TavilyAPISearchTool()
                
                # Mock get_best_key
                tool.key_manager.get_best_key = AsyncMock(
                    return_value=(sample_api_keys[0], 0)
                )
                
                # Mock _rate_limited_request：非限流错误
                async def mock_rate_limited(*args, **kwargs):
                    raise Exception("Network connection failed")
                
                tool._rate_limited_request = mock_rate_limited
                tool.key_manager.mark_key_used = AsyncMock()
                
                # 执行搜索（应该抛出异常且不重试）
                query = SearchQuery(query="test query", max_results=5)
                
                with pytest.raises(Exception, match="Network"):
                    await tool.execute(query)
                
                # 验证只尝试了 1 次（不重试）
                assert tool.key_manager.get_best_key.call_count == 1


class TestErrorClassification:
    """测试错误分类功能"""
    
    def test_classify_rate_limit_error(self):
        """测试识别限流错误"""
        from app.tools.search.tavily_api_search import TavilyAPISearchTool
        
        tool = TavilyAPISearchTool.__new__(TavilyAPISearchTool)
        
        # 测试不同形式的限流错误
        assert tool._classify_error(Exception("Rate limit exceeded")) == "rate_limit"
        assert tool._classify_error(Exception("429 Too Many Requests")) == "rate_limit"
        assert tool._classify_error(Exception("too many requests")) == "rate_limit"
    
    def test_classify_timeout_error(self):
        """测试识别超时错误"""
        from app.tools.search.tavily_api_search import TavilyAPISearchTool
        
        tool = TavilyAPISearchTool.__new__(TavilyAPISearchTool)
        
        assert tool._classify_error(Exception("Request timeout")) == "timeout"
        assert tool._classify_error(Exception("Connection timed out")) == "timeout"
    
    def test_classify_auth_error(self):
        """测试识别认证错误"""
        from app.tools.search.tavily_api_search import TavilyAPISearchTool
        
        tool = TavilyAPISearchTool.__new__(TavilyAPISearchTool)
        
        assert tool._classify_error(Exception("Unauthorized access")) == "auth"
        assert tool._classify_error(Exception("401 Unauthorized")) == "auth"
        assert tool._classify_error(Exception("Invalid API key")) == "auth"
    
    def test_classify_network_error(self):
        """测试识别网络错误"""
        from app.tools.search.tavily_api_search import TavilyAPISearchTool
        
        tool = TavilyAPISearchTool.__new__(TavilyAPISearchTool)
        
        assert tool._classify_error(Exception("Network connection failed")) == "network"
        assert tool._classify_error(Exception("Connection refused")) == "network"
    
    def test_classify_unknown_error(self):
        """测试未知错误分类"""
        from app.tools.search.tavily_api_search import TavilyAPISearchTool
        
        tool = TavilyAPISearchTool.__new__(TavilyAPISearchTool)
        
        assert tool._classify_error(Exception("Something went wrong")) == "unknown"


class TestQuotaTrackingIntegration:
    """测试配额追踪集成"""
    
    @pytest.mark.asyncio
    async def test_quota_usage_recorded(self, mock_redis_client, sample_api_keys):
        """测试配额使用被正确记录"""
        with patch('app.tools.search.tavily_api_search.get_redis_client', return_value=mock_redis_client):
            with patch.object(settings, 'get_tavily_api_keys', sample_api_keys):
                tool = TavilyAPISearchTool()
                
                # Mock get_best_key
                tool.key_manager.get_best_key = AsyncMock(
                    return_value=(sample_api_keys[0], 0)
                )
                
                # Mock 成功搜索
                tool._rate_limited_request = AsyncMock(return_value={"results": []})
                tool.key_manager.mark_key_used = AsyncMock()
                
                # 执行搜索
                query = SearchQuery(query="test", max_results=5)
                await tool.execute(query)
                
                # 验证 mark_key_used 被调用
                tool.key_manager.mark_key_used.assert_called_once()
                call_args = tool.key_manager.mark_key_used.call_args
                
                # 验证参数
                assert call_args[1]["key_index"] == 0
                assert call_args[1]["success"] is True
                assert call_args[1]["error_type"] is None


class TestHealthCheckIntegration:
    """测试健康检查集成"""
    
    @pytest.mark.asyncio
    async def test_unhealthy_key_skipped(self, mock_redis_client, sample_api_keys):
        """测试不健康的 Key 被跳过"""
        with patch('app.tools.search.tavily_api_search.get_redis_client', return_value=mock_redis_client):
            with patch.object(settings, 'get_tavily_api_keys', sample_api_keys):
                with patch.object(settings, 'TAVILY_QUOTA_TRACKING_ENABLED', True):
                    key_manager = TavilyAPIKeyManager(
                        redis_client=mock_redis_client,
                        api_keys=sample_api_keys
                    )
                    
                    # Mock get_key_stats：Key 0 不健康，Key 1 健康
                    from app.tools.search.tavily_key_manager import KeyStats
                    
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
                    
                    # 获取最优 Key（应该跳过 Key 0）
                    best_key, best_idx = await key_manager.get_best_key()
                    
                    # Key 0 应该被跳过
                    assert best_idx != 0
                    assert best_idx in [1, 2]


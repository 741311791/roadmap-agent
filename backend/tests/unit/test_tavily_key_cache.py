"""
Tavily Key Redis 缓存单元测试

验证缓存选择逻辑在存在部分失效 key 时仍能找到后续可用 key。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.tavily_key_cache import TavilyKeyCacheManager


@pytest.mark.asyncio
async def test_get_random_key_skips_invalid_entries_and_finds_valid_key():
    """
    测试在前几个缓存条目失效时，仍然能找到后续有效 key

    场景：
    - Redis Set 中共有 10 个 key_id
    - 前 5 个 key_id 对应的 hash 已经过期
    - 第 6 个 key_id 仍然有效且有剩余额度

    验证：
    - get_random_key() 不会因为前 5 个失效条目提前返回 None
    - 会继续扫描后续条目并返回有效 API Key
    - 失效条目会被自动从集合中清理
    """
    manager = TavilyKeyCacheManager()
    manager.redis = MagicMock()
    manager.redis.connect = AsyncMock()
    manager.redis._client = MagicMock()

    key_ids = [f"tvly-test-{index}" for index in range(10)]
    manager.redis._client.smembers = AsyncMock(return_value=key_ids)
    manager.redis._client.hgetall = AsyncMock(
        side_effect=[
            {},
            {},
            {},
            {},
            {},
            {
                "api_key": "tvly-valid-key",
                "remaining_quota": "88",
            },
        ]
    )
    manager.redis._client.srem = AsyncMock()

    # 保持测试顺序稳定，确保先遇到 5 个失效条目再命中有效 key。
    with patch("app.core.tavily_key_cache.random.shuffle", lambda _: None):
        api_key = await manager.get_random_key(max_retries=5)

    assert api_key == "tvly-valid-key"
    assert manager.redis._client.hgetall.await_count == 6
    assert manager.redis._client.srem.await_count == 5


@pytest.mark.asyncio
async def test_get_random_key_refreshes_cache_on_demand_when_empty():
    """
    测试缓存为空时会按需回源刷新一次

    验证：
    - 第一次读取集合为空时，不会直接返回 None
    - 会主动调用 refresh()
    - 刷新后能继续从新缓存中拿到可用 key
    """
    manager = TavilyKeyCacheManager()
    manager.redis = MagicMock()
    manager.redis.connect = AsyncMock()
    manager.redis._client = MagicMock()

    manager.redis._client.smembers = AsyncMock(
        side_effect=[
            [],
            ["tvly-fresh-key"],
        ]
    )
    manager.redis._client.hgetall = AsyncMock(
        return_value={
            "api_key": "tvly-fresh-key",
            "remaining_quota": "21",
        }
    )
    manager.redis._client.srem = AsyncMock()
    manager.refresh = AsyncMock(return_value=1)

    with patch("app.core.tavily_key_cache.random.shuffle", lambda _: None):
        api_key = await manager.get_random_key()

    assert api_key == "tvly-fresh-key"
    manager.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_quota_removes_key_when_quota_exhausted():
    """
    测试运行时扣减额度后会自动移除耗尽的 key

    验证：
    - update_quota() 能直接命中对应详情 hash
    - 当剩余额度扣减为 0 时，会同步从可用集合中移除
    """
    manager = TavilyKeyCacheManager()
    manager.redis = MagicMock()
    manager.redis.connect = AsyncMock()
    manager.redis._client = MagicMock()

    manager.redis._client.exists = AsyncMock(return_value=1)
    manager.redis._client.hincrby = AsyncMock(return_value=0)
    manager.redis._client.srem = AsyncMock()

    result = await manager.update_quota("tvly-exhausted-key", used_count=1)

    assert result is True
    manager.redis._client.srem.assert_awaited_once_with(
        manager.KEYS_SET,
        "tvly-exhausted-key",
    )

# Tavily API Integration Update

## 更新日期
2025-12-22

## 更新概述

将配额追踪机制从**本地 Redis 计数**改为**直接调用 Tavily API `/usage` 端点**，获取真实的配额信息。

---

## 主要变更

### 1. 配额获取方式改变 ✨

#### 旧方案（已废弃）
- 使用环境变量配置固定配额：
  - `TAVILY_DAILY_QUOTA_PER_KEY`
  - `TAVILY_MINUTE_QUOTA_PER_KEY`
- 在 Redis 中本地计数使用次数
- 配额信息可能不准确（无法反映 Tavily 实际限制）

#### 新方案（当前）
- **直接调用 Tavily API**: `GET https://api.tavily.com/usage`
- 获取真实配额信息：
  - **Key 级别配额**: `key.usage` / `key.limit`
  - **账户计划配额**: `account.plan_usage` / `account.plan_limit`
  - **Pay-as-you-go**: `account.paygo_usage` / `account.paygo_limit`
- 配额信息缓存 60 秒（减少 API 调用）
- 更准确、更可靠

---

## 代码变更详情

### 1. TavilyAPIKeyManager (`tavily_key_manager.py`)

#### 新增数据结构

```python
@dataclass
class TavilyUsageInfo:
    """Tavily API 配额信息（从 /usage API 获取）"""
    key_usage: int
    key_limit: Optional[int]
    plan_name: str
    plan_usage: int
    plan_limit: int
    paygo_usage: int
    paygo_limit: int
```

#### 新增方法

- `_fetch_usage_from_api(key_index)`: 从 Tavily API 获取配额
- `_get_cached_usage(key_index)`: 获取缓存的配额信息
- `_cache_usage(key_index, usage_info)`: 缓存配额信息
- `get_usage_info(key_index, force_refresh)`: 获取配额（优先使用缓存）

#### 移除方法

- ~~`_get_minute_usage(key_index)`~~: 不再需要本地计数
- ~~`_get_daily_usage(key_index)`~~: 不再需要本地计数
- ~~`_increment_usage(key_index)`~~: 不再需要本地计数

#### 修改方法

- `get_key_stats()`: 返回 `TavilyUsageInfo` 而非本地计数
- `_calculate_key_score()`: 基于真实配额计算分数
- `mark_key_used()`: 成功使用后使配额缓存失效

---

### 2. 监控 API (`tavily_metrics.py`)

#### 响应格式变更

**旧格式**:
```json
{
  "quota": {
    "minute_usage": 15,
    "minute_quota": 100,
    "minute_remaining": 85,
    "daily_usage": 350,
    "daily_quota": 1000,
    "daily_remaining": 650
  }
}
```

**新格式**:
```json
{
  "quota": {
    "key": {
      "usage": 150,
      "limit": 1000,
      "remaining": 850
    },
    "plan": {
      "name": "Bootstrap",
      "usage": 500,
      "limit": 15000,
      "remaining": 14500
    },
    "paygo": {
      "usage": 25,
      "limit": 100
    },
    "total_remaining": 850
  }
}
```

#### 新增端点

```
POST /api/v1/tavily/refresh-quota
```

**功能**: 强制刷新所有 Keys 的配额信息（跳过缓存）

---

## 配置变更

### 不再需要的环境变量

以下环境变量**不再使用**，可以从 `.env` 中移除：

```bash
# ❌ 已废弃
TAVILY_DAILY_QUOTA_PER_KEY=1000
TAVILY_MINUTE_QUOTA_PER_KEY=100
```

### 保留的环境变量

```bash
# ✅ 仍然需要
TAVILY_API_KEY_LIST=["key1", "key2", "key3"]
TAVILY_QUOTA_TRACKING_ENABLED=true
```

---

## 优势对比

| 特性 | 旧方案 | 新方案 |
|------|--------|--------|
| 配额准确性 | ❌ 基于假设的固定值 | ✅ 从 Tavily API 获取真实数据 |
| 多计划支持 | ❌ 无法区分不同计划 | ✅ 自动识别 Key 和计划配额 |
| Pay-as-you-go | ❌ 不支持 | ✅ 完整支持 |
| 配置复杂度 | ⚠️ 需要手动配置配额 | ✅ 零配置，自动获取 |
| 配额同步 | ❌ 可能与实际不符 | ✅ 60 秒缓存，接近实时 |
| API 调用开销 | ✅ 无额外调用 | ⚠️ 每 60 秒调用一次 |

---

## 迁移指南

### 对于现有用户

1. **无需修改代码**：所有变更对应用代码透明
2. **可选清理**: 从 `.env` 中移除废弃的配额配置
3. **重启应用**：新配额机制会自动生效

### 验证步骤

1. 启动应用后，查看日志：
```
tavily_usage_fetched - 确认配额获取成功
```

2. 调用监控 API：
```bash
curl http://localhost:8000/api/v1/tavily/metrics
```

3. 检查响应中的 `quota` 字段，确认包含 `key`、`plan`、`paygo` 信息

---

## 常见问题

### Q1: 配额信息多久更新一次？

**A**: 配额信息缓存 60 秒。如需立即刷新，调用：
```bash
POST /api/v1/tavily/refresh-quota
```

### Q2: Tavily API 调用失败会怎样？

**A**: 系统会降级处理：
- 使用缓存的配额信息（如果有）
- 如果无缓存，给予中等优先级分数（35/100）
- 不影响搜索功能

### Q3: 是否增加了 API 调用成本？

**A**: 影响很小：
- `/usage` 端点调用频率：每个 Key 每 60 秒最多 1 次
- 3 个 Keys = 每分钟最多 3 次 `/usage` 调用
- 远低于搜索 API 调用频率

### Q4: 如何验证配额信息准确性？

**A**: 手动查询 Tavily API 对比：
```bash
curl --request GET \
  --url https://api.tavily.com/usage \
  --header 'Authorization: Bearer YOUR_KEY'
```

---

## 技术细节

### Tavily /usage API 规格

**端点**: `GET https://api.tavily.com/usage`

**认证**: `Authorization: Bearer <tavily_api_key>`

**响应结构**:
```typescript
{
  key: {
    usage: number;        // 当前使用次数
    limit: number | null; // 限制（null 表示无限制）
  };
  account: {
    current_plan: string; // 计划名称
    plan_usage: number;   // 计划使用次数
    plan_limit: number;   // 计划限制
    paygo_usage: number;  // Pay-as-you-go 使用
    paygo_limit: number;  // Pay-as-you-go 限制
  };
}
```

### 缓存策略

- **存储位置**: Redis
- **缓存键**: `tavily:{key_id}:usage_cache`
- **TTL**: 60 秒
- **失效时机**: 
  - 自动过期（60 秒）
  - 成功使用后主动失效
  - 手动刷新

---

## 相关文件

### 修改的文件
- `backend/app/tools/search/tavily_key_manager.py`
- `backend/app/api/v1/endpoints/tavily_metrics.py`
- `TAVILY_MULTI_KEY_SETUP_GUIDE.md`

### 新增的文件
- `TAVILY_API_INTEGRATION_UPDATE.md`（本文档）

---

## 后续优化建议

1. **自适应缓存**: 根据配额消耗速度动态调整缓存 TTL
2. **预警机制**: 配额低于阈值时主动通知
3. **配额历史**: 记录配额使用趋势，用于容量规划
4. **多区域支持**: 如果 Tavily 提供区域化 API，支持按区域查询

---

## 版本信息

- **更新版本**: v2.0
- **兼容性**: 向后兼容，无破坏性变更
- **Python 依赖**: 新增 `httpx`（用于调用 Tavily API）

---

## 总结

本次更新将配额管理从**假设驱动**改为**数据驱动**，显著提升了配额追踪的准确性和可靠性。同时保持了系统的容错能力和向后兼容性。

✅ **推荐立即更新**以享受更精准的配额管理！


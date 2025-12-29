# Tavily 配额自动更新 - 快速开始指南

本指南帮助你快速部署和测试 Tavily API 配额自动更新功能。

---

## 🚀 快速部署（Railway）

### 步骤 1: 安装依赖

```bash
cd backend
uv sync  # 或 poetry install
```

这会自动安装新增的 `schedule>=1.2.0` 依赖。

### 步骤 2: Railway 部署

1. **创建新 Service**：
   - 登录 Railway 控制台
   - 进入项目 → 点击 "New Service"
   - 选择现有仓库（roadmap-agent）
   - 命名为 `tavily-quota-updater`

2. **配置环境变量**：
   ```env
   SERVICE_TYPE=tavily_quota_updater
   QUOTA_UPDATE_INTERVAL_HOURS=1  # 可选，默认 1 小时
   ```
   
   其他数据库变量会自动继承。

3. **部署**：
   - Railway 会自动构建并启动
   - 查看 Logs 确认启动成功

### 步骤 3: 验证部署

检查日志输出（Railway Logs）：

```json
{
  "event": "tavily_quota_updater_starting",
  "update_interval_hours": 1,
  "environment": "production"
}
{
  "event": "tavily_quota_update_completed",
  "success_count": 5,
  "failed_count": 0
}
```

查询数据库验证更新：

```sql
SELECT 
  api_key, 
  remaining_quota, 
  plan_limit, 
  updated_at 
FROM tavily_api_keys 
ORDER BY updated_at DESC;
```

---

## 🧪 本地测试

### 方法 1: 快速测试（推荐）

运行测试脚本，不启动定时调度：

```bash
cd backend
python scripts/test_tavily_quota_update.py
```

**预期输出**：

```
============================================================
Tavily Quota Update Test Script
============================================================

[Test 1] Database Connection
2025-12-29T10:00:00 [info] Testing database connection...
2025-12-29T10:00:01 [info] Database connection successful total_keys=5
2025-12-29T10:00:01 [info] Found API key key_prefix=tvly-xxxxx... remaining_quota=800 plan_limit=1000

[Test 2] Single Quota Update
2025-12-29T10:00:02 [info] Starting single quota update test...
2025-12-29T10:00:05 [info] tavily_quota_update_completed success_count=5 failed_count=0

============================================================
✅ All tests passed!
You can now run the full scheduler:
  python scripts/update_tavily_quota.py
============================================================
```

### 方法 2: 完整定时任务测试

启动完整的定时调度器：

```bash
cd backend
python scripts/update_tavily_quota.py
```

- 脚本会立即执行一次更新
- 然后每小时自动执行
- 按 `Ctrl+C` 退出

### 方法 3: 模拟 Railway 环境

```bash
cd backend
export SERVICE_TYPE=tavily_quota_updater
bash scripts/railway_entrypoint.sh
```

---

## 📊 监控与维护

### 查看最近更新

```sql
SELECT 
  COUNT(*) as total,
  MIN(updated_at) as oldest_update,
  MAX(updated_at) as newest_update,
  EXTRACT(EPOCH FROM (NOW() - MAX(updated_at)))/60 as minutes_ago
FROM tavily_api_keys;
```

如果 `minutes_ago > 70`，说明定时任务可能出现问题。

### 查看失败的 Key

Railway Logs 搜索：

```
event:"tavily_api_http_error" OR event:"tavily_api_timeout"
```

### 手动触发更新

在 Railway 控制台重启 `tavily-quota-updater` Service。

---

## 🔧 常见问题

### Q: 如何修改更新频率为 6 小时？

Railway 中添加环境变量：

```env
QUOTA_UPDATE_INTERVAL_HOURS=6
```

### Q: 定时任务会影响主应用性能吗？

不会。定时任务运行在独立进程中，有自己的数据库连接池。

### Q: 如何查看实时日志？

Railway 控制台 → 选择 `tavily-quota-updater` Service → Logs 标签页。

---

## 📚 完整文档

详细说明请参考：[TAVILY_QUOTA_UPDATER.md](./TAVILY_QUOTA_UPDATER.md)

---

## ✅ 部署检查清单

- [ ] 安装依赖 `uv sync`
- [ ] Railway 创建 `tavily-quota-updater` Service
- [ ] 设置环境变量 `SERVICE_TYPE=tavily_quota_updater`
- [ ] 部署并查看日志确认启动
- [ ] 查询数据库验证 `updated_at` 更新
- [ ] 配置监控告警（可选）

完成后，系统将自动每小时更新所有 Tavily API Key 的配额信息！


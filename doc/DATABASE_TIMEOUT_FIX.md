# 数据库超时问题修复报告

## 问题描述

用户在生成路线图时遇到以下问题：

1. **数据库超时错误**：
   ```
   OperationalError: consuming input failed: could not receive data from server: Operation timed out
   ```

2. **前端轮询显示 404**（但实际 API 接口正常工作）

## 根本原因分析

### 1. 数据库连接池配置不足

**原配置**：
```python
pool_size=10
max_overflow=20
pool_pre_ping=True
# 没有配置超时和回收参数
```

**问题**：
- 连接池大小偏小，在高并发场景下容易耗尽
- 缺少 `pool_recycle` 导致长时间连接可能过期
- 缺少 `pool_timeout` 导致等待连接时间不可控
- 缺少查询超时配置，长查询可能阻塞连接

### 2. 数据库连接稳定性问题

**症状**：
- 错误信息显示"could not receive data from server"
- 多个任务在大约 18 秒后超时失败

**可能原因**：
- 数据库服务器网络不稳定
- PostgreSQL 默认超时配置
- 连接过期未及时回收
- AsyncPG 连接池管理不当

### 3. 诊断数据

在数据库中找到 3 个失败的任务：

```
Task 1:
  task_id: 007b3301-4e95-49fa-ab80-fcd8fe022654
  status: failed
  error: OperationalError: consuming input failed: could not receive data from server: Operation timed out
  created: 2025-12-07 11:18:00
  updated: 2025-12-07 11:18:18 (失败用时 ~18秒)

Task 2:
  task_id: 473e1974-9b50-4c92-a3d2-a8a051ee5e61
  status: failed
  error: OperationalError: consuming input failed: could not receive data from server: Operation timed out
  created: 2025-12-06 23:58:04
  updated: 2025-12-06 23:58:23 (失败用时 ~19秒)
```

## 修复方案

### 1. 增强数据库连接池配置

**修改文件**: `backend/app/db/session.py`

**新配置**：
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,  # ✅ 增加连接池大小（10 → 20）
    max_overflow=40,  # ✅ 增加溢出连接数（20 → 40）
    pool_pre_ping=True,  # ✅ 连接前 ping 检查
    pool_recycle=3600,  # ✅ 1小时回收连接，避免长时间连接过期
    pool_timeout=30,  # ✅ 获取连接的超时时间 30 秒
    connect_args={
        "server_settings": {
            "application_name": "roadmap_agent",
            "jit": "off",  # 禁用 JIT，提高稳定性
        },
        "command_timeout": 60,  # ✅ 命令超时 60 秒
        "timeout": 30,  # ✅ 连接超时 30 秒
    },
)
```

**改进说明**：

| 参数 | 旧值 | 新值 | 说明 |
|------|------|------|------|
| `pool_size` | 10 | 20 | 增加基础连接池大小 |
| `max_overflow` | 20 | 40 | 增加溢出连接数 |
| `pool_recycle` | 无 | 3600 | 每小时回收连接，避免过期 |
| `pool_timeout` | 无 | 30 | 获取连接最多等待 30 秒 |
| `command_timeout` | 无 | 60 | SQL 命令执行最多 60 秒 |
| `timeout` | 无 | 30 | TCP 连接超时 30 秒 |

### 2. 前端 404 问题的可能原因

**实际测试结果**：
- ✅ API 接口 `/api/v1/roadmaps/{task_id}/status` 正常工作
- ✅ 可以正确返回失败任务的状态

**可能的原因**：
1. 前端保存的 task_id 不正确
2. 前端 API 路径配置错误
3. 某些边缘情况下的 404

**建议检查**：
- 前端生成任务后是否正确保存 task_id
- 前端轮询使用的 URL 是否正确
- 检查浏览器控制台的完整请求 URL

## 测试验证

### 1. 验证 API 正常工作

```bash
# 测试查询失败任务状态
curl -s "http://localhost:8000/api/v1/roadmaps/007b3301-4e95-49fa-ab80-fcd8fe022654/status" | python3 -m json.tool
```

**响应**：
```json
{
    "task_id": "007b3301-4e95-49fa-ab80-fcd8fe022654",
    "status": "failed",
    "current_step": "failed",
    "roadmap_id": null,
    "created_at": "2025-12-07T11:18:00.077681",
    "updated_at": "2025-12-07T11:18:18.587678",
    "error_message": "OperationalError: consuming input failed: could not receive data from server: Operation timed out"
}
```

✅ API 接口正常返回失败任务状态

### 2. 重启后端服务应用修复

```bash
# 后端会通过 --reload 自动重启，应用新的连接池配置
```

## 预期效果

修复后应该能够：

1. ✅ **减少数据库超时错误**
   - 更大的连接池可以处理更多并发请求
   - 超时配置可以及时释放问题连接
   - 连接回收可以避免长时间连接过期

2. ✅ **提高系统稳定性**
   - 查询超时保护，避免无限等待
   - 连接前检查，避免使用过期连接
   - 更好的错误处理和恢复机制

3. ✅ **改善用户体验**
   - 减少生成失败的概率
   - 更快的错误反馈
   - 更可靠的任务状态查询

## 进一步优化建议

### 1. 监控和告警

```python
# 添加连接池监控
@router.get("/health/db")
async def db_health_check():
    pool_status = {
        "pool_size": engine.pool.size(),
        "checked_in": engine.pool.checkedin(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow(),
    }
    return pool_status
```

### 2. 数据库查询优化

- 添加索引优化慢查询
- 使用 `EXPLAIN ANALYZE` 分析查询性能
- 考虑使用连接池预热

### 3. 错误重试机制

```python
# 为数据库超时错误添加自动重试
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(OperationalError)
)
async def resilient_db_operation():
    # 数据库操作
    pass
```

### 4. PostgreSQL 服务器端优化

检查 PostgreSQL 配置：
```sql
-- 查看超时配置
SHOW statement_timeout;
SHOW idle_in_transaction_session_timeout;
SHOW tcp_keepalives_idle;
SHOW tcp_keepalives_interval;
```

建议配置：
```ini
# postgresql.conf
statement_timeout = 60000  # 60 seconds
idle_in_transaction_session_timeout = 300000  # 5 minutes
tcp_keepalives_idle = 60
tcp_keepalives_interval = 10
tcp_keepalives_count = 5
```

## 修复状态

- ✅ **数据库连接池配置已优化** - 2025-12-07
- ⏳ **等待测试验证** - 需要用户重新尝试生成路线图
- 📝 **前端 404 问题待进一步诊断** - 需要具体的前端日志

## 相关文件

- `backend/app/db/session.py` - 数据库连接池配置
- `backend/app/config/settings.py` - 应用配置
- `backend/app/services/roadmap_service.py` - 任务状态查询服务

## 注意事项

1. 修改已自动应用（--reload 模式）
2. 建议监控连接池使用情况
3. 如果问题持续，需要检查：
   - 数据库服务器性能和网络
   - PostgreSQL 服务器端配置
   - 是否有慢查询需要优化
4. 前端 404 需要提供具体的请求 URL 和 task_id 进行进一步诊断

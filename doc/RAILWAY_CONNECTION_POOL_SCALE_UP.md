# Railway 生产环境连接池扩容修复

**修复日期**: 2025-12-26  
**问题类型**: 连接池容量不足导致高并发时连接取消 (CancelledError)  
**数据库**: PostgreSQL (最大连接数 200)

---

## 问题描述

### 错误信息

```
asyncio.exceptions.CancelledError
```

**错误堆栈**（关键部分）：
```python
File "/usr/local/lib/python3.12/site-packages/asyncpg/connection.py", line 2421, in connect
File "/usr/local/lib/python3.12/site-packages/asyncpg/connect_utils.py", line 886, in _connect_addr
asyncio.exceptions.CancelledError
```

**错误位置**：
- API 端点：`/api/v1/waitlist` (`join_waitlist`)
- 操作：创建数据库连接时被取消

### 现象

1. Railway 生产环境频繁报错 `CancelledError`
2. 错误发生在创建数据库连接过程中
3. 高并发场景下更容易触发
4. 数据库支持 200 个连接，但连接池配置偏小

---

## 根本原因

### 1. 连接池容量不足

**修复前配置**：
- SQLAlchemy 连接池: `pool_size=10, max_overflow=20` (总计 **30 个连接**)
- Checkpointer 连接池: `min_size=1, max_size=5` (总计 **5 个连接**)
- **总连接数**: 35 个连接
- **数据库上限**: 200 个连接
- **利用率**: 17.5%（严重浪费资源）

**问题**：
- 生产环境并发请求较多（用户访问、路线图生成、教程内容生成）
- 30 个连接在高峰期很快耗尽
- 新请求等待连接超时后被取消

### 2. 超时配置偏低

**修复前**：
- SQLAlchemy `pool_timeout=30` 秒
- Checkpointer `timeout=30` 秒
- Railway 网络延迟可能较高，30 秒不够

**问题**：
- Railway 到数据库的网络可能有延迟
- 连接创建时间可能超过 30 秒
- 导致连接请求被提前取消

---

## 修复方案

### 1. 扩容 SQLAlchemy 连接池

**文件**: `backend/app/db/session.py`

**修改前**:
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)
```

**修改后**:
```python
# 生产环境配置（数据库最大连接数 200）
# - pool_size=40: 基础连接池（常驻连接）
# - max_overflow=60: 溢出连接（高峰期临时连接）
# - 总计: 100 个连接（预留 100 个给其他服务/管理连接）
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=40,           # 从 10 增加到 40
    max_overflow=60,        # 从 20 增加到 60
    pool_timeout=60,        # 从 30 秒增加到 60 秒
    pool_recycle=1800,
    pool_use_lifo=True,
    connect_args={
        "timeout": 60,      # 连接超时从 30 秒增加到 60 秒
    },
)
```

**优化效果**:
- ✅ **连接数 +233%**: 30 → 100 个连接
- ✅ **超时时间 +100%**: 30 秒 → 60 秒
- ✅ **高并发支持**: 可同时支持 100 个并发数据库操作

---

### 2. 扩容 Checkpointer 连接池

**文件**: `backend/app/core/orchestrator_factory.py`

**修改前**:
```python
cls._connection_pool = AsyncConnectionPool(
    conninfo=settings.CHECKPOINTER_DATABASE_URL,
    min_size=1,
    max_size=5,
    timeout=30,
)
```

**修改后**:
```python
# 使用连接池管理连接（生产环境配置）
# - min_size=2: 最小保持 2 个连接（确保基本可用性）
# - max_size=10: 最大 10 个连接（适度增加，应对 LangGraph 工作流并发）
# - timeout=60: 获取连接超时 60 秒（增加以应对 Railway 网络延迟）
# 总连接数预算: SQLAlchemy(100) + Checkpointer(10) = 110/200
cls._connection_pool = AsyncConnectionPool(
    conninfo=settings.CHECKPOINTER_DATABASE_URL,
    min_size=2,         # 从 1 增加到 2
    max_size=10,        # 从 5 增加到 10
    timeout=60,         # 从 30 秒增加到 60 秒
)
```

**优化效果**:
- ✅ **连接数 +100%**: 5 → 10 个连接
- ✅ **超时时间 +100%**: 30 秒 → 60 秒
- ✅ **工作流支持**: 支持更多 LangGraph 工作流并发

---

### 3. 增加数据库连接超时

**文件**: `backend/app/config/settings.py`

**修改**:
```python
@property
def CHECKPOINTER_DATABASE_URL(self) -> str:
    return (
        f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
        f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        f"?keepalives=1&keepalives_idle=30&keepalives_interval=10&keepalives_count=5"
        f"&connect_timeout=60&options=-c%20statement_timeout%3D120s"
        # ^^^^^^^^^^^^^ 从 30 增加到 60
    )
```

---

## 总连接数对比

| 连接池 | 修复前 | 修复后 | 增幅 |
|--------|--------|--------|------|
| **SQLAlchemy** | 10 + 20 = 30 | 40 + 60 = 100 | **+233%** |
| **Checkpointer** | 1~5 | 2~10 | **+100%** |
| **总连接数** | **35** | **110** | **+214%** |
| **数据库上限** | 200 | 200 | - |
| **利用率** | 17.5% | 55% | **+37.5%** |
| **预留连接** | 165 | 90 | - |

---

## 超时配置对比

| 配置项 | 修复前 | 修复后 | 增幅 |
|--------|--------|--------|------|
| **SQLAlchemy pool_timeout** | 30 秒 | 60 秒 | **+100%** |
| **SQLAlchemy connect timeout** | 30 秒 | 60 秒 | **+100%** |
| **Checkpointer pool timeout** | 30 秒 | 60 秒 | **+100%** |
| **Checkpointer connect_timeout** | 30 秒 | 60 秒 | **+100%** |

---

## 部署后验证

### 验证步骤

1. **检查启动日志**
   ```bash
   # Railway 日志应该显示新的连接池配置
   # SQLAlchemy: pool_size=40, max_overflow=60
   # Checkpointer: pool_min_size=2, pool_max_size=10
   ```

2. **监控数据库连接数**
   ```sql
   -- 查看当前连接数
   SELECT count(*) FROM pg_stat_activity WHERE datname = 'roadmap_db';
   
   -- 查看应用连接数
   SELECT count(*) FROM pg_stat_activity 
   WHERE datname = 'roadmap_db' AND application_name = 'roadmap_agent';
   ```

3. **压力测试**
   ```bash
   # 模拟高并发请求
   ab -n 1000 -c 50 https://your-railway-domain.up.railway.app/api/v1/waitlist
   ```

4. **观察日志**
   - ✅ 没有 `CancelledError` 错误
   - ✅ 没有 `QueuePool limit reached` 警告
   - ✅ 响应时间稳定

---

## 预期效果

### 修复前
```
❌ 高并发场景下频繁出现 CancelledError
❌ 连接池耗尽，新请求等待超时
❌ 用户体验差，部分请求失败
```

### 修复后
```
✅ 支持 100 个并发数据库连接（+233%）
✅ 连接超时时间增加到 60 秒，应对网络延迟
✅ 高并发场景下稳定运行
✅ 用户体验提升，请求成功率提高
```

---

## 监控建议

### 1. 连接池监控

在应用中添加连接池状态监控：

```python
# 在 /health 端点中添加连接池状态
@app.get("/health")
async def health_check():
    pool_status = {
        "pool_size": engine.pool.size(),
        "checked_in": engine.pool.checkedin(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow(),
    }
    return {
        "status": "healthy",
        "pool": pool_status,
    }
```

### 2. 数据库监控

定期检查数据库连接数：

```sql
-- 每小时执行一次
SELECT 
    application_name,
    count(*) as connections,
    state
FROM pg_stat_activity 
WHERE datname = 'roadmap_db'
GROUP BY application_name, state;
```

### 3. 告警配置

设置告警阈值：
- 连接数超过 150 → 发出警告
- 连接数超过 180 → 发出严重警告
- `CancelledError` 出现 → 立即通知

---

## 备注

1. **为什么不设置更大？**
   - 预留 90 个连接给：数据库管理工具、备份任务、其他服务
   - 避免单个应用占用所有连接，影响数据库稳定性

2. **如果还不够怎么办？**
   - 可以再增加到 `pool_size=50, max_overflow=80` (总计 130)
   - 但需要监控数据库 CPU 和内存，避免过载
   - 考虑引入读写分离或连接池分片

3. **开发环境是否需要调整？**
   - 不需要，开发环境并发低，保持原配置即可
   - 可以通过环境变量区分：
     ```python
     if settings.ENVIRONMENT == "production":
         pool_size = 40
     else:
         pool_size = 10
     ```

---

## 相关文档

- [DATABASE_CONNECTION_POOL_EXHAUSTION_FIX.md](./DATABASE_CONNECTION_POOL_EXHAUSTION_FIX.md) - 初次连接池优化
- [DEPLOYMENT_CONNECTION_POOL_FIX.md](./DEPLOYMENT_CONNECTION_POOL_FIX.md) - 部署环境连接池修复
- [CHECKPOINT_WRITE_TIMEOUT_FIX.md](./CHECKPOINT_WRITE_TIMEOUT_FIX.md) - Checkpoint 写入超时修复

---

## 修复状态

- [x] SQLAlchemy 连接池扩容 (30 → 100)
- [x] Checkpointer 连接池扩容 (5 → 10)
- [x] 超时时间增加 (30s → 60s)
- [ ] 部署到 Railway 生产环境
- [ ] 压力测试验证
- [ ] 监控数据收集


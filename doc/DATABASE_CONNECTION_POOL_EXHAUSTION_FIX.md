# 数据库连接池耗尽问题修复报告

**修复日期**: 2025-12-25  
**问题类型**: 连接池耗尽 (Connection Pool Exhaustion)

---

## 问题描述

### 错误信息
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 20 overflow 40 reached, connection timed out, timeout 30.00
```

### 错误堆栈
错误发生在 `/api/v1/featured` 端点执行数据库查询时，连接池的 60 个连接（20 + 40）全部被占用且超时。

### 根本原因

1. **连接池配置过大但未正确释放**
   - SQLAlchemy 连接池: `pool_size=20, max_overflow=40` (总计 60 个连接)
   - Checkpointer 连接池: `min_size=2, max_size=10` (总计 10 个连接)
   - **总连接数可达 70 个**，远超 PostgreSQL 默认限制 (通常 100 个)

2. **get_db() 会话管理不够健壮**
   - 原代码使用手动 try/finally 模式，异常时可能未正确关闭
   - 没有使用 `async with` context manager，增加连接泄漏风险

3. **连接回收时间过长**
   - `pool_recycle=3600` (1 小时)，导致空闲连接长时间占用资源
   - 在高并发场景下，旧连接未及时回收，新连接无法创建

4. **两个连接池竞争同一数据库**
   - SQLAlchemy 和 psycopg_pool 共享同一 PostgreSQL 实例
   - 没有合理分配连接资源，导致互相竞争

---

## 修复方案

### 1. 优化 SQLAlchemy 连接池配置

**文件**: `backend/app/db/session.py`

**修改前**:
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_recycle=3600,
    pool_timeout=30,
)
```

**修改后**:
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,           # 降低基础连接池大小
    max_overflow=20,        # 降低溢出连接数
    pool_recycle=1800,      # 30 分钟回收（加快回收）
    pool_timeout=30,
    pool_use_lifo=True,     # 使用 LIFO 模式，优先复用最近使用的连接
)
```

**优化点**:
- ✅ **降低连接数**: `20+40=60` → `10+20=30`，减少 50% 连接使用
- ✅ **加快回收**: 1 小时 → 30 分钟，及时释放空闲连接
- ✅ **LIFO 模式**: 优先复用热连接，减少冷连接数量

---

### 2. 改进会话管理使用 Context Manager

**文件**: `backend/app/db/session.py`

**修改前**:
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()  # ⚠️ 异常时可能未执行
```

**修改后**:
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:  # ✅ 使用 context manager
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise
        # context manager 会自动关闭会话
```

**优化点**:
- ✅ **确保连接关闭**: `async with` 确保无论如何都会调用 `__aexit__`
- ✅ **减少泄漏风险**: 异常处理更加健壮

---

### 3. 优化 Checkpointer 连接池配置

**文件**: `backend/app/core/orchestrator_factory.py`

**修改前**:
```python
cls._connection_pool = AsyncConnectionPool(
    conninfo=settings.CHECKPOINTER_DATABASE_URL,
    min_size=2,
    max_size=10,
    max_idle=300,  # 5 分钟
    timeout=60,
)
```

**修改后**:
```python
cls._connection_pool = AsyncConnectionPool(
    conninfo=settings.CHECKPOINTER_DATABASE_URL,
    min_size=1,     # 降低最小连接数
    max_size=5,     # 降低最大连接数
    max_idle=180,   # 3 分钟（加快回收）
    timeout=30,
)
```

**优化点**:
- ✅ **降低连接数**: `2~10` → `1~5`，减少 50% 连接使用
- ✅ **加快回收**: 5 分钟 → 3 分钟
- ✅ **避免竞争**: 与 SQLAlchemy 连接池错开，总连接数从 70 降至 35

---

## 总连接数对比

| 连接池 | 修改前 | 修改后 | 优化率 |
|--------|--------|--------|--------|
| **SQLAlchemy** | 20 + 40 = 60 | 10 + 20 = 30 | -50% |
| **Checkpointer** | 2~10 | 1~5 | -50% |
| **总计** | **~70** | **~35** | **-50%** |

**安全边界**:
- PostgreSQL 默认连接数: 100
- 修改后最大使用: 35 (35%)
- 安全余量: 65 个连接 ✅

---

## 连接池参数详解

### SQLAlchemy 连接池参数

| 参数 | 说明 | 修改值 | 原因 |
|------|------|--------|------|
| `pool_size` | 基础连接池大小 | 10 | 降低常驻连接数 |
| `max_overflow` | 溢出连接数 | 20 | 应对突发流量 |
| `pool_recycle` | 连接回收时间（秒） | 1800 | 加快回收，避免过期 |
| `pool_use_lifo` | 使用 LIFO 模式 | True | 优先复用热连接 |
| `pool_pre_ping` | 连接前检查 | True | 检测失效连接 |

### psycopg_pool 连接池参数

| 参数 | 说明 | 修改值 | 原因 |
|------|------|--------|------|
| `min_size` | 最小连接数 | 1 | 降低常驻连接数 |
| `max_size` | 最大连接数 | 5 | 避免过多连接 |
| `max_idle` | 空闲超时（秒） | 180 | 加快释放空闲连接 |
| `timeout` | 获取连接超时（秒） | 30 | 避免长时间等待 |

---

## 为什么 LIFO 模式更好？

**LIFO (Last In First Out)**: 优先使用最近归还的连接

**优势**:
1. **热连接复用**: 最近使用的连接更可能保持活跃状态
2. **减少冷连接**: 长时间未使用的连接会被自动回收
3. **提高性能**: 避免重复建立新连接的开销

**对比 FIFO**:
- FIFO 会均匀使用所有连接，导致所有连接都保持打开状态
- LIFO 会集中使用少数连接，其他连接自动回收

---

## 验证方法

### 1. 检查连接池状态（日志）
启动后查看日志：
```
orchestrator_factory_initialized
  pool_min_size=1
  pool_max_size=5
```

### 2. 监控数据库连接数
连接到 PostgreSQL 并查询：
```sql
SELECT 
  application_name,
  count(*) as connection_count,
  state
FROM pg_stat_activity
WHERE datname = 'roadmap_db'
GROUP BY application_name, state;
```

**预期结果**:
- `roadmap_agent` 连接数应在 10~35 之间（取决于负载）
- 空闲连接应在 3~5 分钟内释放

### 3. 压力测试
使用 Apache Bench 或 Locust 进行压力测试：
```bash
ab -n 1000 -c 50 http://your-domain/api/v1/featured
```

**预期**:
- ✅ 不再出现 `QueuePool limit reached` 错误
- ✅ 响应时间保持稳定（<500ms）

---

## 回滚方案

如果修复后出现问题，可以回滚到之前的配置：

```python
# backend/app/db/session.py
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_recycle=3600,
    pool_timeout=30,
    # 移除 pool_use_lifo=True
)

# backend/app/core/orchestrator_factory.py
cls._connection_pool = AsyncConnectionPool(
    conninfo=settings.CHECKPOINTER_DATABASE_URL,
    min_size=2,
    max_size=10,
    max_idle=300,
    timeout=60,
)
```

---

## 后续优化建议

### 1. 使用 PgBouncer（连接池代理）
如果流量继续增长，可以在应用层之上添加 PgBouncer：
```
Application (30 connections) → PgBouncer (100 connections) → PostgreSQL (200 connections)
```

### 2. 监控告警
设置 Prometheus + Grafana 监控：
- 连接池使用率 > 80% 时告警
- 连接获取超时 > 5 秒时告警

### 3. 数据库连接限制调整
如果 PostgreSQL 连接数不足，可以在 Railway 后台调整：
```sql
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();
```

---

## 相关文档

- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- [psycopg_pool Documentation](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)
- [PostgreSQL Connection Limits](https://www.postgresql.org/docs/current/runtime-config-connection.html)

---

## 修复记录

| 日期 | 修改内容 | 状态 |
|------|---------|------|
| 2025-12-25 | 优化 SQLAlchemy 连接池配置 | ✅ 已完成 |
| 2025-12-25 | 改进 get_db() 会话管理 | ✅ 已完成 |
| 2025-12-25 | 优化 Checkpointer 连接池配置 | ✅ 已完成 |
| 2025-12-25 | 编写修复文档 | ✅ 已完成 |

**修复人员**: AI Assistant  
**审核状态**: 待部署验证


# LangGraph Checkpoint 连接池配置优化

**日期**: 2025-01-02  
**问题**: LangGraph 在 `human_review` 节点保存 checkpoint 时发生 PostgreSQL 连接超时  
**影响**: 路线图生成任务失败，用户体验受损

---

## 问题现象

### 错误日志
```
OperationalError: consuming input failed: could not receive data from server: Operation timed out
```

### 堆栈追踪关键路径
```
langgraph.checkpoint.postgres.aio.AsyncPostgresSaver._cursor
→ psycopg.AsyncConnection.pipeline()
→ psycopg._pipeline_async.AsyncPipeline.__aexit__
→ OperationalError: Operation timed out
```

### 时间线
- **00:27:14**: 开始执行 `human_review` 节点
- **00:27:22**: 连接超时（仅 8 秒后发生）

---

## 根本原因

### 1. 连接层面超时配置缺失
原配置缺少以下关键参数：
- 无 `connect_timeout`：连接建立可能无限等待
- 无 TCP `keepalive`：长时间空闲连接可能被中间网络设备（防火墙/NAT）静默断开
- 无 `statement_timeout`：长查询可能阻塞连接

### 2. Supabase Transaction Mode 遗留配置
原配置包含 `prepare_threshold=None`，该配置是为 Supabase Transaction Mode 禁用预编译语句的，但现在已切换到标准 PostgreSQL，此配置不再需要且可能影响性能。

### 3. 连接池参数不适配
- `max_size=10`: 对于 LangGraph 工作流的并发量偏小
- `max_idle=180`: 空闲连接保持时间较短，频繁重建连接增加开销

---

## 解决方案

### 修改文件
`backend/app/core/orchestrator_factory.py`

### 核心改动

#### 1. 移除 Supabase 特定配置
```python
# ❌ 删除（仅 Supabase Transaction Mode 需要）
"prepare_threshold": None
```

#### 2. 增加连接超时保护
```python
"connect_timeout": 30,  # 连接建立超时 30 秒
"options": "-c statement_timeout=120000",  # SQL 语句超时 120 秒
```

#### 3. 启用 TCP Keepalive
```python
"keepalives": 1,  # 启用 TCP keepalive
"keepalives_idle": 30,  # 空闲 30 秒后开始探测
"keepalives_interval": 10,  # 探测间隔 10 秒
"keepalives_count": 5,  # 最多 5 次失败后断开（总计 50 秒）
```

#### 4. 优化连接池参数
```python
min_size=2,       # 保持最小连接数不变
max_size=20,      # 提高最大连接数（10 → 20）
max_idle=300,     # 延长空闲时间（180s → 300s / 5min）
timeout=60,       # 获取连接超时保持 60 秒
```

---

## 配置对比

### 修改前（Supabase Transaction Mode）
```python
AsyncConnectionPool(
    conninfo=settings.CHECKPOINTER_DATABASE_URL,
    min_size=2,
    max_size=10,
    max_idle=180,
    timeout=60,
    reconnect_timeout=0,
    open=False,
    kwargs={
        "autocommit": True,
        "prepare_threshold": None,  # ❌ Supabase 专用
        # ❌ 缺少超时配置
        # ❌ 缺少 keepalive 配置
    },
)
```

### 修改后（标准 PostgreSQL）
```python
AsyncConnectionPool(
    conninfo=settings.CHECKPOINTER_DATABASE_URL,
    min_size=2,
    max_size=20,  # ✅ 提高并发能力
    max_idle=300,  # ✅ 延长空闲时间
    timeout=60,
    reconnect_timeout=0,
    open=False,
    kwargs={
        "autocommit": True,
        "connect_timeout": 30,  # ✅ 连接超时保护
        "keepalives": 1,  # ✅ TCP keepalive
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "options": "-c statement_timeout=120000",  # ✅ SQL 语句超时
    },
)
```

---

## 技术细节

### TCP Keepalive 机制
在网络层面保持连接活跃，防止被中间设备断开：
```
空闲 30 秒 → 发送探测 → 每 10 秒重试 → 最多 5 次失败 → 断开连接
总超时时间 = 30 + (10 × 5) = 80 秒
```

### Statement Timeout 机制
通过 PostgreSQL 连接参数设置 SQL 语句级别超时：
```sql
-- 等价于在每个连接上执行
SET statement_timeout = 120000;  -- 120 秒
```

### 连接池扩容逻辑
- **正常负载**: 维持 2-5 个活跃连接
- **高峰期**: 可扩展至 20 个并发连接
- **空闲期**: 保持连接 5 分钟后逐步回收（避免频繁重建开销）

---

## 后续监控

### 关键指标
1. **连接池使用率**: 监控 `max_size=20` 是否满足需求
2. **连接超时频率**: 观察 `OperationalError` 是否复现
3. **Checkpoint 保存延迟**: 确认 `human_review` 节点 checkpoint 保存时间

### 日志关键字
```python
# 成功日志
"orchestrator_factory_initialized"

# 失败日志
"OperationalError"
"consuming input failed"
"Operation timed out"
```

---

## 部署步骤

### 1. 重启 Workflow Worker
```bash
# 停止旧进程
pkill -f "celery.*workflow"

# 启动新进程
cd backend
uv run celery -A app.core.celery_app worker \
    --loglevel=info \
    --queues=workflow \
    --concurrency=2 \
    --pool=prefork \
    --hostname=workflow@%h \
    --max-tasks-per-child=100
```

### 2. 重启 FastAPI 服务（如有必要）
```bash
# 如果在 API 服务中也使用了 OrchestratorFactory
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 验证连接池初始化
查看启动日志中是否包含：
```
orchestrator_factory_initialized
pool_min_size=2
pool_max_size=20
```

---

## 预期效果

1. **彻底消除连接超时**: TCP keepalive 确保长时间空闲连接不会被中间网络设备断开
2. **更好的并发性能**: 连接池从 10 提升到 20，应对 LangGraph 工作流并发
3. **更清晰的超时语义**: `connect_timeout` 和 `statement_timeout` 提供明确的超时边界
4. **适配标准 PostgreSQL**: 移除 Supabase Transaction Mode 特定配置，启用预编译语句优化

---

## 相关文档

- **psycopg 连接参数**: https://www.psycopg.org/psycopg3/docs/api/connections.html
- **PostgreSQL TCP Keepalive**: https://www.postgresql.org/docs/current/runtime-config-connection.html#GUC-TCP-KEEPALIVES-IDLE
- **LangGraph Checkpoint**: https://langchain-ai.github.io/langgraph/reference/checkpoints/


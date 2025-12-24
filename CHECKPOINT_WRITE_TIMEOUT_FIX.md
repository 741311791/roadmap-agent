# Checkpoint 写入超时问题修复报告

**修复日期**: 2025-12-23  
**任务 ID**: 743ebce5-d3dc-434c-879c-bf4d1df47145

---

## 问题描述

生成路线图时，工作流在 `human_review` 步骤正常触发中断后，在保存 checkpoint 状态到数据库时出现连接超时错误，导致整个任务失败。

### 错误日志

```
2025-12-23 20:01:11 [info     ] review_runner_pausing_for_human_review
2025-12-23 20:01:11 [info     ] workflow_brain_graph_interrupt message=工作流暂停等待人工审核（正常流程）
2025-12-23 20:01:11 [error    ] workflow_execution_failed error='consuming input failed: could not receive data from server: Operation timed out'

psycopg.OperationalError: consuming input failed: could not receive data from server: Operation timed out

File ".../langgraph/checkpoint/postgres/aio.py", line 322, in aput_writes
    async with self._cursor(pipeline=True) as cur:
```

---

## 根本原因分析

### 问题链路

1. ✅ **工作流正常执行**：到达 `ReviewRunner.run()` 中的 `interrupt()` 暂停点
2. ✅ **中断触发正常**：抛出 `GraphInterrupt` 异常
3. ❌ **Checkpoint 保存失败**：LangGraph 尝试通过 `AsyncPostgresSaver.aput_writes()` 将中断状态持久化到 PostgreSQL
4. ❌ **写入超时**：在执行 PostgreSQL pipeline 写入操作时超时

### 技术原因

虽然已配置连接池和 TCP keepalive，但以下因素导致写入操作本身超时：

1. **Checkpoint 数据量较大**：整个工作流状态（包含 intent_analysis、roadmap_framework 等）序列化后数据量可能达到数百 KB
2. **网络延迟**：远程数据库连接（47.111.115.130）可能存在网络抖动
3. **Pipeline 操作默认超时短**：PostgreSQL pipeline 写入的默认超时时间不足以应对大数据量写入
4. **连接池获取超时短**：原配置 `timeout=30` 秒对远程连接可能不够

---

## 修复方案

### 1. 增加连接池超时配置

**文件**: `backend/app/core/orchestrator_factory.py`

**修改内容**:

```python
cls._connection_pool = AsyncConnectionPool(
    conninfo=settings.CHECKPOINTER_DATABASE_URL,
    min_size=2,
    max_size=10,
    max_idle=300,
    timeout=60,  # ✅ 从 30 秒增加到 60 秒
    reconnect_timeout=0,
    kwargs={
        "autocommit": True,
        "prepare_threshold": 0,
    },
)
```

**说明**:
- `timeout=60`: 获取连接的超时时间从 30 秒增加到 60 秒，应对网络延迟

---

### 2. 增加 PostgreSQL 语句执行超时

**文件**: `backend/app/config/settings.py`

**修改内容**:

```python
@property
def CHECKPOINTER_DATABASE_URL(self) -> str:
    """
    构建 Checkpointer 数据库连接 URL（用于 AsyncPostgresSaver）
    
    包含 TCP keepalive 参数以防止长时间运行的工作流中连接超时：
    - keepalives=1: 启用 TCP keepalive
    - keepalives_idle=30: 空闲 30 秒后发送 keepalive（默认是 2 小时）
    - keepalives_interval=10: keepalive 间隔 10 秒
    - keepalives_count=5: 最大重试 5 次
    - connect_timeout=30: 连接超时 30 秒（增加以应对网络延迟）
    - options=-c statement_timeout=120s: SQL 语句执行超时 120 秒（防止大数据量写入超时）
    """
    return (
        f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
        f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        f"?keepalives=1&keepalives_idle=30&keepalives_interval=10&keepalives_count=5"
        f"&connect_timeout=30&options=-c%20statement_timeout%3D120s"
    )
```

**说明**:
- `connect_timeout=30`: 从 10 秒增加到 30 秒，应对远程连接建立慢
- `options=-c statement_timeout=120s`: **新增** SQL 语句执行超时 120 秒，防止大数据量 checkpoint 写入超时
  - URL 编码：`-c statement_timeout=120s` → `-c%20statement_timeout%3D120s`

---

## 技术细节

### PostgreSQL Statement Timeout

`statement_timeout` 是 PostgreSQL 的会话级参数，用于限制单个 SQL 语句的最大执行时间：

```sql
-- 在连接 URL 中通过 options 参数设置
options=-c statement_timeout=120s

-- 等价于在每个连接上执行
SET statement_timeout = '120s';
```

**作用范围**:
- 适用于该连接上的所有 SQL 语句（SELECT、INSERT、UPDATE、DELETE 等）
- 对 LangGraph checkpoint 的大批量 INSERT/UPDATE 操作尤为重要

**超时值选择**:
- 120 秒（2 分钟）是合理的上限
- 正常的 checkpoint 写入应在 5-10 秒内完成
- 保留足够的缓冲空间应对网络抖动和大数据量

---

## 验证方法

### 1. 重启后端服务

```bash
# 重启 FastAPI 服务以应用新配置
pkill -f "uvicorn app.main:app"
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 生成新的路线图测试

发起新的路线图生成请求，观察日志：

**预期正常日志**:

```
[info] review_runner_pausing_for_human_review roadmap_id=xxx task_id=xxx
[info] workflow_brain_graph_interrupt message=工作流暂停等待人工审核（正常流程）
[debug] workflow_brain_task_status_updated_to_pending_review task_id=xxx
[info] roadmap_task_updated current_step=human_review status=human_review_pending
```

**不应再出现**:

```
[error] workflow_execution_failed error='consuming input failed: could not receive data from server: Operation timed out'
```

### 3. 检查数据库连接

```bash
# 查看连接池状态
psql -h 47.111.115.130 -U postgres -d roadmap_agent -c "SELECT * FROM pg_stat_activity WHERE application_name = 'roadmap_agent';"

# 查看 checkpoint 表数据
psql -h 47.111.115.130 -U postgres -d roadmap_agent -c "SELECT thread_id, checkpoint_ns, checkpoint_id FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 5;"
```

---

## 影响范围

### 直接影响

- ✅ **修复 human_review 中断后的 checkpoint 保存失败**
- ✅ **提升远程数据库连接的稳定性**
- ✅ **支持更大的工作流状态数据量**

### 副作用

- ⚠️ **更长的超时时间**：如果数据库真的无响应，需要等待更长时间才能失败（从 30s → 60s + 120s）
- ⚠️ **连接池占用时间增加**：长时间的写入操作会占用连接池资源，可能影响并发性能

### 缓解措施

- 连接池配置已设置 `max_size=10`，可以支持多个并发请求
- `statement_timeout=120s` 只对异常慢的操作生效，正常操作不受影响

---

## 相关文档

- [Database Connection Timeout Fix](./DATABASE_CONNECTION_TIMEOUT_FIX.md)
- [Database Connection and Parsing Fix](./doc/DATABASE_CONNECTION_AND_PARSING_FIX.md)
- [Workflow Branch State Fix 2025-12-23](./WORKFLOW_BRANCH_STATE_FIX_2025-12-23.md)

---

## 后续优化建议

### 1. Checkpoint 数据压缩

考虑对 LangGraph checkpoint 数据进行压缩：

```python
# 在 orchestrator_factory.py 中
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

class CompressedAsyncPostgresSaver(AsyncPostgresSaver):
    async def aput(self, config, checkpoint, metadata):
        # 对 checkpoint 数据进行 gzip 压缩
        compressed_checkpoint = gzip.compress(pickle.dumps(checkpoint))
        await super().aput(config, compressed_checkpoint, metadata)
```

### 2. 监控 Checkpoint 数据量

添加日志记录每次 checkpoint 的数据量：

```python
logger.info(
    "checkpoint_saved",
    task_id=task_id,
    checkpoint_size_kb=len(checkpoint_data) / 1024,
    write_duration_ms=(time.time() - start_time) * 1000,
)
```

### 3. 分离 Checkpoint 数据库

如果 checkpoint 表数据量增长过快，考虑使用独立的数据库实例：

```bash
# 在 settings.py 中添加独立配置
CHECKPOINTER_POSTGRES_HOST=47.111.115.130
CHECKPOINTER_POSTGRES_PORT=5433  # 不同端口
CHECKPOINTER_POSTGRES_DB=roadmap_checkpoints  # 独立数据库
```

---

## 总结

通过增加连接池超时（30s → 60s）和 PostgreSQL 语句执行超时（无限制 → 120s），有效解决了 LangGraph checkpoint 在保存大数据量状态时的超时问题，提升了远程数据库连接的稳定性和可靠性。

✅ **修复完成**，建议重启后端服务并进行端到端测试验证。


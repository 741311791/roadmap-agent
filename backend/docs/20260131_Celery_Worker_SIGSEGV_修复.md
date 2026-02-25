# Celery Worker SIGSEGV 崩溃问题修复

**日期**：2026-01-31  
**问题类型**：严重 Bug（导致路线图生成任务失败）  
**状态**：✅ 已修复

---

## 一、问题现象

### 1.1 用户报错

前端发起路线图生成任务后，Celery Worker 进程崩溃并报错：

```
[2026-01-31 15:40:14,640: ERROR/MainProcess] Process 'ForkPoolWorker-56' pid:57545 exited with 'signal 11 (SIGSEGV)'
[2026-01-31 15:40:14,657: ERROR/MainProcess] Task handler raised error: WorkerLostError('Worker exited prematurely: signal 11 (SIGSEGV) Job: 48.')
```

### 1.2 崩溃时序

从日志分析，崩溃发生在：

1. ✅ Worker 进程初始化完成
2. ✅ LangGraph 连接池配置完成：`langgraph_connection_pool_configured`
3. ❌ **立即崩溃**：`Process exited with 'signal 11 (SIGSEGV)'`
4. 🔄 任务自动重试，新 Worker 继续崩溃（死循环）

---

## 二、根本原因分析

### 2.1 SIGSEGV 错误

**SIGSEGV (Segmentation Fault)** 是段错误，通常由以下原因引起：

- 访问无效内存地址
- C 扩展库的 bug
- 多进程环境下的资源竞争

### 2.2 Celery Prefork 模式问题

Celery 使用 prefork 模式启动 Worker：

1. **父进程**：启动时创建 `OrchestratorFactory`，初始化 `AsyncConnectionPool`
2. **子进程**：通过 `fork()` 继承父进程的内存空间
3. ⚠️ **问题**：`AsyncConnectionPool` 内部的连接和事件循环绑定到父进程
4. ❌ **崩溃**：子进程尝试使用这些连接时，触发 SIGSEGV

### 2.3 代码位置

**问题代码**：`backend/app/core/celery_app.py`

```python
@worker_process_init.connect
def on_worker_process_init(**kwargs):
    # ...
    
    # ❌ 错误：只是置空引用，没有重新初始化
    OrchestratorFactory._initialized = False
    OrchestratorFactory._connection_pool = None
    OrchestratorFactory._checkpointer = None
    # ...
```

**核心问题**：

- 虽然将引用置空，但没有在子进程中重新创建连接池
- 子进程后续访问数据库时，仍然尝试使用父进程的连接，导致崩溃

---

## 三、解决方案

### 3.1 核心修复

在 `worker_process_init` 钩子中，完全重新初始化 `OrchestratorFactory`：

```python
@worker_process_init.connect
def on_worker_process_init(**kwargs):
    # ...
    
    # ✅ 步骤1: 关闭父进程的连接池
    if OrchestratorFactory._connection_pool:
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(OrchestratorFactory._connection_pool.close())
            logger.info("worker_parent_connection_pool_closed")
        except Exception as close_error:
            logger.warning("worker_parent_connection_pool_close_failed", error=str(close_error))
    
    # ✅ 步骤2: 重置所有单例对象
    OrchestratorFactory._initialized = False
    OrchestratorFactory._connection_pool = None
    OrchestratorFactory._checkpointer = None
    OrchestratorFactory._state_manager = None
    OrchestratorFactory._agent_factory = None
    
    # ✅ 步骤3: 在子进程中重新初始化（关键）
    loop = asyncio.get_event_loop()
    loop.run_until_complete(OrchestratorFactory.initialize())
    
    logger.info("worker_orchestrator_factory_reinitialized")
```

### 3.2 降低 Tavily API 速率限制

从错误日志发现，还存在 Tavily API 限流问题：

```
ERROR | tavily_api_search_failed | error='Your request has been blocked due to excessive requests.'
```

**修复**：降低开发环境的速率限制

```bash
# .env 修改
TAVILY_RATE_LIMIT_PER_MINUTE=5  # 从 80 降低到 5
```

**原因**：

- 开发环境的 Tavily API Key（`tvly-dev-*`）限制较低
- 高并发 Celery Worker 导致短时间内请求过多
- 虽然有全局速率限制器，但仍然超限

### 3.3 降低 Celery Worker 并发数

当前启动命令：

```bash
uv run celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency=8 \      # ❌ 太高
    --hostname=workflow@%h \
    --max-tasks-per-child=500 \
    --queues=celery
```

**建议修改**：

```bash
uv run celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency=2 \      # ✅ 降低到 2
    --hostname=workflow@%h \
    --max-tasks-per-child=500 \
    --queues=celery
```

**理由**：

- 开发环境无需高并发（节省资源）
- 降低数据库连接池压力
- 减少 Tavily API 并发请求
- 便于调试和日志分析

---

## 四、验证步骤

### 4.1 重启 Celery Worker

```bash
# 1. 停止当前 Worker（Ctrl+C）

# 2. 重新启动（使用新的并发配置）
cd backend
uv run celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --hostname=workflow@%h \
    --max-tasks-per-child=500 \
    --queues=celery
```

### 4.2 测试路线图生成

1. 前端提交一个新的路线图生成任务
2. 观察 Celery Worker 日志，确认以下内容：

```
✅ worker_parent_connection_pool_closed
✅ worker_orchestrator_factory_reset
✅ worker_orchestrator_factory_reinitialized
✅ worker_process_init_completed
✅ 任务正常执行，无 SIGSEGV 崩溃
```

### 4.3 检查日志

```bash
# 查看错误日志
tail -f backend/logs/err.log

# 确认没有以下错误：
# ❌ signal 11 (SIGSEGV)
# ❌ WorkerLostError
# ❌ Your request has been blocked due to excessive requests
```

---

## 五、相关问题

### 5.1 为什么之前没有崩溃？

**可能原因**：

1. **连接池配置变化**：最近调整了 `AsyncConnectionPool` 的参数
2. **LangGraph 升级**：新版本的 `AsyncPostgresSaver` 行为变化
3. **并发增加**：从低并发（2-4）提升到高并发（8），问题暴露

### 5.2 生产环境是否会有此问题？

**是的**，生产环境也会遇到相同问题，因为：

- Celery prefork 模式是默认配置
- `AsyncConnectionPool` 不能跨进程共享（这是 PostgreSQL 客户端的通用限制）

**建议**：

- 在生产环境部署前，务必使用本修复版本
- 监控 Celery Worker 的崩溃率（`signal 11`）
- 设置 Sentry 告警，捕获 SIGSEGV 错误

---

## 六、总结

### 6.1 关键修复

1. ✅ **重新初始化连接池**：在子进程中完全重建 `OrchestratorFactory`
2. ✅ **降低 API 速率限制**：`TAVILY_RATE_LIMIT_PER_MINUTE=5`
3. ✅ **降低 Worker 并发**：`--concurrency=2`

### 6.2 技术要点

- **AsyncConnectionPool 不能跨进程共享**（关键知识点）
- **Celery worker_process_init 钩子**必须重新初始化所有进程级资源
- **开发环境 API Key 限制较低**，需要保守配置速率限制

### 6.3 预防措施

- 在 FastAPI 应用启动时初始化 `OrchestratorFactory`（已有）
- 在 Celery Worker 启动时重新初始化（本次修复）
- 监控 Worker 崩溃率和 API 限流错误
- 定期检查 `psycopg_pool` 和 `LangGraph` 的更新日志

---

## 七、参考资料

- [Celery Signals - worker_process_init](https://docs.celeryq.dev/en/stable/userguide/signals.html#worker-process-init)
- [psycopg3 Connection Pool](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)
- [LangGraph AsyncPostgresSaver](https://langchain-ai.github.io/langgraph/reference/checkpoints/#langgraph.checkpoint.postgres.aio.AsyncPostgresSaver)
- [SIGSEGV 错误排查](https://en.wikipedia.org/wiki/Segmentation_fault)

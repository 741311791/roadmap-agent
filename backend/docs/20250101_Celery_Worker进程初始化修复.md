# Celery Worker 进程初始化修复

## 问题描述

Celery Worker 在处理路线图生成请求时发生 `TimeoutError`，阻塞整个进程，导致后续请求无法处理。

### 错误表现

```
TimeoutError
  File "~/.local/share/uv/python/cpython-3.12.8-macos-aarch64-none/lib/python3.12/asyncio/base_events.py", line 665, in run_until_complete
    return future.result()
```

## 根本原因分析

### 1. Celery prefork 模型的问题

Celery 使用 prefork 模式启动 Worker：
1. **父进程**：加载应用代码，初始化全局变量（包括数据库 engine 缓存）
2. **Fork 子进程**：继承父进程的所有全局状态
3. **问题**：子进程继承的 engine 绑定到**父进程的事件循环**

### 2. asyncpg 的事件循环绑定

- asyncpg 在创建连接时会设置 JSON codec（异步操作）
- 这些操作的 Future 对象绑定到创建时的事件循环
- 子进程使用独立的事件循环，无法完成这些 Future
- 结果：`asyncio.run_until_complete()` 永久阻塞

### 3. 连接池继承问题

即使使用事件循环感知的 engine 缓存（`_engine_cache[loop_id]`）：
- Fork 后，子进程的 `_engine_cache` 仍包含父进程的 engine 引用
- 新事件循环的 ID 可能与父进程相同或不同
- 如果相同，会错误地复用父进程的 engine

## 解决方案

### 1. 添加 Engine 缓存重置函数

在 `session.py` 中添加：

```python
def reset_engine_cache() -> None:
    """
    重置全局 engine 缓存
    
    ⚠️ 用于 Celery Worker 进程初始化时调用
    """
    global _engine_cache
    _engine_cache.clear()
    logger.info("db_engine_cache_reset")
```

### 2. 添加 Worker 进程初始化钩子

在 `celery_app.py` 中：

```python
from celery.signals import worker_process_init

@worker_process_init.connect
def on_worker_process_init(**kwargs):
    """Worker 子进程初始化时调用"""
    from app.db.session import reset_engine_cache
    reset_engine_cache()
    
    try:
        from app.db.celery_session import reset_celery_engine_cache
        reset_celery_engine_cache()
    except ImportError:
        pass
```

### 3. Celery 专用数据库会话模块

`celery_session.py` 提供：
- **NullPool**：每次创建新连接，避免连接池状态共享
- **CeleryRepositoryFactory**：专用的 Repository 工厂
- **celery_safe_session_with_retry**：带重试机制的会话管理

## 修改文件清单

1. **`app/db/session.py`**：添加 `reset_engine_cache()` 函数
2. **`app/db/celery_session.py`**：添加 `reset_celery_engine_cache()` 函数
3. **`app/core/celery_app.py`**：添加 `worker_process_init` 信号处理器

## 验证方法

1. 启动 Celery Worker
2. 观察日志：应看到 `celery_worker_process_init` 和 `db_engine_cache_reset`
3. 提交路线图生成请求
4. 确认请求正常完成，无 TimeoutError

## 相关文档

- `20250101_Celery连接池耗尽修复.md`
- `20251231_Railway连接池耗尽修复.md`


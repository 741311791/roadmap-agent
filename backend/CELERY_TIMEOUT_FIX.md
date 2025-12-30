# Celery 任务超时问题修复

## 问题描述

Celery Worker 在执行路线图生成任务时抛出 `SoftTimeLimitExceeded` 异常：

```
billiard/pool.py:228 in soft_timeout_sighandler
❱ 228 │   raise SoftTimeLimitExceeded()
SoftTimeLimitExceeded: SoftTimeLimitExceeded()
```

**根本原因**：路线图生成工作流包含多个阶段（意图分析、课程设计、结构验证、人工审核、内容生成），每个阶段都可能涉及多次 LLM API 调用。之前的全局超时配置（4 分钟软超时、5 分钟硬超时）对于这类复杂任务来说太短了。

## 解决方案

### 1. 调整全局超时配置

**文件**：`backend/app/core/celery_app.py`

```python
# 任务超时配置（全局默认值，特定任务可覆盖）
task_time_limit=600,  # 10 分钟硬超时（原 5 分钟）
task_soft_time_limit=540,  # 9 分钟软超时（原 4 分钟）
```

**影响**：所有未明确指定超时的任务将使用新的 10 分钟默认超时。

### 2. 路线图生成任务专用超时

**文件**：`backend/app/tasks/roadmap_generation_tasks.py`

```python
@celery_app.task(
    name="roadmap_generation.generate_roadmap",
    bind=True,
    max_retries=0,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=1800,  # 30 分钟硬超时（新增）
    soft_time_limit=1680,  # 28 分钟软超时（新增）
)
def generate_roadmap(...):
    ...
```

**理由**：路线图生成工作流是最复杂的任务，可能包含：
- **IntentAnalysisRunner**：1-2 次 LLM 调用
- **CurriculumDesignRunner**：2-5 次 LLM 调用
- **ValidationRunner**（可能循环）：每次循环 2-3 次 LLM 调用
- **ReviewRunner**（人工审核，可能暂停）：等待时间不可控
- **ContentRunner**：每个 Concept 3-5 次 LLM 调用（教程、资源、测验）

30 分钟的超时为复杂路线图（如 10+ 个概念）提供了足够的执行时间。

### 3. 其他任务的超时配置（已存在，保持不变）

#### 内容生成任务
**文件**：`backend/app/tasks/content_generation_tasks.py`

```python
@celery_app.task(
    time_limit=1800,  # 30 分钟
    soft_time_limit=1500,  # 25 分钟
)
def generate_roadmap_content(...):
    ...
```

#### 内容重试任务
**文件**：`backend/app/tasks/content_retry_tasks.py`

```python
@celery_app.task(
    time_limit=600,  # 10 分钟
    soft_time_limit=540,  # 9 分钟
)
def retry_tutorial_task(...):
    ...
```

## 超时配置策略

| 任务类型 | 硬超时 | 软超时 | 说明 |
|---------|--------|--------|------|
| 全局默认 | 10 分钟 | 9 分钟 | 适用于大多数任务 |
| 路线图生成 | 30 分钟 | 28 分钟 | 复杂工作流，多阶段多 LLM 调用 |
| 批量内容生成 | 30 分钟 | 25 分钟 | 多个 Concept 的内容生成 |
| 单个内容重试 | 10 分钟 | 9 分钟 | 单个教程/资源/测验 |
| 日志批量写入 | 5 分钟 | 4 分钟 | 简单数据库操作 |

## 部署步骤

### 1. 重启 Celery Worker

```bash
# 停止当前 Worker
pkill -f "celery -A app.core.celery_app worker"

# 启动新 Worker
cd backend
celery -A app.core.celery_app worker \
    --loglevel=info \
    --pool=prefork \
    --concurrency=2 \
    -Q content_generation,roadmap_workflow,logs,celery
```

### 2. 验证配置

```bash
# 检查 Worker 配置
celery -A app.core.celery_app inspect conf | grep time_limit
```

应该看到：
```json
{
  "task_time_limit": 600,
  "task_soft_time_limit": 540
}
```

### 3. 监控任务执行

```bash
# 实时查看任务状态
celery -A app.core.celery_app inspect active

# 查看任务执行历史
celery -A app.core.celery_app inspect stats
```

## 注意事项

### Soft Timeout vs Hard Timeout

- **Soft Timeout**：抛出 `SoftTimeLimitExceeded` 异常，任务可以捕获并进行清理操作（如保存状态、发送通知）
- **Hard Timeout**：强制终止任务进程（SIGKILL），无法清理，2 分钟后触发

**最佳实践**：
```python
@celery_app.task(soft_time_limit=540)
def long_running_task():
    try:
        # 执行任务逻辑
        ...
    except SoftTimeLimitExceeded:
        # 捕获软超时，进行清理
        logger.warning("Task is taking too long, cleaning up...")
        # 保存状态到数据库
        # 发送 WebSocket 通知
        raise  # 重新抛出，标记任务失败
```

### 如何选择合适的超时时间

1. **测量实际执行时间**：
   ```python
   logger.info("task_started", task_id=task_id)
   start_time = time.time()
   
   # 执行任务
   ...
   
   duration = time.time() - start_time
   logger.info("task_completed", task_id=task_id, duration=duration)
   ```

2. **设置超时为 P95 执行时间的 2-3 倍**：
   - 如果任务通常在 5 分钟内完成，但偶尔需要 10 分钟
   - 设置软超时为 25 分钟，硬超时为 30 分钟

3. **考虑外部 API 的延迟**：
   - LLM API 调用：2-30 秒/次
   - 网页搜索（Tavily）：1-5 秒/次
   - 数据库操作：0.1-1 秒/次

## 相关资源

- [Celery Time Limits Documentation](https://docs.celeryq.dev/en/stable/userguide/workers.html#time-limits)
- [Billiard (Celery's Multiprocessing Library)](https://github.com/celery/billiard)
- `backend/CELERY_WORKER_GUIDE.md`：Celery Worker 部署完整指南
- `backend/app/core/celery_app.py`：Celery 应用配置


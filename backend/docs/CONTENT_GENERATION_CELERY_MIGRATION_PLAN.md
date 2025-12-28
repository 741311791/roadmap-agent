# 内容生成 Celery 迁移执行计划

> **目标**：将内容生成（ContentRunner）从 FastAPI BackgroundTasks 迁移到 Celery 独立进程，彻底解决请求阻塞问题。

---

## 一、问题背景

### 1.1 当前架构问题

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Process                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Event Loop (单个)                   │   │
│  │                                                  │   │
│  │   ┌─────────────┐    ┌─────────────────────┐    │   │
│  │   │ HTTP 请求处理 │    │  BackgroundTasks    │    │   │
│  │   │   (等待)     │<-->│  (内容生成任务)      │    │   │
│  │   └─────────────┘    │  - 30+ 概念并发      │    │   │
│  │                      │  - 90+ LLM 调用      │    │   │
│  │                      └─────────────────────┘    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓
            ⚠️ 事件循环被内容生成任务占满
            ⚠️ 其他请求无法及时处理
```

### 1.2 目标架构

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Process                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Event Loop                          │   │
│  │   ┌─────────────┐                               │   │
│  │   │ HTTP 请求处理 │  ← 专注处理 HTTP 请求         │   │
│  │   └─────────────┘                               │   │
│  └─────────────────────────────────────────────────┘   │
│                         │                               │
│                    Redis Queue                          │
│                         │                               │
└─────────────────────────┼───────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Celery Worker Process (独立)               │
│  ┌─────────────────────────────────────────────────┐   │
│  │   ┌─────────────────────┐                       │   │
│  │   │  内容生成任务        │  ← 独立进程执行       │   │
│  │   │  - 教程生成          │                       │   │
│  │   │  - 资源推荐          │                       │   │
│  │   │  - 测验生成          │                       │   │
│  │   └─────────────────────┘                       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 二、短期方案（已完成 ✅）

### 2.1 增加 uvicorn Workers

**修改 `Dockerfile`**：
```dockerfile
# 使用多 Worker 模式
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-4}
```

**效果**：
- 4 个 Worker 进程分担请求
- 一个 Worker 执行内容生成时，其他 Worker 仍可处理请求

### 2.2 事件循环让出优化

**修改 `content_runner.py`**：
```python
async with semaphore:
    # 主动让出事件循环时间片
    await asyncio.sleep(0)
    
    # 每 5 个概念额外让出
    if current_progress % 5 == 0:
        await asyncio.sleep(0.05)
```

**效果**：
- 允许其他协程有机会执行
- 减少事件循环"饥饿"现象

---

## 三、中长期迁移计划

### Phase 1: 基础设施准备（1-2 天）

#### 1.1 创建内容生成 Celery 任务模块

```bash
# 创建新文件
touch backend/app/tasks/content_generation_tasks.py
```

**文件结构**：
```python
# backend/app/tasks/content_generation_tasks.py
"""
内容生成 Celery 任务

将内容生成从 FastAPI 主进程迁移到独立的 Celery Worker，
实现真正的进程隔离，避免阻塞主应用。
"""
from celery import shared_task
from app.core.celery_app import celery_app

@celery_app.task(
    name="app.tasks.content_generation_tasks.generate_roadmap_content",
    queue="content_generation",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=1800,  # 30分钟硬超时
    soft_time_limit=1500,  # 25分钟软超时
)
def generate_roadmap_content(
    self,
    task_id: str,
    roadmap_id: str,
    roadmap_framework_data: dict,
    user_preferences_data: dict,
):
    """
    为路线图生成所有概念的内容
    
    Args:
        task_id: 追踪 ID
        roadmap_id: 路线图 ID
        roadmap_framework_data: 路线图框架数据（JSON 序列化）
        user_preferences_data: 用户偏好数据（JSON 序列化）
    """
    # 实现见 Phase 2
    pass
```

#### 1.2 更新 Celery 配置

```python
# backend/app/core/celery_app.py

celery_app.conf.update(
    # ... 现有配置 ...
    
    task_routes={
        "app.tasks.log_tasks.batch_write_logs": {"queue": "logs"},
        "app.tasks.content_generation_tasks.*": {"queue": "content_generation"},
    },
    
    # 自动发现任务模块
    imports=(
        "app.tasks.log_tasks",
        "app.tasks.content_generation_tasks",  # 新增
    ),
)
```

#### 1.3 更新 docker-compose.yml

```yaml
# 新增内容生成 Worker
celery_content_worker:
  build:
    context: .
    dockerfile: Dockerfile
  environment:
    - ENVIRONMENT=development
    - DEBUG=true
    - POSTGRES_HOST=postgres
    - REDIS_HOST=redis
  env_file:
    - .env
  depends_on:
    - postgres
    - redis
  volumes:
    - ./app:/app/app
    - ./prompts:/app/prompts
  command: >
    celery -A app.core.celery_app worker
    --loglevel=info
    --queues=content_generation
    --concurrency=2
    --pool=prefork
    --hostname=content@%h
    --max-tasks-per-child=50
```

---

### Phase 2: 任务实现（2-3 天）

#### 2.1 实现同步版 ContentRunner

由于 Celery 任务默认是同步执行的，需要将异步逻辑包装为同步：

```python
# backend/app/tasks/content_generation_tasks.py

import asyncio
from typing import Any

def run_async(coro):
    """在同步上下文中运行异步协程"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(...)
def generate_roadmap_content(self, task_id: str, ...):
    """Celery 任务入口（同步）"""
    return run_async(_async_generate_content(task_id, ...))


async def _async_generate_content(
    task_id: str,
    roadmap_id: str,
    roadmap_framework_data: dict,
    user_preferences_data: dict,
):
    """内容生成核心逻辑（异步）"""
    from app.models.domain import RoadmapFramework, LearningPreferences
    from app.core.orchestrator.node_runners.content_runner import ContentRunner
    from app.db.repository_factory import get_repository_factory
    
    # 反序列化数据
    framework = RoadmapFramework.model_validate(roadmap_framework_data)
    preferences = LearningPreferences.model_validate(user_preferences_data)
    
    # 创建 ContentRunner 并执行
    # ... 实现细节
```

#### 2.2 修改工作流分离内容生成

将工作流拆分为两部分：

1. **Framework 生成阶段**（在 FastAPI 进程中执行）
   - IntentAnalysis → CurriculumDesign → Validation → Review
   
2. **Content 生成阶段**（在 Celery Worker 中执行）
   - Tutorial + Resource + Quiz 并行生成

```python
# backend/app/core/orchestrator/node_runners/content_runner.py

class ContentRunner:
    async def run(self, state: RoadmapState) -> dict:
        """修改后：发送任务到 Celery 而不是直接执行"""
        from app.tasks.content_generation_tasks import generate_roadmap_content
        
        framework = state.get("roadmap_framework")
        if not framework:
            raise ValueError("路线图框架不存在")
        
        # 发送任务到 Celery（异步，立即返回）
        task = generate_roadmap_content.delay(
            task_id=state["task_id"],
            roadmap_id=state.get("roadmap_id"),
            roadmap_framework_data=framework.model_dump(mode="json"),
            user_preferences_data=state["user_request"].preferences.model_dump(mode="json"),
        )
        
        logger.info(
            "content_generation_task_queued",
            task_id=state["task_id"],
            celery_task_id=task.id,
        )
        
        # 返回状态，标记内容生成已启动
        return {
            "content_generation_status": "queued",
            "celery_task_id": task.id,
            "current_step": "content_generation_queued",
        }
```

#### 2.3 实现进度回调

使用 WebSocket 或 Redis Pub/Sub 报告进度：

```python
# 在 Celery 任务中发送进度更新
async def _report_progress(task_id: str, concept_id: str, status: str):
    """通过 Redis Pub/Sub 发送进度"""
    from app.services.notification_service import notification_service
    
    await notification_service.publish_concept_progress(
        task_id=task_id,
        concept_id=concept_id,
        status=status,
    )
```

---

### Phase 3: API 适配（1-2 天）

#### 3.1 修改生成端点

```python
# backend/app/api/v1/endpoints/generation.py

@router.post("/generate")
async def generate_roadmap_async(request: UserRequest, ...):
    """
    修改后：
    1. Framework 生成仍使用 BackgroundTasks
    2. Content 生成由 Celery 处理
    """
    task_id = str(uuid.uuid4())
    
    # 只执行 Framework 生成阶段
    background_tasks.add_task(
        _execute_framework_generation_task,  # 新函数：不包含 Content 生成
        request,
        task_id,
        orchestrator,
        repo_factory,
    )
    
    return {"task_id": task_id, "status": "processing"}
```

#### 3.2 新增内容生成状态查询端点

```python
@router.get("/{task_id}/content-status")
async def get_content_generation_status(task_id: str):
    """查询内容生成进度"""
    from celery.result import AsyncResult
    
    # 从数据库获取 Celery task ID
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        task = await task_repo.get_by_task_id(task_id)
    
    if not task or not task.celery_task_id:
        raise HTTPException(404, "Task not found")
    
    # 查询 Celery 任务状态
    result = AsyncResult(task.celery_task_id)
    
    return {
        "task_id": task_id,
        "celery_task_id": task.celery_task_id,
        "status": result.status,
        "progress": result.info if result.status == "PROGRESS" else None,
    }
```

---

### Phase 4: 测试与部署（1-2 天）

#### 4.1 本地测试

```bash
# 1. 启动所有服务
docker-compose up -d

# 2. 验证 Celery Worker 已启动
docker-compose logs celery_content_worker

# 3. 发起路线图生成请求
curl -X POST http://localhost:8000/api/v1/roadmaps/generate \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "preferences": {...}}'

# 4. 同时验证其他请求不受影响
curl http://localhost:8000/health  # 应立即响应
```

#### 4.2 压力测试

```bash
# 使用 hey 或 ab 进行压力测试
hey -n 100 -c 10 http://localhost:8000/health
```

**验证指标**：
- P99 延迟 < 100ms（内容生成期间）
- 健康检查成功率 100%

#### 4.3 Railway 部署

1. 更新 `railway.toml` 配置
2. 添加 Celery Worker 服务
3. 配置共享 Redis 实例

---

## 四、回滚计划

如果迁移后出现问题，可以快速回滚：

1. **临时禁用 Celery 内容生成**：
   ```python
   # 在 content_runner.py 中添加开关
   USE_CELERY_FOR_CONTENT = os.getenv("USE_CELERY_FOR_CONTENT", "true") == "true"
   
   if USE_CELERY_FOR_CONTENT:
       # 使用 Celery
       generate_roadmap_content.delay(...)
   else:
       # 回退到原来的 BackgroundTasks 方式
       await self._generate_content_parallel(...)
   ```

2. **环境变量控制**：
   ```bash
   USE_CELERY_FOR_CONTENT=false
   ```

---

## 五、时间表

| 阶段 | 任务 | 预计时间 | 状态 |
|------|------|----------|------|
| Phase 0 | 短期优化（多 Workers + 事件循环让出） | 0.5 天 | ✅ 已完成 |
| Phase 1 | 基础设施准备 | 1-2 天 | ⏳ 待开始 |
| Phase 2 | 任务实现 | 2-3 天 | ⏳ 待开始 |
| Phase 3 | API 适配 | 1-2 天 | ⏳ 待开始 |
| Phase 4 | 测试与部署 | 1-2 天 | ⏳ 待开始 |

**总计**：5-9 个工作日

---

## 六、风险与缓解措施

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Celery Worker 崩溃 | 内容生成中断 | 配置任务重试，使用 `acks_late=True` |
| 数据库连接池耗尽 | Worker 无法写入 | 使用独立连接池配置 |
| 进度通知丢失 | 前端状态不同步 | 使用 Redis 持久化 + 轮询兜底 |
| 任务堆积 | 用户等待时间长 | 配置 Celery 优先级队列 |

---

## 七、监控指标

迁移后需要关注的指标：

1. **Celery 任务指标**
   - 任务队列长度
   - 任务执行时间
   - 任务失败率

2. **FastAPI 响应指标**
   - P50/P95/P99 延迟
   - 请求成功率
   - 活跃连接数

3. **资源使用**
   - Worker 进程 CPU/内存
   - Redis 内存使用
   - 数据库连接数

---

## 八、相关文件

- `backend/app/tasks/log_tasks.py` - 现有 Celery 日志任务（参考实现）
- `backend/app/core/celery_app.py` - Celery 配置
- `backend/app/core/orchestrator/node_runners/content_runner.py` - 需要修改的内容生成器
- `backend/docker-compose.yml` - Docker 配置

---

*文档创建时间：2025-12-27*
*最后更新：2025-12-27*


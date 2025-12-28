# Celery 内容生成最佳实践与问题解答

> **日期**: 2025-12-27  
> **适用场景**: 内容生成任务监控、恢复、重试、状态管理  
> **相关文档**: [CELERY_CONTENT_GENERATION_MIGRATION_COMPLETE.md](./CELERY_CONTENT_GENERATION_MIGRATION_COMPLETE.md)

---

## 目录

1. [任务执行进度与状态监控](#1-任务执行进度与状态监控)
2. [前端实时通知机制](#2-前端实时通知机制)
3. [中断恢复与失败重试](#3-中断恢复与失败重试)
4. [数据库更新策略](#4-数据库更新策略)
5. [任务整体状态更新](#5-任务整体状态更新)
6. [Framework Data 字段更新](#6-framework-data-字段更新)
7. [完整工作流示意图](#7-完整工作流示意图)
8. [监控仪表盘设计](#8-监控仪表盘设计)

---

## 1. 任务执行进度与状态监控

### 1.1 多层次状态监控架构

```
┌─────────────────────────────────────────────────────────┐
│               监控层级架构                                │
├─────────────────────────────────────────────────────────┤
│  L1: Celery 任务级别（粗粒度）                            │
│      - 状态: PENDING, PROGRESS, SUCCESS, FAILURE, RETRY  │
│      - 数据源: Celery Result Backend (Redis)             │
│      - 查询方式: GET /api/v1/roadmaps/{task_id}/content-status │
│                                                          │
│  L2: 概念级别（细粒度）                                   │
│      - 事件: concept_start, concept_complete, concept_failed │
│      - 数据源: Redis Pub/Sub                             │
│      - 推送方式: WebSocket 实时推送                        │
│                                                          │
│  L3: 数据库持久化状态                                     │
│      - 字段: RoadmapTask.status, current_step, failed_concepts │
│      - 数据源: PostgreSQL                                │
│      - 查询方式: GET /api/v1/roadmaps/{task_id}/status   │
└─────────────────────────────────────────────────────────┘
```

### 1.2 查询 Celery 任务状态（L1）

**端点**: `GET /api/v1/roadmaps/{task_id}/content-status`

**已实现位置**: `backend/app/api/v1/endpoints/generation.py:241-319`

**响应示例**:

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "celery_task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "PROGRESS",
  "progress": {
    "current": 15,
    "total": 30,
    "percentage": 50.0
  }
}
```

**状态说明**:

| Celery 状态 | 含义 | 处理建议 |
|------------|------|----------|
| `NOT_STARTED` | 内容生成未启动 | 等待 ContentRunner 触发 |
| `PENDING` | 任务在队列中等待 | 正常状态，显示"排队中" |
| `PROGRESS` | 正在执行 | 显示进度条（百分比） |
| `SUCCESS` | 完成 | 显示成功通知，引导查看路线图 |
| `FAILURE` | 失败 | 显示错误信息，提供重试按钮 |
| `RETRY` | 正在重试 | 显示"重试中"，展示重试次数 |

### 1.3 监听概念级别事件（L2）

**WebSocket 端点**: `ws://localhost:8000/api/v1/ws/task/{task_id}`

**事件类型**:

```typescript
// 概念开始生成
{
  type: "concept_start",
  task_id: string,
  concept_id: string,
  concept_name: string,
  content_type: "tutorial" | "resources" | "quiz",
  progress: {
    current: number,
    total: number,
    percentage: number
  },
  timestamp: string
}

// 概念生成完成
{
  type: "concept_complete",
  task_id: string,
  concept_id: string,
  concept_name: string,
  content_type: "tutorial" | "resources" | "quiz",
  data: {
    tutorial_id?: string,
    resources_count?: number,
    quiz_questions?: number
  },
  timestamp: string
}

// 概念生成失败
{
  type: "concept_failed",
  task_id: string,
  concept_id: string,
  concept_name: string,
  content_type: "tutorial" | "resources" | "quiz",
  error: string,
  timestamp: string
}
```

**前端代码示例**:

```typescript
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/task/${taskId}`);

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case "concept_start":
      updateConceptStatus(message.concept_id, "generating");
      updateProgressBar(message.progress.percentage);
      break;
    
    case "concept_complete":
      updateConceptStatus(message.concept_id, "completed");
      showSuccessToast(`${message.concept_name} 内容生成完成`);
      break;
    
    case "concept_failed":
      updateConceptStatus(message.concept_id, "failed");
      showRetryButton(message.concept_id, message.content_type);
      break;
    
    case "completed":
      // 全部完成
      window.location.href = `/roadmap/${message.roadmap_id}`;
      break;
  }
};
```

### 1.4 查询数据库持久化状态（L3）

**端点**: `GET /api/v1/roadmaps/{task_id}/status`

**响应示例**:

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "partial_failure",
  "current_step": "content_generation",
  "roadmap_id": "python-web-dev-2024",
  "failed_concepts": {
    "count": 3,
    "concept_ids": ["concept-1", "concept-2", "concept-3"]
  },
  "execution_summary": {
    "tutorial_count": 27,
    "resource_count": 27,
    "quiz_count": 27,
    "failed_count": 3
  },
  "created_at": "2024-12-27T10:00:00",
  "updated_at": "2024-12-27T10:15:30"
}
```

---

## 2. 前端实时通知机制

### 2.1 通知架构图

```
┌─────────────────────────────────────────────────────────┐
│                   Celery Worker 进程                     │
│  ┌────────────────────────────────────────────────┐     │
│  │  content_generation_tasks.py                   │     │
│  │                                                 │     │
│  │  await notification_service.publish_concept_start() │
│  │  await notification_service.publish_concept_complete() │
│  │  await notification_service.publish_concept_failed() │
│  └─────────────────────┬───────────────────────────┘    │
└────────────────────────┼────────────────────────────────┘
                         │
                         ↓ Redis Pub/Sub
              ┌──────────────────────┐
              │   Redis Channel:     │
              │  roadmap:task:{id}   │
              └──────────┬───────────┘
                         │
                         ↓ Subscribe
┌─────────────────────────────────────────────────────────┐
│               FastAPI WebSocket 端点                     │
│  ┌────────────────────────────────────────────────┐     │
│  │  GET /api/v1/ws/task/{task_id}                 │     │
│  │                                                 │     │
│  │  async for event in notification_service.subscribe() │
│  │      await websocket.send_json(event)           │     │
│  └─────────────────────┬───────────────────────────┘    │
└────────────────────────┼────────────────────────────────┘
                         │
                         ↓ WebSocket
┌─────────────────────────────────────────────────────────┐
│                  前端任务详情页面                         │
│  ┌────────────────────────────────────────────────┐     │
│  │  const ws = new WebSocket(...)                 │     │
│  │  ws.onmessage = (event) => {                   │     │
│  │    // 更新 UI                                   │     │
│  │  }                                              │     │
│  └────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### 2.2 前端任务详情页面设计

**页面结构**:

```
┌──────────────────────────────────────────────────┐
│  📊 路线图生成进度                                │
├──────────────────────────────────────────────────┤
│  ● 需求分析 ✅                                    │
│  ● 课程设计 ✅                                    │
│  ● 结构验证 ✅                                    │
│  ● 人工审核 ✅                                    │
│  ● 内容生成 🔄                                    │
│     └─ 进度: 15/30 (50%)                          │
│        [████████░░░░░░░░] 50%                    │
├──────────────────────────────────────────────────┤
│  📝 概念内容生成详情                              │
├──────────────────────────────────────────────────┤
│  ✅ Python 基础语法                               │
│      - 教程: 已完成                               │
│      - 资源: 已完成                               │
│      - 测验: 已完成                               │
│                                                   │
│  🔄 面向对象编程（正在生成...）                    │
│      - 教程: 生成中...                            │
│      - 资源: 等待中                               │
│      - 测验: 等待中                               │
│                                                   │
│  ❌ 装饰器与元类（生成失败）                       │
│      - 教程: 失败 [重试]                          │
│      - 资源: 失败 [重试]                          │
│      - 测验: 失败 [重试]                          │
└──────────────────────────────────────────────────┘
```

**前端实现示例（React）**:

```typescript
import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';

interface ConceptStatus {
  concept_id: string;
  concept_name: string;
  tutorial_status: 'pending' | 'generating' | 'completed' | 'failed';
  resources_status: 'pending' | 'generating' | 'completed' | 'failed';
  quiz_status: 'pending' | 'generating' | 'completed' | 'failed';
}

export function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [concepts, setConcepts] = useState<Map<string, ConceptStatus>>(new Map());
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    // 建立 WebSocket 连接
    const websocket = new WebSocket(
      `ws://localhost:8000/api/v1/ws/task/${taskId}`
    );

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      handleWebSocketMessage(message);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      // 降级到轮询模式
      startPolling();
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, [taskId]);

  const handleWebSocketMessage = (message: any) => {
    switch (message.type) {
      case 'concept_start':
        updateConceptStatus(message.concept_id, message.content_type, 'generating');
        setProgress(message.progress);
        break;

      case 'concept_complete':
        updateConceptStatus(message.concept_id, message.content_type, 'completed');
        break;

      case 'concept_failed':
        updateConceptStatus(message.concept_id, message.content_type, 'failed');
        break;

      case 'completed':
        // 全部完成，跳转到路线图详情页
        window.location.href = `/roadmap/${message.roadmap_id}`;
        break;
    }
  };

  const updateConceptStatus = (
    conceptId: string,
    contentType: string,
    status: string
  ) => {
    setConcepts((prev) => {
      const updated = new Map(prev);
      const concept = updated.get(conceptId) || {
        concept_id: conceptId,
        concept_name: '',
        tutorial_status: 'pending',
        resources_status: 'pending',
        quiz_status: 'pending',
      };

      if (contentType === 'tutorial') {
        concept.tutorial_status = status;
      } else if (contentType === 'resources') {
        concept.resources_status = status;
      } else if (contentType === 'quiz') {
        concept.quiz_status = status;
      }

      updated.set(conceptId, concept);
      return updated;
    });
  };

  const startPolling = () => {
    // 降级方案：每 5 秒轮询一次状态
    const intervalId = setInterval(async () => {
      const response = await fetch(
        `/api/v1/roadmaps/${taskId}/content-status`
      );
      const data = await response.json();

      if (data.status === 'SUCCESS' || data.status === 'FAILURE') {
        clearInterval(intervalId);
      }

      // 更新 UI
      if (data.progress) {
        setProgress(data.progress);
      }
    }, 5000);
  };

  return (
    <div className="task-detail-page">
      <h1>路线图生成进度</h1>
      
      {/* 进度条 */}
      <div className="progress-section">
        <div className="progress-text">
          进度: {progress.current}/{progress.total} ({(progress.current / progress.total * 100).toFixed(1)}%)
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${(progress.current / progress.total * 100)}%` }}
          />
        </div>
      </div>

      {/* 概念列表 */}
      <div className="concepts-section">
        <h2>概念内容生成详情</h2>
        {Array.from(concepts.values()).map((concept) => (
          <ConceptCard key={concept.concept_id} concept={concept} />
        ))}
      </div>
    </div>
  );
}
```

### 2.3 降级方案：轮询模式

当 WebSocket 连接失败时，前端应自动降级到轮询模式：

```typescript
// 轮询间隔：5秒
const POLLING_INTERVAL = 5000;

function startPolling(taskId: string) {
  const intervalId = setInterval(async () => {
    try {
      // 查询 Celery 任务状态
      const response = await fetch(
        `/api/v1/roadmaps/${taskId}/content-status`
      );
      const data = await response.json();

      // 更新 UI
      updateProgressBar(data.progress);

      // 如果任务完成或失败，停止轮询
      if (data.status === 'SUCCESS' || data.status === 'FAILURE') {
        clearInterval(intervalId);
        handleTaskComplete(data);
      }
    } catch (error) {
      console.error('轮询失败:', error);
    }
  }, POLLING_INTERVAL);

  return intervalId;
}
```

---

## 3. 中断恢复与失败重试

### 3.1 中断场景分类

| 中断类型 | 场景描述 | 恢复策略 |
|---------|---------|---------|
| **服务器重启** | Celery Worker 进程终止 | Celery 自动重新入队（`acks_late=True`） |
| **单个概念失败** | LLM API 调用超时/限流 | 自动重试 3 次（指数退避） |
| **批量概念失败** | 失败率 > 50% | 中止任务，记录失败详情 |
| **用户主动取消** | 用户在前端点击"取消" | 调用 `revoke` 取消 Celery 任务 |

### 3.2 Celery 自动重试机制

**已配置参数**（`backend/app/tasks/content_generation_tasks.py:71-80`）:

```python
@celery_app.task(
    name="app.tasks.content_generation_tasks.generate_roadmap_content",
    queue="content_generation",
    bind=True,
    max_retries=3,                   # 最多重试 3 次
    default_retry_delay=60,          # 初始延迟 60 秒
    time_limit=1800,                 # 硬超时 30 分钟
    soft_time_limit=1500,            # 软超时 25 分钟
    acks_late=True,                  # 任务完成后才确认（防止丢失）
)
```

**重试逻辑**（`backend/app/tasks/content_generation_tasks.py:142-153`）:

```python
except Exception as e:
    logger.error(
        "celery_content_generation_task_failed",
        task_id=task_id,
        error=str(e),
        retry_count=self.request.retries,
    )
    
    # 指数退避重试：60s, 120s, 240s
    raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
```

### 3.3 单个概念失败重试（手动触发）

**场景**: 内容生成完成后，部分概念失败（失败率 < 50%）

**已实现 API**:

- `POST /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorial/retry`
- `POST /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/resources/retry`
- `POST /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz/retry`

**请求示例**:

```bash
curl -X POST "http://localhost:8000/api/v1/roadmaps/python-web-dev-2024/concepts/concept-123/tutorial/retry" \
  -H "Content-Type: application/json" \
  -d '{
    "preferences": {
      "learning_goal": "Learn Python web development",
      "time_available": "3 months",
      "difficulty_level": "beginner"
    }
  }'
```

**响应示例**:

```json
{
  "success": true,
  "concept_id": "concept-123",
  "content_type": "tutorial",
  "message": "教程重新生成成功",
  "data": {
    "task_id": "retry-tutorial-concept-12345678",
    "tutorial_id": "uuid-xxx",
    "title": "Python 装饰器详解",
    "summary": "本教程介绍...",
    "content_url": "s3://tutorials/python-web-dev-2024/concept-123/v2.md",
    "content_version": 2
  }
}
```

**前端集成示例**:

```typescript
async function retryFailedConcept(
  roadmapId: string,
  conceptId: string,
  contentType: 'tutorial' | 'resources' | 'quiz',
  preferences: LearningPreferences
) {
  const response = await fetch(
    `/api/v1/roadmaps/${roadmapId}/concepts/${conceptId}/${contentType}/retry`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preferences }),
    }
  );

  const result = await response.json();

  if (result.success) {
    // 显示成功提示
    toast.success(`${contentType} 重新生成成功`);
    
    // 刷新路线图数据
    await refetchRoadmap(roadmapId);
  } else {
    // 显示错误提示
    toast.error(result.message);
  }
}
```

### 3.4 批量失败概念重试（待实现）

**场景**: 内容生成完成后，用户希望一键重试所有失败的概念

**推荐实现方案**:

#### 3.4.1 新增 API 端点

**文件**: `backend/app/api/v1/endpoints/generation.py`

```python
@router.post("/{roadmap_id}/retry-failed")
async def retry_all_failed_concepts(
    roadmap_id: str,
    request: RetryContentRequest,
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
):
    """
    批量重试所有失败的概念内容生成
    
    工作流：
    1. 从 framework_data 中提取所有 status="failed" 的概念
    2. 将它们发送到 Celery 队列（使用独立的 Celery 任务）
    3. 返回批量重试任务 ID
    
    Args:
        roadmap_id: 路线图 ID
        request: 用户学习偏好
        
    Returns:
        批量重试任务信息
    """
    # 1. 获取路线图元数据
    async with repo_factory.create_session() as session:
        roadmap_repo = repo_factory.create_roadmap_meta_repo(session)
        roadmap_metadata = await roadmap_repo.get_by_roadmap_id(roadmap_id)
    
    if not roadmap_metadata:
        raise HTTPException(status_code=404, detail="路线图不存在")
    
    # 2. 提取失败的概念
    failed_concepts = []
    framework_data = roadmap_metadata.framework_data
    
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept in module.get("concepts", []):
                concept_id = concept.get("concept_id")
                
                # 检查各个内容类型的状态
                if concept.get("content_status") == "failed":
                    failed_concepts.append({
                        "concept_id": concept_id,
                        "concept_data": concept,
                        "content_type": "tutorial",
                    })
                if concept.get("resources_status") == "failed":
                    failed_concepts.append({
                        "concept_id": concept_id,
                        "concept_data": concept,
                        "content_type": "resources",
                    })
                if concept.get("quiz_status") == "failed":
                    failed_concepts.append({
                        "concept_id": concept_id,
                        "concept_data": concept,
                        "content_type": "quiz",
                    })
    
    if not failed_concepts:
        return {
            "success": True,
            "message": "没有失败的概念需要重试",
            "failed_count": 0,
        }
    
    # 3. 创建批量重试任务
    batch_task_id = f"retry-batch-{roadmap_id}-{uuid.uuid4().hex[:8]}"
    
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        await task_repo.create_task(
            task_id=batch_task_id,
            user_id=roadmap_metadata.user_id,
            user_request={
                "type": "retry_batch",
                "roadmap_id": roadmap_id,
                "failed_concepts": failed_concepts,
                "preferences": request.preferences.model_dump(mode='json'),
            },
            task_type="retry_batch",
        )
        await task_repo.update_task_status(
            task_id=batch_task_id,
            status="processing",
            current_step="batch_retry",
            roadmap_id=roadmap_id,
        )
        await session.commit()
    
    # 4. 发送到 Celery 队列
    from app.tasks.content_generation_tasks import retry_failed_concepts_batch
    
    celery_task = retry_failed_concepts_batch.delay(
        batch_task_id=batch_task_id,
        roadmap_id=roadmap_id,
        failed_concepts=failed_concepts,
        preferences_data=request.preferences.model_dump(mode='json'),
    )
    
    # 5. 保存 Celery task ID
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        await task_repo.update_by_id(
            batch_task_id,
            celery_task_id=celery_task.id,
        )
        await session.commit()
    
    return {
        "success": True,
        "message": f"已开始批量重试 {len(failed_concepts)} 个失败的内容",
        "batch_task_id": batch_task_id,
        "celery_task_id": celery_task.id,
        "failed_count": len(failed_concepts),
    }
```

#### 3.4.2 新增 Celery 任务

**文件**: `backend/app/tasks/content_generation_tasks.py`

```python
@celery_app.task(
    name="app.tasks.content_generation_tasks.retry_failed_concepts_batch",
    queue="content_generation",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=1800,
    soft_time_limit=1500,
    acks_late=True,
)
def retry_failed_concepts_batch(
    self,
    batch_task_id: str,
    roadmap_id: str,
    failed_concepts: list[dict],
    preferences_data: dict,
):
    """
    批量重试失败的概念内容生成
    
    Args:
        batch_task_id: 批量重试任务 ID
        roadmap_id: 路线图 ID
        failed_concepts: 失败的概念列表
        preferences_data: 用户偏好数据
    """
    logger.info(
        "celery_batch_retry_task_started",
        batch_task_id=batch_task_id,
        roadmap_id=roadmap_id,
        failed_count=len(failed_concepts),
    )
    
    try:
        result = run_async(
            _async_batch_retry(
                batch_task_id=batch_task_id,
                roadmap_id=roadmap_id,
                failed_concepts=failed_concepts,
                preferences_data=preferences_data,
            )
        )
        
        logger.info(
            "celery_batch_retry_task_completed",
            batch_task_id=batch_task_id,
            roadmap_id=roadmap_id,
            success_count=result["success_count"],
            failed_count=result["failed_count"],
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "celery_batch_retry_task_failed",
            batch_task_id=batch_task_id,
            roadmap_id=roadmap_id,
            error=str(e),
        )
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


async def _async_batch_retry(
    batch_task_id: str,
    roadmap_id: str,
    failed_concepts: list[dict],
    preferences_data: dict,
) -> dict:
    """
    批量重试核心逻辑
    
    Returns:
        {
            "success_count": int,
            "failed_count": int,
            "results": list[dict],
        }
    """
    from app.agents.factory import AgentFactory
    from app.models.domain import LearningPreferences
    
    preferences = LearningPreferences.model_validate(preferences_data)
    agent_factory = AgentFactory()
    
    success_count = 0
    failed_count = 0
    results = []
    
    # 并发重试所有失败的内容
    semaphore = asyncio.Semaphore(10)  # 限制并发数为 10
    
    tasks = [
        _retry_single_concept_content(
            batch_task_id=batch_task_id,
            roadmap_id=roadmap_id,
            concept_data=item["concept_data"],
            content_type=item["content_type"],
            preferences=preferences,
            agent_factory=agent_factory,
            semaphore=semaphore,
        )
        for item in failed_concepts
    ]
    
    task_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, result in enumerate(task_results):
        concept_id = failed_concepts[i]["concept_id"]
        content_type = failed_concepts[i]["content_type"]
        
        if isinstance(result, Exception):
            failed_count += 1
            results.append({
                "concept_id": concept_id,
                "content_type": content_type,
                "status": "failed",
                "error": str(result),
            })
        else:
            success_count += 1
            results.append({
                "concept_id": concept_id,
                "content_type": content_type,
                "status": "success",
                "data": result,
            })
    
    # 更新任务状态
    from app.db.repository_factory import RepositoryFactory
    from app.db.session import safe_session_with_retry
    
    async with safe_session_with_retry() as session:
        repo_factory = RepositoryFactory()
        task_repo = repo_factory.create_task_repo(session)
        
        final_status = "completed" if failed_count == 0 else "partial_failure"
        
        await task_repo.update_task_status(
            task_id=batch_task_id,
            status=final_status,
            current_step="completed",
            execution_summary={
                "total": len(failed_concepts),
                "success": success_count,
                "failed": failed_count,
            },
        )
        await session.commit()
    
    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results,
    }


async def _retry_single_concept_content(
    batch_task_id: str,
    roadmap_id: str,
    concept_data: dict,
    content_type: str,
    preferences: any,
    agent_factory: any,
    semaphore: asyncio.Semaphore,
):
    """
    重试单个概念的单个内容类型
    
    Returns:
        生成的内容数据
    """
    from app.models.domain import (
        Concept,
        TutorialGenerationInput,
        ResourceRecommendationInput,
        QuizGenerationInput,
    )
    
    async with semaphore:
        concept = Concept.model_validate(concept_data)
        concept_id = concept.concept_id
        
        # 发送 WebSocket 事件：开始重试
        await notification_service.publish_concept_start(
            task_id=batch_task_id,
            concept_id=concept_id,
            concept_name=concept.name,
            current=1,
            total=1,
            content_type=content_type,
        )
        
        try:
            # 根据内容类型创建相应的 Agent 和输入
            if content_type == "tutorial":
                agent = agent_factory.create_tutorial_generator()
                input_data = TutorialGenerationInput(
                    concept=concept,
                    user_preferences=preferences,
                    context={"roadmap_id": roadmap_id},
                )
            elif content_type == "resources":
                agent = agent_factory.create_resource_recommender()
                input_data = ResourceRecommendationInput(
                    concept=concept,
                    user_preferences=preferences,
                    context={"roadmap_id": roadmap_id},
                )
            elif content_type == "quiz":
                agent = agent_factory.create_quiz_generator()
                input_data = QuizGenerationInput(
                    concept=concept,
                    user_preferences=preferences,
                    context={"roadmap_id": roadmap_id},
                )
            else:
                raise ValueError(f"Unknown content_type: {content_type}")
            
            # 执行生成
            result = await agent.execute(input_data)
            
            # 保存结果
            await _save_single_content_result(
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                content_type=content_type,
                result=result,
            )
            
            # 发送 WebSocket 事件：重试成功
            await notification_service.publish_concept_complete(
                task_id=batch_task_id,
                concept_id=concept_id,
                concept_name=concept.name,
                content_type=content_type,
                data={"status": "retry_success"},
            )
            
            return result
            
        except Exception as e:
            # 发送 WebSocket 事件：重试失败
            await notification_service.publish_concept_failed(
                task_id=batch_task_id,
                concept_id=concept_id,
                concept_name=concept.name,
                error=str(e),
                content_type=content_type,
            )
            raise


async def _save_single_content_result(
    roadmap_id: str,
    concept_id: str,
    content_type: str,
    result: any,
):
    """
    保存单个内容生成结果
    """
    from app.db.session import safe_session_with_retry
    from app.db.repository_factory import RepositoryFactory
    
    repo_factory = RepositoryFactory()
    
    async with safe_session_with_retry() as session:
        if content_type == "tutorial":
            repo = repo_factory.create_tutorial_repo(session)
            await repo.save_tutorial(result, roadmap_id)
        elif content_type == "resources":
            repo = repo_factory.create_resource_repo(session)
            await repo.save_resource_recommendation(result, roadmap_id)
        elif content_type == "quiz":
            repo = repo_factory.create_quiz_repo(session)
            await repo.save_quiz(result, roadmap_id)
        
        await session.commit()
    
    # 更新 framework_data 中的状态
    await _update_framework_concept_status(
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        content_type=content_type,
        status="completed",
        result=result,
    )


async def _update_framework_concept_status(
    roadmap_id: str,
    concept_id: str,
    content_type: str,
    status: str,
    result: any = None,
):
    """
    更新 framework_data 中概念的状态
    """
    from app.db.session import safe_session_with_retry
    from app.db.repository_factory import RepositoryFactory
    from app.models.domain import RoadmapFramework
    
    repo_factory = RepositoryFactory()
    
    async with safe_session_with_retry() as session:
        roadmap_repo = repo_factory.create_roadmap_meta_repo(session)
        roadmap_metadata = await roadmap_repo.get_by_roadmap_id(roadmap_id)
        
        if not roadmap_metadata:
            return
        
        framework_data = roadmap_metadata.framework_data
        
        # 遍历更新状态
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    if concept.get("concept_id") == concept_id:
                        if content_type == "tutorial":
                            concept["content_status"] = status
                            if result:
                                concept["content_ref"] = result.content_url
                                concept["content_summary"] = result.summary
                        elif content_type == "resources":
                            concept["resources_status"] = status
                            if result:
                                concept["resources_id"] = result.id
                                concept["resources_count"] = len(result.resources)
                        elif content_type == "quiz":
                            concept["quiz_status"] = status
                            if result:
                                concept["quiz_id"] = result.quiz_id
                                concept["quiz_questions_count"] = result.total_questions
        
        # 保存更新后的框架
        updated_framework = RoadmapFramework.model_validate(framework_data)
        await roadmap_repo.update_framework_data(
            roadmap_id=roadmap_id,
            framework=updated_framework,
        )
        await session.commit()
```

#### 3.4.3 前端集成示例

```typescript
async function retryAllFailedConcepts(
  roadmapId: string,
  preferences: LearningPreferences
) {
  try {
    // 1. 调用批量重试 API
    const response = await fetch(
      `/api/v1/roadmaps/${roadmapId}/retry-failed`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preferences }),
      }
    );

    const result = await response.json();

    if (!result.success) {
      toast.error(result.message);
      return;
    }

    // 2. 显示进度提示
    toast.success(
      `已开始批量重试 ${result.failed_count} 个失败的内容`
    );

    // 3. 建立 WebSocket 连接监听进度
    const ws = new WebSocket(
      `ws://localhost:8000/api/v1/ws/task/${result.batch_task_id}`
    );

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      if (message.type === 'concept_complete') {
        // 更新 UI，显示某个概念重试成功
        updateConceptStatus(message.concept_id, message.content_type, 'completed');
      } else if (message.type === 'concept_failed') {
        // 更新 UI，显示某个概念重试失败
        updateConceptStatus(message.concept_id, message.content_type, 'failed');
      } else if (message.type === 'completed') {
        // 批量重试完成
        toast.success('批量重试完成');
        ws.close();
        refetchRoadmap(roadmapId);
      }
    };

  } catch (error) {
    console.error('批量重试失败:', error);
    toast.error('批量重试失败，请稍后重试');
  }
}
```

### 3.5 用户主动取消任务

**场景**: 用户在内容生成期间点击"取消"按钮

**实现方案**:

#### 3.5.1 新增取消 API

**文件**: `backend/app/api/v1/endpoints/generation.py`

```python
@router.post("/{task_id}/cancel")
async def cancel_content_generation(
    task_id: str,
    repo_factory: RepositoryFactory = Depends(get_repository_factory),
):
    """
    取消内容生成任务
    
    Args:
        task_id: 任务 ID
        
    Returns:
        取消结果
    """
    from celery.result import AsyncResult
    
    # 1. 获取任务记录
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        task = await task_repo.get_by_task_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if not task.celery_task_id:
        raise HTTPException(status_code=400, detail="内容生成尚未启动")
    
    # 2. 取消 Celery 任务
    result = AsyncResult(task.celery_task_id)
    result.revoke(terminate=True)  # terminate=True 会强制终止正在运行的任务
    
    # 3. 更新任务状态
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        await task_repo.update_task_status(
            task_id=task_id,
            status="cancelled",
            current_step="cancelled",
            error_message="用户主动取消任务",
        )
        await session.commit()
    
    # 4. 发送取消通知
    await notification_service.publish_failed(
        task_id=task_id,
        error="任务已取消",
        step="content_generation",
    )
    
    logger.info(
        "content_generation_task_cancelled",
        task_id=task_id,
        celery_task_id=task.celery_task_id,
    )
    
    return {
        "success": True,
        "message": "任务已取消",
        "task_id": task_id,
    }
```

#### 3.5.2 前端集成示例

```typescript
async function cancelTask(taskId: string) {
  if (!confirm('确定要取消内容生成吗？')) {
    return;
  }

  try {
    const response = await fetch(
      `/api/v1/roadmaps/${taskId}/cancel`,
      { method: 'POST' }
    );

    const result = await response.json();

    if (result.success) {
      toast.success('任务已取消');
      // 跳转回首页
      window.location.href = '/';
    }
  } catch (error) {
    console.error('取消任务失败:', error);
    toast.error('取消任务失败');
  }
}
```

---

## 4. 数据库更新策略

### 4.1 分批保存策略（已实现）

**位置**: `backend/app/tasks/content_generation_tasks.py:602-722`

**核心原则**:

1. **分批保存元数据**（避免长事务）
2. **单独更新 framework_data**（减少锁竞争）
3. **最后更新任务状态**（确保原子性）

**完整流程**:

```
┌─────────────────────────────────────────────────────────┐
│  Phase 1: 分批保存元数据（每批 10 个概念）                │
├─────────────────────────────────────────────────────────┤
│  1.1 分批保存教程元数据                                  │
│      - INSERT INTO tutorial_metadata (batch_size=10)    │
│      - COMMIT                                           │
│                                                         │
│  1.2 分批保存资源元数据                                  │
│      - INSERT INTO resource_recommendations (batch_size=10) │
│      - COMMIT                                           │
│                                                         │
│  1.3 分批保存测验元数据                                  │
│      - INSERT INTO quiz_metadata (batch_size=10)        │
│      - COMMIT                                           │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  Phase 2: 更新 framework_data（单独事务）                │
├─────────────────────────────────────────────────────────┤
│  2.1 读取当前 framework_data                             │
│  2.2 调用 _update_framework_with_content_refs()          │
│      - 更新每个概念的状态字段：                           │
│        * content_status: "completed" | "failed"         │
│        * content_ref, content_summary                   │
│        * resources_id, resources_count                  │
│        * quiz_id, quiz_questions_count                  │
│  2.3 保存更新后的 framework                              │
│      - UPDATE roadmap_metadata SET framework_data=...   │
│      - COMMIT                                           │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  Phase 3: 更新任务最终状态（单独事务）                    │
├─────────────────────────────────────────────────────────┤
│  3.1 确定最终状态：                                       │
│      - failed_concepts 为空 → "completed"               │
│      - failed_concepts 非空 → "partial_failure"         │
│  3.2 更新任务记录                                        │
│      - UPDATE roadmap_tasks SET status=..., current_step=... │
│      - COMMIT                                           │
└─────────────────────────────────────────────────────────┘
```

### 4.2 批次大小调优建议

**当前配置**: `BATCH_SIZE = 10`

**调优依据**:

| 批次大小 | 优点 | 缺点 | 适用场景 |
|---------|------|------|----------|
| **5** | 事务更快，锁竞争更少 | 总事务数多（N/5），总耗时可能增加 | 高并发场景，多个路线图同时生成 |
| **10（当前）** | 平衡性能和可靠性 | - | 通用场景 |
| **20** | 减少总事务数，总耗时更短 | 单个事务更长，失败影响更大 | 低并发场景，数据库负载低 |

**调优代码位置**:

```python
# backend/app/tasks/content_generation_tasks.py:637
BATCH_SIZE = 10  # 可根据实际负载调整
```

### 4.3 事务失败处理

**问题**: 如果某个批次保存失败，是否会影响整体？

**答案**: 不会。每个批次独立事务，失败会回滚，但不影响其他批次。

**重试机制**:

```python
# backend/app/db/session.py
async def safe_session_with_retry(
    max_retries: int = 3,
    retry_delay: float = 1.0,
):
    """
    带重试的数据库会话上下文管理器
    
    自动处理：
    - OperationalError（数据库连接失败）
    - DeadlockDetected（死锁）
    - 指数退避重试
    """
    for attempt in range(max_retries):
        try:
            async with AsyncSession(...) as session:
                yield session
                return
        except OperationalError as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2 ** attempt))
                continue
            raise
```

---

## 5. 任务整体状态更新

### 5.1 任务状态生命周期

```
┌──────────────────────────────────────────────────────────┐
│                 任务状态生命周期                          │
└──────────────────────────────────────────────────────────┘

  pending
    │
    ↓ POST /api/v1/roadmaps/generate
  processing
    │
    ├─→ intent_analysis → curriculum_design → structure_validation
    │
    ├─→ human_review (waiting / editing)
    │
    ├─→ content_generation_queued  ← ContentRunner 发送 Celery 任务
    │
    ├─→ content_generation  ← Celery Worker 正在执行
    │
    ├─→ completed  ← 全部成功
    │
    ├─→ partial_failure  ← 部分失败（失败率 < 50%）
    │
    └─→ failed  ← 全部失败或失败率 ≥ 50%
```

### 5.2 状态更新触发点

| 触发点 | 位置 | 更新内容 |
|--------|------|---------|
| **任务创建** | `generation.py:170-183` | `status="processing"`, `current_step="queued"` |
| **ContentRunner 启动** | `content_runner.py:109-112` | `celery_task_id=...` |
| **内容生成完成** | `content_generation_tasks.py:693-714` | `status="completed"/"partial_failure"`, `failed_concepts`, `execution_summary` |
| **内容生成失败** | `content_generation_tasks.py:142-153` | Celery 自动重试（不更新数据库） |

### 5.3 状态更新代码示例

**完整实现**（`backend/app/tasks/content_generation_tasks.py:693-714`）:

```python
# Phase 3: 更新 task 最终状态
final_status = "partial_failure" if failed_concepts else "completed"
final_step = "content_generation" if failed_concepts else "completed"

async with safe_session_with_retry() as session:
    repo = RoadmapRepository(session)
    await repo.update_task_status(
        task_id=task_id,
        status=final_status,
        current_step=final_step,
        failed_concepts={
            "count": len(failed_concepts),
            "concept_ids": failed_concepts,
        } if failed_concepts else None,
        execution_summary={
            "tutorial_count": len(tutorial_refs),
            "resource_count": len(resource_refs),
            "quiz_count": len(quiz_refs),
            "failed_count": len(failed_concepts),
        },
    )
    await session.commit()
```

**数据库字段映射**:

```python
class RoadmapTask(SQLModel, table=True):
    task_id: str  # 主键
    status: str  # pending, processing, completed, partial_failure, failed
    current_step: str  # intent_analysis, curriculum_design, ..., completed
    
    # 失败详情（JSON）
    failed_concepts: Optional[dict]  # {"count": 3, "concept_ids": [...]}
    
    # 执行摘要（JSON）
    execution_summary: Optional[dict]  # {"tutorial_count": 27, "failed_count": 3}
    
    # Celery 关联
    celery_task_id: Optional[str]  # 内容生成任务的 Celery task ID
```

---

## 6. Framework Data 字段更新

### 6.1 Framework Data 结构说明

**表**: `roadmap_metadata`  
**字段**: `framework_data` (JSON)

**完整结构**:

```json
{
  "title": "Python Web 开发学习路线图",
  "total_estimated_hours": 240.0,
  "recommended_completion_weeks": 12,
  "stages": [
    {
      "stage_id": "stage-1",
      "name": "基础阶段",
      "modules": [
        {
          "module_id": "module-1",
          "name": "Python 基础",
          "concepts": [
            {
              "concept_id": "concept-1",
              "name": "变量与数据类型",
              
              // 教程相关字段
              "content_status": "completed",  // pending, generating, completed, failed
              "content_ref": "s3://tutorials/python-web-dev/concept-1/v1.md",
              "content_summary": "本教程介绍 Python 的变量...",
              
              // 资源相关字段
              "resources_status": "completed",
              "resources_id": "res-uuid-xxx",
              "resources_count": 5,
              
              // 测验相关字段
              "quiz_status": "completed",
              "quiz_id": "quiz-uuid-xxx",
              "quiz_questions_count": 10,
              
              // 其他字段
              "prerequisites": [],
              "estimated_hours": 2.0,
              "difficulty": "beginner"
            }
          ]
        }
      ]
    }
  ]
}
```

### 6.2 更新 Framework Data 的时机

| 时机 | 触发点 | 更新内容 |
|------|--------|---------|
| **初始创建** | CurriculumDesignRunner | 创建完整框架，所有状态为 `"pending"` |
| **内容生成完成** | `_save_content_results()` | 批量更新所有概念的状态和引用 |
| **单个概念重试** | `retry_tutorial/resources/quiz()` | 更新单个概念的对应字段 |
| **批量重试** | `retry_failed_concepts_batch()` | 更新多个概念的状态 |

### 6.3 更新函数详解

**核心函数**: `_update_framework_with_content_refs()`

**位置**: `backend/app/tasks/content_generation_tasks.py:724-782`

**工作流程**:

```python
def _update_framework_with_content_refs(
    framework_data: dict,
    tutorial_refs: dict,  # {concept_id: TutorialGenerationOutput}
    resource_refs: dict,  # {concept_id: ResourceRecommendationOutput}
    quiz_refs: dict,      # {concept_id: QuizGenerationOutput}
    failed_concepts: list,  # [concept_id1, concept_id2, ...]
) -> dict:
    """
    更新 framework 中所有 Concept 的内容引用字段
    
    核心逻辑：
    1. 三层嵌套循环：Stage -> Module -> Concept
    2. 对每个概念，检查是否在 tutorial_refs / resource_refs / quiz_refs 中
    3. 如果存在，更新状态为 "completed"，并填充引用字段
    4. 如果在 failed_concepts 中，更新状态为 "failed"
    """
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept in module.get("concepts", []):
                concept_id = concept.get("concept_id")
                
                if not concept_id:
                    continue
                
                # 更新教程相关字段
                if concept_id in tutorial_refs:
                    tutorial_output = tutorial_refs[concept_id]
                    concept["content_status"] = "completed"
                    concept["content_ref"] = tutorial_output.content_url
                    concept["content_summary"] = tutorial_output.summary
                elif concept_id in failed_concepts:
                    if "content_status" not in concept or concept["content_status"] == "pending":
                        concept["content_status"] = "failed"
                
                # 更新资源相关字段
                if concept_id in resource_refs:
                    resource_output = resource_refs[concept_id]
                    concept["resources_status"] = "completed"
                    concept["resources_id"] = resource_output.id
                    concept["resources_count"] = len(resource_output.resources)
                elif concept_id in failed_concepts:
                    if "resources_status" not in concept or concept["resources_status"] == "pending":
                        concept["resources_status"] = "failed"
                
                # 更新测验相关字段
                if concept_id in quiz_refs:
                    quiz_output = quiz_refs[concept_id]
                    concept["quiz_status"] = "completed"
                    concept["quiz_id"] = quiz_output.quiz_id
                    concept["quiz_questions_count"] = quiz_output.total_questions
                elif concept_id in failed_concepts:
                    if "quiz_status" not in concept or concept["quiz_status"] == "pending":
                        concept["quiz_status"] = "failed"
    
    return framework_data
```

**调用位置**:

```python
# backend/app/tasks/content_generation_tasks.py:670-691
async with safe_session_with_retry() as session:
    repo = RoadmapRepository(session)
    roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
    
    if roadmap_metadata and roadmap_metadata.framework_data:
        # 更新 framework 中的 Concept 状态
        updated_framework = _update_framework_with_content_refs(
            framework_data=roadmap_metadata.framework_data,
            tutorial_refs=tutorial_refs,
            resource_refs=resource_refs,
            quiz_refs=quiz_refs,
            failed_concepts=failed_concepts,
        )
        
        framework_obj = RoadmapFramework.model_validate(updated_framework)
        await repo.save_roadmap_metadata(
            roadmap_id=roadmap_id,
            user_id=roadmap_metadata.user_id,
            framework=framework_obj,
        )
        await session.commit()
```

### 6.4 性能优化建议

**当前实现**: 每次更新都读取整个 `framework_data`，修改后整体写回

**优点**:
- 简单直观，易于维护
- 支持复杂的嵌套结构更新
- 事务性强，确保一致性

**缺点**:
- 对于大型路线图（100+ 概念），JSON 序列化/反序列化开销较大
- 可能出现并发更新冲突（如果同时有多个重试任务）

**优化方案**（适用于超大型路线图）:

```sql
-- 使用 PostgreSQL JSON 部分更新（jsonb_set）
UPDATE roadmap_metadata
SET framework_data = jsonb_set(
  framework_data,
  '{stages,0,modules,0,concepts,0,content_status}',
  '"completed"'
)
WHERE roadmap_id = 'xxx';
```

**SQLAlchemy 实现示例**:

```python
from sqlalchemy import text

# 方案 1: 使用原生 SQL
stmt = text("""
    UPDATE roadmap_metadata
    SET framework_data = jsonb_set(
        framework_data,
        :path,
        :value
    )
    WHERE roadmap_id = :roadmap_id
""")

await session.execute(
    stmt,
    {
        "path": "{stages,0,modules,0,concepts,0,content_status}",
        "value": '"completed"',
        "roadmap_id": roadmap_id,
    }
)
```

**注意**: 仅在路线图规模 > 100 概念时考虑此优化，否则代码复杂度增加不值得。

---

## 7. 完整工作流示意图

### 7.1 端到端数据流

```
┌─────────────────────────────────────────────────────────────────────┐
│                          前端用户界面                                │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐         │
│  │ 提交生成请求    │  │  监听进度      │  │  查看结果      │         │
│  │ POST /generate │  │  WebSocket     │  │  GET /roadmap  │         │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘         │
└──────────┼───────────────────┼───────────────────┼──────────────────┘
           │                   │                   │
           ↓                   ↓                   ↓
┌─────────────────────────────────────────────────────────────────────┐
│                       FastAPI 主进程                                 │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  1. 创建任务记录（RoadmapTask）                                │  │
│  │     - task_id: UUID                                           │  │
│  │     - status: "processing"                                    │  │
│  │     - current_step: "queued"                                  │  │
│  └──────────────────────┬────────────────────────────────────────┘  │
│                         ↓                                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  2. 工作流节点执行（IntentAnalysisRunner -> ... -> ContentRunner） │
│  │     - 每个节点完成后发送 WebSocket 事件                        │  │
│  │     - 更新 task.current_step                                  │  │
│  └──────────────────────┬────────────────────────────────────────┘  │
│                         ↓                                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  3. ContentRunner.run()                                       │  │
│  │     ✅ 发送 Celery 任务到队列                                  │  │
│  │     ✅ 保存 celery_task_id                                     │  │
│  │     ✅ 返回（不等待完成）                                       │  │
│  └──────────────────────┬────────────────────────────────────────┘  │
└─────────────────────────┼────────────────────────────────────────────┘
                          │
                          ↓ Redis Queue
┌─────────────────────────────────────────────────────────────────────┐
│                    Celery Worker 进程                                │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  4. generate_roadmap_content()                                │  │
│  │     - 反序列化 framework 和 preferences                        │  │
│  │     - 提取所有概念（30+ 个）                                   │  │
│  └──────────────────────┬────────────────────────────────────────┘  │
│                         ↓                                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  5. _generate_content_parallel()                              │  │
│  │     - 并发执行所有概念的内容生成（Semaphore=30）               │  │
│  │     - 每个概念生成 Tutorial + Resources + Quiz                │  │
│  │     - 实时发送 WebSocket 事件（concept_start, concept_complete） │
│  └──────────────────────┬────────────────────────────────────────┘  │
│                         ↓                                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  6. _save_content_results()                                   │  │
│  │     Phase 1: 分批保存元数据（每批 10 个）                      │  │
│  │       - tutorial_metadata                                     │  │
│  │       - resource_recommendations                              │  │
│  │       - quiz_metadata                                         │  │
│  │                                                               │  │
│  │     Phase 2: 更新 framework_data                              │  │
│  │       - 调用 _update_framework_with_content_refs()            │  │
│  │       - 批量更新所有概念的状态字段                             │  │
│  │                                                               │  │
│  │     Phase 3: 更新任务状态                                      │  │
│  │       - status: "completed" / "partial_failure"               │  │
│  │       - failed_concepts: {...}                                │  │
│  │       - execution_summary: {...}                              │  │
│  └──────────────────────┬────────────────────────────────────────┘  │
│                         ↓                                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  7. notification_service.publish_completed()                  │  │
│  │     - 发送 WebSocket 事件：任务完成                            │  │
│  │     - 前端自动跳转到路线图详情页                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ↓ Redis Pub/Sub
┌─────────────────────────────────────────────────────────────────────┐
│                     前端 WebSocket 客户端                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  8. 接收并处理事件                                             │  │
│  │     - progress: 更新进度条                                     │  │
│  │     - concept_start: 显示"生成中"                              │  │
│  │     - concept_complete: 显示"已完成"                           │  │
│  │     - concept_failed: 显示"失败"和重试按钮                     │  │
│  │     - completed: 跳转到路线图详情页                            │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 关键路径时间线

```
时间轴（示例）：
┌──────────────────────────────────────────────────────────────────┐
│  T=0s     用户提交请求                                            │
│  T=0.1s   任务记录创建成功                                        │
│  T=1s     IntentAnalysisRunner 完成                               │
│  T=15s    CurriculumDesignRunner 完成                             │
│  T=18s    ValidationRunner 完成                                   │
│  T=20s    ReviewRunner 等待人工审核（阻塞）                        │
│           ↓ 用户点击"批准"                                        │
│  T=300s   ContentRunner 发送 Celery 任务（立即返回）               │
│  T=301s   Celery Worker 开始执行                                  │
│  T=302s   第 1 个概念开始生成（WebSocket 推送）                    │
│  T=310s   第 1 个概念完成（WebSocket 推送）                        │
│  ...      30 个概念并发生成...                                    │
│  T=600s   最后一个概念完成                                        │
│  T=605s   保存结果到数据库（分 3 批）                              │
│  T=610s   更新 framework_data                                     │
│  T=612s   更新任务状态为 "completed"                              │
│  T=613s   发送 WebSocket 事件：任务完成                            │
│  T=614s   前端跳转到路线图详情页                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. 监控仪表盘设计

### 8.1 实时监控指标

**推荐工具**: Flower（Celery 官方监控工具）

**启动命令**:

```bash
# 在 docker-compose.yml 中添加 Flower 服务
celery_flower:
  image: mher/flower
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
    - CELERY_RESULT_BACKEND=redis://redis:6379/0
  ports:
    - "5555:5555"
  depends_on:
    - redis
  command: celery --broker=redis://redis:6379/0 flower
```

**访问**: http://localhost:5555

**关键指标**:

| 指标 | 说明 | 阈值 |
|------|------|------|
| **任务队列长度** | `content_generation` 队列中待处理任务数 | < 10 |
| **Worker 活跃数** | 正在运行的 Worker 进程数 | ≥ 2 |
| **任务成功率** | 成功任务数 / 总任务数 | > 95% |
| **平均任务耗时** | 单个路线图内容生成耗时 | 5-10 分钟 |
| **失败任务数** | 过去 1 小时内失败的任务数 | < 5 |

### 8.2 自定义监控面板

**位置**: `frontend-next/app/(app)/admin/monitoring`

**页面设计**:

```
┌──────────────────────────────────────────────────────────────┐
│  📊 内容生成监控面板                                          │
├──────────────────────────────────────────────────────────────┤
│  ⏱️  实时指标                                                 │
│     - 队列长度: 3                                             │
│     - 活跃 Worker: 2                                          │
│     - 正在执行的任务: 2                                       │
│                                                              │
│  📈 过去 24 小时统计                                          │
│     - 总任务数: 156                                           │
│     - 成功: 148 (94.9%)                                      │
│     - 失败: 8 (5.1%)                                         │
│     - 平均耗时: 7.2 分钟                                      │
│                                                              │
│  🚨 近期失败任务                                              │
│     ┌────────────────────────────────────────────────────┐  │
│     │ task-123 | Python 路线图 | 2024-12-27 10:15:30     │  │
│     │ 错误: OpenAI API 超时                                │  │
│     │ [重试] [查看日志]                                     │  │
│     └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**API 端点**:

```python
# backend/app/api/v1/endpoints/monitoring.py

@router.get("/monitoring/celery/stats")
async def get_celery_stats():
    """
    获取 Celery 统计数据
    
    Returns:
        {
            "queue_length": int,
            "active_workers": int,
            "active_tasks": int,
            "stats_24h": {
                "total": int,
                "success": int,
                "failed": int,
                "avg_duration_seconds": float,
            },
            "recent_failures": list[dict],
        }
    """
    from celery import current_app as celery_app
    
    # 获取队列长度
    inspect = celery_app.control.inspect()
    active = inspect.active()
    reserved = inspect.reserved()
    
    queue_length = sum(len(tasks) for tasks in reserved.values()) if reserved else 0
    active_tasks = sum(len(tasks) for tasks in active.values()) if active else 0
    active_workers = len(active) if active else 0
    
    # 查询数据库获取过去 24 小时统计
    # ...（实现略）
    
    return {
        "queue_length": queue_length,
        "active_workers": active_workers,
        "active_tasks": active_tasks,
        "stats_24h": stats_24h,
        "recent_failures": recent_failures,
    }
```

---

## 总结

### 核心要点回顾

1. **多层次监控**：Celery 任务级别（粗粒度）+ 概念级别（细粒度）+ 数据库持久化状态
2. **实时通知**：Redis Pub/Sub + WebSocket 推送，前端实时更新 UI
3. **容错机制**：自动重试（Celery）+ 手动重试（单个概念）+ 批量重试（所有失败概念）
4. **数据库策略**：分批保存元数据 → 更新 framework_data → 更新任务状态
5. **状态同步**：Celery 任务状态、RoadmapTask 状态、Framework Data 三者保持一致

### 最佳实践建议

✅ **监控告警**：配置 Flower 或 Prometheus，监控任务队列长度和失败率  
✅ **降级方案**：WebSocket 失败时降级到轮询模式  
✅ **日志记录**：使用 execution_logger 记录详细日志，便于问题排查  
✅ **批次调优**：根据实际负载调整 BATCH_SIZE（默认 10）  
✅ **超时保护**：为所有 LLM 调用设置合理的超时时间  

### 待实现功能

⏳ 批量失败概念重试 API（`POST /api/v1/roadmaps/{roadmap_id}/retry-failed`）  
⏳ 任务取消 API（`POST /api/v1/roadmaps/{task_id}/cancel`）  
⏳ 监控面板前端页面（`/admin/monitoring`）  
⏳ Flower 集成到 docker-compose.yml  

---

**文档版本**: 1.0  
**创建日期**: 2025-12-27  
**作者**: Roadmap Agent Development Team  
**相关文档**: [CELERY_CONTENT_GENERATION_MIGRATION_COMPLETE.md](./CELERY_CONTENT_GENERATION_MIGRATION_COMPLETE.md)


# 重试教程时序竞争问题修复

## 问题描述

用户反馈：前端触发重新生成教程的请求后，后端日志显示成功，但前端显示重试失败。页面刷新后数据正常。

## 根本原因

### 1. Redis Pub/Sub 不持久化消息
- Redis Pub/Sub 是实时消息系统
- 消息发布后，只有当时订阅的客户端能收到
- 晚订阅的客户端会错过之前的消息

### 2. 时序竞争条件

**后端执行流程** (`backend/app/api/v1/endpoints/generation.py:515-545`)：
```python
# 步骤 1: 发送 WebSocket 事件
await notification_service.publish_concept_complete(
    task_id=task_id,
    concept_id=concept_id,
    ...
)

# 步骤 2: 更新任务状态为 completed
await task_repo.update_task_status(
    task_id=task_id,
    status="completed",
    ...
)

# 步骤 3: 返回 HTTP 响应
return RetryContentResponse(
    success=True,
    data={"task_id": task_id, ...}
)
```

**前端执行流程** (`frontend-next/components/common/retry-content-button.tsx:111-171`)：
```typescript
// 步骤 1: 等待 HTTP 响应
response = await retryTutorial(roadmapId, conceptId, request);

// 步骤 2: 创建 WebSocket 连接
const ws = new TaskWebSocket(taskId, {...});

// 步骤 3: 建立连接
ws.connect(false); // 原来不获取历史事件
```

**问题**：
- 后端在返回响应前就发送了 `concept_complete` 事件
- 前端收到响应后才开始建立 WebSocket
- 前端使用 `include_history=false`，错过了已发送的事件
- 前端一直等待永远不会到来的事件，最终超时显示失败

### 3. 为什么刷新后正常

刷新页面时，前端会从数据库重新加载路线图数据，此时教程已经生成完成并保存，所以能正常显示。

## 修复方案

### 方案 1: 前端获取历史状态（已实施）

修改 `frontend-next/components/common/retry-content-button.tsx:170`：

```typescript
// 修改前
ws.connect(false); // 不需要历史事件

// 修改后
ws.connect(true); // 包括历史事件
```

**原理**：
- 使用 `include_history=true` 连接 WebSocket
- 后端会发送任务的当前状态 (`current_status` 事件)
- 如果任务已完成，前端能立即获取到状态

### 方案 2: 处理 `current_status` 事件（已实施）

添加 `onStatus` 处理器：

```typescript
const ws = new TaskWebSocket(taskId, {
  onStatus: (event) => {
    if (event.status === 'completed') {
      // 任务已完成，更新状态
      updateConceptStatus(conceptId, { [statusKey]: 'completed' });
      onSuccess?.(response);
      ws.disconnect();
      setIsRetrying(false);
    } else if (event.status === 'failed') {
      // 任务失败
      updateConceptStatus(conceptId, { [statusKey]: 'failed' });
      onError?.(new Error('内容生成失败'));
      ws.disconnect();
      setIsRetrying(false);
    }
  },
  
  // 其他事件处理器保持不变...
  onConceptComplete: (event) => { ... },
  onConceptFailed: (event) => { ... },
});
```

**原理**：
- 前端连接时请求历史状态（`include_history=true`）
- 后端查询任务当前状态并发送 `current_status` 事件
- 前端收到 `current_status` 后检查任务是否已完成
- 如果已完成，直接更新 UI 状态，不再等待 `concept_complete` 事件

## 技术细节

### 后端 `include_history` 实现

```python
# backend/app/api/v1/websocket.py:133-134
if include_history:
    await _send_current_status(websocket, task_id)
```

```python
async def _send_current_status(websocket: WebSocket, task_id: str):
    """发送任务的当前状态"""
    task = await repo.get_task(task_id)
    if task:
        await websocket.send_json({
            "type": "current_status",
            "task_id": task_id,
            "status": task.status,
            "current_step": task.current_step,
            ...
        })
```

### 前端 WebSocket 事件处理

```typescript
// frontend-next/lib/api/websocket.ts:271-272
case 'current_status':
  this.handlers.onStatus?.(data as WSCurrentStatusEvent);
  break;
```

## 测试验证

### 测试步骤

1. 触发教程重试：点击"重新生成教程"按钮
2. 观察控制台日志：
   - 应该看到 `[RetryContentButton] 订阅 WebSocket: xxx`
   - 应该看到 `[RetryContentButton] 收到 current_status 事件`
   - 如果任务已完成，应该看到状态更新为 `completed`
3. 检查 UI：按钮状态应该正确更新，不再显示失败

### 预期行为

**场景 1：快速完成（< 1秒）**
- 后端发送 `concept_complete` → 返回响应 → 前端建立连接
- 前端收到 `current_status`（status=completed）
- 立即更新 UI，显示成功

**场景 2：正常完成（1-5秒）**
- 后端返回响应 → 前端建立连接 → 后端发送 `concept_complete`
- 前端可能先收到 `current_status`（status=processing）
- 然后收到 `concept_complete` 事件
- 更新 UI，显示成功

## 其他可能受影响的功能

以下功能使用了类似的重试机制，应该验证是否也存在相同问题：

1. **重试资源推荐** (`retryResources`)
2. **重试测验生成** (`retryQuiz`)
3. **批量重试失败内容** (`retryFailed`)

建议对这些功能应用相同的修复。

## 文件变更清单

- `frontend-next/components/common/retry-content-button.tsx`
  - 修改 `ws.connect(false)` 为 `ws.connect(true)`
  - 添加 `onStatus` 事件处理器

## 总结

这是一个典型的**分布式系统时序竞争问题**，由以下因素导致：
1. 异步消息系统（Redis Pub/Sub）不持久化
2. 快速的后端处理速度（教程重试通常几秒完成）
3. 网络延迟导致的订阅滞后

修复方案利用了后端的 `include_history` 功能，在建立连接时主动获取任务状态，避免依赖实时事件的到达时序。

---

**修复日期**: 2024-12-14  
**影响范围**: 教程重试功能  
**严重程度**: 中等（用户体验问题，刷新后数据正常）  
**状态**: ✅ 已修复

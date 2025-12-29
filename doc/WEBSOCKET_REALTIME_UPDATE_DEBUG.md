# WebSocket 实时更新问题排查指南

**日期**: 2025-12-27  
**问题**: 后端日志显示 `intent_runner_completed`，但前端任务详情页面没有实时更新

---

## 问题现象

- ✅ **后端**: 日志显示节点完成 (`intent_runner_completed`, `validation_runner_completed`)
- ✅ **后端**: WebSocket 通知已发送 (`notification_published`)
- ❌ **前端**: 任务详情页面没有实时更新

---

## 排查流程

### Step 1: 检查浏览器控制台日志 🔍

打开浏览器开发者工具（F12），查看 Console 面板，搜索以下关键字：

#### 1.1 WebSocket 连接状态

应该看到：
```
[WS] Connecting to: ws://localhost:8000/api/v1/ws/{task_id}?include_history=true
[WS] Connected
```

**如果看到连接错误**：
```
[WS] Connection failed: xxx
```
说明 WebSocket 连接失败，需要检查网络或后端状态。

#### 1.2 WebSocket 消息

应该看到：
```
[WS] Message received: progress {type: "progress", step: "intent_analysis", status: "completed", ...}
[TaskDetail] Progress update: {type: "progress", step: "intent_analysis", ...}
```

**如果没有看到这些日志**：
- WebSocket 连接可能断开了
- 或消息没有被正确接收

#### 1.3 状态更新日志

应该看到：
```
[TaskDetail] Progress update: {step: "intent_analysis", status: "completed"}
```

**如果没有看到**：
- `handleProgress` 函数没有被调用
- 或事件处理器没有正确绑定

---

### Step 2: 检查 WebSocket 连接状态 🔌

#### 2.1 查看后端日志

**你已经看到的**：
```
2025-12-27 20:56:39 [info] websocket_connected task_id=xxx total_connections=2
2025-12-27 20:56:39 [debug] notification_published channel=roadmap:task:xxx event_type=progress
```

这说明：
- ✅ WebSocket 连接成功（2 个连接）
- ✅ 通知已发送到 Redis 频道

#### 2.2 检查前端连接

在浏览器 Console 中输入：
```javascript
// 查看当前 WebSocket 状态
window.__ws_debug__ = true;
```

然后刷新页面，观察连接日志。

---

### Step 3: 检查消息格式 📦

#### 3.1 后端发送的消息格式

从 `backend/app/services/notification_service.py` (第 311-317 行)：

```python
await self.notification_service.publish_progress(
    task_id=ctx.task_id,
    step=ctx.node_name,  # 例如 "intent_analysis"
    status="completed",
    message=f"完成: {ctx.node_name}",
    extra_data=extra_data if extra_data else None,
)
```

实际发送的消息：
```json
{
  "type": "progress",
  "task_id": "xxx",
  "step": "intent_analysis",
  "status": "completed",
  "message": "完成: intent_analysis",
  "timestamp": "2025-12-27T20:56:39.xxx",
  "data": {}
}
```

#### 3.2 前端期望的消息格式

从 `frontend-next/app/(app)/tasks/[taskId]/page.tsx` (第 386-454 行)：

```typescript
const handleProgress = async (event: any) => {
  console.log('[TaskDetail] Progress update:', event);
  
  // 添加实时日志
  const newLog: ExecutionLog = {
    id: `ws-${Date.now()}`,
    task_id: taskId,
    level: event.status === 'completed' ? 'success' : 'info',
    category: 'workflow',
    step: event.step || null,  // ✅ 使用 event.step
    agent_name: null,
    message: event.message || `Step: ${event.step}`,
    details: event,
    duration_ms: null,
    created_at: new Date().toISOString(),
  };
  
  setExecutionLogs((prev) => [...prev, newLog]);
  
  // 更新 current_step
  if (event.step) {
    setTaskInfo((prev) => prev ? { ...prev, current_step: event.step } : null);
  }
  
  // 当节点完成时，刷新日志和路线图
  if (event.status === 'completed' && event.step) {
    // 刷新数据...
  }
};
```

格式是**匹配**的！

---

### Step 4: 检查 step 名称映射 🏷️

#### 4.1 后端 node_name

从 `backend/app/core/orchestrator/builder.py`：

```python
workflow.add_node("intent_analysis", self.intent_runner.run)
workflow.add_node("curriculum_design", self.curriculum_runner.run)
workflow.add_node("structure_validation", self.validation_runner.run)
workflow.add_node("roadmap_edit", self.editor_runner.run)
workflow.add_node("human_review", self.review_runner.run)
workflow.add_node("tutorial_generation", self.content_runner.run)
```

后端发送的 `step` 值：
- `"intent_analysis"`
- `"curriculum_design"`
- `"structure_validation"`
- `"roadmap_edit"`
- `"human_review"`
- `"tutorial_generation"` (实际是 content_generation)

#### 4.2 前端识别的 step

从 `frontend-next/app/(app)/tasks/[taskId]/page.tsx` (第 425-450 行)：

```typescript
if (event.status === 'completed' && event.step) {
  try {
    // 刷新日志
    const logsData = await getTaskLogs(taskId, undefined, undefined, 2000);
    // ...
    
    // 如果是 curriculum_design 或 roadmap_edit 完成，重新加载路线图
    if (['curriculum_design', 'roadmap_edit'].includes(event.step)) {
      const currentRoadmapId = taskInfo.roadmap_id;
      if (currentRoadmapId) {
        await loadRoadmapFramework(currentRoadmapId);
      }
    }
  } catch (err) {
    console.error('Failed to refresh data after node completion:', err);
  }
}
```

前端**会处理**所有 step！

---

## 可能的原因分析

### 原因 1: WebSocket 连接在页面加载后断开了 🔴

**症状**：
- 初始连接成功，但后续消息没有接收到
- 后端日志显示 `notification_published`，但前端没有反应

**验证方法**：
在浏览器 Console 输入：
```javascript
// 检查 WebSocket 连接状态
document.querySelector('[data-task-id]')?.__ws__?.isConnected()
```

**解决方案**：
- 刷新页面重新建立连接
- 检查网络是否稳定
- 检查浏览器是否阻止了 WebSocket 连接

---

### 原因 2: Redis Pub/Sub 消息没有正确转发 🔴

**症状**：
- 后端日志显示 `notification_published`
- 但 WebSocket 端点没有收到消息

**验证方法**：
检查后端日志中是否有：
```
[debug] redis_forward_message task_id=xxx event_type=progress
```

**如果没有这条日志**：
说明 Redis Pub/Sub 订阅有问题。

**解决方案**：
检查 `backend/app/api/v1/websocket.py` 中的订阅逻辑。

---

### 原因 3: 前端状态更新被 React 优化跳过了 🔴

**症状**：
- Console 显示 `[TaskDetail] Progress update: xxx`
- 但 UI 没有更新

**原因**：
React 的状态更新可能被批处理或优化掉了。

**验证方法**：
在 `handleProgress` 函数中添加强制刷新：
```typescript
const handleProgress = async (event: any) => {
  console.log('[TaskDetail] Progress update:', event);
  
  // 强制触发状态更新
  setTaskInfo((prev) => {
    console.log('[TaskDetail] Updating taskInfo:', { prev, event });
    return prev ? { ...prev, current_step: event.step } : null;
  });
  
  // ...
};
```

---

### 原因 4: WebSocket 连接被防火墙/代理阻止 🔴

**症状**：
- 连接建立后立即断开
- 或长时间没有消息

**验证方法**：
检查浏览器 Network 面板：
1. 打开 F12 → Network → WS (WebSocket)
2. 查看 WebSocket 连接状态
3. 查看接收到的消息

**如果看到**：
```
Status: 101 Switching Protocols
```
说明连接成功。

**如果看到**：
```
Status: 400/500/503
```
说明连接失败。

---

## 调试步骤

### Step 1: 启用详细日志

在**浏览器 Console** 中运行：
```javascript
// 启用 WebSocket 调试日志
localStorage.setItem('debug', 'ws:*');
location.reload();
```

### Step 2: 检查 WebSocket 消息

在 **Network 面板 → WS** 中：
- 查看 `ws://localhost:8000/api/v1/ws/{task_id}` 连接
- 点击该连接，切换到 "Messages" 标签页
- 应该看到接收到的消息

**示例**：
```json
{
  "type": "progress",
  "task_id": "xxx",
  "step": "intent_analysis",
  "status": "completed",
  "message": "完成: intent_analysis",
  "timestamp": "2025-12-27T20:56:39.xxx"
}
```

### Step 3: 手动触发状态更新

在 Console 中运行：
```javascript
// 获取当前任务 ID
const taskId = window.location.pathname.split('/').pop();

// 手动刷新任务数据
fetch(`http://localhost:8000/api/v1/roadmaps/${taskId}/status`)
  .then(res => res.json())
  .then(data => {
    console.log('Task status:', data);
  });
```

### Step 4: 检查后端 WebSocket 端点

在后端日志中搜索：
```
notification_subscription_cancelled
redis_forward_cancelled
websocket_disconnected
```

**如果看到这些日志**：
说明 WebSocket 连接被意外关闭了。

---

## 临时解决方案

如果 WebSocket 实时更新不工作，前端已经有**轮询兜底机制**：

### 自动轮询机制

从代码第 364-368 行：
```typescript
let pollingInterval: NodeJS.Timeout | null = null;
let lastWebSocketMessageTime = Date.now();
let pollingAttempts = 0;
const MAX_POLLING_INTERVAL = 120000; // 最大轮询间隔：2分钟
const INITIAL_POLLING_INTERVAL = 30000; // 初始轮询间隔：30秒
const WS_SILENCE_THRESHOLD = 180000; // WebSocket 静默阈值：3分钟无消息则启动轮询
```

**如果 WebSocket 连接失败或长时间无消息**：
- 前端会自动启动轮询
- 每 30 秒检查一次任务状态
- 如果任务完成，自动刷新页面

**手动触发轮询**：
刷新页面即可。

---

## 修复建议

### 方案 1: 检查前端 WebSocket 事件处理器是否正确绑定

在 `frontend-next/app/(app)/tasks/[taskId]/page.tsx` 的第 630-646 行：

```typescript
const websocket = new TaskWebSocket(taskId, {
  onStatus: handleStatus,
  onProgress: handleProgress,  // ✅ 确认这里已绑定
  onConceptStart: handleConceptStart,
  onConceptComplete: handleConceptComplete,
  onConceptFailed: handleConceptFailed,
  onHumanReview: handleHumanReview,
  onCompleted: handleCompleted,
  onFailed: handleFailed,
  onError: handleError,
  onAnyEvent: (event: any) => {
    lastWebSocketMessageTime = Date.now();
  },
});

websocket.connect(true);  // ✅ 包含历史消息
setWs(websocket);
```

### 方案 2: 增强日志输出

在 `handleProgress` 函数开头添加：

```typescript
const handleProgress = async (event: any) => {
  console.log('[TaskDetail] Progress update:', event);
  console.log('[TaskDetail] Current taskInfo:', taskInfo);
  console.log('[TaskDetail] Will update current_step to:', event.step);
  
  // ... 原有代码
};
```

### 方案 3: 检查 WebSocket 连接健康状况

在 `frontend-next/lib/api/websocket.ts` 的 `TaskWebSocket` 类中添加心跳检测：

```typescript
private startHeartbeat() {
  this.heartbeatInterval = setInterval(() => {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('[WS] Sending ping');
      this.ws.send(JSON.stringify({ type: 'ping' }));
    }
  }, 30000); // 每 30 秒发送一次 ping
}
```

---

## 快速诊断命令

在**浏览器 Console** 中运行以下命令进行诊断：

```javascript
// 1. 检查 WebSocket 连接状态
console.log('WebSocket connected:', window.__current_ws__?.isConnected());

// 2. 检查任务 ID
const taskId = window.location.pathname.split('/').pop();
console.log('Task ID:', taskId);

// 3. 手动获取任务状态
fetch(`http://localhost:8000/api/v1/roadmaps/${taskId}/status`)
  .then(res => res.json())
  .then(data => console.log('Task status:', data));

// 4. 检查执行日志
fetch(`http://localhost:8000/api/v1/trace/${taskId}/logs?limit=10`)
  .then(res => res.json())
  .then(data => console.log('Recent logs:', data.logs));
```

---

## 下一步操作

1. **打开浏览器开发者工具（F12）**
2. **切换到 Console 面板**
3. **刷新页面**
4. **观察日志输出**，特别是：
   - `[WS] Connecting to...`
   - `[WS] Message received: progress`
   - `[TaskDetail] Progress update:`

5. **如果没有看到这些日志**：
   - 检查 Network 面板 → WS
   - 查看 WebSocket 连接状态和消息

6. **将 Console 日志截图或复制**，我可以帮你进一步分析

---

**参考文档**:
- `frontend-next/lib/api/websocket.ts` - WebSocket 客户端实现
- `backend/app/services/notification_service.py` - 通知服务
- `backend/app/api/v1/websocket.py` - WebSocket 端点

**修复者**: AI Assistant  
**版本**: v1.0








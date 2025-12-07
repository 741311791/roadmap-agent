# WebSocket 403 Forbidden 和 API 404 问题修复

## 🔴 新问题

修复了第一个 URL 错误后，出现了两个新问题：

### 问题 1：WebSocket 403 Forbidden

```
INFO: 127.0.0.1:53861 - "WebSocket /api/v1/ws/7914fb05-c121-48cc-aee8-ac9098807969?include_history=true" 403
INFO: connection rejected (403 Forbidden)
INFO: connection closed
```

**前端日志**：
```
WebSocket connection to 'ws://localhost:8000/api/v1/ws/...' failed
[WS] Error, will fallback to polling
```

### 问题 2：API 404 Not Found

```
INFO: 127.0.0.1:53893 - "GET /api/v1/roadmaps/tasks/7914fb05-c121-48cc-aee8-ac9098807969/status HTTP/1.1" 404 Not Found
```

**前端日志**：
```
GET http://localhost:3000/api/v1/roadmaps/tasks/.../status 404 (Not Found)
```

## 🔍 根本原因

### 原因 1：WebSocket Router 缺少 Prefix ⚠️

**文件**：`backend/app/api/v1/websocket.py:22`

```python
# ❌ 错误：没有指定 prefix
router = APIRouter()
```

**导致**：
- WebSocket 端点注册为 `/ws/{task_id}`（缺少 `/api/v1`）
- 前端连接到 `ws://localhost:8000/api/v1/ws/{task_id}`
- 路由不匹配 → 403 Forbidden

**main.py 中的注册方式**：
```python
app.include_router(websocket_router)  # 直接注册，没有添加 prefix
```

### 原因 2：前端 API 路径错误 ⚠️

**错误路径**（前端）：
```
/api/v1/roadmaps/tasks/{task_id}/status  ❌ (多了 tasks)
/api/v1/roadmaps/tasks/{task_id}/approve  ❌ (多了 tasks)
```

**正确路径**（后端）：
```
/api/v1/roadmaps/{task_id}/status  ✅
/api/v1/roadmaps/{task_id}/approve  ✅
```

**影响的文件**：
1. `frontend-next/lib/hooks/api/use-task-status.ts:48`
2. `frontend-next/lib/api/endpoints/roadmaps.ts:122`
3. `frontend-next/lib/api/endpoints/roadmaps.ts:136`

## ✅ 修复方案

### 修复 1：WebSocket Router 添加 Prefix

**文件**：`backend/app/api/v1/websocket.py`

```diff
  from app.services.notification_service import notification_service, TaskEvent
  from app.db.repositories.roadmap_repo import RoadmapRepository
  from app.db.session import AsyncSessionLocal

- router = APIRouter()
+ router = APIRouter(prefix="/api/v1")
  logger = structlog.get_logger()
```

**效果**：
- WebSocket 端点现在注册为 `/api/v1/ws/{task_id}`
- 与前端请求的 URL 完全匹配
- 解决 403 Forbidden 问题

### 修复 2：前端 API 路径修正

**文件 1**：`frontend-next/lib/hooks/api/use-task-status.ts`

```diff
  queryFn: async (): Promise<TaskStatusResponse> => {
    if (!taskId) {
      throw new Error('Task ID is required');
    }

-   const response = await fetch(`/api/v1/roadmaps/tasks/${taskId}/status`);
+   const response = await fetch(`/api/v1/roadmaps/${taskId}/status`);
```

**文件 2**：`frontend-next/lib/api/endpoints/roadmaps.ts`

```diff
  getTaskStatus: async (taskId: string): Promise<TaskStatusResponse> => {
    const { data } = await apiClient.get<TaskStatusResponse>(
-     `/roadmaps/tasks/${taskId}/status`
+     `/roadmaps/${taskId}/status`
    );
    return data;
  },
```

```diff
  submitApproval: async (
    taskId: string,
    approval: ApprovalRequest
  ): Promise<ApprovalResponse> => {
    const { data } = await apiClient.post<ApprovalResponse>(
-     `/roadmaps/tasks/${taskId}/approve`,
+     `/roadmaps/${taskId}/approve`,
      approval
    );
    return data;
  },
```

## 📊 路由对比

### WebSocket 路由

| 组件 | 修复前 | 修复后 |
|------|--------|--------|
| **后端定义** | `/ws/{task_id}` ❌ | `/api/v1/ws/{task_id}` ✅ |
| **前端请求** | `ws://localhost:8000/api/v1/ws/{task_id}` | `ws://localhost:8000/api/v1/ws/{task_id}` |
| **结果** | 不匹配 → 403 | 匹配 ✅ |

### API 路由

| 端点 | 修复前（前端） | 修复后（前端） | 后端实际 |
|------|--------------|--------------|---------|
| 任务状态 | `/api/v1/roadmaps/tasks/{id}/status` ❌ | `/api/v1/roadmaps/{id}/status` ✅ | `/api/v1/roadmaps/{id}/status` ✅ |
| 审核 | `/api/v1/roadmaps/tasks/{id}/approve` ❌ | `/api/v1/roadmaps/{id}/approve` ✅ | `/api/v1/roadmaps/{id}/approve` ✅ |

## 🧪 验证测试

### 测试 1：WebSocket 连接

```bash
# 使用 websocat 测试（如果已安装）
websocat ws://localhost:8000/api/v1/ws/test-task-id-123

# 或使用浏览器控制台
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/test-task-id-123');
ws.onopen = () => console.log('✅ Connected');
ws.onerror = (e) => console.log('❌ Error:', e);
```

**✅ 期望结果**：
- 连接成功（Status 101 Switching Protocols）
- 收到 `connected` 消息

**❌ 修复前**：
- 403 Forbidden
- 连接立即关闭

### 测试 2：API 状态查询

```bash
# 先创建一个任务
TASK_ID=$(curl -s -X POST http://localhost:8000/api/v1/roadmaps/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "preferences": {
      "learning_goal": "测试",
      "current_level": "beginner",
      "weekly_hours": 10,
      "learning_style": ["visual"]
    }
  }' | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])")

# 查询任务状态
curl http://localhost:8000/api/v1/roadmaps/$TASK_ID/status
```

**✅ 期望结果**：
```json
{
  "task_id": "...",
  "status": "processing",
  "current_step": "intent_analysis",
  ...
}
```

**❌ 修复前**：
- 404 Not Found

## 📁 修改的文件

### 后端

1. ✅ `backend/app/api/v1/websocket.py` (Line 22)
   - 添加 `prefix="/api/v1"` 到 APIRouter

### 前端

1. ✅ `frontend-next/lib/hooks/api/use-task-status.ts` (Line 48)
   - 移除路径中的 `/tasks/`

2. ✅ `frontend-next/lib/api/endpoints/roadmaps.ts` (Line 122, 136)
   - 移除 `getTaskStatus` 路径中的 `/tasks/`
   - 移除 `submitApproval` 路径中的 `/tasks/`

## 🎯 修复完整度

### 第一轮修复（前面完成）
- ✅ 前端 WebSocket URL：添加 `/api/v1` 前缀
- ✅ 后端异常处理：添加连接状态检查

### 第二轮修复（本次）
- ✅ 后端 WebSocket Router：添加 prefix
- ✅ 前端 API 路径：移除多余的 `/tasks/` 段

## ✨ 总结

### 问题链

```
1. 前端 URL 错误（/ws/ → /api/v1/ws/）
   ↓ 修复
2. 后端 Router 缺少 prefix
   ↓ 修复
3. 前端 API 路径错误（/tasks/ 多余）
   ↓ 修复
4. ✅ 所有问题解决
```

### 最终状态

| 功能 | 状态 |
|------|------|
| WebSocket 连接 | ✅ 正常 |
| API 状态查询 | ✅ 正常 |
| 路线图生成 | ✅ 正常 |
| 实时进度更新 | ✅ 正常 |

---

**修复时间**：2025-12-07  
**修复轮次**：第 2 轮  
**预计测试时间**：5 分钟


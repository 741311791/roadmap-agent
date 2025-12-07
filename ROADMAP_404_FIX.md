# 路线图详情页 404 错误修复报告

## 问题描述

路线图生成完成后，前端尝试跳转到详情页时出现 404 错误：
- 错误 URL: `http://localhost:3000/app/roadmap/langgraph-multi-agent-development-d8c9b7e2`
- WebSocket 断开时出现未捕获的异常

## 根本原因分析

### 1. 前端路由路径错误 ❌

**问题**: 前端使用了错误的路由路径 `/app/roadmap/[id]`

**原因**: 
- Next.js App Router 中，`(app)` 是一个路由组（Route Group）
- 路由组不会出现在最终的 URL 中
- 实际文件路径: `app/(app)/roadmap/[id]/page.tsx`
- 正确的 URL: `/roadmap/[id]`
- 错误的 URL: `/app/roadmap/[id]`

**影响文件**:
- `frontend-next/lib/hooks/websocket/use-roadmap-generation-ws.ts`

### 2. WebSocket 断开异常未正确处理 ❌

**问题**: 后端在客户端断开连接时抛出未捕获的异常

**原因**:
- `_handle_client_messages` 函数中捕获 `WebSocketDisconnect` 后重新抛出
- 该函数作为 asyncio 任务运行，异常不会自动传播
- 导致 "Task exception was never retrieved" 错误

**影响文件**:
- `backend/app/api/v1/websocket.py`

## 修复方案

### 修复 1: 更正前端路由路径

**文件**: `frontend-next/lib/hooks/websocket/use-roadmap-generation-ws.ts`

**修改**: 将所有 `/app/roadmap/` 改为 `/roadmap/`

```typescript
// 修改前 ❌
router.push(`/app/roadmap/${data.roadmap_id}`);

// 修改后 ✅
router.push(`/roadmap/${data.roadmap_id}`);
```

**修改位置**:
1. 第 67 行 - 轮询模式完成回调
2. 第 96 行 - current_status 事件处理
3. 第 113 行 - 早期导航（curriculum_design 步骤）
4. 第 151 行 - completed 事件处理

### 修复 2: 优化 WebSocket 断开异常处理

**文件**: `backend/app/api/v1/websocket.py`

**修改**: 在 `_handle_client_messages` 函数中正确处理断开异常

```python
# 修改前 ❌
except WebSocketDisconnect:
    raise  # 重新抛出异常

# 修改后 ✅
except WebSocketDisconnect:
    # 客户端正常断开连接，不需要重新抛出异常
    logger.debug("websocket_client_messages_disconnected", task_id=task_id)

except asyncio.CancelledError:
    # 任务被取消（通常是因为 Redis 任务完成），正常情况
    logger.debug("websocket_client_messages_cancelled", task_id=task_id)
```

## 修复验证

### 测试步骤

1. **启动后端服务**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. **启动前端服务**
   ```bash
   cd frontend-next
   npm run dev
   ```

3. **创建新路线图**
   - 访问 `/new` 页面
   - 填写学习目标和偏好
   - 点击"生成路线图"

4. **验证跳转**
   - 等待路线图生成完成
   - 确认自动跳转到正确的详情页
   - 确认 URL 格式为 `/roadmap/{roadmap_id}`（无 `/app/` 前缀）

5. **验证 WebSocket**
   - 检查后端日志，确认没有未捕获的异常
   - 确认客户端断开时日志正常

### 预期结果 ✅

1. **路由正确**: 
   - URL: `http://localhost:3000/roadmap/langgraph-multi-agent-development-d8c9b7e2`
   - 页面正常加载，显示路线图详情

2. **WebSocket 正常**:
   - 无 "Task exception was never retrieved" 错误
   - 断开连接日志正常：`websocket_client_messages_disconnected`

## 相关技术说明

### Next.js Route Groups

Route Groups 是 Next.js 13+ App Router 的特性：
- 用括号命名文件夹，如 `(app)`、`(marketing)`
- 不会影响 URL 路径
- 用于组织路由而不影响 URL 结构
- 示例：
  ```
  app/
    (app)/
      roadmap/
        [id]/
          page.tsx  → URL: /roadmap/[id]
    (marketing)/
      about/
        page.tsx  → URL: /about
  ```

### asyncio Task 异常处理

在 Python asyncio 中：
- 使用 `asyncio.create_task()` 创建的任务
- 如果任务内部抛出异常且未被捕获
- 异常不会自动传播到创建任务的地方
- 需要显式处理或不重新抛出异常

## 总结

本次修复解决了两个关键问题：

1. ✅ **前端路由 404 错误** - 更正了路由路径，从 `/app/roadmap/[id]` 改为 `/roadmap/[id]`
2. ✅ **WebSocket 异常处理** - 优化了断开连接的异常处理，避免未捕获的异常

这两个修复确保了：
- 路线图生成完成后能正确跳转到详情页
- WebSocket 连接断开时不会产生错误日志
- 用户体验更加流畅

## 修改文件列表

```
frontend-next/lib/hooks/websocket/use-roadmap-generation-ws.ts
backend/app/api/v1/websocket.py
```

---

**修复完成时间**: 2025-12-07
**修复人员**: AI Assistant

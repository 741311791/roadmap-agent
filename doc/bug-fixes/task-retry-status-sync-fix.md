# Bug 修复：Retry 后任务状态不同步

## 问题描述

**症状：**
1. 用户在任务列表点击 Retry 按钮
2. 任务实际上已经重试成功并启动（后端正在处理）
3. 但任务列表中的状态仍然显示 `failed`
4. 点击进入任务详情页，状态也显示 `failed`
5. 只有刷新页面后才能看到正确的 `processing` 状态

**影响：** 用户体验差，容易误以为 retry 失败或系统无响应。

## 根本原因

### 原因 1：任务列表页延迟刷新（次要）

在 `frontend-next/app/(app)/tasks/page.tsx` 中：

```typescript
// ❌ 问题代码（第 92-95 行）
await retryTask(taskId, userId);

// 成功后 1 秒后刷新任务列表
setTimeout(() => {
  fetchTasks(activeFilter);
}, 1000);
```

**问题分析：**
- retry API 调用成功后，等待 1 秒才刷新任务列表
- 在这 1 秒内，用户如果点击进入详情页，会看到旧的 `failed` 状态
- 虽然有乐观更新（本地立即改为 `processing`），但这只是 UI 的临时状态，不是从后端获取的真实状态

### 原因 2：任务详情页 WebSocket 不建立（主要）

在 `frontend-next/app/(app)/tasks/[taskId]/page.tsx` 的 WebSocket `useEffect` 中：

```typescript
// ❌ 问题代码（第 515-523 行）
// 只有正在处理中的任务才需要 WebSocket
const isActiveTask = 
  taskInfo.status === 'processing' || 
  taskInfo.status === 'pending' ||
  taskInfo.status === 'human_review_pending';

if (!isActiveTask) {
  return;  // 如果任务状态是 failed，直接退出，不建立 WebSocket
}
```

**问题分析：**
1. 用户从任务列表进入详情页时，`taskInfo` 是从数据库加载的
2. 如果数据库的状态还是旧的 `failed`（retry 后数据库更新有延迟），`isActiveTask` 为 false
3. `useEffect` 直接 return，不建立 WebSocket 连接
4. 没有 WebSocket，无法接收后端推送的状态更新（`processing`、`completed` 等）
5. UI 一直卡在 `failed` 状态，直到用户刷新页面

### 执行时序图

```
Time  |  User Action           |  Task List Page         |  Task Detail Page      |  Backend Status
------|------------------------|-------------------------|------------------------|------------------
t0    | Click Retry            | status: failed          | -                      | failed
t1    | -                      | 乐观更新: processing     | -                      | failed → processing
t2    | -                      | API call success        | -                      | processing
t3    | Click into detail      | 等待 1 秒刷新...         | Load: status=failed ❌  | processing
t4    | -                      | -                       | No WebSocket ❌         | processing
t5    | -                      | fetchTasks() ✅          | Still shows failed ❌   | processing
t6    | Refresh page           | -                       | Reload: status=processing ✅ | processing
```

## 修复方案

### 修复 1：任务详情页 - 防御性 WebSocket 建立

**文件：** `frontend-next/app/(app)/tasks/[taskId]/page.tsx`

**修改：** 允许 `failed` 状态的任务在最近更新（10秒内）时尝试建立 WebSocket

```typescript
// ✅ 修复后（第 515-532 行）
// 只有正在处理中的任务才需要 WebSocket
const isActiveTask = 
  taskInfo.status === 'processing' || 
  taskInfo.status === 'pending' ||
  taskInfo.status === 'human_review_pending';

// 防御性处理：如果任务是 failed 但最近更新（10秒内），可能是刚刚 retry 的
// 尝试建立 WebSocket 连接以接收最新状态（retry 后状态会变为 processing）
const isRecentlyUpdated = taskInfo.updated_at 
  ? (Date.now() - new Date(taskInfo.updated_at).getTime()) < 10000 
  : false;
const mightBeRetrying = taskInfo.status === 'failed' && isRecentlyUpdated;

if (!isActiveTask && !mightBeRetrying) {
  return;
}

// 如果是可能正在 retry 的任务，记录日志
if (mightBeRetrying) {
  console.log('[TaskDetail] Task might be retrying, establishing WebSocket to check for updates');
}
```

**原理：**
- 判断任务的 `updated_at` 时间是否在 10 秒内
- 如果是，即使状态是 `failed`，也尝试建立 WebSocket
- WebSocket 连接后会收到后端推送的最新状态（如 `processing`）
- 收到状态更新后，`handleStatus` 回调会更新 `taskInfo.status`，UI 自动同步

### 修复 2：任务列表页 - 立即刷新（移除延迟）

**文件：** `frontend-next/app/(app)/tasks/page.tsx`

**修改：** retry 成功后立即刷新任务列表，而不是延迟 1 秒

```typescript
// ✅ 修复后（第 89-93 行）
// 调用智能重试 API
await retryTask(taskId, userId);

// 立即刷新任务列表以获取最新状态（移除延迟）
// 这样用户点击进入详情页时，能看到最新的 processing 状态
await fetchTasks(activeFilter);
```

**原理：**
- 移除 `setTimeout(..., 1000)`，改为 `await fetchTasks()`
- retry API 成功后立即刷新任务列表
- 确保用户点击进入详情页时，看到的是最新的 `processing` 状态

## 测试验证

### 测试场景 1：快速进入详情页

1. 在任务列表中找到一个 `failed` 的任务
2. 点击 Retry 按钮
3. **立即**点击任务卡片进入详情页（不等待）
4. 验证：
   - ✅ 详情页应该显示 `processing` 状态（而不是 `failed`）
   - ✅ Workflow Progress 应该显示正在进行的步骤
   - ✅ WebSocket 应该正常工作，接收实时更新

### 测试场景 2：在详情页内 retry

1. 进入一个 `failed` 任务的详情页
2. 点击详情页内的 Retry 按钮（如果有）
3. 验证：
   - ✅ 状态应该立即更新为 `processing`
   - ✅ WebSocket 应该重新建立（如果之前断开）
   - ✅ 能够接收实时进度更新

### 测试场景 3：多次 retry

1. retry 一个任务
2. 在任务处理过程中，再次失败
3. 再次点击 retry
4. 验证：
   - ✅ 状态同步正常
   - ✅ WebSocket 能够正确处理状态切换

### 验证步骤

```bash
# 1. 启动前端服务
cd frontend-next
npm run dev

# 2. 打开浏览器控制台，观察日志
# 3. 执行测试场景 1-3
# 4. 检查以下日志输出：
#    - [TaskDetail] Task might be retrying, establishing WebSocket to check for updates
#    - [WS] Connection opened
#    - [TaskDetail] Status update: {status: "processing", ...}
```

## 相关文件

### 修改的文件

- `frontend-next/app/(app)/tasks/page.tsx` - 任务列表页（移除刷新延迟）
- `frontend-next/app/(app)/tasks/[taskId]/page.tsx` - 任务详情页（防御性 WebSocket）

### 相关文件（参考）

- `frontend-next/lib/api/websocket.ts` - WebSocket 客户端实现
- `frontend-next/lib/api/endpoints.ts` - `retryTask` API 定义
- `backend/app/api/v1/endpoints/retry.py` - Retry 后端逻辑

## 影响范围

### 正面影响

- ✅ 用户 retry 后立即看到正确的状态
- ✅ 提升用户体验，减少困惑
- ✅ WebSocket 连接更稳健
- ✅ 减少不必要的页面刷新

### 潜在风险

- ⚠️ 10 秒的时间窗口是否合理？
  - 如果用户在 retry 后 11 秒才进入详情页，仍然会遇到问题
  - 但这种情况较少见，且影响不大（刷新页面即可）

- ⚠️ 立即刷新可能增加服务器压力
  - 从 1 秒延迟改为立即刷新，理论上会稍微增加请求频率
  - 但影响很小，且提升了用户体验，权衡后是值得的

### 兼容性

- ✅ **无破坏性变更**：修复后的行为符合用户预期
- ✅ **向后兼容**：不影响现有正常流程
- ✅ **不需要数据迁移**：纯前端逻辑优化

## 后续改进

### 短期改进

1. **添加全局状态管理：**
   - 使用 Zustand 或 Context 管理任务状态
   - 任务列表页 retry 后，通知详情页刷新数据
   - 避免依赖时间窗口判断

2. **优化 WebSocket 重连逻辑：**
   - 当 WebSocket 接收到状态变化（failed → processing）时，自动刷新页面数据
   - 确保 UI 和 WebSocket 状态完全同步

3. **添加 Loading 指示器：**
   - 在 retry 按钮上显示 loading 状态
   - 直到确认任务状态已更新为 `processing`

### 长期改进

1. **实现 Server-Sent Events (SSE)：**
   - 作为 WebSocket 的备选方案
   - 更容易处理断线重连

2. **使用 TanStack Query 的 mutation：**
   - 利用 `useMutation` 和 `queryClient.invalidateQueries`
   - 自动刷新相关查询的缓存
   - 统一管理异步状态

3. **添加乐观更新到详情页：**
   - 当用户在详情页点击 retry 时，立即更新 UI
   - 不等待 API 响应

## 修复时间线

- **发现时间：** 2025-12-30
- **修复时间：** 2025-12-30
- **状态：** ✅ 已修复，待测试验证

## 参考资料

- [WebSocket 连接管理](../../frontend-next/lib/api/websocket.ts)
- [Retry API 文档](../../backend/docs/RETRY_STRATEGY.md)
- [任务状态同步设计](../../frontend-next/docs/task-status-sync.md)


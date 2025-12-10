# Partial Failure 状态处理修复报告

## 问题描述

### 现象
路线图生成完成后，数据库中任务状态为 `partial_failure`，`current_step` 为 `completed`，但前端仍然显示 "Generating Your Learning Roadmap"，没有跳转到路线图详情页。

### 根本原因
前端代码没有处理 `partial_failure` 状态，导致：
1. 类型定义中缺少该状态
2. 状态检查逻辑中未处理该状态
3. 轮询和 WebSocket 都无法识别该状态为完成状态

## 修复内容

### 1. 类型定义修复 ✅

**文件**: `frontend-next/types/generated/models.ts`

```typescript
// 修复前
export type TaskStatus = 
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'human_review_required'
  | 'approved'
  | 'rejected';

// 修复后
export type TaskStatus = 
  | 'pending'
  | 'processing'           // ← 新增
  | 'running'
  | 'completed'
  | 'partial_failure'      // ← 新增
  | 'failed'
  | 'human_review_pending' // ← 新增
  | 'human_review_required'
  | 'approved'
  | 'rejected';
```

**文件**: `frontend-next/lib/api/endpoints.ts`

```typescript
// 修复前
export interface TaskStatus {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  // ...
}

// 修复后
export interface TaskStatus {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'partial_failure' | 'failed' | 'human_review_pending' | 'human_review_required';
  // ...
}
```

### 2. 任务恢复逻辑修复 ✅

**文件**: `frontend-next/app/(app)/new/new-roadmap-client.tsx`

**修复点**: URL 参数恢复任务时的状态处理逻辑

```typescript
// 修复前：只处理 completed 状态
if (status.status === 'completed' && status.roadmap_id) {
  router.push(`/roadmap/${status.roadmap_id}`);
}

// 修复后：同时处理 partial_failure 状态
if ((taskStatus === 'completed' || taskStatus === 'partial_failure') && status.roadmap_id) {
  console.log('[NewRoadmap] Task finished with status:', taskStatus, 'Navigating to roadmap:', status.roadmap_id);
  router.push(`/roadmap/${status.roadmap_id}`);
  return;
}
```

**改进**: 重新组织了条件判断顺序，避免 TypeScript 类型推断问题：
1. 先检查完成状态（completed / partial_failure）
2. 再检查进行中状态（processing / pending / human_review_pending）
3. 最后检查失败状态（failed）

### 3. 轮询 Hook 修复 ✅

**文件**: `frontend-next/lib/hooks/api/use-task-status.ts`

**修复点 1**: 回调触发逻辑

```typescript
// 修复前
if (data.status === 'completed') {
  onComplete?.(data);
}

// 修复后：partial_failure 也触发 onComplete
if (data.status === 'completed' || data.status === 'partial_failure') {
  onComplete?.(data);
}
```

**修复点 2**: 轮询停止条件

```typescript
// 修复前
if (data && (data.status === 'completed' || data.status === 'failed')) {
  return false; // 停止轮询
}

// 修复后：partial_failure 也停止轮询
if (
  data &&
  (data.status === 'completed' || 
   data.status === 'partial_failure' || 
   data.status === 'failed')
) {
  return false;
}
```

### 4. WebSocket Hook 修复 ✅

**文件**: `frontend-next/lib/hooks/websocket/use-roadmap-generation-ws.ts`

**修复点 1**: current_status 消息处理

```typescript
// 修复前
if (data.status === 'completed' && data.roadmap_id) {
  onComplete?.(data.roadmap_id);
  if (autoNavigate) {
    router.push(`/roadmap/${data.roadmap_id}`);
  }
}

// 修复后
if ((data.status === 'completed' || data.status === 'partial_failure') && data.roadmap_id) {
  console.log('[WS] Task finished with status:', data.status, 'roadmap_id:', data.roadmap_id);
  onComplete?.(data.roadmap_id);
  if (autoNavigate) {
    router.push(`/roadmap/${data.roadmap_id}`);
  }
}
```

**修复点 2**: completed 和 partial_failure 事件处理

```typescript
// 修复前
case 'completed':
  console.log('[WS] Task completed:', data.roadmap_id);
  setLiveGenerating(false);
  onComplete?.(data.roadmap_id);
  if (autoNavigate) {
    router.push(`/roadmap/${data.roadmap_id}`);
  }
  disconnect();
  break;

// 修复后：合并处理两种完成状态
case 'completed':
case 'partial_failure':
  console.log('[WS] Task finished:', data.type, 'roadmap_id:', data.roadmap_id);
  setLiveGenerating(false);
  if (data.roadmap_id) {
    onComplete?.(data.roadmap_id);
    if (autoNavigate) {
      router.push(`/roadmap/${data.roadmap_id}`);
    }
  }
  disconnect();
  break;
```

## 设计决策

### 为什么将 partial_failure 视为成功状态？

`partial_failure` 表示：
- ✅ 路线图主体结构已成功生成
- ✅ 大部分内容已成功生成
- ⚠️ 部分内容（如某些教程、资源、测验）生成失败

**理由**:
1. 用户仍然可以查看和使用路线图的主要内容
2. 失败的部分可以通过重试按钮单独重新生成
3. 完全阻止用户访问会导致糟糕的用户体验

## 后续优化建议

### 1. 状态展示优化
在路线图详情页中，对于 `partial_failure` 状态的路线图：
- 显示警告提示："部分内容生成失败"
- 标记失败的内容项
- 提供重试按钮

### 2. 类型定义统一
建议：
- 删除 `lib/api/endpoints.ts` 中的重复 `TaskStatus` 接口
- 统一使用 `types/generated/models.ts` 中的 `TaskStatusResponse` 类型
- 使用类型导入而不是接口重复定义

### 3. 状态枚举集中管理
建议创建 `lib/constants/task-status.ts`:
```typescript
export const TASK_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  PARTIAL_FAILURE: 'partial_failure',
  FAILED: 'failed',
  // ...
} as const;

export const isTaskFinished = (status: TaskStatus): boolean => {
  return status === TASK_STATUS.COMPLETED || 
         status === TASK_STATUS.PARTIAL_FAILURE ||
         status === TASK_STATUS.FAILED;
};

export const isTaskSuccessful = (status: TaskStatus): boolean => {
  return status === TASK_STATUS.COMPLETED || 
         status === TASK_STATUS.PARTIAL_FAILURE;
};
```

## 测试建议

### 场景 1: 正常流程测试
1. 创建新路线图
2. 等待生成完成
3. 验证跳转到路线图详情页

### 场景 2: Partial Failure 测试
1. 模拟部分内容生成失败（通过后端调试）
2. 验证前端能正确识别 `partial_failure` 状态
3. 验证跳转到路线图详情页
4. 验证路线图页面显示警告和重试选项

### 场景 3: 任务恢复测试
1. 开始路线图生成
2. 复制带有 `task_id` 参数的 URL
3. 关闭浏览器标签
4. 在新标签中打开 URL
5. 验证能恢复到正确状态（进行中或已完成）

### 场景 4: WebSocket 降级测试
1. 禁用 WebSocket 连接（模拟网络问题）
2. 验证自动降级到轮询模式
3. 验证轮询模式下 `partial_failure` 状态也能正确处理

## 修改文件清单

- ✅ `frontend-next/types/generated/models.ts`
- ✅ `frontend-next/lib/api/endpoints.ts`
- ✅ `frontend-next/app/(app)/new/new-roadmap-client.tsx`
- ✅ `frontend-next/lib/hooks/api/use-task-status.ts`
- ✅ `frontend-next/lib/hooks/websocket/use-roadmap-generation-ws.ts`

## 相关文档

- 后端状态定义: `backend/app/db/repositories/roadmap_repo.py:150`
- 后端状态使用: `backend/app/services/roadmap_service.py:317,414`
- 前端状态枚举: `frontend-next/types/generated/models.ts:245-252`

---

**修复日期**: 2025-12-09  
**问题严重程度**: 高（阻止用户访问已生成的路线图）  
**修复状态**: ✅ 已完成

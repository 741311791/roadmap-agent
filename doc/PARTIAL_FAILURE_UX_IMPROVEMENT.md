# Partial Failure 状态用户体验优化

## 问题描述

### 当前体验问题

当路线图生成过程中部分概念失败时（如内容审核问题、API 错误等），后端返回 `status=partial_failure`，但前端存在以下问题：

1. **TaskList 列表页**:
   - `partial_failure` 被映射为 `failed`
   - 显示红色错误 Badge，让用户误以为整个任务失败
   - 无法查看路线图（没有"View Roadmap"按钮）

2. **TaskDetail 详情页**:
   - 状态显示为 `Pending`（因为 `getStatusConfig` 中没有处理 `partial_failure`）
   - 让用户误以为系统不可靠或卡住了

3. **用户认知偏差**:
   - 用户看到 "Failed" 会认为整个任务失败
   - 不知道大部分内容已经生成成功
   - 不知道可以进入路线图重试失败的概念

### 期望的用户体验

1. 用户能清楚知道：
   - ✅ 大部分内容已成功生成
   - ⚠️ 只有少部分概念失败
   - 🔄 可以进入路线图查看并重试失败的概念

2. 状态展示清晰：
   - 列表页：橙色 "Partially Completed" 状态
   - 详情页：友好的提示卡片引导用户查看路线图

---

## 优化方案

### 1. TaskList 列表页优化

**文件**: `frontend-next/components/task/task-list.tsx`

#### 改进 A: 添加 `partial_failure` 状态配置

```typescript
const getStatusConfig = (status: string) => {
  const config = {
    // ... 其他状态 ...
    partial_failure: { 
      variant: 'default' as const, 
      label: 'Partially Completed',  // ✅ 正面表述
      icon: AlertCircle,
      className: 'border-orange-300 text-orange-700 bg-orange-50'  // ✅ 橙色，区别于红色错误
    },
    failed: { 
      variant: 'destructive' as const, 
      label: 'Failed', 
      icon: AlertCircle,
      className: 'border-red-300 text-red-600 bg-red-50'  // ❌ 红色，表示完全失败
    },
  };
  
  return config[status as keyof typeof config] || config.failed;
};
```

**视觉对比**：
- 🟢 `completed`: 绿色 "Completed"
- 🟠 `partial_failure`: 橙色 "Partially Completed" ⬅️ 新增
- 🔴 `failed`: 红色 "Failed"

#### 改进 B: 调整 Actions 按钮逻辑

```typescript
{/* View Roadmap Button - 完成后显示（包括部分失败） */}
{(task.status === 'completed' || task.status === 'partial_failure') && task.roadmap_id && (
  <Tooltip>
    <TooltipTrigger asChild>
      <Link href={`/roadmap/${task.roadmap_id}`}>
        <Button size="icon" variant="ghost" className="h-8 w-8">
          <Eye className="h-4 w-4" />
        </Button>
      </Link>
    </TooltipTrigger>
    <TooltipContent>
      <p>
        {task.status === 'partial_failure' 
          ? 'View roadmap & retry failed concepts'  // ✅ 引导用户重试
          : 'View roadmap'}
      </p>
    </TooltipContent>
  </Tooltip>
)}

{/* Retry Button - 仅完全失败时显示 */}
{task.status === 'failed' && (
  <Tooltip>
    <TooltipTrigger asChild>
      <Button size="icon" variant="ghost" onClick={() => onRetry(task.task_id)}>
        <RefreshCw className="h-4 w-4" />
      </Button>
    </TooltipTrigger>
    <TooltipContent>
      <p>Retry task</p>
    </TooltipContent>
  </Tooltip>
)}
```

**关键改进**：
- `partial_failure`: 显示 "View Roadmap" 按钮（引导用户查看）
- `failed`: 显示 "Retry" 按钮（重新生成整个任务）

---

### 2. TaskDetail 详情页优化

**文件**: `frontend-next/app/(app)/tasks/[taskId]/page.tsx`

#### 改进 A: 添加 `partial_failure` 状态配置

```typescript
const getStatusConfig = (status: string) => {
  const configs: Record<string, { icon: any; label: string; className: string }> = {
    // ... 其他状态 ...
    partial_failure: {
      icon: AlertCircle,
      label: 'Partially Completed',
      className: 'bg-orange-50 text-orange-700 border-orange-200',
    },
    // ...
  };

  return configs[status] || configs.pending;
};
```

#### 改进 B: 添加友好的提示卡片

在详情页底部添加一个橙色提示卡片，明确告知用户：

```typescript
{/* Partial Failure Info Card - 部分失败时显示 */}
{taskInfo.status === 'partial_failure' && taskInfo.roadmap_id && (
  <Card className="border-orange-200 bg-orange-50/50">
    <div className="p-6">
      <div className="flex items-start gap-3">
        <CheckCircle2 className="w-5 h-5 text-orange-600 shrink-0 mt-0.5" />
        <div className="space-y-3 flex-1">
          <div>
            <h3 className="font-medium text-orange-900">
              Roadmap Generated Successfully
            </h3>
            <p className="text-sm text-orange-700 mt-1">
              Most of your learning content has been generated successfully. 
              Some concepts failed during generation due to content policy restrictions or API errors.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              onClick={() => router.push(`/roadmap/${taskInfo.roadmap_id}`)}
              className="bg-orange-600 hover:bg-orange-700 text-white"
            >
              <Eye className="w-4 h-4 mr-2" />
              View Roadmap & Retry Failed Concepts
            </Button>
            <p className="text-xs text-orange-600">
              You can retry the failed concepts individually from the roadmap page
            </p>
          </div>
        </div>
      </div>
    </div>
  </Card>
)}
```

**卡片要素**：
- ✅ **正面标题**: "Roadmap Generated Successfully"（强调成功）
- ⚠️ **解释原因**: 说明部分概念失败的原因
- 🔄 **行动召唤**: 明确的按钮引导用户查看路线图并重试
- 💡 **辅助说明**: 告知可以单独重试失败的概念

#### 改进 C: 调整 WebSocket 订阅逻辑

```typescript
useEffect(() => {
  if (!taskId || !taskInfo) return;

  // 只有正在处理中的任务才需要WebSocket
  // 已完成（包括partial_failure）的任务不需要订阅
  if (taskInfo.status !== 'processing' && taskInfo.status !== 'pending') {
    return;
  }
  
  // ... WebSocket setup
}, [taskId, taskInfo?.status]);
```

---

## 视觉效果对比

### Before (修复前)

**TaskList 列表页**:
```
┌─────────────────────────────────────────────────────────────┐
│ Task Title         │ Status │ Current Step │ Actions        │
├─────────────────────────────────────────────────────────────┤
│ Badminton Skills   │ 🔴 Failed │ content_generation │ 📄 🔄 │
└─────────────────────────────────────────────────────────────┘
```

**TaskDetail 详情页**:
```
┌─────────────────────────────────────────────────────────────┐
│ Badminton Skills Enhancement                  🟡 Pending     │
├─────────────────────────────────────────────────────────────┤
│ [Stepper: content_generation is active]                     │
│                                                              │
│ [Execution Logs...]                                         │
└─────────────────────────────────────────────────────────────┘
```

**用户感受**: 😞
- "任务失败了？"
- "系统卡住了吗？Pending 是什么意思？"
- "我不知道还能做什么..."

---

### After (修复后)

**TaskList 列表页**:
```
┌─────────────────────────────────────────────────────────────┐
│ Task Title         │ Status              │ Current Step     │ Actions  │
├─────────────────────────────────────────────────────────────┤
│ Badminton Skills   │ 🟠 Partially        │ content_generation │ 📄 👁️   │
│                    │    Completed        │                    │          │
└─────────────────────────────────────────────────────────────┘
                                                Tooltip: "View roadmap & retry failed concepts"
```

**TaskDetail 详情页**:
```
┌─────────────────────────────────────────────────────────────┐
│ Badminton Skills Enhancement      🟠 Partially Completed    │
├─────────────────────────────────────────────────────────────┤
│ [Stepper: content_generation is completed]                  │
│                                                              │
│ [Execution Logs...]                                         │
│                                                              │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ ✅ Roadmap Generated Successfully                      │  │
│ │                                                        │  │
│ │ Most of your learning content has been generated      │  │
│ │ successfully. Some concepts failed during generation   │  │
│ │ due to content policy restrictions or API errors.      │  │
│ │                                                        │  │
│ │ [👁️ View Roadmap & Retry Failed Concepts]             │  │
│ │ You can retry the failed concepts individually...     │  │
│ └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**用户感受**: 😊
- "✅ 大部分内容已经生成成功了！"
- "⚠️ 只有少部分失败，可以理解"
- "🔄 我知道可以进入路线图重试失败的部分"

---

## 技术实现细节

### 1. 状态映射关系

| 后端状态 | 前端展示 | 颜色 | 含义 |
|---------|---------|------|------|
| `completed` | Completed | 🟢 绿色 | 全部成功 |
| `partial_failure` | Partially Completed | 🟠 橙色 | 大部分成功，少部分失败 |
| `failed` | Failed | 🔴 红色 | 完全失败 |
| `processing` | Processing | 🔵 蓝色 | 正在处理 |
| `pending` | Pending | 🟡 黄色 | 等待中 |

### 2. Actions 按钮显示逻辑

| 状态 | View Roadmap | Retry | View Logs |
|------|-------------|-------|-----------|
| `completed` | ✅ | ❌ | ❌ |
| `partial_failure` | ✅ (引导重试) | ❌ | ✅ |
| `failed` | ❌ | ✅ | ✅ |
| `processing` | ✅ (实时进度) | ❌ | ❌ |

**关键设计决策**：
- `partial_failure` 不显示 "Retry" 按钮，因为：
  - 大部分内容已经成功，不需要重新生成整个任务
  - 用户可以在路线图页面单独重试失败的概念
  - 避免用户误操作浪费时间和资源

### 3. 信息传递策略

#### 列表页（TaskList）- 简洁信息
- **目标**: 快速扫描，了解状态
- **策略**: 
  - 使用橙色 "Partially Completed" 状态
  - Tooltip 提示可以查看路线图并重试

#### 详情页（TaskDetail）- 详细信息
- **目标**: 了解具体情况，知道下一步怎么做
- **策略**:
  - 友好的提示卡片
  - 明确的行动召唤按钮
  - 辅助说明文字

---

## 用户体验改进效果

### 改进前的用户流程（痛点）

1. 用户在列表页看到 🔴 "Failed"
2. 点进详情页看到 🟡 "Pending"（困惑）
3. 不知道路线图已生成，不知道下一步该做什么
4. 认为系统不可靠，可能放弃使用

### 改进后的用户流程（顺畅）

1. 用户在列表页看到 🟠 "Partially Completed"
2. 理解大部分内容已生成，只有少部分失败
3. 点击 "View Roadmap" 进入路线图页面
4. 在路线图中看到失败的概念（标记为 `failed`）
5. 点击单独重试失败的概念
6. 成功完成整个学习路线图

---

## 后续优化建议

### 1. 在列表页添加成功率指标

在 `TaskList` 中显示成功率，让用户更清楚地知道完成情况：

```typescript
<TableCell>
  <div className="flex items-center gap-2">
    <Badge variant="outline" className={statusConfig.className}>
      <StatusIcon className="w-3 h-3" />
      {statusConfig.label}
    </Badge>
    {task.status === 'partial_failure' && task.execution_summary && (
      <span className="text-xs text-muted-foreground">
        {task.execution_summary.completed_count}/{task.execution_summary.total_count} concepts
      </span>
    )}
  </div>
</TableCell>
```

**效果**：
```
🟠 Partially Completed  (18/24 concepts)
```

### 2. 在路线图页面高亮失败的概念

在路线图页面，自动筛选或高亮显示 `content_status=failed` 的概念，并在顶部显示：

```typescript
{failedConceptsCount > 0 && (
  <Alert variant="warning">
    <AlertCircle className="h-4 w-4" />
    <AlertTitle>Some concepts failed to generate</AlertTitle>
    <AlertDescription>
      {failedConceptsCount} concept(s) marked in red. Click to retry individually.
    </AlertDescription>
  </Alert>
)}
```

### 3. 添加批量重试功能

在路线图页面添加"Retry All Failed Concepts"按钮：

```typescript
<Button onClick={() => retryFailedConcepts(roadmapId)}>
  <RefreshCw className="w-4 h-4 mr-2" />
  Retry All Failed Concepts ({failedConceptsCount})
</Button>
```

---

## 相关文件清单

### 修改的文件
1. `frontend-next/components/task/task-list.tsx`
   - 添加 `partial_failure` 状态配置
   - 调整 Actions 按钮显示逻辑

2. `frontend-next/app/(app)/tasks/[taskId]/page.tsx`
   - 添加 `partial_failure` 状态配置
   - 添加友好的提示卡片
   - 调整 WebSocket 订阅逻辑

### 后端配置
- `backend/app/core/orchestrator/workflow_brain.py` (已修复)
  - 正确设置 `current_step=content_generation` (部分失败时)
  - 正确设置 `current_step=completed` (全部成功时)

---

## 总结

本次优化通过以下三个方面改善了用户体验：

1. **视觉区分**: 使用橙色 "Partially Completed" 区别于红色 "Failed"
2. **信息透明**: 明确告知用户大部分内容已成功，只有少部分失败
3. **行动引导**: 提供清晰的按钮和说明，引导用户查看路线图并重试失败的概念

**核心设计理念**：
- ✅ **正面表述**：强调成功的部分（"Partially Completed" vs "Failed"）
- 🎯 **清晰引导**：告诉用户下一步该做什么
- 💡 **降低焦虑**：减少红色错误提示，使用橙色警告色调

这样，即使有部分概念生成失败，用户也不会感到沮丧或困惑，而是知道大部分工作已经完成，只需要简单地重试失败的部分即可。


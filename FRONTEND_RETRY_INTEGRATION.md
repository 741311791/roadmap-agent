# 前端智能重试集成完成

## ✅ 已完成的修改

### 1. **更新 API 类型定义** (`lib/api/endpoints.ts`)

#### 新增接口定义

```typescript
export interface RetryTaskResponse {
  success: boolean;
  recovery_type: 'checkpoint' | 'content_retry';
  
  // Checkpoint 恢复时返回
  task_id?: string;
  checkpoint_step?: string;
  
  // 内容重试时返回
  new_task_id?: string;
  old_task_id?: string;
  items_to_retry?: Record<string, number>;
  total_items?: number;
  
  // 通用字段
  roadmap_id: string;
  status: string;
  message: string;
}
```

#### 更新函数签名

```typescript
export async function retryTask(
  taskId: string,
  userId: string,
  forceCheckpoint: boolean = false  // 新增参数
): Promise<RetryTaskResponse>
```

---

### 2. **更新任务列表页面** (`app/(app)/tasks/page.tsx`)

#### 新增导入

```typescript
import { useRouter } from 'next/navigation';
import { useRoadmapGenerationWS } from '@/lib/hooks/websocket/use-roadmap-generation-ws';
import { toast } from 'sonner';
import { RetryTaskResponse } from '@/lib/api/endpoints';
```

#### 新增状态管理

```typescript
const [retryingTaskId, setRetryingTaskId] = useState<string | null>(null);
const [retryRoadmapId, setRetryRoadmapId] = useState<string | null>(null);
const [retryType, setRetryType] = useState<'checkpoint' | 'content_retry' | null>(null);
```

#### 实现 WebSocket 订阅

```typescript
const { connectionType, isConnected } = useRoadmapGenerationWS(
  retryingTaskId,
  {
    autoNavigate: false,
    onComplete: (roadmapId) => {
      toast.success('Task retry completed!', {
        action: {
          label: 'View Roadmap',
          onClick: () => router.push(`/roadmap/${roadmapId}`),
        },
      });
      setRetryingTaskId(null);
      setRetryRoadmapId(null);
      setRetryType(null);
      fetchTasks(activeFilter);
    },
    onError: (error) => {
      toast.error(`Retry failed: ${error}`);
      setRetryingTaskId(null);
      setRetryRoadmapId(null);
      setRetryType(null);
    },
  }
);
```

#### 智能重试处理逻辑

```typescript
const handleRetry = async (taskId: string) => {
  const userId = getUserId();
  if (!userId) return;
  
  try {
    setIsRetrying(taskId);
    
    // 调用智能重试 API
    const result: RetryTaskResponse = await retryTask(taskId, userId);
    
    // 根据恢复类型显示不同的提示
    if (result.recovery_type === 'checkpoint') {
      // Checkpoint 恢复
      toast.info(
        `Recovering from ${result.checkpoint_step || 'last checkpoint'}...`,
        {
          description: 'The workflow will continue from where it left off.',
          duration: 5000,
          action: {
            label: 'View Progress',
            onClick: () => router.push(`/roadmap/${result.roadmap_id}`),
          },
        }
      );
      
      // 使用原 task_id 订阅进度
      setRetryingTaskId(result.task_id || taskId);
      setRetryRoadmapId(result.roadmap_id);
      setRetryType('checkpoint');
      
    } else if (result.recovery_type === 'content_retry') {
      // 内容重试
      toast.info(
        `Retrying ${result.total_items || 0} failed items...`,
        {
          description: 'Only failed content will be regenerated.',
          duration: 5000,
          action: {
            label: 'View Progress',
            onClick: () => router.push(`/roadmap/${result.roadmap_id}`),
          },
        }
      );
      
      // 使用新 task_id 订阅进度
      setRetryingTaskId(result.new_task_id || null);
      setRetryRoadmapId(result.roadmap_id);
      setRetryType('content_retry');
    }
    
  } catch (error: any) {
    console.error('Failed to retry task:', error);
    
    const errorMessage = error.response?.data?.detail || 
      'Failed to retry task. Please try again later.';
    toast.error('Retry Failed', {
      description: errorMessage,
      duration: 7000,
    });
  } finally {
    setIsRetrying(null);
  }
};
```

#### 新增重试进度横幅

```tsx
{/* Retry Progress Banner */}
{retryingTaskId && retryRoadmapId && (
  <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
        <div>
          <p className="font-medium text-blue-900">
            {retryType === 'checkpoint' 
              ? 'Recovering from checkpoint...' 
              : 'Retrying failed content...'}
          </p>
          <p className="text-sm text-blue-600">
            Connection: {connectionType === 'ws' ? 'WebSocket' : 'Polling'} 
            {isConnected && ' • Connected'}
          </p>
        </div>
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => router.push(`/roadmap/${retryRoadmapId}`)}
      >
        View Details
      </Button>
    </div>
  </div>
)}
```

---

### 3. **添加 Toast 通知** (`app/providers.tsx`)

```typescript
import { Toaster } from 'sonner';

export function Providers({ children }: ProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster 
        position="top-right"
        expand={true}
        richColors
        closeButton
      />
    </QueryClientProvider>
  );
}
```

---

## 🎨 用户体验流程

### 场景 1：Checkpoint 恢复

```
用户操作：点击失败任务的 "Retry" 按钮

前端行为：
1. ✅ 调用 API: POST /api/v1/tasks/{task_id}/retry
2. ✅ 收到响应: { recovery_type: 'checkpoint', checkpoint_step: 'roadmap_edit' }
3. ✅ 显示 Toast: "Recovering from roadmap_edit..."
4. ✅ 显示进度横幅: "Recovering from checkpoint..."
5. ✅ 订阅 WebSocket: 使用原 task_id
6. ✅ 实时更新进度
7. ✅ 完成后显示: "Task retry completed!" + "View Roadmap" 按钮
```

### 场景 2：内容重试

```
用户操作：点击部分失败任务的 "Retry" 按钮

前端行为：
1. ✅ 调用 API: POST /api/v1/tasks/{task_id}/retry
2. ✅ 收到响应: { recovery_type: 'content_retry', total_items: 6, new_task_id: '...' }
3. ✅ 显示 Toast: "Retrying 6 failed items..."
4. ✅ 显示进度横幅: "Retrying failed content..."
5. ✅ 订阅 WebSocket: 使用新 task_id
6. ✅ 实时更新进度
7. ✅ 完成后显示: "Task retry completed!" + "View Roadmap" 按钮
```

### 场景 3：错误处理

```
用户操作：点击无法重试的任务

前端行为：
1. ✅ 调用 API: POST /api/v1/tasks/{task_id}/retry
2. ✅ 收到错误: 400 Bad Request
3. ✅ 显示详细错误 Toast:
   "Retry Failed"
   "无法重试此任务：
    - 没有失败的 Concept 内容
    - Checkpoint 不存在
    提示：如果任务在早期阶段失败，请使用 force_checkpoint=true 参数"
4. ✅ 错误消息持续 7 秒
```

---

## 📱 UI 组件说明

### Toast 通知类型

#### 信息提示 (Info)
```typescript
toast.info('Recovering from checkpoint...', {
  description: 'The workflow will continue from where it left off.',
  duration: 5000,
  action: {
    label: 'View Progress',
    onClick: () => router.push(`/roadmap/${roadmapId}`),
  },
});
```

#### 成功提示 (Success)
```typescript
toast.success('Task retry completed!', {
  action: {
    label: 'View Roadmap',
    onClick: () => router.push(`/roadmap/${roadmapId}`),
  },
});
```

#### 错误提示 (Error)
```typescript
toast.error('Retry Failed', {
  description: errorMessage,
  duration: 7000,
});
```

### 进度横幅

- **位置**: 任务列表顶部
- **显示条件**: `retryingTaskId && retryRoadmapId`
- **内容**:
  - 加载动画图标
  - 恢复类型说明
  - WebSocket 连接状态
  - "View Details" 按钮

---

## 🧪 测试建议

### 测试用例 1：Checkpoint 恢复

```bash
# 准备：找一个早期阶段失败的任务
Task ID: e2054e91-c19f-4221-9e5e-449de50ca1ef
Status: failed
Current Step: roadmap_edit

# 操作
1. 在任务列表中点击 "Retry" 按钮
2. 观察 Toast 提示
3. 观察进度横幅
4. 点击 "View Details" 查看路线图页面
5. 等待任务完成

# 预期结果
✅ Toast 显示: "Recovering from roadmap_edit..."
✅ 横幅显示: "Recovering from checkpoint..."
✅ WebSocket 连接成功
✅ 任务完成后显示成功提示
✅ 任务列表自动刷新
```

### 测试用例 2：内容重试

```bash
# 准备：找一个内容生成阶段部分失败的任务
Task ID: xxx-yyy-zzz
Status: partial_failure
Failed: 3 tutorials, 2 resources, 1 quiz

# 操作
1. 在任务列表中点击 "Retry" 按钮
2. 观察 Toast 提示
3. 观察进度横幅
4. 等待任务完成

# 预期结果
✅ Toast 显示: "Retrying 6 failed items..."
✅ 横幅显示: "Retrying failed content..."
✅ 使用新 task_id 订阅进度
✅ 任务完成后显示成功提示
```

### 测试用例 3：错误处理

```bash
# 准备：找一个无法重试的任务
Task ID: completed-task-id
Status: completed
No failed content

# 操作
1. 在任务列表中点击 "Retry" 按钮

# 预期结果
✅ Toast 显示错误信息
✅ 错误描述清晰
✅ 持续 7 秒后自动消失
```

---

## 🔍 调试技巧

### 查看 WebSocket 连接状态

```typescript
// 在浏览器控制台
console.log('Retrying Task ID:', retryingTaskId);
console.log('Connection Type:', connectionType);
console.log('Is Connected:', isConnected);
```

### 查看 API 响应

```typescript
// 在 handleRetry 中添加
console.log('Retry Response:', result);
console.log('Recovery Type:', result.recovery_type);
```

### 查看 Toast 状态

```typescript
// Sonner 会在控制台显示 toast 调用
// 可以看到所有 toast 的触发时机
```

---

## 📊 性能优化

### WebSocket 连接管理

- ✅ 只在重试时建立连接
- ✅ 完成/失败后自动断开
- ✅ 支持降级到轮询
- ✅ 自动重连机制

### 状态管理

- ✅ 最小化状态更新
- ✅ 及时清理状态
- ✅ 避免内存泄漏

### Toast 通知

- ✅ 合理的持续时间
- ✅ 可关闭按钮
- ✅ 操作按钮（View Progress/View Roadmap）

---

## 🎯 下一步优化建议

### 1. 添加重试历史

```typescript
// 记录用户的重试操作
interface RetryHistory {
  taskId: string;
  timestamp: Date;
  recoveryType: 'checkpoint' | 'content_retry';
  result: 'success' | 'failed';
}
```

### 2. 批量重试

```typescript
// 支持选择多个失败任务一起重试
const handleBatchRetry = async (taskIds: string[]) => {
  // ...
};
```

### 3. 重试配置

```typescript
// 允许用户选择重试策略
<Select>
  <SelectItem value="auto">Auto (Recommended)</SelectItem>
  <SelectItem value="checkpoint">Force Checkpoint Recovery</SelectItem>
  <SelectItem value="content">Content Retry Only</SelectItem>
</Select>
```

---

## ✅ 完成清单

- [x] 更新 API 类型定义
- [x] 实现智能重试处理逻辑
- [x] 添加 WebSocket 进度订阅
- [x] 实现 Toast 通知
- [x] 添加进度横幅 UI
- [x] 添加 Toaster 组件到 Providers
- [x] 错误处理和用户反馈
- [x] 代码 Lint 检查通过

---

## 🎉 总结

前端已完全集成智能重试机制，支持：

1. **✅ 自动识别恢复类型** - 根据后端响应自动选择 UI 展示
2. **✅ 实时进度订阅** - WebSocket 实时推送进度更新
3. **✅ 友好的用户反馈** - Toast 通知 + 进度横幅
4. **✅ 完整的错误处理** - 详细的错误信息展示
5. **✅ 无缝的用户体验** - 一键重试，自动导航

现在用户可以轻松重试失败的任务，系统会自动选择最佳的恢复策略！🚀


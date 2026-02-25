# Frontend API Migration Guide
# 前端API迁移指南

**日期**: 2026-01-17  
**版本**: 1.0  
**状态**: ✅ 核心重构完成

---

## 一、快速开始

### 1.1 安装依赖并生成类型

```bash
cd frontend-next

# 安装依赖
npm install

# 确保后端服务运行在 http://localhost:8000
# 生成TypeScript类型
npm run generate:types

# 验证类型生成
npm run type-check
```

---

### 1.2 导入新的API

```typescript
// ✅ 推荐：使用新的业务领域API
import { 
  authApi, 
  usersApi, 
  tasksApi, 
  roadmapsApi, 
  contentApi, 
  adminApi 
} from '@/lib/api/endpoints';

// ⚠️ 过渡期：仍可使用旧函数（已标记@deprecated）
import { 
  generateRoadmapAsync, 
  getUserProfile,
  deleteRoadmap,
} from '@/lib/api/endpoints';
```

---

## 二、API路径变更对照表

### 2.1 认证授权（auth）

| 功能 | 旧路径 | 新路径 | 新API调用 |
|------|--------|--------|----------|
| 登出 | `/users/auth/logout` | `/auth/logout` | `authApi.logout()` |
| 登出所有设备 | `/users/auth/logout-all-devices` | `/auth/logout-all-devices` | `authApi.logoutAllDevices()` |
| 黑名单统计 | `/users/auth/blacklist/stats` | `/auth/blacklist/stats` | `authApi.getBlacklistStats()` |

---

### 2.2 用户管理（users）

| 功能 | 旧路径 | 新路径 | 参数变更 | 新API调用 |
|------|--------|--------|---------|----------|
| 获取用户画像 | `/users/{userId}/profile` | `/users/profile` | ❌ 移除userId | `usersApi.getUserProfile()` |
| 更新用户画像 | `/users/{userId}/profile` | `/users/profile` | ❌ 移除userId | `usersApi.updateUserProfile(profile)` |

**重要变更**：
- ❌ **不再需要传递userId参数**
- ✅ 后端从JWT Token自动提取user_id
- ✅ 防止权限伪造攻击

---

### 2.3 任务管理（tasks）

| 功能 | 旧路径 | 新路径 | 新API调用 |
|------|--------|--------|----------|
| 生成路线图 | `/workflows/generation/generate` | `/tasks/generate` | `tasksApi.generate(request)` |
| 获取用户任务 | `/users/{user_id}/tasks` | `/tasks/users/{user_id}` | `tasksApi.getUserTasks(userId, params)` |
| 获取任务详情 | - | `/tasks/{task_id}` | `tasksApi.getById(taskId)` |
| 取消任务 | `/workflows/generation/tasks/{id}/cancel` | `/tasks/{id}/cancel` | `tasksApi.cancel(taskId)` |
| 重试任务 | `/workflows/generation/retry/{id}` | `/tasks/{id}/retry` | `tasksApi.retry(taskId)` |
| 人工审核 | `/workflows/generation/{id}/approve` | `/tasks/{id}/approve` | `tasksApi.approve(taskId, approval)` |
| 执行日志 | `/admin/admin/trace/{id}/logs` | `/tasks/{id}/logs` | `tasksApi.getLogs(taskId)` |
| 日志摘要 | `/admin/admin/trace/{id}/summary` | `/tasks/{id}/summary` | `tasksApi.getLogSummary(taskId)` |
| 错误日志 | `/admin/admin/trace/{id}/errors` | `/tasks/{id}/errors` | `tasksApi.getErrors(taskId)` |

**重要变更**：
- ✅ 路线图生成从`roadmapsApi`迁移到`tasksApi`
- ✅ 执行日志从`admin`迁移到`tasks`
- ✅ 语义更清晰（任务管理统一在tasks领域）

---

### 2.4 路线图管理（roadmaps）

| 功能 | 旧路径 | 新路径 | 参数变更 | 新API调用 |
|------|--------|--------|---------|----------|
| 用户路线图列表 | `/users/{user_id}/roadmaps` | `/roadmaps/users/{user_id}` | - | `roadmapsApi.getUserRoadmaps(userId, params)` |
| 回收站 | `/users/{user_id}/roadmaps/trash` | `/roadmaps/users/{user_id}/trash` | - | `roadmapsApi.getUserTrash(userId)` |
| 精选路线图 | - | `/roadmaps/featured` | - | `roadmapsApi.getFeatured(params)` |
| 获取路线图详情 | `/roadmaps/{roadmap_id}` | `/roadmaps/{roadmap_id}` | - | `roadmapsApi.getById(roadmapId)` |
| 删除路线图 | `/roadmaps/{roadmap_id}` | `/roadmaps/{roadmap_id}` | ❌ 移除userId | `roadmapsApi.delete(roadmapId)` |
| 恢复路线图 | - | `/roadmaps/{roadmap_id}/restore` | ❌ 移除userId | `roadmapsApi.restore(roadmapId)` |
| 永久删除 | - | `/roadmaps/{roadmap_id}/permanent` | ❌ 移除userId | `roadmapsApi.permanentDelete(roadmapId)` |
| 路线图状态 | `/roadmaps/{task_id}/status` | `/roadmaps/{roadmap_id}/status` | - | `roadmapsApi.getStatus(roadmapId)` |
| 意图分析 | `/roadmaps/{task_id}` | `/roadmaps/{roadmap_id}/intent-analysis` | - | `roadmapsApi.getIntentAnalysis(roadmapId)` |
| 编辑记录 | - | `/roadmaps/{roadmap_id}/edit-records` | - | `roadmapsApi.getEditRecords(roadmapId)` |
| 验证记录 | - | `/roadmaps/{roadmap_id}/validation-records` | - | `roadmapsApi.getValidationRecords(roadmapId)` |
| 生成封面图 | `/roadmap/{roadmap_id}/cover-image/generate` | `/roadmaps/{roadmap_id}/cover-image/generate` | - | `roadmapsApi.generateCoverImage(roadmapId)` |

**重要变更**：
- ✅ 路径统一：资源优先原则（`/roadmaps/users/{id}` 而非 `/users/{id}/roadmaps`）
- ❌ **删除/恢复操作移除userId参数**（从JWT自动提取）

---

### 2.5 内容管理（content）

| 功能 | 旧路径 | 新路径 | 新API调用 |
|------|--------|--------|----------|
| 获取教程 | `/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorial` | （保持） | `contentApi.getTutorial(roadmapId, conceptId, version)` |
| 获取资源 | `/roadmaps/{roadmap_id}/concepts/{concept_id}/resources` | （保持） | `contentApi.getResources(roadmapId, conceptId)` |
| 获取测验 | `/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz` | （保持） | `contentApi.getQuiz(roadmapId, conceptId)` |
| 修改教程 | `/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorial/modify` | （保持） | `contentApi.modifyTutorial(roadmapId, conceptId, request)` |

---

### 2.6 平台管理（admin）

| 功能 | 旧路径 | 新路径 | 新API调用 |
|------|--------|--------|----------|
| 加入Waitlist | `/users/waitlist` | `/waitlist` | `adminApi.joinWaitlist(email)` |
| 获取Waitlist | - | `/admin/waitlist` | `adminApi.getWaitlist(params)` |
| 邀请用户 | - | `/admin/users/invite` | `adminApi.inviteUser(email)` |
| Tavily Keys | - | `/admin/tavily/keys` | `adminApi.getTavilyKeys()` |
| Celery监控 | - | `/admin/monitoring/celery/tasks` | `adminApi.getCeleryTasks(params)` |

---

## 三、代码迁移示例

### 3.1 路线图生成

```typescript
// ❌ 旧版本
import { generateRoadmapAsync } from '@/lib/api/endpoints';

const result = await generateRoadmapAsync(request);

// ✅ 新版本
import { tasksApi } from '@/lib/api/endpoints';

const result = await tasksApi.generate(request);
```

---

### 3.2 用户画像

```typescript
// ❌ 旧版本
import { getUserProfile, updateUserProfile } from '@/lib/api/endpoints';

const profile = await getUserProfile(userId);
await updateUserProfile(userId, newProfile);

// ✅ 新版本
import { usersApi } from '@/lib/api/endpoints';

const profile = await usersApi.getUserProfile();  // 无需userId
await usersApi.updateUserProfile(newProfile);     // 无需userId
```

---

### 3.3 路线图删除/恢复

```typescript
// ❌ 旧版本
import { deleteRoadmap, restoreRoadmap } from '@/lib/api/endpoints';

await deleteRoadmap(roadmapId, userId);
await restoreRoadmap(roadmapId, userId);

// ✅ 新版本
import { roadmapsApi } from '@/lib/api/endpoints';

await roadmapsApi.delete(roadmapId);    // 无需userId
await roadmapsApi.restore(roadmapId);   // 无需userId
```

---

### 3.4 任务审核和日志

```typescript
// ❌ 旧版本
import { approveRoadmap } from '@/lib/api/endpoints';

await approveRoadmap(taskId, true, 'Looks good');
// 执行日志：分散在admin模块

// ✅ 新版本
import { tasksApi } from '@/lib/api/endpoints';

await tasksApi.approve(taskId, { approved: true, feedback: 'Looks good' });
const logs = await tasksApi.getLogs(taskId);
const summary = await tasksApi.getLogSummary(taskId);
const errors = await tasksApi.getErrors(taskId);
```

---

## 四、Hooks迁移

### 4.1 useRoadmapGeneration

```typescript
// ❌ 旧版本
export function useRoadmapGeneration() {
  return useMutation({
    mutationFn: async (request: UserRequest) => {
      const response = await fetch('/api/v1/roadmaps/generate', {...});
      ...
    },
  });
}

// ✅ 新版本
export function useRoadmapGeneration() {
  return useMutation({
    mutationFn: async (request: UserRequest) => {
      const { tasksApi } = await import('@/lib/api/endpoints/tasks');
      return tasksApi.generate(request);
    },
  });
}
```

---

### 4.2 useUserProfile

```typescript
// ❌ 旧版本
export function useUserProfile(userId: string | undefined) {
  return useQuery({
    queryKey: ['user-profile', userId],
    queryFn: async () => {
      const response = await fetch(`/api/v1/users/${userId}/profile`);
      ...
    },
    enabled: !!userId,
  });
}

// ✅ 新版本
export function useUserProfile() {  // 移除userId参数
  return useQuery({
    queryKey: ['user-profile'],
    queryFn: async () => {
      const { usersApi } = await import('@/lib/api/endpoints/users');
      return usersApi.getUserProfile();  // 从JWT自动提取
    },
  });
}
```

---

### 4.3 useRoadmapList

```typescript
// ❌ 旧版本
const response = await fetch(`/api/v1/roadmaps/user/${userId}?...`);

// ✅ 新版本
const response = await fetch(`/api/v1/roadmaps/users/${userId}?...`);
```

---

## 五、错误处理升级

### 5.1 使用统一错误处理工具

```typescript
import { handleApiError } from '@/lib/utils/error-handler';

// 基础用法
try {
  const roadmap = await roadmapsApi.getById(roadmapId);
} catch (error) {
  handleApiError(error, { context: 'Roadmap' });
}

// 高级用法
try {
  await tasksApi.approve(taskId, approval);
} catch (error) {
  const message = handleApiError(error, {
    context: 'Task Approval',
    showToast: true,
    customMessages: {
      notFound: 'Task not found, it may have been deleted',
      unauthorized: 'Please login to approve tasks',
    },
    onError: (err) => {
      console.error('[Approval Failed]', err);
    },
  });
}
```

---

### 5.2 APIException便捷方法

```typescript
import { APIException } from '@/types/custom/api-response';

try {
  const data = await someApi();
} catch (error) {
  if (error instanceof APIException) {
    if (error.isNotFound()) {
      console.log('Resource not found');
    } else if (error.isUnauthorized()) {
      // 401已由拦截器自动处理（登出+跳转）
      console.log('User logged out automatically');
    } else if (error.isValidationError()) {
      console.log('Validation failed:', error.details);
    } else {
      console.log('Error:', error.getUserMessage());
    }
  }
}
```

---

## 六、Store使用

### 6.1 路线图Store（分离后）

```typescript
import { useRoadmapStore } from '@/lib/store';

function MyComponent() {
  // 路线图数据和状态
  const currentRoadmap = useRoadmapStore((state) => state.currentRoadmap);
  const history = useRoadmapStore((state) => state.history);
  const setRoadmap = useRoadmapStore((state) => state.setRoadmap);
  
  // ❌ 不再包含任务状态（已分离到taskStore）
}
```

---

### 6.2 任务Store（新增）

```typescript
import { useTaskStore } from '@/lib/store';

function TaskComponent() {
  const currentTaskId = useTaskStore((state) => state.currentTaskId);
  const taskStatus = useTaskStore((state) => state.taskStatus);
  const taskProgress = useTaskStore((state) => state.taskProgress);
  
  const setCurrentTask = useTaskStore((state) => state.setCurrentTask);
  const updateTaskProgress = useTaskStore((state) => state.updateTaskProgress);
}

// 或使用选择器
import { selectTaskId, selectTaskStatus } from '@/lib/store';

const taskId = useTaskStore(selectTaskId);
const status = useTaskStore(selectTaskStatus);
```

---

## 七、类型系统

### 7.1 使用自动生成的类型

```typescript
// ✅ 优先使用自动生成的类型
import type { 
  RoadmapFramework, 
  Concept, 
  Module, 
  Stage,
  Tutorial,
} from '@/types/generated';

// ❌ 不要重复定义后端模型
interface RoadmapFramework {  // 错误：不要手动定义
  roadmap_id: string;
  // ...
}
```

---

### 7.2 扩展自动生成的类型

```typescript
import type { RoadmapFramework } from '@/types/generated';
import type { RoadmapWithUI } from '@/types/custom/api';

// ✅ 使用交叉类型扩展
function MyComponent() {
  const [roadmap, setRoadmap] = useState<RoadmapWithUI | null>(null);
  
  // roadmap 包含后端字段 + UI字段（isFavorite, isExpanded, cachedAt）
}
```

---

### 7.3 类型导入规则

```typescript
// ✅ 后端模型 - 从 types/generated 导入
import type { RoadmapFramework, Concept } from '@/types/generated';

// ✅ 前端专用 - 从 types/custom 导入
import type { RoadmapWithUI, ViewMode, ToastConfig } from '@/types/custom/api';
import type { RoadmapStore, TaskStore } from '@/types/custom/store';

// ✅ API响应格式 - 从 endpoints 或 custom 导入
import type { GenerateRoadmapResponse } from '@/lib/api/endpoints/tasks';
import type { APIResponse, APIException } from '@/types/custom/api-response';
```

---

## 八、常见问题 FAQ

### Q1: 为什么要移除userId参数？

**A**: 安全性考虑。

```typescript
// ❌ 旧方式：用户可以伪造userId访问他人数据
await deleteRoadmap('roadmap-123', 'fake-user-id');  // 危险

// ✅ 新方式：后端从JWT Token自动提取，无法伪造
await roadmapsApi.delete('roadmap-123');  // 安全
```

---

### Q2: 旧代码会立即报错吗？

**A**: 不会。我们提供了兼容层。

```typescript
// ⚠️ 旧代码仍然可以运行（通过兼容层）
import { deleteRoadmap } from '@/lib/api/endpoints';
await deleteRoadmap(roadmapId, userId);  // 内部转发到 roadmapsApi.delete

// ✅ 但建议逐步迁移到新API
import { roadmapsApi } from '@/lib/api/endpoints';
await roadmapsApi.delete(roadmapId);
```

---

### Q3: 如何知道应该使用哪个API？

**A**: 根据功能所属的业务领域判断。

| 功能 | 使用API | 示例 |
|------|--------|------|
| 生成路线图、任务状态 | `tasksApi` | `tasksApi.generate()` |
| 路线图列表、删除 | `roadmapsApi` | `roadmapsApi.getUserRoadmaps()` |
| 教程、资源、测验 | `contentApi` | `contentApi.getTutorial()` |
| 用户画像 | `usersApi` | `usersApi.getUserProfile()` |
| 登录、登出 | `authApi` | `authApi.logout()` |
| 管理后台 | `adminApi` | `adminApi.getTavilyKeys()` |

---

### Q4: 类型生成失败怎么办？

**A**: 使用占位符类型。

```bash
# 1. 检查后端是否运行
curl http://localhost:8000/health

# 2. 如果后端不可用，会自动生成占位符类型
npm run generate:types
# ✅ Placeholder types generated successfully!

# 3. 后端可用后重新生成
npm run generate:types
# ✅ TypeScript types generated successfully!
```

---

### Q5: 如何处理类型不匹配？

**A**: 使用类型断言或Utility Types。

```typescript
// 场景1：字段可选
import type { UserProfileRequest } from '@/lib/api/endpoints/users';

const partialProfile: Partial<UserProfileRequest> = {
  learning_goal: 'Learn Python',
  // 其他字段可选
};

// 场景2：类型扩展
import type { RoadmapFramework } from '@/types/generated';

interface RoadmapWithExtra extends RoadmapFramework {
  isFavorite: boolean;
}

// 场景3：类型断言（谨慎使用）
const data = response.data as MyType;
```

---

## 九、测试策略

### 9.1 单元测试

```bash
# 运行所有单元测试
npm run test

# 运行特定测试文件
npm run test __tests__/api/endpoints/tasks.test.ts

# 查看测试覆盖率
npm run test:coverage
```

---

### 9.2 类型检查

```bash
# 运行TypeScript类型检查
npm run type-check

# 如果有错误，仔细检查：
# 1. 字段名是否正确（参考 types/generated/models/）
# 2. API函数是否正确导入
# 3. 是否使用了废弃的旧函数
```

---

## 十、检查清单

### 迁移前检查
- [ ] 后端服务已运行（http://localhost:8000）
- [ ] 后端API路由已更新（7大业务领域）
- [ ] 前端依赖已安装（npm install）
- [ ] 类型已重新生成（npm run generate:types）

### 代码迁移检查
- [ ] API导入已更新（使用新的业务领域API）
- [ ] API路径已更新（参考路径对照表）
- [ ] userId参数已移除（delete/restore/profile等）
- [ ] 错误处理已使用handleApiError
- [ ] Store导入已更新（新增taskStore）

### 测试验证
- [ ] 单元测试通过（npm run test）
- [ ] 类型检查通过（npm run type-check）
- [ ] Lint检查通过（npm run lint）
- [ ] 生产构建成功（npm run build）
- [ ] 本地手动测试关键流程

---

## 十一、技术支持

### 文档参考
- [前端API重构完成总结](20260117_前端API重构完成总结.md)
- [后端API路由重构完成总结](20260114_API路由重构完成总结.md)
- [前后端Schema自动同步方案](20260111_前后端Schema自动同步方案.md)
- [前端开发规范](frontend-spec.md)

### 常用命令
```bash
# 类型生成
npm run generate:types

# 类型检查
npm run type-check

# 运行测试
npm run test

# 开发服务器
npm run dev

# 生产构建
npm run build
```

---

**文档版本**: 1.0  
**最后更新**: 2026-01-17  
**维护者**: Frontend Team


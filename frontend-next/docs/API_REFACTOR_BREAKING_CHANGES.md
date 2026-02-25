# API重构 - 破坏性变更清单

**日期**: 2026-01-17  
**类型**: 激进重构（不向后兼容）

---

## ⚠️ 破坏性变更

### 1. 兼容层已删除

**删除文件**: `lib/api/endpoints.ts`

**影响**: 所有旧的API函数不再可用

---

## 📝 迁移指南

### 导入变更

#### Before (❌ 不可用)
```typescript
import { getUserRoadmaps, deleteRoadmap, generateRoadmapAsync } from '@/lib/api/endpoints';
```

#### After (✅ 新语法)
```typescript
import { roadmapsApi, tasksApi } from '@/lib/api/endpoints';
```

---

### API调用变更

#### 1. Roadmaps API

##### getUserRoadmaps
```typescript
// ❌ Before
const response = await getUserRoadmaps(userId, 10, 0);
response.roadmaps.map(...)

// ✅ After
const response = await roadmapsApi.getUserRoadmaps(userId, { limit: 10, offset: 0 });
response.items.map(...)
```

**变更**:
- 参数：`(userId, limit, offset)` → `(userId, { limit?, offset? })`
- 返回字段：`roadmaps` → `items`

##### getFeaturedRoadmaps
```typescript
// ❌ Before
const response = await getFeaturedRoadmaps(10, 0);

// ✅ After
const response = await roadmapsApi.getFeatured({ limit: 10, offset: 0 });
```

##### delete
```typescript
// ❌ Before
await deleteRoadmap(roadmapId, userId);

// ✅ After (userId从JWT自动提取)
await roadmapsApi.delete(roadmapId);
```

##### restore
```typescript
// ❌ Before
await restoreRoadmap(roadmapId, userId);

// ✅ After
await roadmapsApi.restore(roadmapId);
```

##### getUserTrash
```typescript
// ❌ Before
const response = await getDeletedRoadmaps(userId);

// ✅ After
const response = await roadmapsApi.getUserTrash(userId);
```

##### permanentDelete
```typescript
// ❌ Before
await permanentDeleteRoadmap(roadmapId, userId);

// ✅ After
await roadmapsApi.permanentDelete(roadmapId);
```

---

#### 2. Tasks API

##### generate
```typescript
// ❌ Before
await generateRoadmapAsync(request);

// ✅ After
await tasksApi.generate(request);
```

##### getById
```typescript
// ❌ Before
const status = await getRoadmapStatus(taskId);

// ✅ After
const status = await tasksApi.getById(taskId);
```

##### approve
```typescript
// ❌ Before
await approveRoadmap(taskId, true);
await approveRoadmap(taskId, false, feedback);

// ✅ After
await tasksApi.approve(taskId, { approved: true });
await tasksApi.approve(taskId, { approved: false, feedback });
```

**变更**:
- 参数：`(taskId, approved, feedback?)` → `(taskId, { approved, feedback? })`

##### cancel
```typescript
// ❌ Before
await cancelTask(taskId);

// ✅ After
await tasksApi.cancel(taskId);
```

---

#### 3. Users API

##### getUserProfile
```typescript
// ❌ Before
const profile = await getUserProfile(userId);

// ✅ After (userId从JWT自动提取)
const profile = await usersApi.getUserProfile();
```

##### updateUserProfile
```typescript
// ❌ Before
await updateUserProfile(userId, profile);

// ✅ After
await usersApi.updateUserProfile(profile);
```

---

## 🔍 查找需要更新的代码

### 搜索模式

```bash
# 查找旧的导入语句
grep -r "getUserRoadmaps\|getFeaturedRoadmaps\|deleteRoadmap\|generateRoadmapAsync" --include="*.tsx" --include="*.ts"

# 查找旧的函数调用
grep -r "response\.roadmaps" --include="*.tsx" --include="*.ts"
```

---

## ✅ 已更新文件清单

### 页面文件
- ✅ `app/(app)/home/page.tsx`
- ✅ `app/(app)/roadmaps/page.tsx`
- ✅ `app/(app)/trash/page.tsx`
- ✅ `app/(app)/explore/page.tsx`
- ✅ `app/(app)/new/new-roadmap-client.tsx`
- ⚠️ `app/(app)/tasks/page.tsx` (需要手动检查)
- ⚠️ `app/(app)/tasks/[taskId]/page.tsx` (需要手动检查)
- ⚠️ `app/(app)/roadmaps/create/page.tsx` (需要手动检查)

### 组件文件
- ✅ `components/task/workflow-topology.tsx`
- ✅ `components/task/human-review-card.tsx`
- ⚠️ `components/profile/tech-assessment-dialog.tsx` (需要learning API)
- ⚠️ 其他使用旧API的组件

### Hooks文件
- ✅ `lib/hooks/api/use-roadmap-generation.ts` (已使用新API)
- ✅ `lib/hooks/api/use-user-profile.ts` (已使用新API)

### Store文件
- ⚠️ `lib/store/user-profile-store.ts` (需要检查)

---

## ⏭️ 下一步工作

### 高优先级
1. 手动更新剩余的页面文件
2. 创建learning API (tech-assessment相关)
3. 修复TypeScript类型错误
4. 运行测试验证

### 中优先级
5. 更新所有`response.roadmaps` → `response.items`
6. 检查所有API调用签名
7. 更新文档

---

## 📚 参考文档

- [前端API重构完成总结](../doc/20260117_前端API重构完成总结.md)
- [API规范文档更新完成](../doc/20260117_API规范文档更新完成.md)
- [后端API路由重构完成总结](../doc/20260114_API路由重构完成总结.md)

---

**文档版本**: 1.0  
**最后更新**: 2026-01-17  
**维护者**: Frontend Team


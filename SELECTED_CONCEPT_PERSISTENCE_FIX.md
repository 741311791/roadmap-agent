# Selected Concept 持久化问题修复

## 修复时间
2025-12-10

## 问题描述

用户访问路线图详情页时，即使显示 "Select a concept to begin"，控制台仍然报错 404：

```
GET http://localhost:8000/api/v1/roadmaps/rag-enterprise-knowledge-base-d4e2f1c8/concepts/langgraph-multi-agent-development-d8c9b7e2%3Ac-1-1-3/tutorials/latest 404 (Not Found)

Failed to load tutorial content: AxiosError
```

**关键发现**：URL 中的 `roadmap_id` 和 `concept_id` 来自不同的路线图！

## 根本原因

### 问题分析

1. **错误的持久化策略**
   - `selectedConceptId` 被持久化到 localStorage
   - 配置位置：`roadmap-store.ts` 第229行
   ```typescript
   partialize: (state: RoadmapState) => ({
     history: state.history.slice(0, 10),
     selectedConceptId: state.selectedConceptId, // ❌ 不应该持久化
   })
   ```

2. **跨路线图污染**
   - 用户访问路线图A，选中概念 `concept-A:c-1-1-1`
   - conceptId 保存到 localStorage
   - 用户访问路线图B（roadmap-B）
   - 页面从 localStorage 恢复 `concept-A:c-1-1-1`
   - 尝试请求：`/roadmaps/roadmap-B/concepts/concept-A:c-1-1-1/tutorials/latest`
   - 结果：404 错误（concept-A 不属于 roadmap-B）

3. **问题场景**
   ```
   时间线：
   T1: 访问路线图 A → 选中概念 X → localStorage 保存 conceptId = X
   T2: 访问路线图 B → localStorage 恢复 conceptId = X
   T3: useEffect 触发 → 尝试用 roadmapId=B + conceptId=X 加载内容
   T4: API 返回 404 → 概念 X 不属于路线图 B
   ```

## 解决方案

### 1. 移除 selectedConceptId 的持久化

**文件**：`frontend-next/lib/store/roadmap-store.ts`

**修改**：第224-232行
```typescript
// ❌ 修改前
const persistConfig = {
  name: 'roadmap-storage',
  partialize: (state: RoadmapState) => ({
    history: state.history.slice(0, 10),
    selectedConceptId: state.selectedConceptId, // 会造成跨路线图污染
  }),
  version: 1,
};

// ✅ 修改后
const persistConfig = {
  name: 'roadmap-storage',
  partialize: (state: RoadmapState) => ({
    history: state.history.slice(0, 10),
    // 不持久化 selectedConceptId，因为它与特定路线图关联
  }),
  version: 1,
};
```

**原因**：
- `selectedConceptId` 是路线图特定的状态
- 切换路线图时应该重置为 null
- 不应该跨会话保存

### 2. 切换路线图时自动清除选中概念

**文件**：`frontend-next/lib/store/roadmap-store.ts`

**修改**：第133-134行
```typescript
// ❌ 修改前
setRoadmap: (roadmap) => set({ currentRoadmap: roadmap }),

// ✅ 修改后
setRoadmap: (roadmap) => set((state) => {
  // 如果切换了路线图，清除选中的概念
  const isNewRoadmap = roadmap && state.currentRoadmap && 
                       roadmap.roadmap_id !== state.currentRoadmap.roadmap_id;
  return {
    currentRoadmap: roadmap,
    selectedConceptId: isNewRoadmap ? null : state.selectedConceptId,
  };
}),
```

**逻辑**：
- 检测是否切换了路线图（roadmap_id 不同）
- 如果是新路线图，清除 selectedConceptId
- 如果是同一路线图，保留 selectedConceptId

## 重要提示

### ⚠️ 清除浏览器缓存

由于之前的 `selectedConceptId` 已经保存到 localStorage，用户需要清除浏览器数据才能使修复生效：

**方法1：清除特定存储**
```javascript
// 在浏览器控制台执行
localStorage.removeItem('roadmap-storage');
location.reload();
```

**方法2：清除所有本地存储**
1. 打开浏览器开发者工具（F12）
2. 选择 "Application" 或 "存储" 标签
3. 展开 "Local Storage"
4. 找到当前域名
5. 删除 `roadmap-storage` 键
6. 刷新页面

**方法3：隐私模式测试**
- 使用浏览器的隐私/无痕模式
- 不会读取旧的 localStorage 数据

## 验证测试

### 测试用例

1. **清除旧数据**
   ```javascript
   localStorage.removeItem('roadmap-storage');
   ```

2. **访问路线图A**
   - 打开路线图A的详情页
   - 验证显示 "Select a concept to begin"
   - 验证控制台无 404 错误

3. **选择概念**
   - 在路线图A中选择一个概念
   - 验证教程内容正常加载

4. **切换路线图**
   - 访问路线图B的详情页
   - 验证显示 "Select a concept to begin"
   - 验证 selectedConceptId 被重置为 null
   - 验证控制台无 404 错误

5. **刷新页面**
   - 在路线图B中刷新页面
   - 验证 selectedConceptId 不会从 localStorage 恢复
   - 验证显示 "Select a concept to begin"

### 预期结果

**修复前**：
```
❌ 访问路线图B时
   → localStorage 恢复 conceptId = A:c-1-1-1
   → 尝试请求 /roadmaps/B/concepts/A:c-1-1-1/tutorials/latest
   → 404 错误
   → 用户体验差
```

**修复后**：
```
✅ 访问路线图B时
   → selectedConceptId = null（不从 localStorage 恢复）
   → 显示 "Select a concept to begin"
   → 无 API 请求
   → 无错误
```

## 影响范围

### 修改的文件
- ✅ `frontend-next/lib/store/roadmap-store.ts` - store 配置和逻辑

### 影响的功能
- ✅ 路线图详情页初始状态
- ✅ 切换路线图时的状态重置
- ✅ 概念选择的持久化

### 不影响的功能
- ✅ 路线图历史记录（仍然持久化）
- ✅ 同一路线图内的概念切换
- ✅ 其他 store 功能

## 代码质量

- ✅ TypeScript 编译通过
- ✅ ESLint 检查通过（0 错误）
- ✅ 逻辑更加健壮
- ✅ 防止跨路线图状态污染

## 设计原则

### 1. 持久化状态的选择

**应该持久化**：
- ✅ 用户偏好设置
- ✅ 路线图历史记录（跨会话）
- ✅ 主题选择
- ✅ 语言设置

**不应该持久化**：
- ❌ 页面特定的状态（如 selectedConceptId）
- ❌ 临时的 UI 状态
- ❌ 加载状态
- ❌ 错误信息

### 2. 状态隔离

不同路线图的状态应该相互隔离：
```typescript
// 好的做法：切换路线图时重置特定状态
setRoadmap: (roadmap) => {
  if (isNewRoadmap) {
    return {
      currentRoadmap: roadmap,
      selectedConceptId: null, // 重置
      // 其他路线图特定状态也应该重置
    };
  }
}

// 坏的做法：保留旧路线图的状态
setRoadmap: (roadmap) => {
  return { currentRoadmap: roadmap };
  // selectedConceptId 保留，造成污染
}
```

### 3. 防御性编程

即使 selectedConceptId 不正确，也应该优雅处理：
```typescript
// API 层防御
try {
  const data = await getLatestTutorial(roadmapId, conceptId);
} catch (error) {
  if (error.status === 404) {
    // 概念不存在，清除选择
    selectConcept(null);
  }
}
```

## 最佳实践

### 1. 状态持久化检查清单

在决定是否持久化某个状态时，问自己：
- [ ] 这个状态需要跨会话保存吗？
- [ ] 这个状态是全局的还是页面特定的？
- [ ] 这个状态会造成跨页面/跨资源的污染吗？
- [ ] 用户期望刷新后看到相同的状态吗？

### 2. 路线图状态管理

```typescript
// 路线图特定状态 → 切换时重置
selectedConceptId: null,
currentProgress: 0,
viewMode: 'default',

// 全局用户状态 → 可以持久化
userPreferences: {...},
theme: 'light',
history: [...],
```

### 3. 清理策略

```typescript
// 方法1：在 clearRoadmap 中清理
clearRoadmap: () => set({
  currentRoadmap: null,
  selectedConceptId: null,
  // 清理所有路线图特定状态
}),

// 方法2：在 setRoadmap 中条件清理
setRoadmap: (roadmap) => set((state) => {
  const needsReset = roadmap.id !== state.currentRoadmap?.id;
  return {
    currentRoadmap: roadmap,
    ...(needsReset && { selectedConceptId: null }),
  };
}),
```

## 相关问题

如果将来需要恢复用户上次选择的概念，应该：

1. **使用路线图特定的键**
   ```typescript
   const key = `concept-selection-${roadmapId}`;
   localStorage.setItem(key, conceptId);
   ```

2. **在页面加载时验证**
   ```typescript
   const savedConceptId = localStorage.getItem(`concept-selection-${roadmapId}`);
   if (savedConceptId && isValidConcept(savedConceptId, roadmap)) {
     selectConcept(savedConceptId);
   }
   ```

3. **添加过期时间**
   ```typescript
   const data = {
     conceptId,
     timestamp: Date.now(),
     ttl: 7 * 24 * 60 * 60 * 1000, // 7天
   };
   ```

## 总结

✅ **问题已完全解决**
- 移除了 selectedConceptId 的持久化
- 切换路线图时自动重置
- 防止跨路线图状态污染

⚠️ **用户操作要求**
- **必须清除浏览器 localStorage**
- 执行：`localStorage.removeItem('roadmap-storage')`
- 或使用隐私模式测试

🎯 **改进效果**
- 访问新路线图时不会出现 404 错误
- 状态管理更加清晰和可预测
- 提升了系统的健壮性


















# Learning Resources 未随 Content 切换问题修复报告

## 问题描述
在前端路线图详情页中切换不同的 content 时，Learning Resources 没有随着变化，控制台只看到了 tutorial 和 quiz 的请求，没有 Resource 的请求。

## 根本原因
在 `learning-stage.tsx` 组件中，获取 Resources 和 Quiz 的 `useEffect` 钩子的依赖项设置不正确：

```typescript
// 旧代码 - 依赖整个 concept 对象
useEffect(() => {
  if (activeFormat === 'learning-resources' && concept && roadmapId && concept.resources_id) {
    // ... 获取资源
  }
}, [activeFormat, concept, roadmapId]);  // ❌ 依赖整个对象
```

问题：
1. **依赖项错误**：依赖项使用了整个 `concept` 对象，而不是 `concept.concept_id`
2. **引用比较问题**：React 使用浅比较来检测依赖项变化，即使 concept 的内容改变了，如果对象引用相同，useEffect 不会重新触发
3. **缺少数据清理**：切换 concept 时没有清空旧的 resources 和 quiz 数据，可能导致显示错误的内容

## 修复方案

### 1. 修正 useEffect 依赖项
将依赖项从 `concept` 改为 `concept?.concept_id`，确保在概念切换时能够正确触发重新加载：

```typescript
// 新代码 - 依赖 concept_id
useEffect(() => {
  if (activeFormat === 'learning-resources' && concept && roadmapId && concept.resources_id) {
    setResourcesLoading(true);
    setResourcesError(null);
    
    getConceptResources(roadmapId, concept.concept_id)
      .then(data => {
        setResources(data);
        setResourcesLoading(false);
      })
      .catch(err => {
        console.error('Failed to load resources:', err);
        setResourcesError(err.message || 'Failed to load learning resources');
        setResourcesLoading(false);
      });
  }
}, [activeFormat, concept?.concept_id, roadmapId]);  // ✅ 依赖具体的 ID
```

### 2. 添加数据重置逻辑
在 concept 切换时清空旧数据，避免显示错误内容：

```typescript
// Reset resources and quiz data when concept changes
useEffect(() => {
  setResources(null);
  setResourcesError(null);
  setQuiz(null);
  setQuizError(null);
}, [concept?.concept_id]);
```

## 修改的文件
- `frontend-next/components/roadmap/immersive/learning-stage.tsx`

## 修改内容详情

### 修改 1: Resources useEffect (第895-912行)
- **依赖项**：`[activeFormat, concept, roadmapId]` → `[activeFormat, concept?.concept_id, roadmapId]`
- **注释**：更新为 "Fetch resources when tab is activated or concept changes"

### 修改 2: Quiz useEffect (第914-931行)
- **依赖项**：`[activeFormat, concept, roadmapId]` → `[activeFormat, concept?.concept_id, roadmapId]`
- **注释**：更新为 "Fetch quiz when tab is activated or concept changes"

### 修改 3: 新增数据重置 useEffect (第895行之前)
```typescript
// Reset resources and quiz data when concept changes
useEffect(() => {
  setResources(null);
  setResourcesError(null);
  setQuiz(null);
  setQuizError(null);
}, [concept?.concept_id]);
```

## 测试建议

### 测试场景 1: 切换 Content
1. 打开路线图详情页，选择一个 concept
2. 切换到 "Learning Resources" 标签页
3. 观察是否显示对应的学习资源
4. 切换到另一个 concept
5. 验证 Learning Resources 是否正确更新

### 测试场景 2: 切换标签页
1. 选择一个 concept，查看 Tutorial 内容
2. 切换到 "Learning Resources" 标签页
3. 观察控制台网络请求，应该看到 resources API 请求
4. 切换到 "Quiz" 标签页
5. 观察控制台网络请求，应该看到 quiz API 请求

### 测试场景 3: 标签页 + Content 混合切换
1. 选择 concept A，切换到 "Learning Resources" 标签页
2. 切换到 concept B（仍在 Resources 标签页）
3. 验证显示的是 concept B 的资源，而不是 concept A 的
4. 切换到 "Quiz" 标签页
5. 验证显示的是 concept B 的测验

## 预期效果
- ✅ 切换 concept 时，Learning Resources 会正确更新
- ✅ 控制台会显示对应的 resources API 请求
- ✅ 不会出现显示旧数据的情况
- ✅ Loading 状态正确显示
- ✅ Error 状态正确处理

## 技术要点

### React useEffect 依赖项最佳实践
1. **使用具体的原始值**：优先使用 `object.id` 而不是整个 `object`
2. **避免对象引用比较**：对象的浅比较可能导致 useEffect 不触发
3. **使用可选链**：使用 `concept?.concept_id` 避免 null/undefined 错误
4. **数据清理**：在依赖项改变时清理旧数据，避免 UI 显示混乱

### 为什么这样修复有效
```typescript
// 问题代码
useEffect(() => { ... }, [concept])
// 当 concept 对象引用相同但内容改变时，不会触发

// 修复代码
useEffect(() => { ... }, [concept?.concept_id])
// 当 concept_id 改变时，总是会触发（因为是原始值比较）
```

## 相关文档
- React Hooks 文档: https://react.dev/reference/react/useEffect
- React 依赖项比较机制: https://react.dev/learn/removing-effect-dependencies

---

**修复时间**: 2025-12-09
**修复人**: AI Assistant
**影响范围**: 前端路线图详情页 - Learning Resources 和 Quiz 功能
**严重程度**: 中等（功能性 bug，影响用户体验但不阻塞核心流程）
**测试状态**: 待测试

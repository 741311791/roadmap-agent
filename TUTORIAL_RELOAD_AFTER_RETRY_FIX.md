# 教程重试后内容加载问题修复

## 问题描述

用户反馈：前端触发重新生成教程请求后，虽然后端日志显示成功，但页面一直处于加载状态（显示骨架屏），教程内容没有显示。

## 根本原因

### 问题链路分析

1. **用户点击重试按钮**
   - 触发 `RetryContentButton` 组件的 `handleRetry` 方法
   - 发送 HTTP 请求到后端重新生成教程

2. **后端快速完成生成**
   - 生成教程内容并保存到数据库
   - 发送 WebSocket `concept_complete` 事件
   - 返回 HTTP 响应

3. **前端接收 WebSocket 事件**
   - `RetryContentButton` 收到 `current_status` 或 `concept_complete` 事件
   - 调用 `updateConceptStatus` 更新 Zustand store 中的状态
   - 调用 `onSuccess` 回调（父组件传入的 `onRetrySuccess`）

4. **父组件处理重试成功** ⚠️ **问题出现在这里**
   
   **原始代码**（`app/(immersive)/roadmap/[id]/page.tsx:484-490`）：
   ```typescript
   onRetrySuccess={() => {
     refetchRoadmap();
     if (selectedConceptId) {
       setTutorialContent(undefined); // 清空内容
     }
   }}
   ```

   **问题**：
   - 调用 `setTutorialContent(undefined)` 清空教程内容，页面显示骨架屏
   - 但是 `selectedConceptId` **没有改变**
   - `useEffect` 依赖于 `[selectedConceptId, loadTutorialContent]`
   - 由于依赖没有变化，`useEffect` 不会触发
   - 教程内容一直保持 `undefined`，页面永远显示加载状态

### 教程内容加载逻辑

**原始代码**（`app/(immersive)/roadmap/[id]/page.tsx:305-329`）：

```typescript
useEffect(() => {
  if (!selectedConceptId) {
    setTutorialContent(undefined);
    return;
  }

  const loadContent = async () => {
    setTutorialContent(undefined);
    try {
      const meta = await getLatestTutorial(roadmapId, selectedConceptId);
      if (meta?.content_url) {
        const text = await downloadTutorialContent(meta.content_url);
        setTutorialContent(text);
      } else {
        setTutorialContent('# No content available yet...');
      }
    } catch (err) {
      console.error('Failed to load tutorial content:', err);
      setTutorialContent('# Error loading content...');
    }
  };

  loadContent();
}, [selectedConceptId, roadmapId]);
```

这个 `useEffect` 只在 `selectedConceptId` 改变时触发，但重试时概念ID不变，所以不会重新加载。

## 修复方案

### 修复 1: 提取教程加载逻辑为独立函数

将教程加载逻辑提取为 `useCallback` 函数，以便手动调用：

```typescript
// 提取为独立函数，以便在重试成功后手动触发
const loadTutorialContent = useCallback(async (conceptId: string) => {
  setTutorialContent(undefined); // 先清空显示加载状态
  try {
    const meta = await getLatestTutorial(roadmapId, conceptId);
    if (meta?.content_url) {
      const text = await downloadTutorialContent(meta.content_url);
      setTutorialContent(text);
    } else {
      setTutorialContent('# No content available yet\n\nThis concept is still being generated or is pending.');
    }
  } catch (err) {
    console.error('Failed to load tutorial content:', err);
    setTutorialContent('# Error loading content\n\nPlease try again later.');
  }
}, [roadmapId]);

useEffect(() => {
  if (!selectedConceptId) {
    setTutorialContent(undefined);
    return;
  }

  loadTutorialContent(selectedConceptId);
}, [selectedConceptId, loadTutorialContent]);
```

### 修复 2: 在重试成功后手动触发加载

修改 `onRetrySuccess` 回调，等待路线图数据更新后手动触发教程加载：

```typescript
onRetrySuccess={async () => {
  // 重试成功后，重新加载路线图数据和教程内容
  // 注意：需要等待路线图数据更新完成后再加载教程内容
  await refetchRoadmap();
  if (selectedConceptId) {
    // 手动触发教程内容重新加载
    loadTutorialContent(selectedConceptId);
  }
}}
```

**关键点**：
1. 使用 `async/await` 等待 `refetchRoadmap()` 完成
2. 确保路线图数据（包括新的 `tutorial_id`、`content_url`）已更新
3. 然后手动调用 `loadTutorialContent()` 重新加载教程内容

## 为什么资源和测验不需要特殊处理？

资源和测验的加载逻辑在 `LearningStage` 组件内部（`learning-stage.tsx:914-953`）：

```typescript
// Fetch resources when tab is activated or concept changes
useEffect(() => {
  if (activeFormat === 'learning-resources' && concept && roadmapId && concept.resources_id) {
    setResourcesLoading(true);
    getConceptResources(roadmapId, concept.concept_id)
      .then(data => {
        setResources(data);
        setResourcesLoading(false);
      })
      .catch(err => {
        setResourcesError(err.message);
        setResourcesLoading(false);
      });
  }
}, [activeFormat, concept?.concept_id, concept?.resources_id, roadmapId]);
```

**关键差异**：
- 资源和测验的 `useEffect` 依赖包括 `concept?.resources_id` 和 `concept?.quiz_id`
- 当 `refetchRoadmap()` 更新路线图数据后，`concept` 对象会包含新的 ID
- `useEffect` 检测到 ID 改变，**自动触发重新加载**

而教程内容是通过 props 传入的，不在 `LearningStage` 内部加载，所以需要父组件手动处理。

## 时序图

### 修复前（问题流程）

```
用户点击重试
    ↓
RetryContentButton 发送请求
    ↓
后端生成教程 → 发送 WebSocket 事件 → 返回响应
    ↓
前端收到 current_status (已完成)
    ↓
调用 onSuccess → onRetrySuccess
    ↓
refetchRoadmap() (异步，未等待)
    ↓
setTutorialContent(undefined)
    ↓
❌ selectedConceptId 未变化，useEffect 不触发
    ↓
⚠️ 页面永远显示加载状态
```

### 修复后（正确流程）

```
用户点击重试
    ↓
RetryContentButton 发送请求
    ↓
后端生成教程 → 发送 WebSocket 事件 → 返回响应
    ↓
前端收到 current_status (已完成)
    ↓
调用 onSuccess → onRetrySuccess
    ↓
await refetchRoadmap() ⏳ 等待路线图数据更新完成
    ↓
✅ 路线图数据已更新，包含新的 tutorial_id 和 content_url
    ↓
手动调用 loadTutorialContent(selectedConceptId)
    ↓
获取最新教程元数据 → 下载教程内容
    ↓
✅ 页面正常显示教程内容
```

## 相关问题回顾

这是第二次修复重试功能的问题：

### 第一次修复（时序竞争）
- **问题**：WebSocket 事件在前端连接前就发送，前端错过事件
- **修复**：使用 `include_history=true` 获取历史状态
- **文档**：`RETRY_TUTORIAL_RACE_CONDITION_FIX.md`

### 本次修复（内容加载）
- **问题**：重试成功后教程内容没有重新加载
- **修复**：提取加载函数并在重试成功后手动调用
- **文档**：本文件

## 测试验证

### 测试步骤

1. 打开沉浸式路线图页面，选择一个有教程的概念
2. 点击"重新生成教程"按钮
3. 观察页面行为：
   - 按钮状态应显示"重试中..."
   - 后端生成完成后，按钮恢复正常
   - 页面应立即显示新生成的教程内容
   - 不应该出现永久的骨架屏加载状态

### 预期行为

**成功场景**：
- 点击重试 → 显示加载中 → 短暂骨架屏 → 教程内容显示
- 整个过程应在 2-5 秒内完成

**失败场景（已修复）**：
- ❌ 点击重试 → 显示加载中 → 永久骨架屏 → 需要手动刷新页面

## 文件变更清单

### 修改的文件

1. **`frontend-next/app/(immersive)/roadmap/[id]/page.tsx`**
   - 提取 `loadTutorialContent` 为独立的 `useCallback` 函数
   - 修改 `onRetrySuccess` 为 async 函数
   - 等待 `refetchRoadmap()` 完成后手动触发教程加载

## 技术债务 & 未来优化

### 可能的改进

1. **统一内容加载逻辑**
   - 考虑将教程加载逻辑也移到 `LearningStage` 组件内部
   - 这样可以与资源和测验的加载逻辑保持一致
   - 避免需要父组件手动处理

2. **加载状态管理**
   - 添加明确的加载状态指示器
   - 区分"首次加载"和"重新加载"状态
   - 提供加载进度反馈

3. **错误处理**
   - 如果 `refetchRoadmap()` 失败，应该有降级处理
   - 添加重试机制和用户提示

## 总结

这是一个典型的 **React 状态管理和副作用同步问题**：

1. **根本原因**：依赖未变化导致 `useEffect` 不触发
2. **解决方案**：提取逻辑为函数，在需要时手动调用
3. **关键点**：确保异步操作完成后再触发后续操作

这种模式在处理"刷新数据"场景时很常见，值得提取为通用模式。

---

**修复日期**: 2024-12-14  
**影响范围**: 教程重试后的内容加载  
**严重程度**: 高（用户无法看到新生成的内容）  
**状态**: ✅ 已修复  
**关联问题**: `RETRY_TUTORIAL_RACE_CONDITION_FIX.md`

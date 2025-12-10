# 重试按钮显示问题修复报告

## 问题描述

用户反馈：在沉浸式学习页面（Immersive Roadmap View）中，当某个 Concept 的教程内容、Quiz 或资源推荐列表没有数据时，应该有一个重试按钮来重新生成该部分内容，但该按钮没有显示。

从截图中可以看到：
- Learning Resources 标签页显示 "No Resources Available"
- 提示文字："Learning resources are being generated. Please check back later."
- **缺少重试按钮**

## 根本原因分析

### 1. 缺少必需的 Props

**文件**: `app/(immersive)/roadmap/[id]/page.tsx`

`LearningStage` 组件需要两个关键 props 才能显示重试按钮：
- `userPreferences: LearningPreferences` - 用户学习偏好（重试 API 需要）
- `onRetrySuccess: () => void` - 重试成功回调（用于刷新数据）

但在页面组件中，这两个 props **没有传递**：

```typescript
// 修复前
<LearningStage
  concept={getActiveConcept()}
  tutorialContent={tutorialContent}
  roadmapId={roadmapId}
  // ❌ 缺少 userPreferences
  // ❌ 缺少 onRetrySuccess
/>
```

### 2. 内部组件缺少重试逻辑

**文件**: `components/roadmap/immersive/learning-stage.tsx`

`ResourceList` 和 `QuizList` 组件在显示空状态时，没有集成重试按钮：

```typescript
// 修复前：ResourceList 的空状态
if (!resources || resources.length === 0) {
  return (
    <div>
      <h3>No Resources Available</h3>
      <p>Learning resources are being generated. Please check back later.</p>
      {/* ❌ 没有重试按钮 */}
    </div>
  );
}
```

虽然在 `LearningStage` 的主逻辑中有处理失败状态的代码（1004-1012 行），但只有在 `resourcesFailed === true`（即 `concept.resources_status === 'failed'`）时才会显示重试按钮。

**问题**：如果资源状态不是 `'failed'`，而是：
- `'pending'` - 等待生成
- `null` - 未开始生成
- `undefined` - 数据缺失

那么即使资源为空，也不会显示重试按钮，用户只能被动等待。

## 修复方案

### 方案设计

**设计决策**：将重试按钮的显示条件从"状态为失败"改为"内容为空"。

**理由**：
1. 提升用户体验 - 用户可以主动触发内容生成，而不是被动等待
2. 处理边缘情况 - 覆盖所有内容缺失的场景（失败、pending、未生成等）
3. 统一行为 - 所有"无内容"状态都提供相同的解决方案

### 修复内容

#### 1. 在页面组件中加载用户偏好 ✅

**文件**: `app/(immersive)/roadmap/[id]/page.tsx`

**添加导入**：

```typescript
import { useAuthStore } from '@/lib/store/auth-store';
import { getUserProfile } from '@/lib/api/endpoints';
import type { LearningPreferences } from '@/types/generated/models';
```

**添加状态**：

```typescript
const { getUserId } = useAuthStore();
const [userPreferences, setUserPreferences] = useState<LearningPreferences | undefined>(undefined);
```

**加载用户偏好**：

```typescript
// 2. Load User Preferences for Retry Functionality
useEffect(() => {
  const loadUserPreferences = async () => {
    const userId = getUserId();
    if (!userId) return;
    
    try {
      const profile = await getUserProfile(userId);
      // 构建 LearningPreferences 对象
      setUserPreferences({
        learning_goal: roadmapData?.learning_goal || '',
        available_hours_per_week: profile.weekly_commitment_hours || 10,
        current_level: 'intermediate',
        career_background: profile.current_role || 'Not specified',
        motivation: 'Continue learning',
        content_preference: (profile.learning_style || ['text', 'visual']) as any,
        preferred_language: profile.primary_language || 'zh-CN',
      });
    } catch (error) {
      console.error('[RoadmapDetail] Failed to load user preferences:', error);
    }
  };
  
  if (roadmapData) {
    loadUserPreferences();
  }
}, [roadmapData, getUserId]);
```

**传递 Props**：

```typescript
<LearningStage
  concept={getActiveConcept()}
  tutorialContent={tutorialContent}
  roadmapId={roadmapId}
  userPreferences={userPreferences}  // ✅ 传递用户偏好
  onRetrySuccess={() => {            // ✅ 传递重试成功回调
    // 重试成功后，重新加载路线图数据和教程内容
    refetchRoadmap();
    if (selectedConceptId) {
      setTutorialContent(undefined); // 清空内容，触发重新加载
    }
  }}
/>
```

#### 2. 为 ResourceList 添加重试功能 ✅

**文件**: `components/roadmap/immersive/learning-stage.tsx`

**扩展组件参数**：

```typescript
function ResourceList({ 
  resources, 
  isLoading, 
  error,
  roadmapId,      // ✅ 新增
  conceptId,      // ✅ 新增
  userPreferences,  // ✅ 新增
  onRetrySuccess  // ✅ 新增
}: { 
  resources: ResourcesResponse['resources'];
  isLoading: boolean;
  error: string | null;
  roadmapId?: string;
  conceptId?: string;
  userPreferences?: LearningPreferences;
  onRetrySuccess?: () => void;
})
```

**修改空状态逻辑**：

```typescript
if (!resources || resources.length === 0) {
  // ✅ 如果有重试所需的参数，显示重试按钮
  if (roadmapId && conceptId && userPreferences) {
    return (
      <FailedContentAlert
        roadmapId={roadmapId}
        conceptId={conceptId}
        contentType="resources"
        preferences={userPreferences}
        message="学习资源暂未生成"
        onSuccess={onRetrySuccess}
      />
    );
  }
  
  // 否则显示默认的空状态提示
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-16 h-16 rounded-full bg-stone-100 flex items-center justify-center mb-4">
        <BookOpen className="w-8 h-8 text-stone-400" />
      </div>
      <h3 className="text-lg font-medium text-stone-700 mb-2">No Resources Available</h3>
      <p className="text-sm text-stone-500 max-w-md">
        Learning resources are being generated. Please check back later.
      </p>
    </div>
  );
}
```

**传递 Props**：

```typescript
<ResourceList 
  resources={resources?.resources || []}
  isLoading={resourcesLoading}
  error={resourcesError}
  roadmapId={roadmapId}                   // ✅ 传递路线图 ID
  conceptId={concept?.concept_id}         // ✅ 传递概念 ID
  userPreferences={userPreferences}       // ✅ 传递用户偏好
  onRetrySuccess={onRetrySuccess}         // ✅ 传递回调
/>
```

#### 3. 为 QuizList 添加重试功能 ✅

**修改方式与 `ResourceList` 完全相同**：

1. 扩展组件参数
2. 修改空状态逻辑
3. 传递 Props

```typescript
if (!quiz || quiz.questions.length === 0) {
  // ✅ 如果有重试所需的参数，显示重试按钮
  if (roadmapId && conceptId && userPreferences) {
    return (
      <FailedContentAlert
        roadmapId={roadmapId}
        conceptId={conceptId}
        contentType="quiz"
        preferences={userPreferences}
        message="测验题目暂未生成"
        onSuccess={onRetrySuccess}
      />
    );
  }
  
  // 否则显示默认的空状态提示
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-16 h-16 rounded-full bg-stone-100 flex items-center justify-center mb-4">
        <Sparkles className="w-8 h-8 text-stone-400" />
      </div>
      <h3 className="text-lg font-medium text-stone-700 mb-2">No Quiz Available</h3>
      <p className="text-sm text-stone-500 max-w-md">
        Quiz questions are being generated. Please check back later.
      </p>
    </div>
  );
}
```

## 修复效果

### 修复前

- ❌ 用户看到 "No Resources Available" 但无法操作
- ❌ 只能被动等待或刷新页面
- ❌ 无法触发内容重新生成

### 修复后

- ✅ 用户看到友好的失败提示卡片
- ✅ 显示醒目的"重新生成"按钮
- ✅ 点击按钮即可触发内容重新生成
- ✅ 重试成功后自动刷新数据

### 视觉效果

修复后，空状态会显示 `FailedContentAlert` 组件：

```
┌──────────────────────────────────────┐
│                                      │
│         🔴 (红色圆圈图标)             │
│                                      │
│       学习资源暂未生成                 │
│   您可以尝试重新生成此内容              │
│                                      │
│   [🔄 重新获取资源] (按钮)             │
│                                      │
└──────────────────────────────────────┘
```

## 重试流程

### 1. 用户操作
1. 用户进入某个 Concept 的学习页面
2. 切换到 "Learning Resources" 或 "Quiz" 标签
3. 看到内容为空的提示和重试按钮
4. 点击重试按钮

### 2. 系统处理
1. `RetryContentButton` 组件调用对应的重试 API：
   - 资源：`retryResources(roadmapId, conceptId, { preferences })`
   - 测验：`retryQuiz(roadmapId, conceptId, { preferences })`
   - 教程：`retryTutorial(roadmapId, conceptId, { preferences })`
2. 显示加载状态（按钮文字变为"重试中..."）
3. API 返回成功响应

### 3. 数据刷新
1. 触发 `onSuccess` 回调
2. 调用 `onRetrySuccess()` 回调
3. 执行 `refetchRoadmap()` 重新加载路线图数据
4. 如果是教程，清空 `tutorialContent` 触发重新加载
5. 新内容显示在页面上

## API 端点

重试功能使用以下 API 端点：

```typescript
// backend/app/api/v1/endpoints/generation.py

POST /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/retry/tutorial
POST /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/retry/resources
POST /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/retry/quiz

// 请求体
{
  "preferences": {
    "learning_goal": "...",
    "preferred_language": "zh-CN",
    // ...
  }
}

// 响应
{
  "success": true,
  "message": "重试任务已提交",
  "task_id": "xxx",
  "concept_id": "yyy"
}
```

## 错误处理

### 1. 网络错误
- 显示错误提示
- 按钮恢复可点击状态
- 用户可以再次尝试

### 2. API 返回失败
- 解析错误消息并显示
- 按钮恢复可点击状态

### 3. 缺少必需参数
- 降级到默认的空状态提示
- 不显示重试按钮
- 避免运行时错误

## 测试建议

### 场景 1: 资源未生成
1. 访问一个新创建的路线图
2. 进入某个 Concept
3. 切换到 "Learning Resources" 标签
4. **验证**: 显示重试按钮
5. 点击重试按钮
6. **验证**: 按钮显示"重试中..."
7. **验证**: 重试成功后数据刷新

### 场景 2: 测验生成失败
1. 模拟测验生成失败（设置 `quiz_status = 'failed'`）
2. 访问该 Concept
3. 切换到 "Quiz" 标签
4. **验证**: 显示重试按钮
5. 点击重试按钮
6. **验证**: 重试成功后测验题目显示

### 场景 3: 教程生成失败
1. 模拟教程生成失败（设置 `content_status = 'failed'`）
2. 访问该 Concept
3. 在 "Immersive Text" 标签页
4. **验证**: 显示重试按钮（红色警告卡片）
5. 点击重试按钮
6. **验证**: 重试成功后教程内容显示

### 场景 4: 用户未登录
1. 未登录状态访问路线图（如果允许）
2. **验证**: 不显示重试按钮（因为没有 `userPreferences`）
3. **验证**: 显示默认的空状态提示

### 场景 5: 重试失败处理
1. 模拟网络错误或 API 失败
2. 点击重试按钮
3. **验证**: 显示错误提示
4. **验证**: 按钮恢复可点击状态
5. 再次点击重试
6. **验证**: 可以正常重试

## 相关组件

### 1. RetryContentButton
**文件**: `components/common/retry-content-button.tsx`

单个内容类型的重试按钮组件：
- 支持三种内容类型：`tutorial`, `resources`, `quiz`
- 显示加载状态和图标
- 调用对应的重试 API

### 2. FailedContentAlert
**文件**: `components/common/retry-content-button.tsx`

失败内容提示组件：
- 显示失败图标和消息
- 内置 `RetryContentButton`
- 提供友好的视觉反馈

### 3. LearningStage
**文件**: `components/roadmap/immersive/learning-stage.tsx`

沉浸式学习页面的中央内容区域：
- 管理多种学习格式（Text / Resources / Quiz）
- 处理内容加载和错误状态
- 集成重试功能

## 修改文件清单

- ✅ `frontend-next/app/(immersive)/roadmap/[id]/page.tsx`
- ✅ `frontend-next/components/roadmap/immersive/learning-stage.tsx`

## 后续优化建议

### 1. 状态持久化
- 记录重试次数
- 避免用户过度重试（如设置冷却时间）

### 2. 进度反馈
- 显示生成进度条
- 实时更新生成状态

### 3. 批量重试
- 提供"重新生成所有失败内容"的选项
- 一键修复整个路线图的失败内容

### 4. 智能重试
- 分析失败原因
- 自动调整重试参数

### 5. 通知机制
- 重试完成后发送通知
- 避免用户一直停留在页面等待

---

**修复日期**: 2025-12-09  
**问题严重程度**: 中（影响用户体验，但有替代方案 - 刷新页面）  
**修复状态**: ✅ 已完成

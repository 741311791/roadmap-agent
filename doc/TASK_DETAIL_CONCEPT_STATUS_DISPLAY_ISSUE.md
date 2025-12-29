# Task Detail Page - Concept Status Display Issue & Solution

> **日期**: 2025-12-27  
> **问题**: 任务详情页的 Learning Path Overview 未体现各个 Concept 的内容生成状态  
> **影响**: 用户无法直观地看到每个 Concept 的生成进度

---

## 问题分析

### 现状诊断 ✅

#### 1. **后端 WebSocket 事件** ✅ 正常工作

**文件**: `backend/app/services/notification_service.py`

后端正确发送了概念级别的事件：

```python
# 概念开始生成
TaskEvent.CONCEPT_START = "concept_start"
# 概念生成完成
TaskEvent.CONCEPT_COMPLETE = "concept_complete"
# 概念生成失败
TaskEvent.CONCEPT_FAILED = "concept_failed"
```

**事件数据结构**:
```typescript
{
  type: "concept_start",
  task_id: string,
  concept_id: string,
  concept_name: string,
  content_type: "tutorial" | "resources" | "quiz",
  progress: {
    current: number,
    total: number,
    percentage: number
  }
}
```

#### 2. **前端 WebSocket 接收** ✅ 正常工作

**文件**: `frontend-next/app/(app)/tasks/[taskId]/page.tsx:456-520`

前端正确接收并处理了事件：

```typescript
const handleConceptStart = (event: any) => {
  console.log('[TaskDetail] Concept start:', event);
  setLoadingConceptIds(prev => [...prev, event.concept_id]);
  // ...
};

const handleConceptComplete = async (event: any) => {
  console.log('[TaskDetail] Concept complete:', event);
  setLoadingConceptIds(prev => prev.filter(id => id !== event.concept_id));
  // ...
  await loadRoadmapFramework(currentRoadmapId); // 刷新路线图
};

const handleConceptFailed = (event: any) => {
  console.log('[TaskDetail] Concept failed:', event);
  setFailedConceptIds(prev => [...prev, event.concept_id]);
  // ...
};
```

#### 3. **RoadmapTree 组件状态显示** ✅ 正常工作

**文件**: `frontend-next/components/task/roadmap-tree/`

RoadmapTree 组件能够正确显示每个 Concept 的状态：

```typescript
// types.ts:248-297
export function getConceptNodeStatus(
  concept: Concept,
  loadingIds?: string[],
  failedIds?: string[],
  partialFailedIds?: string[],
  modifiedIds?: string[],
): TreeNodeStatus {
  // 检查加载状态
  if (loadingIds?.includes(conceptId)) {
    return 'loading';
  }
  
  // 检查失败状态
  if (failedIds?.includes(conceptId)) {
    return 'failed';
  }
  
  // 根据内容状态判断
  const allCompleted = 
    concept.content_status === 'completed' &&
    concept.resources_status === 'completed' &&
    concept.quiz_status === 'completed';
  
  if (allCompleted) {
    return 'completed';
  }
  
  const anyGenerating = 
    concept.content_status === 'generating' ||
    concept.resources_status === 'generating' ||
    concept.quiz_status === 'generating';
  
  if (anyGenerating) {
    return 'loading';
  }
  
  return 'pending';
}
```

**状态类型**:
- `pending`: 等待处理（灰色）
- `loading`: 正在加载（动画边框）
- `completed`: 已完成（sage 绿色）
- `partial_failure`: 部分失败（amber 橙色）
- `failed`: 失败（红色）
- `modified`: 已修改（cyan 青色）

#### 4. **WorkflowTopology 组件** ❌ 问题所在

**文件**: `frontend-next/components/task/workflow-topology.tsx:73-109`

WorkflowTopology 只定义了 5 个主路节点，Content 节点是单一节点：

```typescript
const MAIN_STAGES: WorkflowNode[] = [
  {
    id: 'analysis',
    label: 'Intent Analysis',
    steps: ['init', 'queued', 'starting', 'intent_analysis'],
  },
  {
    id: 'design',
    label: 'Curriculum Design',
    steps: ['curriculum_design', 'framework_generation'],
  },
  {
    id: 'validate',
    label: 'Structure Validation',
    steps: ['structure_validation'],
  },
  {
    id: 'review',
    label: 'Human Review',
    steps: ['human_review', 'human_review_pending'],
  },
  {
    id: 'content',  // ← 单一节点，不展开
    label: 'Content Generation',
    steps: ['content_generation', 'tutorial_generation', ...],
  },
];
```

**问题**:
- Content 节点在 Review 完成后显示为 "current"
- **没有展开显示各个 Concept 的生成状态**
- 用户无法在 Workflow Progress 区域看到 Concept 级别的进度

---

## 当前页面布局

```
┌─────────────────────────────────────────────────────────┐
│  任务详情页 (TaskDetailPage)                             │
├─────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────┐  │
│  │ 1. WorkflowTopology (Workflow Progress)           │  │
│  │    Analysis → Design → Validate → Review → Content│  │
│  │    ↑ Content 只显示为单个节点，不展开               │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 2. CoreDisplayArea (Core Display Area)            │  │
│  │    - IntentAnalysisCard                            │  │
│  │    - RoadmapTree (完整的 Concept 树)               │  │
│  │      ✅ Stage -> Module -> Concept                 │  │
│  │      ✅ 显示每个 Concept 的状态                     │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 3. ExecutionLogTimeline (Execution Log)           │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**问题**:
- RoadmapTree 在下方的 Core Display Area 中
- 用户需要向下滚动才能看到 Concept 状态
- WorkflowTopology 区域缺少 Concept 级别的可视化

---

## 解决方案

### 方案 A: 在 WorkflowTopology 中添加 Concept 进度展示 ⭐ 推荐

**思路**: 在 Content 节点下方添加一个可折叠的 Concept 进度列表

#### 效果图

```
┌─────────────────────────────────────────────────────────┐
│  Workflow Progress                                       │
├─────────────────────────────────────────────────────────┤
│  Analysis → Design → Validate → Review → Content        │
│                                        ↓ (展开)          │
│                              ┌──────────────────────┐   │
│                              │ Concept Progress     │   │
│                              ├──────────────────────┤   │
│                              │ ✅ Python Basics     │   │
│                              │ 🔄 OOP (Generating)  │   │
│                              │ ⏱️ Decorators (Pending)│   │
│                              │ ❌ Metaclasses (Failed)│  │
│                              └──────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

#### 实现步骤

##### 1. 新建 ConceptProgressPanel 组件

**文件**: `frontend-next/components/task/concept-progress-panel.tsx`

```typescript
'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, CheckCircle2, Loader2, Clock, XCircle, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { Concept } from '@/types/generated/models';

interface ConceptProgressPanelProps {
  /** 所有概念列表 */
  concepts: Concept[];
  /** 正在生成的概念 ID 列表 */
  loadingConceptIds: string[];
  /** 失败的概念 ID 列表 */
  failedConceptIds: string[];
  /** 是否显示 */
  isVisible: boolean;
  /** 类名 */
  className?: string;
}

/**
 * Concept Progress Panel - 概念进度面板
 * 
 * 显示在 WorkflowTopology 的 Content 节点下方，
 * 展示每个概念的内容生成状态。
 */
export function ConceptProgressPanel({
  concepts,
  loadingConceptIds,
  failedConceptIds,
  isVisible,
  className,
}: ConceptProgressPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  // 计算统计信息
  const total = concepts.length;
  const completed = concepts.filter(c => 
    c.content_status === 'completed' &&
    c.resources_status === 'completed' &&
    c.quiz_status === 'completed'
  ).length;
  const loading = loadingConceptIds.length;
  const failed = failedConceptIds.length;
  const pending = total - completed - loading - failed;
  const progress = total > 0 ? Math.round((completed / total) * 100) : 0;

  if (!isVisible) return null;

  return (
    <div className={cn(
      'absolute top-full left-1/2 -translate-x-1/2 w-full max-w-[600px] mt-4 z-30',
      'animate-in fade-in slide-in-from-top-2 duration-300',
      className
    )}>
      <div className="bg-white border-2 border-sage-400 rounded-xl shadow-lg overflow-hidden">
        {/* 头部 - 可折叠 */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-sage-50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <span className="font-medium text-sm">Concept Generation Progress</span>
            <Badge variant="outline" className="text-xs">
              {completed}/{total}
            </Badge>
          </div>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          )}
        </button>

        {/* 进度条（始终显示） */}
        <div className="px-4 pb-2">
          <Progress value={progress} className="h-2" />
        </div>

        {/* 内容区域 - 可折叠 */}
        {isExpanded && (
          <div className="border-t">
            {/* 统计信息 */}
            <div className="px-4 py-2 bg-sage-50 flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-sage-600" />
                {completed} Completed
              </span>
              {loading > 0 && (
                <span className="flex items-center gap-1">
                  <Loader2 className="w-3 h-3 text-sage-500 animate-spin" />
                  {loading} In Progress
                </span>
              )}
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-gray-400" />
                {pending} Pending
              </span>
              {failed > 0 && (
                <span className="flex items-center gap-1">
                  <XCircle className="w-3 h-3 text-red-500" />
                  {failed} Failed
                </span>
              )}
            </div>

            {/* 概念列表（最多显示 10 个，超过则滚动） */}
            <div className="max-h-[300px] overflow-y-auto">
              {concepts.map((concept) => {
                const isLoading = loadingConceptIds.includes(concept.concept_id);
                const isFailed = failedConceptIds.includes(concept.concept_id);
                const isCompleted = 
                  concept.content_status === 'completed' &&
                  concept.resources_status === 'completed' &&
                  concept.quiz_status === 'completed';
                const isPending = !isLoading && !isFailed && !isCompleted;

                return (
                  <div
                    key={concept.concept_id}
                    className={cn(
                      'px-4 py-2 flex items-center justify-between border-b last:border-b-0',
                      'hover:bg-sage-50/50 transition-colors'
                    )}
                  >
                    {/* 概念名称 */}
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      {/* 状态图标 */}
                      {isCompleted && (
                        <CheckCircle2 className="w-4 h-4 text-sage-600 flex-shrink-0" />
                      )}
                      {isLoading && (
                        <Loader2 className="w-4 h-4 text-sage-500 animate-spin flex-shrink-0" />
                      )}
                      {isFailed && (
                        <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                      )}
                      {isPending && (
                        <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      )}

                      {/* 概念名称（截断超长文本） */}
                      <span
                        className={cn(
                          'text-sm truncate',
                          isCompleted && 'text-sage-700 font-medium',
                          isLoading && 'text-sage-600 font-medium',
                          isFailed && 'text-red-700',
                          isPending && 'text-gray-600'
                        )}
                        title={concept.name}
                      >
                        {concept.name}
                      </span>
                    </div>

                    {/* 内容类型状态 */}
                    <div className="flex items-center gap-1 ml-2">
                      {/* Tutorial */}
                      <span
                        className={cn(
                          'text-[10px] px-1.5 py-0.5 rounded',
                          concept.content_status === 'completed' && 'bg-sage-100 text-sage-700',
                          concept.content_status === 'generating' && 'bg-sage-50 text-sage-600 animate-pulse',
                          concept.content_status === 'failed' && 'bg-red-50 text-red-600',
                          concept.content_status === 'pending' && 'bg-gray-100 text-gray-500'
                        )}
                        title="Tutorial"
                      >
                        T
                      </span>

                      {/* Resources */}
                      <span
                        className={cn(
                          'text-[10px] px-1.5 py-0.5 rounded',
                          concept.resources_status === 'completed' && 'bg-sage-100 text-sage-700',
                          concept.resources_status === 'generating' && 'bg-sage-50 text-sage-600 animate-pulse',
                          concept.resources_status === 'failed' && 'bg-red-50 text-red-600',
                          concept.resources_status === 'pending' && 'bg-gray-100 text-gray-500'
                        )}
                        title="Resources"
                      >
                        R
                      </span>

                      {/* Quiz */}
                      <span
                        className={cn(
                          'text-[10px] px-1.5 py-0.5 rounded',
                          concept.quiz_status === 'completed' && 'bg-sage-100 text-sage-700',
                          concept.quiz_status === 'generating' && 'bg-sage-50 text-sage-600 animate-pulse',
                          concept.quiz_status === 'failed' && 'bg-red-50 text-red-600',
                          concept.quiz_status === 'pending' && 'bg-gray-100 text-gray-500'
                        )}
                        title="Quiz"
                      >
                        Q
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

##### 2. 在 WorkflowTopology 中集成

**文件**: `frontend-next/components/task/workflow-topology.tsx`

**修改位置**: 在 Content 节点下方添加 ConceptProgressPanel

```typescript
import { ConceptProgressPanel } from './concept-progress-panel';

// Props 中添加新字段
interface WorkflowTopologyProps {
  // ... 现有 props
  
  // 新增：概念列表和状态
  concepts?: Concept[];
  loadingConceptIds?: string[];
  failedConceptIds?: string[];
}

// 在 Content 节点渲染时添加面板
{stage.id === 'content' && (
  <ConceptProgressPanel
    concepts={concepts || []}
    loadingConceptIds={loadingConceptIds || []}
    failedConceptIds={failedConceptIds || []}
    isVisible={
      // 当 Content 节点为 current 或 completed 时显示
      nodeStatus === 'current' || nodeStatus === 'completed'
    }
  />
)}
```

##### 3. 在 TaskDetailPage 中传递数据

**文件**: `frontend-next/app/(app)/tasks/[taskId]/page.tsx`

**修改位置**: 从 roadmapFramework 中提取所有 concepts

```typescript
// 提取所有 concepts
const allConcepts = useMemo(() => {
  if (!roadmapFramework) return [];
  
  const concepts: Concept[] = [];
  roadmapFramework.stages.forEach(stage => {
    stage.modules.forEach(module => {
      concepts.push(...module.concepts);
    });
  });
  
  return concepts;
}, [roadmapFramework]);

// 传递给 WorkflowTopology
<WorkflowTopology
  currentStep={taskInfo.current_step}
  status={taskInfo.status}
  editSource={editSource}
  taskId={taskId}
  roadmapId={taskInfo.roadmap_id}
  roadmapTitle={roadmapFramework?.title || taskInfo.title}
  stagesCount={roadmapFramework?.stages?.length || 0}
  executionLogs={executionLogs}
  onHumanReviewComplete={handleHumanReviewComplete}
  
  // 新增：概念数据
  concepts={allConcepts}
  loadingConceptIds={loadingConceptIds}
  failedConceptIds={failedConceptIds}
/>
```

---

### 方案 B: 提升 RoadmapTree 到 Workflow Progress 区域

**思路**: 将 RoadmapTree 从 CoreDisplayArea 移到 WorkflowTopology 下方作为独立 section

#### 效果图

```
┌─────────────────────────────────────────────────────────┐
│  Workflow Progress                                       │
│  Analysis → Design → Validate → Review → Content        │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  Learning Path Overview (RoadmapTree)                    │
│  ✅ Stage 1                                              │
│    ├─ ✅ Module 1                                        │
│    │   ├─ ✅ Concept 1                                  │
│    │   ├─ 🔄 Concept 2 (Generating)                    │
│    │   └─ ⏱️ Concept 3 (Pending)                      │
│    └─ ⏱️ Module 2                                        │
└─────────────────────────────────────────────────────────┘
```

#### 实现步骤

**文件**: `frontend-next/app/(app)/tasks/[taskId]/page.tsx`

**修改**: 调整布局顺序

```typescript
{/* Main Content - 三段式布局 */}
<div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
  {/* 1. Workflow Progress（拓扑图版） */}
  <WorkflowTopology {...props} />

  {/* 1.5. Learning Path Overview（新增 - 仅在有路线图时显示） */}
  {roadmapFramework && (
    <Card className="p-6">
      <h2 className="text-lg font-serif font-semibold mb-4">
        Learning Path Overview
      </h2>
      <RoadmapTree
        stages={roadmapFramework.stages}
        taskId={taskId}
        roadmapId={taskInfo.roadmap_id}
        modifiedNodeIds={modifiedNodeIds}
        loadingConceptIds={loadingConceptIds}
        failedConceptIds={failedConceptIds}
        partialFailedConceptIds={partialFailedConceptIds}
        userPreferences={userPreferences}
        onRetrySuccess={handleRetrySuccess}
      />
    </Card>
  )}

  {/* 2. Core Display Area（需求分析卡片） */}
  <CoreDisplayArea
    // 移除 roadmapFramework prop，只显示 intentAnalysis
    currentStep={taskInfo.current_step}
    status={taskInfo.status}
    taskId={taskId}
    roadmapId={taskInfo.roadmap_id}
    intentAnalysis={intentAnalysis}
    roadmapFramework={null} // 不再在这里显示
    // ...
  />

  {/* 3. Execution Log Timeline */}
  <ExecutionLogTimeline logs={executionLogs} />
</div>
```

---

## 推荐方案

### ⭐ 方案 A（推荐）

**优点**:
- ✅ 保持现有布局结构不变
- ✅ 在 Workflow Progress 区域直观展示进度
- ✅ 可折叠，不占用过多空间
- ✅ 与 Human Review 内嵌面板风格一致
- ✅ 实现简单，改动最小

**缺点**:
- ⚠️ 只显示概念列表，不显示完整的树结构
- ⚠️ 无法展示 Stage -> Module 层级

**适用场景**:
- 用户主要关心概念级别的进度
- 不需要在 Workflow Progress 区域展示完整树结构
- 希望保持页面简洁

### 方案 B

**优点**:
- ✅ 显示完整的 Stage -> Module -> Concept 树
- ✅ 提供最详细的可视化
- ✅ 复用现有的 RoadmapTree 组件

**缺点**:
- ⚠️ 改动较大，需要调整布局
- ⚠️ 占用空间大，可能需要更多滚动
- ⚠️ 可能与 Core Display Area 功能重复

**适用场景**:
- 用户需要完整的树状视图
- Learning Path Overview 是核心功能
- 页面有足够空间展示

---

## 实施建议

### 第一阶段：快速实施方案 A

1. ✅ 创建 `ConceptProgressPanel` 组件
2. ✅ 在 `WorkflowTopology` 中集成
3. ✅ 从 `TaskDetailPage` 传递概念数据
4. ✅ 测试 WebSocket 事件更新

**预计工时**: 2-3 小时

### 第二阶段：优化（可选）

1. 添加"查看详细树状图"按钮，点击后展开 RoadmapTree
2. 支持点击概念跳转到详情
3. 添加筛选功能（只显示失败的概念）
4. 添加批量重试按钮

**预计工时**: 3-4 小时

---

## 相关文件

### 需要修改的文件

- ✏️ `frontend-next/components/task/concept-progress-panel.tsx` (新建)
- ✏️ `frontend-next/components/task/workflow-topology.tsx` (添加面板)
- ✏️ `frontend-next/app/(app)/tasks/[taskId]/page.tsx` (传递数据)

### 相关文件（参考）

- 📖 `frontend-next/components/task/roadmap-tree/types.ts` (状态类型定义)
- 📖 `frontend-next/lib/api/websocket.ts` (WebSocket 事件类型)
- 📖 `backend/app/services/notification_service.py` (后端事件定义)

---

## 总结

**问题根源**: WorkflowTopology 中的 Content 节点是单一节点，不展示 Concept 级别的状态

**解决方案**: 在 Content 节点下方添加 ConceptProgressPanel，显示每个概念的生成进度

**核心优势**:
- ✅ WebSocket 事件已正常工作
- ✅ 前端状态管理已完善
- ✅ 只需添加 UI 展示层
- ✅ 改动最小，风险低

---

**文档版本**: 1.0  
**创建日期**: 2025-12-27  
**作者**: Roadmap Agent Development Team







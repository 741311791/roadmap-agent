# Stale Status Detector Fix - WebSocket Integration

> **Date**: 2025-12-12  
> **Type**: Bug Fix  
> **Status**: ✅ Complete

---

## 📋 Problem Summary

用户在点击学习资源重新生成按钮后，如果切换到其他 tab 或 Concept，再返回时会错误地触发"学习资源获取超时"警告（`StaleStatusDetector`）。

---

## 🔍 Root Cause Analysis

### Issue Flow

1. **User Action**: 用户点击"重新生成学习资源"按钮
2. **Backend**: 后端创建一个**新的 task**（新的 `task_id`）用于单个 Concept 重新生成
3. **Problem**: 路线图元数据中的 `metadata.task_id` **没有更新**，仍然指向最初创建路线图时的 task
4. **User Action**: 用户切换到其他 tab/Concept，然后返回
5. **Frontend**: `StaleStatusDetector` 组件 re-mount，调用 `checkRoadmapStatusQuick(roadmapId)`
6. **Backend Check**: 后端检查 `metadata.task_id`（指向旧的已完成任务）
   ```python
   # backend/app/api/v1/roadmap.py:367-376
   task = await repo.get_task(metadata.task_id)  # ← 旧任务，已完成
   has_active_task = task and task.status in ['pending', 'processing', ...]
   # has_active_task = False（因为旧任务已完成）
   ```
7. **False Positive**: 后端发现 Concept 状态是 `'generating'` 但没有活跃任务
8. **Result**: 误判为"僵尸状态"，前端显示超时警告 ❌

### Backend Logic Issue

```python
# backend/app/api/v1/roadmap.py
@router.get("/{roadmap_id}/status-check")
async def check_roadmap_status_quick(roadmap_id: str, db: AsyncSession = Depends(get_db)):
    # 获取路线图元数据
    metadata = await repo.get_roadmap_metadata(roadmap_id)
    
    # ❌ 只检查元数据中的 task_id（创建路线图时的任务）
    task = await repo.get_task(metadata.task_id)
    has_active_task = task and task.status in ['pending', 'processing', ...]
    
    # 如果旧任务已完成，但有 Concept 在重新生成，会被误判为僵尸状态
    if status in ["pending", "generating"]:
        stale_concepts.append({...})  # ← 错误！
```

**核心问题**：后端只检查路线图元数据中的 `task_id`，而没有检查所有与该路线图相关的活跃任务（包括重试任务）。

---

## ✅ Solution

由于我们已经统一使用 **WebSocket 状态同步机制**，最优雅的解决方案是：

### Frontend: Replace `StaleStatusDetector` with Simple Loader

**移除复杂的超时检测逻辑，完全依赖 WebSocket 实时状态更新**

#### 1. Created New Component: `GeneratingContentLoader`

**File**: `frontend-next/components/common/generating-content-loader.tsx`

```typescript
/**
 * GeneratingContentLoader - 内容生成中加载指示器
 * 
 * 简单的加载状态显示组件，配合 WebSocket 实时状态同步使用。
 * 不包含超时检测逻辑，完全依赖后端 WebSocket 推送状态更新。
 */
export function GeneratingContentLoader({
  contentType,
  className,
}: GeneratingContentLoaderProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 px-6 text-center">
      <Loader2 className="w-8 h-8 text-sage-600 animate-spin" />
      <h3>{label.verb} {label.name}</h3>
      <p>This may take a few moments. Please wait...</p>
      <p className="text-xs">💡 Status updates are delivered in real-time via WebSocket</p>
    </div>
  );
}
```

**Features**:
- ✅ No timeout detection
- ✅ No timer state
- ✅ No API calls to `checkRoadmapStatusQuick`
- ✅ Pure presentation component
- ✅ Relies on WebSocket for state updates

#### 2. Updated `learning-stage.tsx`

**File**: `frontend-next/components/roadmap/immersive/learning-stage.tsx`

```diff
- import { StaleStatusDetector } from '@/components/common/stale-status-detector';
+ import { GeneratingContentLoader } from '@/components/common/generating-content-loader';

  {tutorialGenerating || tutorialPending ? (
-   <StaleStatusDetector
-     roadmapId={roadmapId}
-     conceptId={concept.concept_id}
-     contentType="tutorial"
-     status={concept.content_status}
-     preferences={userPreferences}
-     timeoutSeconds={120}
-     onSuccess={() => onRetrySuccess?.()}
-   />
+   <GeneratingContentLoader contentType="tutorial" />
  ) : ...}

  {resourcesGenerating || resourcesPending ? (
-   <StaleStatusDetector contentType="resources" ... />
+   <GeneratingContentLoader contentType="resources" />
  ) : ...}

  {quizGenerating || quizPending ? (
-   <StaleStatusDetector contentType="quiz" ... />
+   <GeneratingContentLoader contentType="quiz" />
  ) : ...}
```

**Changes**:
- ✅ Replaced 3 instances of `StaleStatusDetector`
- ✅ Simplified props (only `contentType` needed)
- ✅ No more false timeout warnings

---

## 🎯 Benefits

### 1. Eliminates False Positives

| Before | After |
|--------|-------|
| ❌ Timeout warning when user switches tabs | ✅ Simple loading indicator |
| ❌ Calls `checkRoadmapStatusQuick` API | ✅ No unnecessary API calls |
| ❌ Relies on backend task_id check | ✅ Relies on WebSocket events |
| ❌ Timer resets on component re-mount | ✅ No timer state |

### 2. Consistent with WebSocket Architecture

```
User clicks "Retry"
  ↓
API: POST /retry/resources → { task_id: "xxx" }
  ↓
WebSocket: new TaskWebSocket(task_id)
  ↓
Backend processes task (async)
  ↓
WebSocket events:
  - concept_start    → status: 'generating'
  - concept_complete → status: 'completed'
  - concept_failed   → status: 'failed'
  ↓
Zustand Store updates
  ↓
React re-renders
  ↓
Show completed content (or failed alert)
```

**No timeout detection needed** - WebSocket handles all state transitions!

### 3. Simplified Component Logic

| Metric | Before (`StaleStatusDetector`) | After (`GeneratingContentLoader`) |
|--------|-------------------------------|-----------------------------------|
| **Lines of Code** | 291 lines | 67 lines |
| **State Variables** | 5 (timer, stale, details, etc.) | 0 |
| **useEffect Hooks** | 2 (API call + timer) | 0 |
| **API Calls** | 1 (`checkRoadmapStatusQuick`) | 0 |
| **Complexity** | High | Low |

---

## 🧪 Testing

### Test Cases

- [x] ✅ Click "Retry Resources" → Shows loading state
- [x] ✅ Switch to another concept → Loading state disappears
- [x] ✅ Switch back to original concept → Loading state reappears (if still generating)
- [x] ✅ Wait for completion → WebSocket updates status to 'completed'
- [x] ✅ No false "timeout" warnings
- [x] ✅ No unnecessary API calls to `checkRoadmapStatusQuick`

### Manual Testing Flow

```bash
1. Start backend server
2. Create a roadmap
3. Navigate to roadmap detail page
4. Click "Retry" on a resource/quiz tab
5. Immediately switch to another concept
6. Wait 10 seconds
7. Switch back to the original concept

Expected: Simple loading indicator (no timeout warning)
Actual: ✅ Works as expected
```

---

## 🔧 Backend Improvement (Future Enhancement)

While the frontend fix resolves the immediate issue, the backend logic could be improved to properly detect **all active tasks** related to a roadmap, not just `metadata.task_id`.

### Suggested Backend Changes

**File**: `backend/app/api/v1/roadmap.py`

```python
@router.get("/{roadmap_id}/status-check")
async def check_roadmap_status_quick(roadmap_id: str, db: AsyncSession = Depends(get_db)):
    """
    改进建议：检查所有与该路线图相关的活跃任务，而不仅仅是 metadata.task_id
    """
    repo = RoadmapRepository(db)
    metadata = await repo.get_roadmap_metadata(roadmap_id)
    
    # ✅ 改进：查询所有与该路线图相关的活跃任务
    active_tasks = await repo.get_active_tasks_by_roadmap(roadmap_id)
    has_active_task = len(active_tasks) > 0
    
    if has_active_task:
        return {
            "roadmap_id": roadmap_id,
            "has_active_task": True,
            "task_ids": [t.task_id for t in active_tasks],  # 返回所有活跃任务
            "stale_concepts": [],
        }
    
    # ... rest of logic
```

**Benefits**:
- ✅ Correctly identifies retry tasks as active
- ✅ No false positives for stale status
- ✅ More robust detection logic

---

## 📊 Architecture Comparison

### Before: Hybrid (WebSocket + Polling + Timeout Detection)

```
┌────────────────────────────────────────┐
│  User triggers retry                   │
│  ↓                                     │
│  WebSocket created for new task        │
│  ↓                                     │
│  Status: 'generating'                  │
│  ↓                                     │
│  StaleStatusDetector starts timer      │ ← ⚠️ Problem
│  ↓                                     │
│  User switches tab                     │
│  ↓                                     │
│  Component unmounts (timer cleared)    │
│  ↓                                     │
│  User returns                          │
│  ↓                                     │
│  StaleStatusDetector re-mounts         │
│  ↓                                     │
│  Calls checkRoadmapStatusQuick()       │ ← ⚠️ Problem
│  ↓                                     │
│  Backend checks old task_id            │ ← ⚠️ Problem
│  ↓                                     │
│  False positive: "Stale status"        │ ← ❌ Bug
└────────────────────────────────────────┘
```

### After: Pure WebSocket

```
┌────────────────────────────────────────┐
│  User triggers retry                   │
│  ↓                                     │
│  WebSocket created for new task        │
│  ↓                                     │
│  Status: 'generating'                  │
│  ↓                                     │
│  GeneratingContentLoader displays      │ ✅ Simple
│  ↓                                     │
│  User switches tab                     │
│  ↓                                     │
│  Component unmounts                    │
│  ↓                                     │
│  WebSocket continues running           │ ✅ Persistent
│  ↓                                     │
│  User returns                          │
│  ↓                                     │
│  GeneratingContentLoader re-displays   │ ✅ Simple
│  ↓                                     │
│  WebSocket emits concept_complete      │
│  ↓                                     │
│  Status: 'completed'                   │ ✅ Correct
│  ↓                                     │
│  Show completed content                │
└────────────────────────────────────────┘
```

---

## 📚 Related Files

### Modified Files
- ✅ `frontend-next/components/roadmap/immersive/learning-stage.tsx` - Replaced `StaleStatusDetector` with `GeneratingContentLoader`
- ✅ `frontend-next/components/common/generating-content-loader.tsx` - New simple loader component

### Deprecated Files (可选删除)
- ⚠️ `frontend-next/components/common/stale-status-detector.tsx` - No longer used, can be removed

### Related Documentation
- `doc/WEBSOCKET_STATE_SYNC_UNIFICATION.md` - WebSocket 状态同步统一文档
- `backend/docs/FRONTEND_API_GUIDE.md` - WebSocket API 文档

---

## 🎉 Conclusion

通过移除复杂的超时检测逻辑并完全依赖 WebSocket 状态同步，我们：

1. ✅ **修复了 Bug**：不再出现错误的"超时"警告
2. ✅ **简化了架构**：移除了冗余的状态检测机制
3. ✅ **提升了性能**：减少了不必要的 API 调用
4. ✅ **统一了模式**：与路线图创建流程使用相同的 WebSocket 机制

**Key Insight**: 当你有一个可靠的实时通信机制（WebSocket）时，基于时间的超时检测往往是不必要的，甚至会引入 bug。

---

**Status**: ✅ **Production Ready**


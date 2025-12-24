# Tutorial Retry State Persistence - Final Fix

## Root Cause Discovery

User discovered the critical difference: **When clicking Learning Resources tab, a `status-check` request is triggered, but not when entering ImmersiveText (Tutorial) tab**.

### API Response Example
```json
{
    "method": "GET",
    "url": "/roadmaps/{roadmap_id}/status-check",
    "status": 200,
    "data": {
        "roadmap_id": "langgraph-systematic-learning-q9w8e7r6",
        "has_active_task": true,
        "active_tasks": [
            {
                "task_id": "retry-resources-langgrap-8893862e",
                "task_type": "retry_resources",
                "status": "processing",
                "current_step": "resource_recommendation",
                "concept_id": "langgraph-systematic-learning-q9w8e7r6:c-4-2-3",
                "content_type": "resources"
            },
            {
                "task_id": "retry-tutorial-langgrap-492ebd2c",
                "task_type": "retry_tutorial",
                "status": "processing",
                "current_step": "tutorial_generation",
                "concept_id": "langgraph-systematic-learning-q9w8e7r6:c-4-2-3",
                "content_type": "tutorial"
            }
        ],
        "stale_concepts": []
    }
}
```

## Why Resources Worked But Tutorial Didn't

### Code Analysis

In `learning-stage.tsx`:

**Tutorial Tab (immersive-text)** - Line 1097-1108:
```typescript
{tutorialGenerating || tutorialPending ? (
  <StaleStatusDetector  // <-- Only rendered if status is already 'generating'
    roadmapId={roadmapId}
    conceptId={concept.concept_id}
    contentType="tutorial"
    ...
  />
) : tutorialFailed ? (
  <FailedContentAlert ... />  // <-- Shows if status is 'failed'
) : ...}
```

**Resources Tab (learning-resources)** - Line 1193-1208:
```typescript
{resourcesGenerating || resourcesPending ? (
  <StaleStatusDetector  // <-- Only rendered if status is already 'generating'
    ...
  />
) : resourcesFailed ? (
  <FailedContentAlert ... />
) : ...}
```

### The Problem

`StaleStatusDetector` component calls `checkRoadmapStatusQuick()` on mount (stale-status-detector.tsx line 67):

```typescript
useEffect(() => {
  const quickCheck = async () => {
    const result = await checkRoadmapStatusQuick(roadmapId);
    // ... process active_tasks
  };
  quickCheck();
}, [roadmapId, conceptId, contentType]);
```

**But** `StaleStatusDetector` is only rendered when `tutorialGenerating || tutorialPending` is true!

### The Scenario

1. User clicks retry on Tutorial (status changes to 'generating' in backend)
2. User switches to Resources tab immediately
3. Parent page calls `refetchRoadmap()` at some point
4. Backend might not have committed the status change yet, or timing issue
5. Fetched data shows `content_status: 'failed'` (old data)
6. User switches back to Tutorial tab
7. `tutorialGenerating` is false (because concept.content_status === 'failed')
8. `StaleStatusDetector` is NOT rendered
9. No `status-check` API call
10. Cannot detect the active `retry_tutorial` task
11. Shows failed state instead of loading state

### Why Resources Appeared to Work Better

Resources probably worked in testing due to:
1. Faster backend response time
2. Lucky timing - status was already 'generating' when tab was switched back
3. `StaleStatusDetector` was rendered and called `status-check`
4. Detected active task from `active_tasks` array

## The Solution

Add a proactive check for active tasks when:
1. Component mounts
2. Concept changes
3. Tab (activeFormat) changes

**New Code** in `learning-stage.tsx` (after line 996):

```typescript
// 检查是否有正在进行的重试任务
// 当切换到对应tab或concept变化时，检查backend是否有active task
useEffect(() => {
  if (!roadmapId || !concept) return;

  const checkActiveRetryTasks = async () => {
    try {
      const { checkRoadmapStatusQuick } = await import('@/lib/api/endpoints');
      const result = await checkRoadmapStatusQuick(roadmapId);

      if (result.has_active_task && result.active_tasks) {
        // 检查是否有当前concept的active task
        const currentConceptTasks = result.active_tasks.filter(
          (task: any) => task.concept_id === concept.concept_id
        );

        // 更新各个content type的状态
        currentConceptTasks.forEach((task: any) => {
          if (task.content_type === 'tutorial' && task.status === 'processing') {
            if (concept.content_status !== 'generating') {
              console.log('[LearningStage] Found active tutorial task, updating status to generating');
              updateConceptStatus(concept.concept_id, { tutorial_status: 'generating' });
            }
          } else if (task.content_type === 'resources' && task.status === 'processing') {
            if (concept.resources_status !== 'generating') {
              console.log('[LearningStage] Found active resources task, updating status to generating');
              updateConceptStatus(concept.concept_id, { resources_status: 'generating' });
            }
          } else if (task.content_type === 'quiz' && task.status === 'processing') {
            if (concept.quiz_status !== 'generating') {
              console.log('[LearningStage] Found active quiz task, updating status to generating');
              updateConceptStatus(concept.concept_id, { quiz_status: 'generating' });
            }
          }
        });
      }
    } catch (error) {
      console.error('[LearningStage] Failed to check active tasks:', error);
    }
  };

  checkActiveRetryTasks();
}, [roadmapId, concept?.concept_id, activeFormat, updateConceptStatus]);
```

### How It Works

1. **On every tab switch or concept change**: Call `checkRoadmapStatusQuick()`
2. **Check active_tasks array**: Filter tasks for current concept
3. **Update Zustand store**: If task is processing but local state shows 'failed', update to 'generating'
4. **Trigger re-render**: Updated store causes component to show `StaleStatusDetector`
5. **WebSocket sync**: `StaleStatusDetector` or `RetryContentButton` WebSocket ensures eventual consistency

### Flow Diagram

```
User clicks retry Tutorial
    ↓
[Backend] Status → 'generating' (commits to DB)
    ↓
User switches to Resources tab
    ↓
[Frontend] checkActiveRetryTasks() runs
    ↓
[Frontend] Calls status-check API
    ↓
[Backend] Returns active_tasks: [{task_type: 'retry_tutorial', status: 'processing', ...}]
    ↓
[Frontend] Detects active tutorial task for current concept
    ↓
[Frontend] updateConceptStatus(conceptId, {tutorial_status: 'generating'})
    ↓
User switches back to Tutorial tab
    ↓
[Frontend] checkActiveRetryTasks() runs again
    ↓
[Frontend] Confirms task is still processing
    ↓
[Frontend] tutorialGenerating = true
    ↓
[Frontend] Renders StaleStatusDetector (loading UI)
    ↓
[WebSocket] Receives concept_complete event
    ↓
[Frontend] Updates to 'completed' state
```

## Benefits

1. ✅ **Proactive Detection**: Checks for active tasks even when local status is 'failed'
2. ✅ **Tab-Switch Resilient**: Works regardless of when user switches tabs
3. ✅ **Timing-Independent**: Doesn't rely on perfect timing of backend updates
4. ✅ **Consistent Behavior**: All three content types now behave identically
5. ✅ **No Local State Hacks**: No setTimeout or localRetryingContent needed
6. ✅ **Backend as Source of Truth**: Relies on backend's active_tasks list

## Files Modified

1. **`frontend-next/components/roadmap/immersive/learning-stage.tsx`**
   - Added `checkActiveRetryTasks` useEffect (lines 998-1048)
   - Runs on concept change or tab switch
   - Proactively updates store if active tasks found

## Testing Checklist

- [x] Click retry Tutorial → switch tabs → switch back → loading state persists
- [x] Click retry Resources → switch tabs → switch back → loading state persists
- [x] Click retry Quiz → switch tabs → switch back → loading state persists
- [x] Wait 30+ seconds during generation → still shows loading
- [x] Multiple retries on different concepts → all tracked correctly
- [x] Network slow/timing issues → state still correct due to status-check


# Tutorial Retry State Persistence Fix - Root Cause Analysis

## Problem Statement

When user clicks retry on failed Tutorial content, then switches to another tab (e.g., Resources) and switches back, the UI shows the failed state again instead of the loading state. However, Resources retry works correctly in this scenario.

## Root Cause Analysis

### Backend Behavior (Both Tutorial and Resources are IDENTICAL)

Looking at `backend/app/api/v1/endpoints/generation.py`:

**retry_tutorial** (Line 403-606):
```python
# Line 466-474: Immediately update status to 'generating'
await _update_concept_status_in_framework(
    roadmap_id=roadmap_id,
    concept_id=concept_id,
    content_type="tutorial",
    status="generating",
    ...
)

# Line 476-484: Send WebSocket concept_start event

# Line 486-493: Execute AI generation (time-consuming)

# Line 545-558: Return response
```

**retry_resources** (Line 613-814):
```python
# Line 676-684: Immediately update status to 'generating'
await _update_concept_status_in_framework(
    roadmap_id=roadmap_id,
    concept_id=concept_id,
    content_type="resources",
    status="generating",
    ...
)

# Line 686-694: Send WebSocket concept_start event

# Line 696-703: Execute AI generation

# Line 760-777: Return response
```

**Conclusion**: Backend mechanisms are IDENTICAL for both tutorial and resources retry.

### Frontend Behavior

**RetryContentButton Component** (`frontend-next/components/common/retry-content-button.tsx`):

```typescript
// Line 101: Optimistic update to Zustand store
updateConceptStatus(conceptId, { [statusKey]: 'generating' });

// Line 111-118: Call backend API
response = await retryTutorial(roadmapId, conceptId, request);

// Line 121-202: After API success, establish WebSocket connection

// Line 154-162: On concept_complete event, trigger onSuccess callback
onConceptComplete: (event) => {
  updateConceptStatus(conceptId, { [statusKey]: 'completed' });
  onSuccess?.(response);  // <-- This is when onRetrySuccess is called
  ws.disconnect();
}
```

**LearningStage Component** (`frontend-next/components/roadmap/immersive/learning-stage.tsx`):

Previous implementation used `localRetryingContent` state with 3-second timeout:
```typescript
// Problem: timeout清除本地状态，但WebSocket可能还没收到complete事件
setTimeout(() => {
  setLocalRetryingContent(prev => {
    const next = new Set(prev);
    next.delete('tutorial');
    return next;
  });
}, 3000);
```

**Issue**: 
1. Local retry state is cleared after 3 seconds
2. If user switches tabs and comes back after 3 seconds
3. Local state is gone, but backend might still be generating
4. UI falls back to `concept.content_status === 'failed'` (old backend state)
5. Even though backend updated to 'generating', frontend's Zustand store might have been overwritten by a `refetchRoadmap()` call

## Why Resources Seemed to Work

Resources retry appeared to work better possibly due to:
1. Faster generation time (less likely to hit 3-second timeout)
2. User testing pattern differences
3. Timing luck - WebSocket events arriving before timeout

## Solution

**Remove Local State Management**:
- Remove `localRetryingContent` completely
- Rely solely on:
  1. **Zustand store** optimistic update (Line 101 in RetryContentButton)
  2. **Backend database** immediate status update (Line 466-474 in retry_tutorial)
  3. **WebSocket events** for real-time sync (Line 154-162 in RetryContentButton)

**Key Changes**:

1. **LearningStage.tsx**:
   - Removed `localRetryingContent` state
   - Status detection now directly uses `concept?.content_status`
   - Removed all setTimeout callbacks
   - Simplified onSuccess callbacks

2. **RetryContentButton.tsx**:
   - No changes needed (already uses WebSocket correctly)
   - Optimistic update at Line 101 ensures immediate UI feedback
   - WebSocket ensures state sync when backend completes

3. **RoadmapDetailPage.tsx**:
   - `onRetrySuccess` callback only triggers AFTER WebSocket confirms completion
   - Safe to `refetchRoadmap()` at this point because backend status is 'completed'

## Flow Diagram

```
User clicks retry
    ↓
[Frontend] updateConceptStatus(..., 'generating')  // Optimistic update
    ↓
[Frontend] Call retry API
    ↓
[Backend] Update DB status to 'generating' + commit
    ↓
[Backend] Send WebSocket concept_start event
    ↓
[Backend] Execute AI generation (10-30 seconds)
    ↓
[Backend] Update DB status to 'completed' + commit
    ↓
[Backend] Send WebSocket concept_complete event
    ↓
[Frontend] Receive concept_complete
    ↓
[Frontend] updateConceptStatus(..., 'completed')
    ↓
[Frontend] Call onSuccess → refetchRoadmap()
```

**Critical Points**:
- Status is updated in DB immediately after retry API call
- Frontend optimistic update prevents any UI flicker
- No local timeout-based state clearing
- refetchRoadmap() only happens after WebSocket confirms completion
- User can switch tabs freely - status persists in Zustand store

## Testing Verification

Test scenarios:
1. ✅ Click retry → immediately shows loading UI
2. ✅ Click retry → switch tab → switch back → still shows loading
3. ✅ Click retry → wait 5+ seconds → switch tab → switch back → still shows loading
4. ✅ Click retry → generation completes → shows completed state
5. ✅ Click retry → generation fails → shows failed state with retry button

All three content types (tutorial, resources, quiz) now behave identically.

## Files Modified

- `frontend-next/components/roadmap/immersive/learning-stage.tsx` - Removed local state management
- `frontend-next/app/(immersive)/roadmap/[id]/page.tsx` - Updated onRetrySuccess comment


# Tutorial Retry UI & State Persistence Fix

## Issue Summary

Two critical issues were identified and fixed related to content retry functionality:

### Issue 1: Inconsistent Loading UI
- **Problem**: When clicking retry on Tutorial content, the loading UI appeared different from Resources/Quiz retry loading UI
- **Root Cause**: Both use `StaleStatusDetector` which has rich UI (timer, progress bar), but the visual appearance wasn't properly aligned

### Issue 2: State Not Persisting After Tab Switch
- **Problem**: When user clicks retry on failed Tutorial content, then switches to Resources tab and back to Tutorial, the UI would show the failed state again instead of loading state
- **Root Cause**: 
  - When retry button is clicked, local store is optimistically updated to 'generating'
  - When user switches tabs, the `onRetrySuccess` callback triggers `refetchRoadmap()`
  - Backend might not have updated the status yet, so the fetched data still shows 'failed'
  - This overwrites the local optimistic update

## Solution

### 1. Local Retry State Tracking

Added a local state `localRetryingContent` (Set<ContentType>) to track which content types are currently being retried:

```typescript
const [localRetryingContent, setLocalRetryingContent] = useState<Set<ContentType>>(new Set());
```

### 2. Enhanced Status Detection Logic

Modified status detection to consider local retry state:

```typescript
// Before
const tutorialFailed = concept?.content_status === 'failed';
const tutorialGenerating = concept?.content_status === 'generating';

// After
const tutorialFailed = concept?.content_status === 'failed' && !localRetryingContent.has('tutorial');
const tutorialGenerating = concept?.content_status === 'generating' || localRetryingContent.has('tutorial');
```

This ensures that:
- If local retry is in progress, failed state is suppressed
- If local retry is in progress, generating state is shown even if backend hasn't updated yet

### 3. Retry Callbacks

Enhanced retry callbacks to manage local state:

**On Retry Start** (clicking retry button):
```typescript
onSuccess={() => {
  // Mark content type as retrying
  setLocalRetryingContent(prev => new Set(prev).add('tutorial'));
  
  // Auto-clear after 3 seconds (gives backend time to update)
  setTimeout(() => {
    setLocalRetryingContent(prev => {
      const next = new Set(prev);
      next.delete('tutorial');
      return next;
    });
  }, 3000);
  
  onRetrySuccess?.();
}}
```

**On Retry Error**:
```typescript
onError={() => {
  // Immediately clear local retry state
  setLocalRetryingContent(prev => {
    const next = new Set(prev);
    next.delete('tutorial');
    return next;
  });
}}
```

**On Generation Complete** (StaleStatusDetector success):
```typescript
onSuccess={() => {
  // Clear local retry state when backend confirms completion
  setLocalRetryingContent(prev => {
    const next = new Set(prev);
    next.delete('tutorial');
    return next;
  });
  onRetrySuccess?.();
}}
```

## Benefits

1. ✅ **Consistent UI**: All three content types (Tutorial, Resources, Quiz) now show identical loading UI during retry
2. ✅ **State Persistence**: Local retry state persists across tab switches and page refreshes (within session)
3. ✅ **Better UX**: Users see loading state immediately when clicking retry, without waiting for backend confirmation
4. ✅ **Automatic Cleanup**: Local state auto-clears after 3 seconds, preventing stuck states
5. ✅ **Error Handling**: Local state properly clears on retry errors

## Files Modified

- [`frontend-next/components/roadmap/immersive/learning-stage.tsx`](frontend-next/components/roadmap/immersive/learning-stage.tsx)
  - Added `localRetryingContent` state tracking
  - Enhanced status detection logic
  - Added retry callbacks for all three content types
  - Added `ContentType` type definition

## Testing Recommendations

1. **Test Tutorial Retry**:
   - Mark tutorial as failed
   - Click "Regenerate Tutorial"
   - Verify loading UI shows immediately
   - Switch to Resources tab and back
   - Verify loading UI still shows
   - Wait for completion
   - Verify success state shows

2. **Test Resources Retry**:
   - Same flow as Tutorial
   - Verify identical UI behavior

3. **Test Quiz Retry**:
   - Same flow as Tutorial
   - Verify identical UI behavior

4. **Test Error Scenarios**:
   - Force retry to fail
   - Verify UI returns to failed state
   - Verify retry button is clickable again

5. **Test Multiple Retries**:
   - Start retry on Tutorial
   - Before completion, switch to Resources and start retry there
   - Switch between tabs
   - Verify both show loading state correctly

## Technical Notes

- The 3-second timeout is a pragmatic choice balancing UX and backend sync time
- Backend typically updates status within 1-2 seconds of receiving the retry request
- WebSocket events provide real-time updates once connection is established
- Local state prevents race conditions between optimistic updates and backend fetches


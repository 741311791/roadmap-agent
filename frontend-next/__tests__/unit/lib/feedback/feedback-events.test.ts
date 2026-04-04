import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  buildGenerationFeedbackRoadmapHref,
  getConceptFeedbackStorageKey,
  getGenerationFeedbackStorageKey,
  hasFeedbackPromptBeenShown,
  markFeedbackPromptAsShown,
  promptConceptFeedback,
  promptGenerationFeedback,
} from '@/lib/feedback/feedback-events';

describe('feedback events', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.useRealTimers();
  });

  it('should build roadmap href with feedback query params', () => {
    expect(buildGenerationFeedbackRoadmapHref('roadmap-1', 'task-1')).toBe(
      '/roadmap/roadmap-1?feedbackSource=generation_completed&feedbackTaskId=task-1'
    );
    expect(buildGenerationFeedbackRoadmapHref('roadmap-1')).toBe(
      '/roadmap/roadmap-1?feedbackSource=generation_completed'
    );
  });

  it('should persist feedback prompt dedupe markers in session storage', () => {
    const storageKey = getGenerationFeedbackStorageKey('task-1');
    expect(hasFeedbackPromptBeenShown(storageKey)).toBe(false);

    markFeedbackPromptAsShown(storageKey);
    expect(hasFeedbackPromptBeenShown(storageKey)).toBe(true);
  });

  it('should dispatch generation prompt only once for the same task', () => {
    vi.useFakeTimers();
    const listener = vi.fn();
    window.addEventListener('roadmap-agent:feedback-open', listener);

    promptGenerationFeedback({
      taskId: 'task-1',
      roadmapId: 'roadmap-1',
      delayMs: 10,
    });
    promptGenerationFeedback({
      taskId: 'task-1',
      roadmapId: 'roadmap-1',
      delayMs: 10,
    });

    vi.advanceTimersByTime(10);

    expect(listener).toHaveBeenCalledTimes(1);
    const event = listener.mock.calls[0][0] as CustomEvent;
    expect(event.detail).toMatchObject({
      contextType: 'generation_completed',
      taskId: 'task-1',
      roadmapId: 'roadmap-1',
      autoPrompt: true,
    });

    window.removeEventListener('roadmap-agent:feedback-open', listener);
  });

  it('should dispatch concept prompt with dedupe key', () => {
    vi.useFakeTimers();
    const listener = vi.fn();
    window.addEventListener('roadmap-agent:feedback-open', listener);

    promptConceptFeedback({
      roadmapId: 'roadmap-1',
      conceptId: 'concept-1',
      conceptName: 'Hooks',
      delayMs: 5,
    });

    vi.advanceTimersByTime(5);

    expect(listener).toHaveBeenCalledTimes(1);
    expect(hasFeedbackPromptBeenShown(getConceptFeedbackStorageKey('roadmap-1', 'concept-1'))).toBe(true);

    window.removeEventListener('roadmap-agent:feedback-open', listener);
  });
});

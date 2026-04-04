'use client';

import type { FeedbackOpenContext } from '@/lib/feedback/types';

export const FEEDBACK_OPEN_EVENT = 'roadmap-agent:feedback-open';
const FEEDBACK_TRIGGER_STORAGE_PREFIX = 'roadmap-agent:feedback-trigger';

/**
 * 生成路线图页跳转时携带反馈参数的链接。
 */
export function buildGenerationFeedbackRoadmapHref(roadmapId: string, taskId?: string | null): string {
  const params = new URLSearchParams();
  params.set('feedbackSource', 'generation_completed');
  if (taskId) {
    params.set('feedbackTaskId', taskId);
  }

  const query = params.toString();
  return query ? `/roadmap/${roadmapId}?${query}` : `/roadmap/${roadmapId}`;
}

/**
 * 广播打开反馈弹窗事件。
 */
export function openFeedbackDialog(context: FeedbackOpenContext): void {
  if (typeof window === 'undefined') {
    return;
  }

  const detail: FeedbackOpenContext = {
    ...context,
    pageUrl: context.pageUrl ?? window.location.href,
  };
  window.dispatchEvent(new CustomEvent<FeedbackOpenContext>(FEEDBACK_OPEN_EVENT, { detail }));
}

/**
 * 手动打开反馈弹窗。
 */
export function openManualFeedbackDialog(): void {
  openFeedbackDialog({
    contextType: 'manual',
    autoPrompt: false,
  });
}

/**
 * 判断某个自动反馈触发是否已经展示过。
 */
export function hasFeedbackPromptBeenShown(storageKey: string): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  return window.sessionStorage.getItem(storageKey) === '1';
}

/**
 * 标记自动反馈触发已展示。
 */
export function markFeedbackPromptAsShown(storageKey: string): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.sessionStorage.setItem(storageKey, '1');
}

/**
 * 创建路线图生成完成的去重 key。
 */
export function getGenerationFeedbackStorageKey(taskId: string): string {
  return `${FEEDBACK_TRIGGER_STORAGE_PREFIX}:generation:${taskId}`;
}

/**
 * 创建 Concept 完成反馈的去重 key。
 */
export function getConceptFeedbackStorageKey(roadmapId: string, conceptId: string): string {
  return `${FEEDBACK_TRIGGER_STORAGE_PREFIX}:concept:${roadmapId}:${conceptId}`;
}

/**
 * 在满足去重条件后，调度路线图生成完成反馈弹窗。
 */
export function promptGenerationFeedback(options: {
  taskId: string;
  roadmapId?: string | null;
  delayMs?: number;
}): void {
  const storageKey = getGenerationFeedbackStorageKey(options.taskId);
  if (hasFeedbackPromptBeenShown(storageKey)) {
    return;
  }

  markFeedbackPromptAsShown(storageKey);
  window.setTimeout(() => {
    openFeedbackDialog({
      contextType: 'generation_completed',
      taskId: options.taskId,
      roadmapId: options.roadmapId,
      autoPrompt: true,
    });
  }, options.delayMs ?? 1200);
}

/**
 * 在满足去重条件后，调度 Concept 完成反馈弹窗。
 */
export function promptConceptFeedback(options: {
  roadmapId: string;
  conceptId: string;
  conceptName?: string | null;
  delayMs?: number;
}): void {
  const storageKey = getConceptFeedbackStorageKey(options.roadmapId, options.conceptId);
  if (hasFeedbackPromptBeenShown(storageKey)) {
    return;
  }

  markFeedbackPromptAsShown(storageKey);
  window.setTimeout(() => {
    openFeedbackDialog({
      contextType: 'concept_completed',
      roadmapId: options.roadmapId,
      conceptId: options.conceptId,
      conceptName: options.conceptName,
      autoPrompt: true,
    });
  }, options.delayMs ?? 900);
}

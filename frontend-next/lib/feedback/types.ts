'use client';

/**
 * 反馈分类类型。
 */
export type FeedbackCategory = 'bug' | 'improvement' | 'question' | 'new_feature';

/**
 * 反馈触发场景类型。
 */
export type FeedbackContextType = 'manual' | 'generation_completed' | 'concept_completed';

/**
 * 反馈弹窗打开上下文。
 */
export interface FeedbackOpenContext {
  contextType: FeedbackContextType;
  pageUrl?: string;
  roadmapId?: string | null;
  roadmapTitle?: string | null;
  conceptId?: string | null;
  conceptName?: string | null;
  taskId?: string | null;
  autoPrompt?: boolean;
}

/**
 * 反馈提交载荷。
 */
export interface SubmitFeedbackPayload {
  rating: number;
  category: FeedbackCategory;
  summary: string;
  details: string;
  pageUrl: string;
  contextType: FeedbackContextType;
  roadmapId?: string | null;
  conceptId?: string | null;
  taskId?: string | null;
  screenshotFile?: File | null;
}

/**
 * 反馈提交结果。
 */
export interface SubmitFeedbackResponse {
  feedback_id: string;
  linear_issue_id: string;
  linear_issue_identifier: string;
  linear_issue_url?: string | null;
}

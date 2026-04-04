/**
 * 用户反馈 API。
 */
import { apiClient } from '../client';
import type { SubmitFeedbackPayload, SubmitFeedbackResponse } from '@/lib/feedback/types';

/**
 * 反馈 API 命名空间。
 */
export const feedbackApi = {
  /**
   * 提交用户反馈。
   */
  submitUserFeedback: async (payload: SubmitFeedbackPayload): Promise<SubmitFeedbackResponse> => {
    const formData = new FormData();
    formData.append('rating', String(payload.rating));
    formData.append('category', payload.category);
    formData.append('summary', payload.summary);
    formData.append('details', payload.details);
    formData.append('page_url', payload.pageUrl);
    formData.append('context_type', payload.contextType);

    if (payload.roadmapId) {
      formData.append('roadmap_id', payload.roadmapId);
    }
    if (payload.conceptId) {
      formData.append('concept_id', payload.conceptId);
    }
    if (payload.taskId) {
      formData.append('task_id', payload.taskId);
    }
    if (payload.screenshotFile) {
      formData.append('screenshot_file', payload.screenshotFile);
    }

    const { data } = await apiClient.post<SubmitFeedbackResponse>(
      '/users/feedback',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return data;
  },
};

export type { SubmitFeedbackPayload, SubmitFeedbackResponse } from '@/lib/feedback/types';

/**
 * 聊天修改 API
 * 
 * 对应后端: backend/app/api/v1/endpoints/chat/ (或类似的端点)
 */

import { apiClient } from '../client';

/**
 * 聊天修改请求
 */
export interface ChatModificationRequest {
  roadmap_id: string;
  message: string;
  context?: any;
}

/**
 * 聊天 API
 */
export const chatApi = {
  /**
   * 聊天修改流式响应
   * 
   * 路径: POST /chat/modification/stream
   * 
   * 注意：此方法返回SSE流，需要使用EventSource处理
   */
  chatModificationStream: async (
    roadmapId: string,
    message: string,
    onMessage?: (data: any) => void,
    onError?: (error: Error) => void
  ): Promise<EventSource> => {
    // 创建SSE连接
    const eventSource = new EventSource(
      `/api/v1/chat/modification/stream?roadmap_id=${roadmapId}&message=${encodeURIComponent(message)}`
    );

    if (onMessage) {
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (error) {
          console.error('Failed to parse SSE message:', error);
        }
      };
    }

    if (onError) {
      eventSource.onerror = (event) => {
        onError(new Error('SSE connection error'));
      };
    }

    return eventSource;
  },
};


/**
 * useTaskStatus - 查询任务状态的 Hook (轮询)
 * 
 * ⚠️ 已弃用：此 Hook 使用轮询机制，对长时间运行的任务（5-10分钟）会产生大量不必要的请求。
 * 
 * 推荐替代方案：
 * - 使用 WebSocket 实时订阅：`TaskWebSocket` (见 @/lib/api/websocket)
 * - 任务详情页已实现完整的 WebSocket 支持，无需轮询
 * 
 * 功能:
 * - 轮询查询任务状态 (默认 2秒间隔)
 * - 任务完成或失败时自动停止轮询
 * - 支持手动控制是否启用
 * 
 * @deprecated 请使用 WebSocket 替代轮询机制
 */

import { useQuery } from '@tanstack/react-query';
import type { TaskStatusResponse } from '@/types/generated';

interface UseTaskStatusOptions {
  /** 是否启用查询 */
  enabled?: boolean;
  /** 轮询间隔 (毫秒)，默认 2000ms */
  refetchInterval?: number;
  /** 任务完成时的回调 */
  onComplete?: (status: TaskStatusResponse) => void;
  /** 任务失败时的回调 */
  onFailed?: (status: TaskStatusResponse) => void;
}

/**
 * 查询任务状态 Hook
 * 
 * @deprecated 请使用 WebSocket (`TaskWebSocket`) 替代轮询机制
 * 
 * @param taskId - 任务 ID
 * @param options - 查询选项
 * @returns TanStack Query 查询结果
 */
export function useTaskStatus(
  taskId: string | undefined,
  options: UseTaskStatusOptions = {}
) {
  // 开发环境下警告
  if (process.env.NODE_ENV === 'development') {
    console.warn(
      '[useTaskStatus] ⚠️ 此 Hook 已弃用。请使用 WebSocket (TaskWebSocket) 替代轮询机制。' +
      '轮询对长时间运行的任务会产生大量不必要的请求。'
    );
  }
  const {
    enabled = true,
    refetchInterval = 2000,
    onComplete,
    onFailed,
  } = options;

  return useQuery({
    queryKey: ['task-status', taskId],
    queryFn: async (): Promise<TaskStatusResponse> => {
      if (!taskId) {
        throw new Error('Task ID is required');
      }

      const response = await fetch(`/api/v1/roadmaps/${taskId}/status`);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch task status');
      }

      const data: TaskStatusResponse = await response.json();

      // 触发回调
      // partial_failure 也视为成功完成（路线图主体已生成，只是部分内容失败）
      if (data.status === 'completed' || data.status === 'partial_failure') {
        onComplete?.(data);
      } else if (data.status === 'failed') {
        onFailed?.(data);
      }

      return data;
    },
    enabled: enabled && !!taskId,
    refetchInterval: (query) => {
      // 任务完成、部分失败或失败时停止轮询
      const data = query?.state?.data;
      if (
        data &&
        (data.status === 'completed' || 
         data.status === 'partial_failure' || 
         data.status === 'failed')
      ) {
        return false;
      }
      return refetchInterval;
    },
    refetchIntervalInBackground: false, // 后台不轮询
    staleTime: 0, // 始终视为过期，确保轮询
  });
}

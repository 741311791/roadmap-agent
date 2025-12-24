/**
 * useTaskStatus - 查询任务状态的 Hook (轮询)
 * 
 * 功能:
 * - 轮询查询任务状态 (默认 2秒间隔)
 * - 任务完成或失败时自动停止轮询
 * - 支持手动控制是否启用
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
 * @param taskId - 任务 ID
 * @param options - 查询选项
 * @returns TanStack Query 查询结果
 */
export function useTaskStatus(
  taskId: string | undefined,
  options: UseTaskStatusOptions = {}
) {
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

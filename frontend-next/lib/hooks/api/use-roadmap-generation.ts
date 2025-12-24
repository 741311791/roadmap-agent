/**
 * useRoadmapGeneration - 生成路线图的 Mutation Hook
 * 
 * 功能:
 * - 调用路线图生成 API
 * - 乐观更新 UI 状态
 * - 成功后保存 task_id 到 Store
 * - 错误处理
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import type { UserRequest, GenerateRoadmapResponse } from '@/types/generated';

/**
 * 生成路线图 Hook
 * @returns TanStack Query Mutation 结果
 */
export function useRoadmapGeneration() {
  const queryClient = useQueryClient();
  const setGenerating = useRoadmapStore((state) => state.setGenerating);
  const setError = useRoadmapStore((state) => state.setError);
  const setActiveTask = useRoadmapStore((state) => state.setActiveTask);

  return useMutation({
    mutationFn: async (request: UserRequest): Promise<GenerateRoadmapResponse> => {
      const response = await fetch('/api/v1/roadmaps/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to generate roadmap');
      }

      return response.json();
    },
    onMutate: () => {
      // 乐观更新：立即更新 UI 状态
      setGenerating(true);
      setError(null);
    },
    onSuccess: (data) => {
      // 保存 task_id 到 Store
      setActiveTask(data.task_id);
      
      // 可选：预填充查询缓存
      if (data.roadmap_id) {
        queryClient.invalidateQueries({ queryKey: ['roadmap', data.roadmap_id] });
      }
    },
    onError: (error: Error) => {
      setError(error.message);
      setGenerating(false);
    },
  });
}

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
import type { APIResponse } from '@/types/custom/api-response';

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
      // ✅ 重构：使用新的 tasksApi.generate（路径从 /roadmaps/generate → /tasks/generate）
      const { tasksApi } = await import('@/lib/api/endpoints/tasks');
      return tasksApi.generate(request);
    },
    onMutate: () => {
      // 乐观更新：立即更新 UI 状态
      setGenerating(true);
      setError(null);
    },
    onSuccess: (data) => {
      // 保存 task_id 到 Store
      setActiveTask(data.task_id);
      
      // 注意：新版本API在生成完成后才返回roadmap_id（通过WebSocket推送）
      // 此处不再有roadmap_id字段
    },
    onError: (error: Error) => {
      setError(error.message);
      setGenerating(false);
    },
  });
}

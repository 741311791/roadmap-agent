/**
 * useContentModification - 修改内容的 Mutation Hooks
 * 
 * 功能:
 * - 修改教程内容
 * - 修改学习资源
 * - 修改测验题目
 * - 支持版本管理
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import type {
  ModifyTutorialRequest,
  ModifyTutorialResponse,
  ModifyResourcesRequest,
  ModifyQuizRequest,
} from '@/types/generated';

/**
 * 修改教程 Hook
 */
export function useModifyTutorial(roadmapId: string, conceptId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      request: ModifyTutorialRequest
    ): Promise<ModifyTutorialResponse> => {
      // ✅ 使用 apiClient 和正确的路径
      const { data } = await apiClient.post<ModifyTutorialResponse>(
        `/content/${roadmapId}/concepts/${conceptId}/tutorial/modify`,
        request
      );
      return data;
    },
    onSuccess: () => {
      // 使教程缓存失效
      queryClient.invalidateQueries({
        queryKey: ['tutorial', roadmapId, conceptId],
      });
    },
  });
}

/**
 * 修改资源 Hook
 */
export function useModifyResources(roadmapId: string, conceptId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: ModifyResourcesRequest) => {
      // ✅ 使用 apiClient 和正确的路径
      const { data } = await apiClient.post(
        `/content/${roadmapId}/concepts/${conceptId}/resources/modify`,
        request
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['resources', roadmapId, conceptId],
      });
    },
  });
}

/**
 * 修改测验 Hook
 */
export function useModifyQuiz(roadmapId: string, conceptId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: ModifyQuizRequest) => {
      // ✅ 使用 apiClient 和正确的路径
      const { data } = await apiClient.post(
        `/content/${roadmapId}/concepts/${conceptId}/quiz/modify`,
        request
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['quiz', roadmapId, conceptId],
      });
    },
  });
}

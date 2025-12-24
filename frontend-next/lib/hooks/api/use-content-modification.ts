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
      const response = await fetch(
        `/api/v1/roadmaps/${roadmapId}/concepts/${conceptId}/tutorial/modify`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to modify tutorial');
      }

      return response.json();
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
      const response = await fetch(
        `/api/v1/roadmaps/${roadmapId}/concepts/${conceptId}/resources/modify`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to modify resources');
      }

      return response.json();
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
      const response = await fetch(
        `/api/v1/roadmaps/${roadmapId}/concepts/${conceptId}/quiz/modify`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to modify quiz');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['quiz', roadmapId, conceptId],
      });
    },
  });
}

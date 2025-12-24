/**
 * useResources - 获取学习资源的 Hook
 * 
 * 功能:
 * - 获取指定 Concept 的学习资源列表
 * - 支持按类型过滤
 */

import { useQuery } from '@tanstack/react-query';
import type { ResourcesResponse } from '@/types/generated';

/**
 * 获取学习资源 Hook
 * @param roadmapId - 路线图 ID
 * @param conceptId - 概念 ID
 * @returns TanStack Query 查询结果
 */
export function useResources(
  roadmapId: string | undefined,
  conceptId: string | undefined
) {
  return useQuery({
    queryKey: ['resources', roadmapId, conceptId],
    queryFn: async (): Promise<ResourcesResponse> => {
      if (!roadmapId || !conceptId) {
        throw new Error('Roadmap ID and Concept ID are required');
      }

      const response = await fetch(
        `/api/v1/roadmaps/${roadmapId}/concepts/${conceptId}/resources`
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch resources');
      }

      return response.json();
    },
    enabled: !!roadmapId && !!conceptId,
    staleTime: 10 * 60 * 1000, // 10分钟
    gcTime: 30 * 60 * 1000, // 30分钟
  });
}

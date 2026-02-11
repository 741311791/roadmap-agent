/**
 * useResources - 获取学习资源的 Hook
 * 
 * 功能:
 * - 获取指定 Concept 的学习资源列表
 * - 支持按类型过滤
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
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

      // ✅ 使用 apiClient 和正确的路径
      const { data } = await apiClient.get<ResourcesResponse>(
        `/content/${roadmapId}/concepts/${conceptId}/resources`
      );

      return data;
    },
    enabled: !!roadmapId && !!conceptId,
    staleTime: 10 * 60 * 1000, // 10分钟
    gcTime: 30 * 60 * 1000, // 30分钟
  });
}

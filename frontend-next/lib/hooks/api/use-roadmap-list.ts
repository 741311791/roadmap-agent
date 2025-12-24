/**
 * useRoadmapList - 获取用户路线图列表的 Hook
 * 
 * 功能:
 * - 获取用户的所有路线图
 * - 支持分页和过滤
 * - 缓存策略
 */

import { useQuery } from '@tanstack/react-query';
import type { RoadmapListResponse } from '@/types/generated';

interface UseRoadmapListOptions {
  userId: string | undefined;
  status?: string;
  limit?: number;
  offset?: number;
}

/**
 * 获取用户路线图列表 Hook
 * @param options - 查询选项
 * @returns TanStack Query 查询结果
 */
export function useRoadmapList(options: UseRoadmapListOptions) {
  const { userId, status, limit = 10, offset = 0 } = options;

  return useQuery({
    queryKey: ['roadmaps', 'user', userId, { status, limit, offset }],
    queryFn: async (): Promise<RoadmapListResponse> => {
      if (!userId) {
        throw new Error('User ID is required');
      }

      const params = new URLSearchParams();
      if (status) params.append('status', status);
      params.append('limit', limit.toString());
      params.append('offset', offset.toString());

      const response = await fetch(
        `/api/v1/roadmaps/user/${userId}?${params.toString()}`
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch roadmap list');
      }

      return response.json();
    },
    enabled: !!userId,
    staleTime: 2 * 60 * 1000, // 2分钟
    gcTime: 5 * 60 * 1000, // 5分钟
  });
}

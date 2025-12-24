/**
 * useRoadmap - 获取路线图详情的 Hook
 * 
 * 功能:
 * - 使用 TanStack Query 获取路线图详情
 * - 5分钟缓存策略
 * - 自动同步到 Zustand Store
 * - 错误处理
 */

import { useQuery } from '@tanstack/react-query';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import type { RoadmapFramework } from '@/types/generated';

/**
 * 获取路线图详情 Hook
 * @param roadmapId - 路线图 ID
 * @returns TanStack Query 查询结果
 */
export function useRoadmap(roadmapId: string | undefined) {
  const setRoadmap = useRoadmapStore((state) => state.setRoadmap);
  const setError = useRoadmapStore((state) => state.setError);

  return useQuery({
    queryKey: ['roadmap', roadmapId],
    queryFn: async (): Promise<RoadmapFramework> => {
      if (!roadmapId) {
        throw new Error('Roadmap ID is required');
      }

      const response = await fetch(`/api/v1/roadmaps/${roadmapId}`);
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch roadmap');
      }

      const data: RoadmapFramework = await response.json();
      
      // 同步到 Store
      setRoadmap(data);
      
      return data;
    },
    enabled: !!roadmapId,
    staleTime: 5 * 60 * 1000, // 5分钟
    gcTime: 10 * 60 * 1000, // 10分钟 (原 cacheTime)
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    meta: {
      onError: (error: Error) => {
        setError(error.message);
      },
    },
  });
}

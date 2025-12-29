/**
 * useRoadmap - 获取路线图详情的 Hook
 * 
 * 功能:
 * - 使用 TanStack Query 获取路线图详情
 * - 优化的缓存策略
 * - 自动同步到 Zustand Store
 * - 错误处理
 * 
 * 优化：增强缓存时间和预取策略
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
    // ========================================
    // 优化：增强缓存配置
    // ========================================
    staleTime: 10 * 60 * 1000, // 10分钟（从5分钟增加）
    gcTime: 30 * 60 * 1000,    // 30分钟（从10分钟增加）
    retry: 1,                   // 减少重试次数（从3降到1）
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    meta: {
      onError: (error: Error) => {
        setError(error.message);
      },
    },
  });
}

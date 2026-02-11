/**
 * useQuiz - 获取测验题目的 Hook
 * 
 * 功能:
 * - 获取指定 Concept 的测验题目
 * - 缓存策略
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import type { QuizResponse } from '@/types/generated';

/**
 * 获取测验题目 Hook
 * @param roadmapId - 路线图 ID
 * @param conceptId - 概念 ID
 * @returns TanStack Query 查询结果
 */
export function useQuiz(
  roadmapId: string | undefined,
  conceptId: string | undefined
) {
  return useQuery({
    queryKey: ['quiz', roadmapId, conceptId],
    queryFn: async (): Promise<QuizResponse> => {
      if (!roadmapId || !conceptId) {
        throw new Error('Roadmap ID and Concept ID are required');
      }

      // ✅ 使用 apiClient 和正确的路径
      const { data } = await apiClient.get<QuizResponse>(
        `/content/${roadmapId}/concepts/${conceptId}/quiz`
      );

      return data;
    },
    enabled: !!roadmapId && !!conceptId,
    staleTime: 10 * 60 * 1000, // 10分钟
    gcTime: 30 * 60 * 1000, // 30分钟
  });
}

/**
 * useTutorial - 获取教程内容的 Hook
 * 
 * 功能:
 * - 获取指定 Concept 的教程内容
 * - 支持版本选择
 * - 自动获取 S3 URL 的 Markdown 内容
 */

import { useQuery } from '@tanstack/react-query';
import type { TutorialResponse } from '@/types/generated';

interface UseTutorialOptions {
  /** 版本号 (可选，默认最新版本) */
  version?: number;
}

interface TutorialWithContent extends TutorialResponse {
  /** 完整的 Markdown 内容 */
  full_content?: string;
}

/**
 * 获取教程内容 Hook
 * @param roadmapId - 路线图 ID
 * @param conceptId - 概念 ID
 * @param options - 查询选项
 * @returns TanStack Query 查询结果
 */
export function useTutorial(
  roadmapId: string | undefined,
  conceptId: string | undefined,
  options: UseTutorialOptions = {}
) {
  const { version } = options;

  return useQuery({
    queryKey: ['tutorial', roadmapId, conceptId, version],
    queryFn: async (): Promise<TutorialWithContent> => {
      if (!roadmapId || !conceptId) {
        throw new Error('Roadmap ID and Concept ID are required');
      }

      // 1. 获取教程元数据
      const params = version ? `?version=${version}` : '';
      const response = await fetch(
        `/api/v1/roadmaps/${roadmapId}/concepts/${conceptId}/tutorial${params}`
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch tutorial');
      }

      const tutorial: TutorialResponse = await response.json();

      // 2. 如果教程状态为 completed，并且有教程数据，返回教程内容
      if (tutorial.status === 'completed' && tutorial.tutorial) {
        // 教程内容已经包含在 tutorial 对象中
        return {
          ...tutorial,
          full_content: JSON.stringify(tutorial.tutorial, null, 2), // 或者根据实际结构处理
        };
      }

      return tutorial;
    },
    enabled: !!roadmapId && !!conceptId,
    staleTime: 10 * 60 * 1000, // 10分钟
    gcTime: 30 * 60 * 1000, // 30分钟
  });
}

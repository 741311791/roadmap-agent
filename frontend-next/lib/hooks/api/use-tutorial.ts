/**
 * useTutorial - 获取教程内容的 Hook
 * 
 * 功能:
 * - 获取指定 Concept 的教程内容
 * - 支持版本选择
 * - 自动下载完整的 Markdown 内容并缓存
 */

import { useQuery } from '@tanstack/react-query';
import { getLatestTutorial, downloadTutorialContent } from '@/lib/api/endpoints';

interface UseTutorialOptions {
  /** 版本号 (可选，默认最新版本) */
  version?: number;
}

export interface TutorialWithContent {
  /** 教程元数据 */
  tutorial_id: string;
  concept_id: string;
  title?: string;
  summary?: string;
  content_status?: 'completed' | 'generating' | 'failed' | 'pending';
  version?: number;
  generated_at?: string;
  
  /** 完整的 Markdown 内容（从 S3/R2 下载） */
  full_content?: string;
}

/**
 * 获取教程内容 Hook（带完整 Markdown 内容缓存）
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
      const meta = await getLatestTutorial(roadmapId, conceptId);

      // 2. 如果教程状态为 completed，下载完整的 Markdown 内容
      let fullContent: string | undefined;
      if (meta && meta.content_status === 'completed') {
        try {
          fullContent = await downloadTutorialContent(roadmapId, conceptId);
        } catch (error) {
          console.error('Failed to download tutorial content:', error);
          fullContent = '# Error loading content\n\nPlease try again later.';
        }
      } else if (meta?.content_status === 'generating') {
        fullContent = '# Content is being generated\n\nPlease wait...';
      } else if (meta?.content_status === 'failed') {
        fullContent = '# Content generation failed\n\nPlease retry.';
      } else {
        fullContent = '# No content available yet\n\nThis concept is still pending generation.';
      }

      return {
        tutorial_id: meta?.tutorial_id || '',
        concept_id: conceptId,
        title: meta?.title,
        summary: meta?.summary,
        content_status: meta?.content_status,
        version: meta?.version,
        generated_at: meta?.generated_at,
        full_content: fullContent,
      };
    },
    enabled: !!roadmapId && !!conceptId,
    staleTime: 10 * 60 * 1000, // 10分钟缓存
    gcTime: 30 * 60 * 1000, // 30分钟后垃圾回收
  });
}

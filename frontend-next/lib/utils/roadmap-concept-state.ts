import type { Concept, RoadmapFramework } from '@/types/generated/models';

type ConceptOverallStatus = 'pending' | 'generating' | 'completed' | 'failed' | 'partial_failed' | null;
type ConceptContentStatus = Concept['content_status'] | Concept['resources_status'] | Concept['quiz_status'];

interface ConceptWithOverallStatus extends Concept {
  overall_status?: ConceptOverallStatus;
}

interface RoadmapFrameworkWithConceptOverallStatus extends Omit<RoadmapFramework, 'stages'> {
  stages: Array<{
    modules: Array<{
      concepts: ConceptWithOverallStatus[];
    }>;
  }>;
}

export interface RoadmapConceptStates {
  loading: string[];
  failed: string[];
  partialFailed: string[];
}

/**
 * 从路线图快照中提取 Concept 的运行状态。
 *
 * 设计原因：
 * - `pending` 是内容生成的默认初始值，不能等价为“正在生成”；
 * - 真正运行中的状态应优先依赖后端写回的 `overall_status === "generating"`，
 *   其次才回退到细粒度字段里的 `"generating"`；
 * - 这样可以避免路线图结构刚生成完、内容阶段尚未开始时，整棵树被误标成 loading。
 *
 * Args:
 *   roadmap: 含有 Concept 状态快照的路线图数据
 *
 * Returns:
 *   需要在详情页高亮的 loading / failed / partialFailed Concept ID 列表
 */
export function extractRoadmapConceptStates(
  roadmap: RoadmapFrameworkWithConceptOverallStatus
): RoadmapConceptStates {
  const loading = new Set<string>();
  const failed = new Set<string>();
  const partialFailed = new Set<string>();

  roadmap.stages.forEach((stage) => {
    stage.modules.forEach((module) => {
      module.concepts.forEach((concept) => {
        const conceptId = concept.concept_id;
        const overallStatus = concept.overall_status;

        if (overallStatus === 'generating') {
          loading.add(conceptId);
          return;
        }

        if (overallStatus === 'failed') {
          failed.add(conceptId);
          return;
        }

        if (overallStatus === 'partial_failed') {
          partialFailed.add(conceptId);
          return;
        }

        if (overallStatus === 'completed' || overallStatus === 'pending') {
          return;
        }

        const statuses: ConceptContentStatus[] = [
          concept.content_status,
          concept.resources_status,
          concept.quiz_status,
        ];

        // 兼容未合并 overall_status 的旧快照，仅把显式 generating 视为运行中。
        if (statuses.some((status) => status === 'generating')) {
          loading.add(conceptId);
          return;
        }

        // 只有三项都进入终态后，才从细粒度字段推断失败或部分失败，避免 pending 被误判。
        const allSettled = statuses.every((status) => status === 'completed' || status === 'failed');
        if (!allSettled) {
          return;
        }

        const failedCount = statuses.filter((status) => status === 'failed').length;
        const completedCount = statuses.filter((status) => status === 'completed').length;

        if (failedCount === statuses.length) {
          failed.add(conceptId);
          return;
        }

        if (failedCount > 0 && completedCount > 0) {
          partialFailed.add(conceptId);
        }
      });
    });
  });

  return {
    loading: Array.from(loading),
    failed: Array.from(failed),
    partialFailed: Array.from(partialFailed),
  };
}

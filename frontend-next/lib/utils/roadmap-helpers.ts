/**
 * 路线图辅助工具函数
 */

import type { RoadmapFramework, Concept, Stage, Module } from '@/types/generated/models';

/**
 * 验证 Concept ID 是否存在于路线图中
 * 
 * @param roadmap - 路线图框架
 * @param conceptId - 要验证的 Concept ID
 * @returns 如果存在返回 true，否则返回 false
 */
export function isConceptIdValid(
  roadmap: RoadmapFramework | null,
  conceptId: string
): boolean {
  if (!roadmap || !roadmap.stages) return false;
  
  return roadmap.stages.some((stage: Stage) =>
    stage.modules?.some((module: Module) =>
      module.concepts?.some((c: Concept) => c.concept_id === conceptId)
    )
  );
}

/**
 * 从路线图中查找指定的 Concept
 * 
 * @param roadmap - 路线图框架
 * @param conceptId - Concept ID
 * @returns 找到的 Concept 对象，如果不存在返回 null
 */
export function findConceptById(
  roadmap: RoadmapFramework | null,
  conceptId: string
): Concept | null {
  if (!roadmap || !roadmap.stages) return null;
  
  for (const stage of roadmap.stages) {
    if (!stage.modules) continue;
    for (const mod of stage.modules) {
      if (!mod.concepts) continue;
      const concept = mod.concepts.find(c => c.concept_id === conceptId);
      if (concept) return concept;
    }
  }
  
  return null;
}

/**
 * 获取路线图中的所有 Concept IDs
 * 
 * @param roadmap - 路线图框架
 * @returns Concept ID 数组
 */
export function getAllConceptIds(roadmap: RoadmapFramework | null): string[] {
  if (!roadmap || !roadmap.stages) return [];
  
  const conceptIds: string[] = [];
  
  for (const stage of roadmap.stages) {
    if (!stage.modules) continue;
    for (const mod of stage.modules) {
      if (!mod.concepts) continue;
      conceptIds.push(...mod.concepts.map(c => c.concept_id));
    }
  }
  
  return conceptIds;
}

/**
 * 获取顺序学习模式下默认解锁的第一个 Concept ID
 *
 * @param roadmap - 路线图框架
 * @returns 第一个可学习的 Concept ID；若不存在则返回 null
 */
export function getInitialUnlockedConceptId(roadmap: RoadmapFramework | null): string | null {
  if (!roadmap || !roadmap.stages) return null;

  const sortedStages = [...roadmap.stages].sort((a, b) => a.order - b.order);
  for (const stage of sortedStages) {
    for (const mod of stage.modules || []) {
      const firstConcept = mod.concepts?.[0];
      if (firstConcept) {
        return firstConcept.concept_id;
      }
    }
  }

  return null;
}

/**
 * 判断当前 Concept 在顺序学习模式下是否处于锁定状态
 *
 * 当前规则：
 * - 只有第一个 Concept 默认可学
 * - 其余 Concept 统一展示为锁定态，等待后续真实解锁规则接入
 *
 * @param roadmap - 路线图框架
 * @param conceptId - 要判断的 Concept ID
 * @returns 如果处于锁定状态则返回 true
 */
export function isSequentialConceptLocked(
  roadmap: RoadmapFramework | null,
  conceptId: string
): boolean {
  const initialUnlockedConceptId = getInitialUnlockedConceptId(roadmap);
  if (!initialUnlockedConceptId) return false;
  return conceptId !== initialUnlockedConceptId;
}

/**
 * 计算路线图的整体完成度
 * 
 * @param roadmap - 路线图框架
 * @returns 完成度百分比 (0-100)
 */
export function calculateRoadmapProgress(roadmap: RoadmapFramework | null): number {
  if (!roadmap || !roadmap.stages) return 0;
  
  const allConcepts = roadmap.stages.flatMap(
    (s: Stage) => s.modules?.flatMap((m: Module) => m.concepts || []) || []
  );
  
  if (allConcepts.length === 0) return 0;
  
  const completed = allConcepts.filter(
    (c: Concept) => c.content_status === 'completed'
  ).length;
  
  return (completed / allConcepts.length) * 100;
}

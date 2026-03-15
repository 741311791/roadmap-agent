import { getConceptNodeStatus } from '@/components/task/roadmap-tree/types';
import type { Concept } from '@/types/generated/models';

function createConcept(overrides: Partial<Concept> = {}): Concept {
  return {
    concept_id: 'concept-1',
    name: 'Concept 1',
    description: 'desc',
    estimated_hours: 2,
    prerequisites: [],
    difficulty: 'easy',
    keywords: [],
    content_status: 'pending',
    content_version: 'v1',
    resources_status: 'pending',
    resources_count: 0,
    quiz_status: 'pending',
    quiz_questions_count: 0,
    ...overrides,
  };
}

describe('roadmap-tree-status', () => {
  it('应该在概念已经全部完成时忽略残留的 loading 标记', () => {
    const concept = createConcept({
      content_status: 'completed',
      resources_status: 'completed',
      quiz_status: 'completed',
    });

    expect(getConceptNodeStatus(concept, ['concept-1'])).toBe('completed');
  });

  it('应该优先使用后端返回的 overall_status 终态而不是本地 loading 标记', () => {
    const concept = createConcept({
      content_status: 'pending',
      resources_status: 'pending',
      quiz_status: 'pending',
    }) as Concept & {
      overall_status?: 'pending' | 'completed' | 'failed' | 'partial_failed' | null;
    };

    concept.overall_status = 'partial_failed';

    expect(getConceptNodeStatus(concept, ['concept-1'])).toBe('partial_failure');
  });

  it('应该在概念尚未终态时继续显示 loading', () => {
    const concept = createConcept({
      content_status: 'completed',
      resources_status: 'pending',
      quiz_status: 'pending',
    });

    expect(getConceptNodeStatus(concept, ['concept-1'])).toBe('loading');
  });
});

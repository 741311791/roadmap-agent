import { extractRoadmapConceptStates } from '@/lib/utils/roadmap-concept-state';
import type { Concept, RoadmapFramework } from '@/types/generated/models';

type ConceptWithOverallStatus = Concept & {
  overall_status?: 'pending' | 'generating' | 'completed' | 'failed' | 'partial_failed' | null;
};

function createConcept(overrides: Partial<ConceptWithOverallStatus> = {}): ConceptWithOverallStatus {
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

function createRoadmap(concept: ConceptWithOverallStatus): RoadmapFramework {
  return {
    roadmap_id: 'roadmap-1',
    title: 'Test Roadmap',
    total_estimated_hours: 12,
    recommended_completion_weeks: 4,
    stages: [
      {
        stage_id: 'stage-1',
        name: 'Stage 1',
        description: 'desc',
        order: 1,
        modules: [
          {
            module_id: 'module-1',
            name: 'Module 1',
            description: 'desc',
            concepts: [concept],
          },
        ],
      },
    ],
  };
}

describe('roadmap-concept-state', () => {
  it('应该在内容阶段尚未开始时忽略 pending 默认值', () => {
    const roadmap = createRoadmap(createConcept({ overall_status: 'pending' }));

    expect(extractRoadmapConceptStates(roadmap)).toEqual({
      loading: [],
      failed: [],
      partialFailed: [],
    });
  });

  it('应该优先使用 overall_status 的 generating 来恢复运行中状态', () => {
    const roadmap = createRoadmap(createConcept({ overall_status: 'generating' }));

    expect(extractRoadmapConceptStates(roadmap)).toEqual({
      loading: ['concept-1'],
      failed: [],
      partialFailed: [],
    });
  });

  it('应该在缺少 overall_status 时回退到细粒度 generating 字段', () => {
    const roadmap = createRoadmap(createConcept({ content_status: 'generating' }));

    expect(extractRoadmapConceptStates(roadmap)).toEqual({
      loading: ['concept-1'],
      failed: [],
      partialFailed: [],
    });
  });

  it('应该在三项都终态且有成功有失败时识别为部分失败', () => {
    const roadmap = createRoadmap(createConcept({
      content_status: 'completed',
      resources_status: 'failed',
      quiz_status: 'completed',
    }));

    expect(extractRoadmapConceptStates(roadmap)).toEqual({
      loading: [],
      failed: [],
      partialFailed: ['concept-1'],
    });
  });
});

/**
 * 路线图辅助工具函数单元测试
 */

import {
  isConceptIdValid,
  findConceptById,
  getAllConceptIds,
  calculateRoadmapProgress,
} from '@/lib/utils/roadmap-helpers';
import type { RoadmapFramework, Concept, Module, Stage } from '@/types/generated/models';

// Mock 数据
const mockRoadmap: RoadmapFramework = {
  roadmap_id: 'roadmap_test',
  title: 'Test Roadmap',
  total_estimated_hours: 100,
  recommended_completion_weeks: 10,
  stages: [
    {
      stage_id: 'stage_1',
      name: 'Stage 1',
      description: 'First stage',
      order: 1,
      modules: [
        {
          module_id: 'module_1',
          name: 'Module 1',
          description: 'First module',
          concepts: [
            {
              concept_id: 'concept_1',
              name: 'Concept 1',
              description: 'First concept',
              estimated_hours: 5,
              prerequisites: [],
              difficulty: 'easy',
              keywords: ['test'],
              content_status: 'completed',
              content_version: '1',
              resources_status: 'completed',
              resources_count: 3,
              quiz_status: 'completed',
              quiz_question_count: 5,
            } as Concept,
            {
              concept_id: 'concept_2',
              name: 'Concept 2',
              description: 'Second concept',
              estimated_hours: 5,
              prerequisites: ['concept_1'],
              difficulty: 'medium',
              keywords: ['test'],
              content_status: 'generating',
              content_version: '1',
              resources_status: 'pending',
              resources_count: 0,
              quiz_status: 'pending',
              quiz_question_count: 0,
            } as Concept,
          ],
        } as Module,
      ],
    } as Stage,
    {
      stage_id: 'stage_2',
      name: 'Stage 2',
      description: 'Second stage',
      order: 2,
      modules: [
        {
          module_id: 'module_2',
          name: 'Module 2',
          description: 'Second module',
          concepts: [
            {
              concept_id: 'stage_2:module_2:concept_3',
              name: 'Concept 3',
              description: 'Third concept with special ID',
              estimated_hours: 10,
              prerequisites: ['concept_2'],
              difficulty: 'hard',
              keywords: ['test', 'advanced'],
              content_status: 'failed',
              content_version: '1',
              resources_status: 'failed',
              resources_count: 0,
              quiz_status: 'failed',
              quiz_question_count: 0,
            } as Concept,
          ],
        } as Module,
      ],
    } as Stage,
  ],
};

describe('roadmap-helpers', () => {
  describe('isConceptIdValid', () => {
    it('应该对存在的 Concept ID 返回 true', () => {
      expect(isConceptIdValid(mockRoadmap, 'concept_1')).toBe(true);
      expect(isConceptIdValid(mockRoadmap, 'concept_2')).toBe(true);
      expect(isConceptIdValid(mockRoadmap, 'stage_2:module_2:concept_3')).toBe(true);
    });

    it('应该对不存在的 Concept ID 返回 false', () => {
      expect(isConceptIdValid(mockRoadmap, 'non_existent')).toBe(false);
      expect(isConceptIdValid(mockRoadmap, '')).toBe(false);
    });

    it('应该处理 null roadmap', () => {
      expect(isConceptIdValid(null, 'concept_1')).toBe(false);
    });

    it('应该处理没有 stages 的 roadmap', () => {
      const emptyRoadmap = { ...mockRoadmap, stages: [] };
      expect(isConceptIdValid(emptyRoadmap, 'concept_1')).toBe(false);
    });
  });

  describe('findConceptById', () => {
    it('应该找到存在的 Concept', () => {
      const concept = findConceptById(mockRoadmap, 'concept_1');
      expect(concept).not.toBeNull();
      expect(concept?.concept_id).toBe('concept_1');
      expect(concept?.name).toBe('Concept 1');
    });

    it('应该找到包含特殊字符的 Concept ID', () => {
      const concept = findConceptById(mockRoadmap, 'stage_2:module_2:concept_3');
      expect(concept).not.toBeNull();
      expect(concept?.concept_id).toBe('stage_2:module_2:concept_3');
    });

    it('应该对不存在的 Concept ID 返回 null', () => {
      expect(findConceptById(mockRoadmap, 'non_existent')).toBeNull();
    });

    it('应该处理 null roadmap', () => {
      expect(findConceptById(null, 'concept_1')).toBeNull();
    });
  });

  describe('getAllConceptIds', () => {
    it('应该返回所有 Concept IDs', () => {
      const ids = getAllConceptIds(mockRoadmap);
      expect(ids).toHaveLength(3);
      expect(ids).toContain('concept_1');
      expect(ids).toContain('concept_2');
      expect(ids).toContain('stage_2:module_2:concept_3');
    });

    it('应该处理 null roadmap', () => {
      expect(getAllConceptIds(null)).toEqual([]);
    });

    it('应该处理空 stages', () => {
      const emptyRoadmap = { ...mockRoadmap, stages: [] };
      expect(getAllConceptIds(emptyRoadmap)).toEqual([]);
    });
  });

  describe('calculateRoadmapProgress', () => {
    it('应该正确计算完成度', () => {
      // mockRoadmap 中有 3 个 concepts，1 个 completed
      const progress = calculateRoadmapProgress(mockRoadmap);
      expect(progress).toBeCloseTo(33.33, 1);
    });

    it('应该处理 null roadmap', () => {
      expect(calculateRoadmapProgress(null)).toBe(0);
    });

    it('应该处理没有 concepts 的 roadmap', () => {
      const emptyRoadmap: RoadmapFramework = {
        ...mockRoadmap,
        stages: [
          {
            stage_id: 'stage_1',
            name: 'Stage 1',
            description: 'Empty stage',
            order: 1,
            modules: [],
          } as Stage,
        ],
      };
      expect(calculateRoadmapProgress(emptyRoadmap)).toBe(0);
    });

    it('应该处理所有 concepts 都完成的情况', () => {
      const completedRoadmap: RoadmapFramework = {
        ...mockRoadmap,
        stages: [
          {
            stage_id: 'stage_1',
            name: 'Stage 1',
            description: 'Stage with completed concepts',
            order: 1,
            modules: [
              {
                module_id: 'module_1',
                name: 'Module 1',
                description: 'Module with completed concepts',
                concepts: [
                  {
                    concept_id: 'concept_1',
                    name: 'Concept 1',
                    description: 'Completed concept',
                    estimated_hours: 5,
                    prerequisites: [],
                    difficulty: 'easy',
                    keywords: ['test'],
                    content_status: 'completed',
                    content_version: '1',
                    resources_status: 'completed',
                    resources_count: 3,
                    quiz_status: 'completed',
                    quiz_question_count: 5,
                  } as Concept,
                ],
              } as Module,
            ],
          } as Stage,
        ],
      };
      expect(calculateRoadmapProgress(completedRoadmap)).toBe(100);
    });
  });
});

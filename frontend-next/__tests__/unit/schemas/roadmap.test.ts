import { describe, it, expect } from 'vitest';
import {
  ConceptSchema,
  ModuleSchema,
  StageSchema,
  RoadmapFrameworkSchema,
  validateRoadmapFramework,
  safeValidateRoadmapFramework,
} from '@/lib/schemas/roadmap';
import { ContentStatus } from '@/lib/constants/status';

describe('路线图 Schema 验证', () => {
  describe('ConceptSchema', () => {
    it('应该验证有效的 Concept 数据', () => {
      const validConcept = {
        concept_id: 'c1',
        concept_number: 1,
        title: 'Test Concept',
        description: 'Test Description',
        key_points: ['Point 1', 'Point 2'],
        prerequisites: ['prereq1'],
        estimated_time: '2 hours',
        tutorial_status: ContentStatus.COMPLETED,
        resources_status: ContentStatus.PENDING,
        quiz_status: ContentStatus.GENERATING,
      };

      const result = ConceptSchema.safeParse(validConcept);
      expect(result.success).toBe(true);
    });

    it('应该拒绝缺少必需字段的数据', () => {
      const invalidConcept = {
        concept_id: 'c1',
        title: 'Test Concept',
        // 缺少其他必需字段
      };

      const result = ConceptSchema.safeParse(invalidConcept);
      expect(result.success).toBe(false);
    });

    it('应该拒绝无效的 concept_number', () => {
      const invalidConcept = {
        concept_id: 'c1',
        concept_number: -1, // 负数
        title: 'Test Concept',
        description: 'Test Description',
        key_points: [],
        prerequisites: [],
        estimated_time: '2 hours',
        tutorial_status: ContentStatus.COMPLETED,
        resources_status: ContentStatus.PENDING,
        quiz_status: ContentStatus.GENERATING,
      };

      const result = ConceptSchema.safeParse(invalidConcept);
      expect(result.success).toBe(false);
    });
  });

  describe('ModuleSchema', () => {
    it('应该验证有效的 Module 数据', () => {
      const validModule = {
        module_id: 'm1',
        module_number: 1,
        title: 'Test Module',
        description: 'Test Description',
        learning_objectives: ['Objective 1', 'Objective 2'],
        concepts: [
          {
            concept_id: 'c1',
            concept_number: 1,
            title: 'Test Concept',
            description: 'Test Description',
            key_points: ['Point 1'],
            prerequisites: [],
            estimated_time: '2 hours',
            tutorial_status: ContentStatus.COMPLETED,
            resources_status: ContentStatus.PENDING,
            quiz_status: ContentStatus.GENERATING,
          },
        ],
      };

      const result = ModuleSchema.safeParse(validModule);
      expect(result.success).toBe(true);
    });
  });

  describe('StageSchema', () => {
    it('应该验证有效的 Stage 数据', () => {
      const validStage = {
        stage_id: 's1',
        stage_number: 1,
        title: 'Test Stage',
        description: 'Test Description',
        estimated_duration: '4 weeks',
        modules: [],
      };

      const result = StageSchema.safeParse(validStage);
      expect(result.success).toBe(true);
    });
  });

  describe('RoadmapFrameworkSchema', () => {
    it('应该验证有效的 RoadmapFramework 数据', () => {
      const validRoadmap = {
        roadmap_id: 'r1',
        title: 'Test Roadmap',
        stages: [],
      };

      const result = RoadmapFrameworkSchema.safeParse(validRoadmap);
      expect(result.success).toBe(true);
    });
  });

  describe('validateRoadmapFramework', () => {
    it('应该成功验证有效数据', () => {
      const validData = {
        roadmap_id: 'r1',
        title: 'Test Roadmap',
        stages: [],
      };

      expect(() => validateRoadmapFramework(validData)).not.toThrow();
    });

    it('应该抛出错误对于无效数据', () => {
      const invalidData = {
        roadmap_id: 'r1',
        // 缺少 title 和 stages
      };

      expect(() => validateRoadmapFramework(invalidData)).toThrow();
    });
  });

  describe('safeValidateRoadmapFramework', () => {
    it('应该返回 success: true 对于有效数据', () => {
      const validData = {
        roadmap_id: 'r1',
        title: 'Test Roadmap',
        stages: [],
      };

      const result = safeValidateRoadmapFramework(validData);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.roadmap_id).toBe('r1');
      }
    });

    it('应该返回 success: false 对于无效数据', () => {
      const invalidData = {
        roadmap_id: 'r1',
      };

      const result = safeValidateRoadmapFramework(invalidData);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBeDefined();
      }
    });
  });
});

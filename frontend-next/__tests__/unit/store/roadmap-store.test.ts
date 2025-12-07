import { describe, it, expect, beforeEach } from 'vitest';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { act, renderHook } from '@testing-library/react';

describe('RoadmapStore', () => {
  beforeEach(() => {
    // 在每个测试前重置store
    const { result } = renderHook(() => useRoadmapStore());
    act(() => {
      result.current.clearRoadmap();
      result.current.setError(null);
      result.current.setLoading(false);
      result.current.setGenerating(false);
    });
  });

  describe('基础状态管理', () => {
    it('应该设置和清除路线图', () => {
      const { result } = renderHook(() => useRoadmapStore());

      const mockRoadmap = {
        roadmap_id: 'test-id',
        title: 'Test Roadmap',
        stages: [],
        total_estimated_hours: 100,
        recommended_completion_weeks: 10,
      };

      act(() => {
        result.current.setRoadmap(mockRoadmap);
      });

      expect(result.current.currentRoadmap).toEqual(mockRoadmap);

      act(() => {
        result.current.clearRoadmap();
      });

      expect(result.current.currentRoadmap).toBeNull();
    });

    it('应该设置加载状态', () => {
      const { result } = renderHook(() => useRoadmapStore());

      expect(result.current.isLoading).toBe(false);

      act(() => {
        result.current.setLoading(true);
      });

      expect(result.current.isLoading).toBe(true);
    });

    it('应该设置错误状态', () => {
      const { result } = renderHook(() => useRoadmapStore());

      expect(result.current.error).toBeNull();

      act(() => {
        result.current.setError('Test error');
      });

      expect(result.current.error).toBe('Test error');
    });
  });

  describe('生成状态管理', () => {
    it('应该设置生成状态', () => {
      const { result } = renderHook(() => useRoadmapStore());

      expect(result.current.isGenerating).toBe(false);

      act(() => {
        result.current.setGenerating(true);
      });

      expect(result.current.isGenerating).toBe(true);
    });

    it('应该更新生成进度', () => {
      const { result } = renderHook(() => useRoadmapStore());

      act(() => {
        result.current.updateProgress('Analyzing intent', 30);
      });

      expect(result.current.currentStep).toBe('Analyzing intent');
      expect(result.current.generationProgress).toBe(30);
    });

    it('应该设置生成阶段', () => {
      const { result } = renderHook(() => useRoadmapStore());

      act(() => {
        result.current.setGenerationPhase('curriculum_design');
      });

      expect(result.current.generationPhase).toBe('curriculum_design');
    });
  });

  describe('历史记录管理', () => {
    it('应该设置历史记录', () => {
      const { result } = renderHook(() => useRoadmapStore());

      const mockHistory = [
        { roadmap_id: 'r1', title: 'Roadmap 1', created_at: '2024-01-01', status: 'completed' as const, total_concepts: 10, completed_concepts: 5 },
        { roadmap_id: 'r2', title: 'Roadmap 2', created_at: '2024-01-02', status: 'draft' as const, total_concepts: 15, completed_concepts: 0 },
      ];

      act(() => {
        result.current.setHistory(mockHistory);
      });

      expect(result.current.history).toEqual(mockHistory);
      expect(result.current.history).toHaveLength(2);
    });

    it('应该添加路线图到历史记录', () => {
      const { result } = renderHook(() => useRoadmapStore());

      const mockRoadmap = {
        roadmap_id: 'r1',
        title: 'Test Roadmap',
        created_at: '2024-01-01',
        status: 'draft' as const,
        total_concepts: 10,
        completed_concepts: 0,
      };

      act(() => {
        result.current.addToHistory(mockRoadmap);
      });

      expect(result.current.history).toContainEqual(mockRoadmap);
      expect(result.current.history).toHaveLength(1);
    });
  });

  describe('概念选择', () => {
    it('应该设置和清除选中的概念', () => {
      const { result } = renderHook(() => useRoadmapStore());

      expect(result.current.selectedConceptId).toBeNull();

      act(() => {
        result.current.selectConcept('concept-1');
      });

      expect(result.current.selectedConceptId).toBe('concept-1');

      act(() => {
        result.current.selectConcept(null);
      });

      expect(result.current.selectedConceptId).toBeNull();
    });
  });

  describe('实时生成追踪', () => {
    it('应该设置活动任务ID', () => {
      const { result } = renderHook(() => useRoadmapStore());

      act(() => {
        result.current.setActiveTask('task-123');
      });

      expect(result.current.activeTaskId).toBe('task-123');
    });

    it('应该设置实时生成状态', () => {
      const { result } = renderHook(() => useRoadmapStore());

      expect(result.current.isLiveGenerating).toBe(false);

      act(() => {
        result.current.setLiveGenerating(true);
      });

      expect(result.current.isLiveGenerating).toBe(true);
    });
  });
});


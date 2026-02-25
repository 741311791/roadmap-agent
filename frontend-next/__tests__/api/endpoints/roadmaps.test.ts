/**
 * Roadmaps API 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { roadmapsApi } from '@/lib/api/endpoints/roadmaps';
import { apiClient } from '@/lib/api/client';

// Mock apiClient
vi.mock('@/lib/api/client');

describe('roadmapsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getMyRoadmaps', () => {
    it('should call GET /roadmaps/my with correct params', async () => {
      const params = { status: 'completed', limit: 20, offset: 0 };

      const mockResponse = {
        roadmaps: [
          {
            roadmap_id: 'roadmap-1',
            task_id: 'task-1',
            learning_goal: 'Learn Python',
            title: 'Python Learning Path',
            status: 'completed',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T01:00:00Z',
          },
        ],
        total: 2,
      };

      vi.spyOn(apiClient, 'get').mockResolvedValue({
        data: mockResponse,
      } as any);

      const result = await roadmapsApi.getMyRoadmaps(params);

      expect(apiClient.get).toHaveBeenCalledWith(
        '/roadmaps/my',
        { params }
      );
      expect(result.total).toBe(2);
      expect(result.items).toHaveLength(1);
    });
  });

  describe('getMyTrash', () => {
    it('should call GET /roadmaps/trash', async () => {
      const params = { limit: 50, offset: 0 };

      const mockResponse = {
        roadmaps: [
          {
            roadmap_id: 'roadmap-2',
            task_id: 'task-2',
            learning_goal: 'Deleted roadmap',
            title: 'Deleted',
            status: 'deleted',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-02T00:00:00Z',
          },
        ],
        total: 1,
      };

      vi.spyOn(apiClient, 'get').mockResolvedValue({
        data: mockResponse,
      } as any);

      const result = await roadmapsApi.getMyTrash(params);

      expect(apiClient.get).toHaveBeenCalledWith('/roadmaps/trash', { params });
      expect(result.total).toBe(1);
      expect(result.items).toHaveLength(1);
    });
  });

  describe('delete', () => {
    it('should call DELETE /roadmaps/{roadmapId} without userId', async () => {
      const roadmapId = 'roadmap-123';

      vi.spyOn(apiClient, 'delete').mockResolvedValue({
        data: { message: 'Roadmap deleted' },
      } as any);

      await roadmapsApi.delete(roadmapId);

      // ✅ 验证：没有传递userId参数（从JWT自动提取）
      expect(apiClient.delete).toHaveBeenCalledWith(`/roadmaps/${roadmapId}`);
      expect(apiClient.delete).toHaveBeenCalledTimes(1);
    });
  });

  describe('restore', () => {
    it('should call POST /roadmaps/{roadmapId}/restore without userId', async () => {
      const roadmapId = 'roadmap-123';

      vi.spyOn(apiClient, 'post').mockResolvedValue({
        data: { message: 'Roadmap restored' },
      } as any);

      await roadmapsApi.restore(roadmapId);

      // ✅ 验证：没有传递userId参数（从JWT自动提取）
      expect(apiClient.post).toHaveBeenCalledWith(`/roadmaps/${roadmapId}/restore`);
      expect(apiClient.post).toHaveBeenCalledTimes(1);
    });
  });

  describe('permanentDelete', () => {
    it('should call DELETE /roadmaps/{roadmapId}/permanent without userId', async () => {
      const roadmapId = 'roadmap-123';

      vi.spyOn(apiClient, 'delete').mockResolvedValue({
        data: { message: 'Roadmap permanently deleted' },
      } as any);

      await roadmapsApi.permanentDelete(roadmapId);

      // ✅ 验证：没有传递userId参数（从JWT自动提取）
      expect(apiClient.delete).toHaveBeenCalledWith(`/roadmaps/${roadmapId}/permanent`);
      expect(apiClient.delete).toHaveBeenCalledTimes(1);
    });
  });

  describe('getIntentAnalysis', () => {
    it('should call GET /roadmaps/{roadmapId}/intent-analysis', async () => {
      const roadmapId = 'roadmap-123';

      const mockResponse = {
        intent_id: 'intent-123',
        roadmap_id: roadmapId,
        parsed_goal: 'Learn Python',
        key_technologies: ['Python', 'FastAPI', 'PostgreSQL'],
        difficulty_profile: 'intermediate',
        time_constraint: '12 weeks',
        recommended_focus: ['Basics', 'Intermediate', 'Advanced'],
        user_profile_summary: null,
        skill_gap_analysis: [],
        personalized_suggestions: [],
        estimated_learning_path_type: null,
        content_format_weights: null,
        language_preferences: null,
        created_at: '2026-01-01T00:00:00Z',
      };

      vi.spyOn(apiClient, 'get').mockResolvedValue({
        data: mockResponse,
      } as any);

      const result = await roadmapsApi.getIntentAnalysis(roadmapId);

      expect(apiClient.get).toHaveBeenCalledWith(
        `/roadmaps/${roadmapId}/intent-analysis`
      );
      expect(result.roadmap_id).toBe(roadmapId);
      expect(result.recommended_focus).toHaveLength(3);
    });
  });

  describe('getFeatured', () => {
    it('should call GET /roadmaps/featured', async () => {
      const params = { limit: 10, offset: 0 };

      const mockResponse = {
        total: 5,
        items: [],
      };

      vi.spyOn(apiClient, 'get').mockResolvedValue({
        data: mockResponse,
      } as any);

      const result = await roadmapsApi.getFeatured(params);

      expect(apiClient.get).toHaveBeenCalledWith(
        '/roadmaps/featured',
        { params }
      );
      expect(result.total).toBe(5);
    });
  });
});


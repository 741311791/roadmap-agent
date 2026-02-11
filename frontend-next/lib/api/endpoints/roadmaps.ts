/**
 * 路线图管理 API
 * 
 * 对应后端: backend/app/api/v1/endpoints/roadmaps/
 * 
 * 重构说明：
 * - ❌ 移除 generate（迁移到 tasksApi）
 * - ❌ 移除 getTaskStatus（迁移到 tasksApi）
 * - ❌ 移除 submitApproval（迁移到 tasksApi）
 * - ✅ 路径更新：/roadmaps/user/{id} → /roadmaps/users/{id}
 * - ✅ 新增：回收站、精选、元数据查询等
 */

import { apiClient } from '../client';
import type { 
  RoadmapFramework,
  RoadmapHistoryItem,
  FeaturedRoadmapItem,
  FeaturedRoadmapsResponse,
  RoadmapHistoryResponse,
  IntentAnalysisResponse as GeneratedIntentAnalysisResponse,
  EditRecordResponse,
  EditRecordListResponse,
  ValidationRecordResponse,
  ValidationRecordListResponse,
  CoverImageResponse
} from '@/types/generated';

/**
 * 路线图详情响应
 * ⚠️ 暂时保留，等待后端提供完整的DetailResponse
 */
export interface RoadmapDetail {
  roadmap_id: string;
  user_id: string;
  learning_goal: string;
  created_at: string;
  updated_at: string;
  framework: RoadmapFramework;
  status: string;
}

/**
 * 路线图摘要（类型别名，统一使用RoadmapHistoryItem）
 * 
 * RoadmapHistoryItem包含所有需要的字段：
 * - roadmap_id, title, created_at, total_concepts, completed_concepts
 * - topic, status, stages, task_id, task_status, current_step
 */
export type RoadmapSummary = RoadmapHistoryItem;

/**
 * 路线图列表响应
 * 
 * 注意：后端使用roadmaps字段，前端期望items字段
 * 这里统一使用items作为标准命名
 */
export interface RoadmapListResponse {
  items: RoadmapSummary[];
  total: number;
  page?: number;
  size?: number;
}

/**
 * 精选路线图列表响应
 */
export interface FeaturedRoadmapListResponse {
  items: FeaturedRoadmapItem[];
  total: number;
}

/**
 * 意图分析响应（重新导出）
 */
export type IntentAnalysisResponse = GeneratedIntentAnalysisResponse;

/**
 * 编辑记录（使用生成的类型）
 */
export type EditRecord = EditRecordResponse;

/**
 * 编辑历史版本数据
 */
export interface EditHistoryVersion {
  version: number;
  framework_data: RoadmapFramework;
  created_at: string;
  edit_round: number;
  modification_summary: string;
  modified_node_ids: string[];
}

/**
 * 完整编辑历史响应
 */
export interface EditHistoryResponse {
  versions: EditHistoryVersion[];
  current_version: number;
}

/**
 * 编辑记录列表响应
 */
export interface EditRecordsResponse {
  roadmap_id: string;
  records: EditRecord[];
  total: number;
}

/**
 * 验证记录（使用生成的类型）
 */
export type ValidationRecord = ValidationRecordResponse;

/**
 * 验证记录列表响应
 */
export interface ValidationRecordsResponse {
  roadmap_id: string;
  records: ValidationRecordResponse[];
  total: number;
}

/**
 * 封面图生成响应
 */
export interface CoverImageGenerationResponse {
  roadmap_id: string;
  task_id: string;
  status: string;
  message: string;
}

/**
 * 路线图管理 API
 */
export const roadmapsApi = {
  /**
   * 获取我的路线图列表
   * 
   * 路径: GET /roadmaps/my
   * 说明: 从JWT Token自动提取user_id，无需传递参数
   */
  getMyRoadmaps: async (
    params?: { status?: string; limit?: number; offset?: number }
  ): Promise<RoadmapListResponse> => {
    const { data } = await apiClient.get<RoadmapHistoryResponse>(
      '/roadmaps/my',
      { params }
    );
    // 转换字段名：roadmaps → items
    return {
      items: data.roadmaps,
      total: data.total,
    };
  },

  /**
   * 获取我的回收站
   * 
   * 路径: GET /roadmaps/trash
   * 说明: 从JWT Token自动提取user_id，无需传递参数
   */
  getMyTrash: async (params?: { limit?: number; offset?: number }): Promise<RoadmapListResponse> => {
    const { data } = await apiClient.get<RoadmapHistoryResponse>(
      '/roadmaps/trash',
      { params }
    );
    // 转换字段名：roadmaps → items
    return {
      items: data.roadmaps,
      total: data.total,
    };
  },

  /**
   * 获取精选路线图
   * 
   * 新增接口
   */
  getFeatured: async (params?: { limit?: number; offset?: number }): Promise<FeaturedRoadmapListResponse> => {
    const { data } = await apiClient.get<FeaturedRoadmapsResponse>(
      '/roadmaps/featured',
      { params }
    );
    // 转换字段名：roadmaps → items
    return {
      items: data.roadmaps,
      total: data.total,
    };
  },

  /**
   * 获取路线图详情
   */
  getById: async (roadmapId: string): Promise<RoadmapDetail> => {
    const { data } = await apiClient.get<RoadmapDetail>(`/roadmaps/${roadmapId}`);
    return data;
  },

  /**
   * 删除路线图（软删除）
   * 
   * 移除userId参数（后端从JWT自动提取）
   */
  delete: async (roadmapId: string): Promise<{ message: string }> => {
    const { data } = await apiClient.delete(`/roadmaps/${roadmapId}`);
    return data;
  },

  /**
   * 恢复路线图（从回收站）
   * 
   * 移除userId参数（后端从JWT自动提取）
   */
  restore: async (roadmapId: string): Promise<{ message: string }> => {
    const { data } = await apiClient.post(`/roadmaps/${roadmapId}/restore`);
    return data;
  },

  /**
   * 永久删除路线图
   * 
   * 移除userId参数（后端从JWT自动提取）
   */
  permanentDelete: async (roadmapId: string): Promise<{ message: string }> => {
    const { data } = await apiClient.delete(`/roadmaps/${roadmapId}/permanent`);
    return data;
  },

  /**
   * 获取路线图状态
   */
  getStatus: async (roadmapId: string): Promise<{
    roadmap_id: string;
    status: string;
    task_id?: string;
  }> => {
    const { data } = await apiClient.get(`/roadmaps/${roadmapId}/status`);
    return data;
  },

  /**
   * 获取意图分析
   * 
   * 旧路径: GET /roadmaps/{task_id}（混淆task_id和roadmap_id）
   * 新路径: GET /roadmaps/{roadmap_id}/intent-analysis
   * 
   * 错误处理：
   * - 404时返回 available=false 的降级数据
   * - 其他错误正常抛出
   */
  getIntentAnalysis: async (roadmapId: string): Promise<IntentAnalysisResponse> => {
    try {
      const { data } = await apiClient.get<IntentAnalysisResponse>(
        `/roadmaps/${roadmapId}/intent-analysis`
      );
      return data;
    } catch (error: any) {
      // ✅ 404 时不再抛出错误，返回降级数据
      if (error.response?.status === 404) {
        return {
          available: false,
          status: 'unknown',
          message: '需求分析数据不存在',
        } as IntentAnalysisResponse;
      }
      throw error;
    }
  },

  /**
   * 获取编辑记录
   * 
   * 路径: GET /roadmaps/{roadmap_id}/edit-records
   * 注意：使用roadmap_id而非task_id
   */
  getEditRecords: async (roadmapId: string): Promise<EditRecordsResponse> => {
    const { data } = await apiClient.get<EditRecordListResponse>(
      `/roadmaps/${roadmapId}/edit-records`
    );
    return {
      roadmap_id: roadmapId,
      records: data.records || [],
      total: data.total || 0,
    };
  },

  /**
   * 获取验证记录
   * 
   * 路径: GET /roadmaps/{roadmap_id}/validation-records
   * 注意：使用roadmap_id而非task_id
   */
  getValidationRecords: async (roadmapId: string): Promise<ValidationRecordsResponse> => {
    const { data } = await apiClient.get<ValidationRecordListResponse>(
      `/roadmaps/${roadmapId}/validation-records`
    );
    return {
      roadmap_id: roadmapId,
      records: data.records || [],
      total: data.total || 0,
    };
  },

  /**
   * 生成封面图
   * 
   * 路径: POST /roadmaps/{roadmap_id}/cover-image/generate
   * 说明: 触发封面图生成任务
   */
  generateCoverImage: async (roadmapId: string): Promise<CoverImageGenerationResponse> => {
    const { data } = await apiClient.post<any>(
      `/roadmaps/${roadmapId}/cover-image/generate`
    );
    return {
      roadmap_id: roadmapId,
      task_id: data.task_id || data.celery_task_id || '',
      status: data.status || 'pending',
      message: data.message || 'Cover image generation started',
    };
  },

  /**
   * 流式生成路线图（SSE）
   * 
   * 注意：此方法返回SSE URL，需要使用EventSource处理
   */
  getStreamingUrl: (roadmapId: string): string => {
    return `/roadmaps/${roadmapId}/streaming`;
  },

  /**
   * 获取完整编辑历史版本链
   * 
   * 路径: GET /roadmaps/{roadmap_id}/edit/history-full
   * 
   * 将编辑记录按时间顺序串联成完整的版本链，
   * 每个版本包含完整的框架数据和相对于上一版本的修改节点列表。
   */
  getFullEditHistory: async (
    roadmapId: string
  ): Promise<EditHistoryResponse> => {
    const { data } = await apiClient.get<EditHistoryResponse>(
      `/roadmaps/${roadmapId}/edit/history-full`
    );
    return data;
  },

  /**
   * 获取最新编辑记录
   * 
   * 旧路径: GET /roadmaps/{roadmapId}/edit-records/latest?task_id={taskId}
   * 新路径: GET /roadmaps/{roadmap_id}/edit-records/latest
   * 注意：不再需要task_id参数
   */
  getLatestEdit: async (roadmapId: string): Promise<EditRecord> => {
    const { data } = await apiClient.get<EditRecordResponse>(
      `/roadmaps/${roadmapId}/edit-records/latest`
    );
    return data;
  },

  /**
   * 快速检查路线图状态
   * 
   * 路径: GET /roadmaps/{roadmapId}/status/quick
   */
  checkRoadmapStatusQuick: async (roadmapId: string): Promise<any> => {
    const { data } = await apiClient.get(
      `/roadmaps/${roadmapId}/status/quick`
    );
    return data;
  },

  /**
   * 流式生成完整路线图
   * 
   * 注意：此方法返回SSE URL，需要使用EventSource处理
   */
  generateFullRoadmapStream: (request: any): string => {
    // 返回SSE端点URL
    return '/roadmaps/generate/stream';
  },
};

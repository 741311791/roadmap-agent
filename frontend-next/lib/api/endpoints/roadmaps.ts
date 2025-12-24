/**
 * 路线图相关 API 端点
 */

import { apiClient } from '../client';
import type {
  UserRequest,
  RoadmapFramework,
} from '@/types/generated/models';

/**
 * 生成路线图响应
 */
export interface GenerateRoadmapResponse {
  task_id: string;
  roadmap_id: string;
  status: string;
  message: string;
}

/**
 * 任务状态响应
 */
export interface TaskStatusResponse {
  task_id: string;
  roadmap_id?: string;
  status: string;
  current_step: string;
  created_at: string;
  updated_at: string;
  error_message?: string;
}

/**
 * 路线图详情响应
 */
export interface RoadmapDetail {
  roadmap_id: string;
  user_id: string;
  learning_goal: string;
  created_at: string;
  updated_at: string;
  framework: RoadmapFramework;
}

/**
 * 路线图列表响应
 */
export interface RoadmapListResponse {
  total: number;
  items: RoadmapSummary[];
}

export interface RoadmapSummary {
  roadmap_id: string;
  task_id: string;
  learning_goal: string;
  status: string;
  created_at: string;
  updated_at: string;
}

/**
 * 审核请求
 */
export interface ApprovalRequest {
  approved: boolean;
  feedback?: string;
}

/**
 * 审核响应
 */
export interface ApprovalResponse {
  task_id: string;
  status: string;
  message: string;
}

/**
 * 编辑记录响应
 */
export interface EditRecordResponse {
  id: string;
  task_id: string;
  roadmap_id: string;
  modification_summary: string;
  modified_node_ids: string[];
  edit_round: number;
  created_at: string;
}

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
 * 路线图 API
 */
export const roadmapsApi = {
  /**
   * 生成路线图（同步）
   */
  generate: async (request: UserRequest): Promise<GenerateRoadmapResponse> => {
    const { data } = await apiClient.post<GenerateRoadmapResponse>(
      '/roadmaps/generate',
      request
    );
    return data;
  },

  /**
   * 获取路线图详情
   */
  getById: async (roadmapId: string): Promise<RoadmapDetail> => {
    const { data } = await apiClient.get<RoadmapDetail>(`/roadmaps/${roadmapId}`);
    return data;
  },

  /**
   * 获取用户的所有路线图
   */
  getUserRoadmaps: async (
    userId: string,
    params?: { status?: string; limit?: number; offset?: number }
  ): Promise<RoadmapListResponse> => {
    const { data } = await apiClient.get<RoadmapListResponse>(
      `/roadmaps/user/${userId}`,
      { params }
    );
    return data;
  },

  /**
   * 查询任务状态
   */
  getTaskStatus: async (taskId: string): Promise<TaskStatusResponse> => {
    const { data } = await apiClient.get<TaskStatusResponse>(
      `/roadmaps/${taskId}/status`
    );
    return data;
  },

  /**
   * 提交人工审核
   */
  submitApproval: async (
    taskId: string,
    approval: ApprovalRequest
  ): Promise<ApprovalResponse> => {
    const { data } = await apiClient.post<ApprovalResponse>(
      `/roadmaps/${taskId}/approve`,
      approval
    );
    return data;
  },

  /**
   * 重试失败的内容生成
   */
  retryFailed: async (roadmapId: string) => {
    const { data } = await apiClient.post(`/roadmaps/${roadmapId}/retry-failed`);
    return data;
  },

  /**
   * 获取最新的编辑记录（包含修改的节点 ID）
   */
  getLatestEdit: async (taskId: string): Promise<EditRecordResponse> => {
    const { data } = await apiClient.get<EditRecordResponse>(
      `/tasks/${taskId}/edit/latest`
    );
    return data;
  },

  /**
   * 获取完整编辑历史版本链
   * 
   * 将编辑记录按时间顺序串联成完整的版本链，
   * 每个版本包含完整的框架数据和相对于上一版本的修改节点列表。
   */
  getFullEditHistory: async (
    taskId: string,
    roadmapId: string
  ): Promise<EditHistoryResponse> => {
    const { data } = await apiClient.get<EditHistoryResponse>(
      `/tasks/${taskId}/edit/history-full`,
      {
        params: { roadmap_id: roadmapId }
      }
    );
    return data;
  },
};

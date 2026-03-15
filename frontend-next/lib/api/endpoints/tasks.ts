/**
 * 任务管理 API
 * 
 * 对应后端: backend/app/api/v1/endpoints/tasks/
 * 
 * 说明：
 * - 路线图生成功能从 roadmapsApi 迁移到 tasksApi
 * - 执行日志从 admin 迁移到 tasks
 */

import { apiClient } from '../client';
import type { 
  UserRequest, 
  ExecutionLogListResponse, 
  TaskListResponse as GeneratedTaskListResponse,
  TaskItemResponse as GeneratedTaskItemResponse,
  GenerateRoadmapResponse 
} from '@/types/generated';
import { TaskStatus } from '@/types/generated/constants';

/**
 * 任务状态响应
 */
export interface TaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  current_step?: string;
  progress?: number;
  error_message?: string;
  roadmap_id?: string;
  created_at: string;
  updated_at: string;
  turbo_mode?: boolean;
  user_request?: UserRequest | null;
  queue_ahead_count?: number | null;
  queue_position?: number | null;
}

/**
 * 任务列表项响应
 */
export interface TaskListItemResponse extends Omit<GeneratedTaskItemResponse, 'status'> {
  status: TaskStatus;
  queue_ahead_count?: number | null;
  queue_position?: number | null;
}

/**
 * 任务列表响应
 */
export interface TaskListResponse extends Omit<GeneratedTaskListResponse, 'tasks'> {
  tasks: TaskListItemResponse[];
}

/**
 * 人工审核请求
 */
export interface ApprovalRequest {
  approved: boolean;
  feedback?: string;
  modifications?: Record<string, any>;
}

/**
 * 人工审核响应
 */
export interface ApprovalResponse {
  success: boolean;
  message: string;
  task_id: string;
  roadmap_id?: string;
}

/**
 * 执行日志响应
 */
export interface ExecutionLogsResponse {
  task_id: string;
  logs: Array<{
    log_id: string;
    step_name: string;
    status: string;
    message: string;
    created_at: string;
    metadata?: Record<string, any>;
  }>;
  total: number;
}

/**
 * 日志摘要响应
 */
export interface LogSummaryResponse {
  task_id: string;
  total_steps: number;
  completed_steps: number;
  failed_steps: number;
  current_step?: string;
  duration_seconds?: number;
}

/**
 * 错误日志响应
 */
export interface ErrorLogsResponse {
  task_id: string;
  errors: Array<{
    error_id: string;
    step_name: string;
    error_type: string;
    error_message: string;
    stack_trace?: string;
    created_at: string;
  }>;
  total: number;
}

/**
 * 任务管理 API
 */
export const tasksApi = {
  /**
   * 生成路线图（从 roadmapsApi 迁移）
   * 
   * 旧路径: POST /workflows/generation/generate
   * 新路径: POST /tasks/generate
   */
  generate: async (request: UserRequest): Promise<GenerateRoadmapResponse> => {
    const { data } = await apiClient.post<GenerateRoadmapResponse>(
      '/tasks/generate',
      request
    );
    return data;
  },

  /**
   * 获取我的任务列表
   * 
   * 路径: GET /tasks/my
   * 说明: 从JWT Token自动提取user_id，无需传递参数
   */
  getMyTasks: async (
    params?: { status?: string; limit?: number; offset?: number }
  ): Promise<TaskListResponse> => {
    const { data } = await apiClient.get<TaskListResponse>(
      '/tasks/my',
      { params }
    );
    return data;
  },

  /**
   * 获取任务详情
   * 
   * 旧路径: GET /tasks/{task_id}
   * 新路径: GET /tasks/{task_id}/status
   */
  getById: async (taskId: string): Promise<TaskStatusResponse> => {
    const { data } = await apiClient.get<TaskStatusResponse>(`/tasks/${taskId}/status`);
    return data;
  },

  /**
   * 取消任务
   * 
   * 旧路径: POST /workflows/generation/tasks/{id}/cancel
   * 新路径: POST /tasks/{id}/cancel
   */
  cancel: async (taskId: string): Promise<{ message: string }> => {
    const { data } = await apiClient.post(`/tasks/${taskId}/cancel`);
    return data;
  },

  /**
   * 删除任务
   * 如果任务正在执行（processing状态），会先自动取消任务再删除
   * 新路径: DELETE /tasks/{id}
   */
  delete: async (taskId: string): Promise<{ message: string }> => {
    const { data } = await apiClient.delete(`/tasks/${taskId}`);
    return data;
  },

  /**
   * 重试任务
   * 
   * 旧路径: POST /workflows/generation/retry/{id}
   * 新路径: POST /tasks/{id}/retry
   */
  retry: async (taskId: string): Promise<GenerateRoadmapResponse> => {
    const { data } = await apiClient.post<GenerateRoadmapResponse>(
      `/tasks/${taskId}/retry`,
      { mode: 'resume' }
    );
    return data;
  },

  /**
   * 人工审核
   * 
   * 旧路径: POST /workflows/generation/{id}/approve
   * 新路径: POST /tasks/{id}/approve
   */
  approve: async (
    taskId: string,
    approval: ApprovalRequest
  ): Promise<ApprovalResponse> => {
    const { data } = await apiClient.post<ApprovalResponse>(
      `/tasks/${taskId}/approve`,
      approval
    );
    return data;
  },

  /**
   * 获取执行日志
   * 
   * 旧路径: GET /admin/admin/trace/{id}/logs
   * 新路径: GET /tasks/{id}/logs
   * 
   * @param taskId - 任务ID
   * @param level - 日志级别（可选）
   * @param category - 日志分类（可选）
   * @param limit - 返回数量限制（默认100）
   * @param offset - 偏移量（默认0）
   * @param signal - AbortSignal for request cancellation
   */
  getLogs: async (
    taskId: string,
    level?: string,
    category?: string | string[],
    limit: number = 100,
    offset: number = 0,
    signal?: AbortSignal,
    limitPerCategory?: number
  ): Promise<ExecutionLogListResponse> => {
    const params: Record<string, string | number | undefined> = {
      level,
      limit,
      offset,
      limit_per_category: limitPerCategory,
    };

    if (Array.isArray(category)) {
      params.categories = category.join(',');
    } else {
      params.category = category;
    }

    const { data } = await apiClient.get<ExecutionLogListResponse>(
      `/tasks/${taskId}/logs`,
      { 
        params,
        signal 
      }
    );
    return data;
  },

  /**
   * 获取日志摘要
   * 
   * 旧路径: GET /admin/admin/trace/{id}/summary
   * 新路径: GET /tasks/{id}/summary
   */
  getLogSummary: async (taskId: string): Promise<LogSummaryResponse> => {
    const { data } = await apiClient.get<LogSummaryResponse>(
      `/tasks/${taskId}/summary`
    );
    return data;
  },

  /**
   * 获取错误日志
   * 
   * 旧路径: GET /admin/admin/trace/{id}/errors
   * 新路径: GET /tasks/{id}/errors
   */
  getErrors: async (taskId: string): Promise<ErrorLogsResponse> => {
    const { data } = await apiClient.get<ErrorLogsResponse>(
      `/tasks/${taskId}/errors`
    );
    return data;
  },

  /**
   * 获取路线图的活跃任务
   * 
   * 路径: GET /tasks/roadmaps/{roadmapId}/active-task
   * 
   * 用于检查路线图是否有正在进行的生成任务
   */
  getRoadmapActiveTask: async (roadmapId: string): Promise<any> => {
    const { data } = await apiClient.get(
      `/tasks/roadmaps/${roadmapId}/active-task`
    );
    return data;
  },
};


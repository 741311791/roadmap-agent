/**
 * Celery 任务监控 API 客户端
 * 
 * 提供与后端 Celery 监控 API 的交互接口
 */

import { apiClient } from './client';

// ============================================================
// 类型定义
// ============================================================

/**
 * Celery 任务信息
 */
export interface CeleryTask {
  task_id: string;
  task_name: string;
  queue?: string;
  status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | 'RETRY' | 'REVOKED' | 'SCHEDULED' | 'RESERVED';
  worker?: string;
  started_at?: string;
  completed_at?: string;
  duration?: number;
  args?: any[];
  kwargs?: Record<string, any>;
  result?: any;
  error?: string;
}

/**
 * Celery 任务队列总览
 */
export interface CeleryOverview {
  active_count: number;
  pending_count: number;
  scheduled_count: number;
  reserved_count: number;
  queue_lengths: Record<string, number>;
  workers: string[];
}

/**
 * Celery 任务列表响应
 */
export interface CeleryTaskListResponse {
  tasks: CeleryTask[];
  total: number;
}

/**
 * Celery Worker 信息
 */
export interface CeleryWorker {
  hostname: string;
  status: string;
  active_tasks: number;
  processed_tasks?: number;
}

/**
 * Celery Worker 列表响应
 */
export interface CeleryWorkerListResponse {
  workers: CeleryWorker[];
  total: number;
}

/**
 * 任务列表查询参数
 */
export interface CeleryTasksParams {
  status?: 'active' | 'scheduled' | 'reserved' | 'all';
  queue?: string;
  limit?: number;
  offset?: number;
}

// ============================================================
// API 函数
// ============================================================

/**
 * 获取 Celery 任务队列总览
 * 
 * @returns Celery 任务队列总览数据
 */
export async function getCeleryOverview(): Promise<CeleryOverview> {
  const response = await apiClient.get<CeleryOverview>('/admin/celery/overview');
  return response.data;
}

/**
 * 获取 Celery 任务列表
 * 
 * @param params 查询参数（状态、队列、分页）
 * @returns Celery 任务列表
 */
export async function getCeleryTasks(params?: CeleryTasksParams): Promise<CeleryTaskListResponse> {
  const response = await apiClient.get<CeleryTaskListResponse>('/admin/celery/tasks', {
    params: {
      status: params?.status,
      queue: params?.queue,
      limit: params?.limit || 50,
      offset: params?.offset || 0,
    },
  });
  return response.data;
}

/**
 * 获取单个 Celery 任务详情
 * 
 * @param taskId 任务 ID
 * @returns Celery 任务详细信息
 */
export async function getCeleryTaskDetail(taskId: string): Promise<CeleryTask> {
  const response = await apiClient.get<CeleryTask>(`/admin/celery/tasks/${taskId}`);
  return response.data;
}

/**
 * 获取 Celery Worker 列表
 * 
 * @returns Celery Worker 列表
 */
export async function getCeleryWorkers(): Promise<CeleryWorkerListResponse> {
  const response = await apiClient.get<CeleryWorkerListResponse>('/admin/celery/workers');
  return response.data;
}


/**
 * 管理员任务监控 API 客户端
 *
 * 重构说明（对齐后端 DB-first + runtime-enriched 混合模式）：
 * - 任务列表主源改为 roadmap_tasks 历史记录，而非瞬时 Celery 队列
 * - overview 新增 DB 统计字段与 inspect_available 可用性标记
 * - 任务详情新增业务字段（workflow_status、current_step、roadmap_id 等）
 */

import { apiClient } from './client';

// ============================================================
// 类型定义
// ============================================================

/**
 * 任务详情（DB + runtime 混合）
 */
export interface CeleryTask {
  /** 业务任务 ID (roadmap_tasks.task_id) */
  task_id: string;
  /** 任务名称或类型描述 */
  task_name: string;
  /** 队列名称（runtime 任务有值） */
  queue?: string;
  /** 对外展示的汇总状态（PENDING/STARTED/SUCCESS/FAILURE/REVOKED） */
  status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | 'RETRY' | 'REVOKED' | 'SCHEDULED' | 'RESERVED';
  /** Worker 名称（runtime 任务有值） */
  worker?: string;
  started_at?: string;
  updated_at?: string;
  completed_at?: string;
  duration?: number;
  args?: any[];
  kwargs?: Record<string, any>;
  result?: any;
  /** Celery 错误信息 */
  error?: string;

  // 业务字段（DB）
  /** 业务工作流状态（原始值：pending/processing/completed/failed 等） */
  workflow_status?: string;
  /** 当前工作流步骤 */
  current_step?: string;
  /** 业务任务类型（creation/retry_tutorial 等） */
  task_type?: string;
  /** 关联的路线图 ID */
  roadmap_id?: string;
  /** Celery 原生任务 ID */
  celery_task_id?: string;
  /** 内容生成子任务状态 */
  content_generation_status?: string;
  /** 业务错误信息（DB） */
  error_message?: string;
  /** Redis 实时步骤（任务执行中时有值） */
  live_step?: string;
  /** 是否为长期未更新的卡住任务 */
  is_stale: boolean;
  /** 已卡住时长（秒） */
  stale_for_seconds?: number;
  /** Celery runtime 中是否仍可见 */
  has_runtime_presence?: boolean;
  /** 管理员是否可以执行安全清理 */
  can_safe_cleanup: boolean;
  /** 管理员是否可以直接执行清理 */
  can_force_cleanup: boolean;
  /** 数据来源标记：runtime / database / hybrid */
  source: 'runtime' | 'database' | 'hybrid';
}

/**
 * 管理员监控总览
 */
export interface CeleryOverview {
  // runtime 统计
  /** Celery inspect 是否可用 */
  inspect_available: boolean;
  /** 当前活跃 Celery 任务数（runtime） */
  runtime_active_count: number;
  /** 当前排队/预约 Celery 任务数（runtime） */
  runtime_pending_count: number;
  scheduled_count: number;
  reserved_count: number;
  /** 在线 Worker 数 */
  workers_online: number;
  queue_lengths: Record<string, number>;
  workers: string[];
  heartbeat_available: boolean;
  heartbeat_workers_online: number;
  heartbeat_workers: string[];

  // DB 统计（始终有值）
  /** DB 中 processing 状态任务数 */
  db_processing_count: number;
  /** DB 中 pending 状态任务数 */
  db_pending_count: number;
  /** 过去 24 小时完成任务数 */
  db_completed_24h: number;
  /** 过去 24 小时失败任务数 */
  db_failed_24h: number;
  /** DB 中活跃任务总数（pending + processing） */
  db_total_active: number;
  /** 当前已达到卡住阈值的 processing 任务数 */
  stale_processing_count: number;
  /** 当前可安全清理的卡住任务数 */
  cleanable_stale_processing_count: number;
  /** 当前可强制清理的卡住任务数 */
  force_cleanable_stale_processing_count: number;
}

/**
 * 任务列表响应
 */
export interface CeleryTaskListResponse {
  tasks: CeleryTask[];
  total: number;
}

/**
 * Worker 信息
 */
export interface CeleryWorker {
  hostname: string;
  status: string;
  active_tasks: number;
  processed_tasks?: number;
  last_seen_at?: string;
  source: 'inspect' | 'heartbeat';
}

/**
 * Worker 列表响应
 */
export interface CeleryWorkerListResponse {
  workers: CeleryWorker[];
  total: number;
}

/**
 * 单个卡住任务清理结果
 */
export interface CeleryTaskCleanupResponse {
  success: boolean;
  task_id: string;
  previous_status: string;
  cleanup_status: string;
  stale_for_seconds?: number;
  runtime_visible?: boolean;
  cleanup_mode: 'safe' | 'force';
  message: string;
}

/**
 * 批量卡住任务清理结果
 */
export interface CeleryTaskCleanupBatchResponse {
  scanned: number;
  cleaned: number;
  skipped: number;
  failed: number;
  task_ids: string[];
  cleanup_mode: 'safe' | 'force';
  message: string;
}

/**
 * 任务列表查询参数
 */
export interface CeleryTasksParams {
  /** 业务状态筛选（pending/processing/completed/failed/human_review_pending 等） */
  status?: string;
  /** 队列筛选（runtime 任务专用） */
  queue?: string;
  /** 任务类型筛选（creation/retry_tutorial 等） */
  task_type?: string;
  limit?: number;
  offset?: number;
}

// ============================================================
// API 函数
// ============================================================

/**
 * 获取管理员监控总览
 *
 * 返回 DB 业务任务统计（始终有值）和 Celery runtime 统计。
 * 当 inspect 超时时，inspect_available=false，DB 统计仍然正常返回。
 */
export async function getCeleryOverview(): Promise<CeleryOverview> {
  const response = await apiClient.get<CeleryOverview>('/admin/celery/overview');
  return response.data;
}

/**
 * 获取任务列表（DB-first 历史视图）
 *
 * 默认仅返回最近 1 天业务任务历史，支持按状态、类型筛选。
 */
export async function getCeleryTasks(params?: CeleryTasksParams): Promise<CeleryTaskListResponse> {
  const response = await apiClient.get<CeleryTaskListResponse>('/admin/celery/tasks', {
    params: {
      status: params?.status,
      queue: params?.queue,
      task_type: params?.task_type,
      limit: params?.limit ?? 50,
      offset: params?.offset ?? 0,
    },
  });
  return response.data;
}

/**
 * 获取任务详情（业务优先，Celery 补充）
 *
 * 优先按业务 task_id 查询，再补充 live_step 和 Celery 结果信息。
 * 若查不到业务任务，fallback 到 Celery 原生 AsyncResult。
 */
export async function getCeleryTaskDetail(taskId: string): Promise<CeleryTask> {
  const response = await apiClient.get<CeleryTask>(`/admin/celery/tasks/${taskId}`);
  return response.data;
}

/**
 * 获取 Celery Worker 列表
 *
 * 以 stats 和 active 并集为 Worker 列表，空闲 Worker 不会消失。
 */
export async function getCeleryWorkers(): Promise<CeleryWorkerListResponse> {
  const response = await apiClient.get<CeleryWorkerListResponse>('/admin/celery/workers');
  return response.data;
}

/**
 * 清理单个卡住任务
 */
export async function cleanupStaleTask(taskId: string): Promise<CeleryTaskCleanupResponse> {
  const response = await apiClient.post<CeleryTaskCleanupResponse>(`/admin/celery/tasks/${taskId}/cleanup-stale`);
  return response.data;
}

/**
 * 批量清理当前卡住任务
 */
export async function cleanupStaleTasks(): Promise<CeleryTaskCleanupBatchResponse> {
  const response = await apiClient.post<CeleryTaskCleanupBatchResponse>('/admin/celery/tasks/stale/cleanup');
  return response.data;
}

/**
 * 强制清理单个卡住任务
 */
export async function forceCleanupStaleTask(taskId: string): Promise<CeleryTaskCleanupResponse> {
  const response = await apiClient.post<CeleryTaskCleanupResponse>(`/admin/celery/tasks/${taskId}/force-cleanup-stale`);
  return response.data;
}

/**
 * 强制批量清理当前卡住任务
 */
export async function forceCleanupStaleTasks(): Promise<CeleryTaskCleanupBatchResponse> {
  const response = await apiClient.post<CeleryTaskCleanupBatchResponse>('/admin/celery/tasks/stale/force-cleanup');
  return response.data;
}

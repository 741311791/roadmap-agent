/**
 * Tavily API Key 管理接口
 * 
 * 提供批量录入、查询、更新和删除 Tavily API Keys 的功能
 */

import { apiClient } from './client';

// ==================== 类型定义 ====================

/**
 * Tavily API Key 信息
 */
export interface TavilyAPIKeyInfo {
  /** API Key（脱敏显示） */
  api_key: string;
  /** 计划总配额 */
  plan_limit: number;
  /** 剩余配额 */
  remaining_quota: number;
  /** 录入时间 */
  created_at: string;
  /** 最后更新时间 */
  updated_at: string;
}

/**
 * Tavily API Key 列表响应
 */
export interface TavilyAPIKeyListResponse {
  /** Key 列表 */
  keys: TavilyAPIKeyInfo[];
  /** 总数 */
  total: number;
}

/**
 * 添加 Tavily API Key 请求
 */
export interface AddTavilyAPIKeyRequest {
  /** API Key */
  api_key: string;
  /** 计划总配额（每月总请求数） */
  plan_limit: number;
}

/**
 * 批量添加 Tavily API Keys 请求
 */
export interface BatchAddTavilyKeysRequest {
  /** Key 列表 */
  keys: AddTavilyAPIKeyRequest[];
}

/**
 * 批量添加 Tavily API Keys 响应
 */
export interface BatchAddTavilyKeysResponse {
  /** 成功添加的数量 */
  success: number;
  /** 失败的数量 */
  failed: number;
  /** 失败详情列表 */
  errors: Array<{
    api_key: string;
    error: string;
  }>;
}

/**
 * 更新 Tavily API Key 配额请求
 */
export interface UpdateTavilyAPIKeyRequest {
  /** 剩余配额 */
  remaining_quota?: number;
  /** 计划总配额 */
  plan_limit?: number;
}

/**
 * 删除 Tavily API Key 响应
 */
export interface DeleteTavilyAPIKeyResponse {
  /** 是否成功 */
  success: boolean;
  /** 提示消息 */
  message: string;
}

/**
 * 刷新配额响应
 */
export interface RefreshQuotaResponse {
  /** 成功更新的数量 */
  success: number;
  /** 失败的数量 */
  failed: number;
  /** 总 Key 数量 */
  total_keys: number;
  /** 耗时（秒） */
  elapsed_seconds: number;
}

// ==================== API 函数 ====================

/**
 * 获取所有 Tavily API Keys
 * 
 * @returns Tavily API Key 列表和统计信息
 */
export async function getTavilyAPIKeys(): Promise<TavilyAPIKeyListResponse> {
  const response = await apiClient.get<TavilyAPIKeyListResponse>(
    '/admin/tavily-keys'
  );
  return response.data;
}

/**
 * 添加单个 Tavily API Key
 * 
 * @param request - 添加请求
 * @returns 添加的 Tavily API Key 信息
 */
export async function addTavilyAPIKey(
  request: AddTavilyAPIKeyRequest
): Promise<TavilyAPIKeyInfo> {
  const response = await apiClient.post<TavilyAPIKeyInfo>(
    '/admin/tavily-keys',
    request
  );
  return response.data;
}

/**
 * 批量添加 Tavily API Keys
 * 
 * @param request - 批量添加请求
 * @returns 批量添加结果
 */
export async function batchAddTavilyAPIKeys(
  request: BatchAddTavilyKeysRequest
): Promise<BatchAddTavilyKeysResponse> {
  const response = await apiClient.post<BatchAddTavilyKeysResponse>(
    '/admin/tavily-keys/batch',
    request
  );
  return response.data;
}

/**
 * 更新 Tavily API Key 配额
 * 
 * @param apiKey - API Key
 * @param request - 更新请求
 * @returns 更新后的 Tavily API Key 信息
 */
export async function updateTavilyAPIKey(
  apiKey: string,
  request: UpdateTavilyAPIKeyRequest
): Promise<TavilyAPIKeyInfo> {
  const response = await apiClient.put<TavilyAPIKeyInfo>(
    `/admin/tavily-keys/${encodeURIComponent(apiKey)}`,
    request
  );
  return response.data;
}

/**
 * 删除 Tavily API Key
 * 
 * @param apiKey - API Key
 * @returns 删除结果
 */
export async function deleteTavilyAPIKey(
  apiKey: string
): Promise<DeleteTavilyAPIKeyResponse> {
  const response = await apiClient.delete<DeleteTavilyAPIKeyResponse>(
    `/admin/tavily-keys/${encodeURIComponent(apiKey)}`
  );
  return response.data;
}

/**
 * 手动刷新所有 Tavily API Keys 的配额信息
 * 
 * 调用 Tavily 官方 API 获取最新的配额使用情况并更新数据库
 * 
 * @returns 刷新结果，包含成功/失败数量和耗时
 */
export async function refreshTavilyQuota(): Promise<RefreshQuotaResponse> {
  const response = await apiClient.post<RefreshQuotaResponse>(
    '/admin/tavily-keys/refresh-quota'
  );
  return response.data;
}


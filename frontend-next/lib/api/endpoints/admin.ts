/**
 * 平台管理 API
 * 
 * 对应后端: backend/app/api/v1/endpoints/admin/
 */

import { apiClient } from '../client';

/**
 * Waitlist条目
 */
export interface WaitlistEntry {
  id: string;
  email: string;
  status: 'pending' | 'invited' | 'registered';
  created_at: string;
  invited_at?: string;
}

/**
 * Waitlist列表响应
 */
export interface WaitlistListResponse {
  total: number;
  items: WaitlistEntry[];
  page: number;
  size: number;
}

/**
 * Tavily Key信息
 */
export interface TavilyKeyInfo {
  id: string;
  key_name: string;
  api_key: string;
  status: 'active' | 'inactive' | 'exhausted';
  daily_limit: number;
  used_today: number;
  last_used_at?: string;
  created_at: string;
}

/**
 * Tavily Keys列表响应
 */
export interface TavilyKeysResponse {
  keys: TavilyKeyInfo[];
  total: number;
  active_count: number;
}

/**
 * Celery任务信息
 */
export interface CeleryTaskInfo {
  task_id: string;
  task_name: string;
  status: 'pending' | 'started' | 'success' | 'failure' | 'retry';
  worker?: string;
  timestamp: string;
  result?: any;
}

/**
 * Celery任务列表响应
 */
export interface CeleryTasksResponse {
  tasks: CeleryTaskInfo[];
  total: number;
  active: number;
  scheduled: number;
  reserved: number;
}

/**
 * 平台管理 API
 */
export const adminApi = {
  /**
   * 加入Waitlist（公开接口，无需认证）
   * 
   * 旧路径: POST /users/waitlist
   * 新路径: POST /waitlist
   */
  joinWaitlist: async (email: string): Promise<{ message: string; position: number }> => {
    const { data } = await apiClient.post('/waitlist', { email });
    return data;
  },

  /**
   * 公开申请试用（自动发送临时账号凭证）
   */
  requestTrialAccess: async (
    email: string
  ): Promise<{
    success: boolean;
    email: string;
    status: 'invited' | 'already_invited' | 'existing_account';
    message: string;
  }> => {
    const { data } = await apiClient.post('/waitlist/trial-access', {
      email,
      source: 'landing_page',
    });
    return data;
  },

  /**
   * 获取Waitlist列表（管理员）
   */
  getWaitlist: async (params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<WaitlistListResponse> => {
    const { data } = await apiClient.get<WaitlistListResponse>(
      '/admin/waitlist',
      { params }
    );
    return data;
  },

  /**
   * 邀请用户（管理员）
   */
  inviteUser: async (email: string): Promise<{ message: string; user_id: string }> => {
    const { data } = await apiClient.post('/admin/users/invite', { email });
    return data;
  },

  /**
   * 创建超级管理员（管理员）
   */
  createSuperuser: async (userData: {
    email: string;
    username: string;
    password: string;
  }): Promise<{ message: string; user_id: string }> => {
    const { data } = await apiClient.post('/admin/users/superuser', userData);
    return data;
  },

  /**
   * 获取Tavily Keys列表
   */
  getTavilyKeys: async (): Promise<TavilyKeysResponse> => {
    const { data } = await apiClient.get<TavilyKeysResponse>('/admin/tavily/keys');
    return data;
  },

  /**
   * 添加Tavily Key（单个）
   * 
   * 注意：后端实际支持批量添加 POST /admin/tavily/keys/batch
   * 这里为了兼容性，单个添加转换为批量请求
   */
  addTavilyKey: async (keyData: {
    key_name: string;
    api_key: string;
    daily_limit?: number;
  }): Promise<{ message: string; key_id: string }> => {
    const { data } = await apiClient.post('/admin/tavily/keys/batch', {
      api_keys: [keyData]
    });
    return {
      message: data.message || 'Key added successfully',
      key_id: data.added_ids?.[0] || '',
    };
  },

  /**
   * 批量添加Tavily Keys
   */
  addTavilyKeys: async (keys: Array<{
    key_name: string;
    api_key: string;
    daily_limit?: number;
  }>): Promise<{ message: string; added_ids: string[] }> => {
    const { data } = await apiClient.post('/admin/tavily/keys/batch', {
      api_keys: keys
    });
    return data;
  },

  /**
   * 删除Tavily Key（单个）
   * 
   * 注意：后端实际支持批量删除 POST /admin/tavily/keys/batch-delete
   * 这里为了兼容性，单个删除转换为批量请求
   */
  deleteTavilyKey: async (keyId: string): Promise<{ message: string }> => {
    const { data } = await apiClient.post('/admin/tavily/keys/batch-delete', {
      key_ids: [keyId]
    });
    return {
      message: data.message || 'Key deleted successfully',
    };
  },

  /**
   * 批量删除Tavily Keys
   */
  deleteTavilyKeys: async (keyIds: string[]): Promise<{ message: string; deleted_count: number }> => {
    const { data } = await apiClient.post('/admin/tavily/keys/batch-delete', {
      key_ids: keyIds
    });
    return data;
  },

  /**
   * 获取Celery任务列表
   */
  getCeleryTasks: async (params?: {
    status?: string;
    limit?: number;
  }): Promise<CeleryTasksResponse> => {
    const { data } = await apiClient.get<CeleryTasksResponse>(
      '/admin/monitoring/celery/tasks',
      { params }
    );
    return data;
  },

  /**
   * 获取可用技术栈列表
   * 
   * 旧路径: GET /admin/technologies
   * 新路径: GET /learning/assessment/available-technologies
   * 
   * 返回平台支持的所有技术名称列表
   */
  getAvailableTechnologies: async (): Promise<{ technologies: string[]; count: number }> => {
    const { data } = await apiClient.get<{ technologies: string[] }>(
      '/learning/assessment/available-technologies'
    );
    return {
      technologies: data.technologies || [],
      count: data.technologies?.length || 0,
    };
  },
};


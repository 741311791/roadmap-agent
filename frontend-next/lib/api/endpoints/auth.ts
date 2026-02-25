/**
 * 认证授权 API
 * 
 * 对应后端: backend/app/api/v1/endpoints/auth/
 */

import { apiClient } from '../client';

/**
 * 认证 API
 */
export const authApi = {
  /**
   * 登出（当前设备）
   */
  logout: async (): Promise<{ message: string }> => {
    const { data } = await apiClient.post('/auth/logout');
    return data;
  },

  /**
   * 登出所有设备
   */
  logoutAllDevices: async (): Promise<{ message: string; devices_count: number }> => {
    const { data } = await apiClient.post('/auth/logout-all-devices');
    return data;
  },

  /**
   * 获取黑名单统计信息（管理员）
   */
  getBlacklistStats: async (): Promise<{
    total_tokens: number;
    active_tokens: number;
    expired_tokens: number;
  }> => {
    const { data } = await apiClient.get('/auth/blacklist/stats');
    return data;
  },
};


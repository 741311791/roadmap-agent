/**
 * 用户相关 API 端点
 */

import { apiClient } from '../client';
import type { UserProfileRequest, UserProfileData } from '../endpoints';

/**
 * 用户 API
 */
export const usersApi = {
  /**
   * 获取用户画像
   */
  getUserProfile: async (userId: string): Promise<UserProfileData> => {
    const { data } = await apiClient.get<UserProfileData>(`/users/${userId}/profile`);
    return data;
  },

  /**
   * 更新用户画像
   */
  updateUserProfile: async (
    userId: string,
    profile: UserProfileRequest
  ): Promise<UserProfileData> => {
    const { data } = await apiClient.put<UserProfileData>(
      `/users/${userId}/profile`,
      profile
    );
    return data;
  },
};

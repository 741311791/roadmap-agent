/**
 * 用户管理 API
 * 
 * 对应后端: backend/app/api/v1/endpoints/users/
 * 
 * 重构说明：
 * - ✅ 移除userId参数（后端从JWT自动提取）
 * - ✅ 路径更新：/users/{userId}/profile → /users/profile
 * - ✅ 使用生成的类型定义
 */

import { apiClient } from '../client';
import type { 
  UserProfileRequest as GeneratedUserProfileRequest,
  UserProfileResponse
} from '@/types/generated';

/**
 * 用户画像请求（重新导出生成的类型）
 */
export type UserProfileRequest = GeneratedUserProfileRequest;

/**
 * 用户画像数据（类型别名，保持向后兼容）
 */
export type UserProfileData = UserProfileResponse;

/**
 * 用户管理 API
 */
export const usersApi = {
  /**
   * 获取用户画像
   * 
   * 旧路径: GET /users/{userId}/profile（需要传递userId）
   * 新路径: GET /users/profile（从JWT自动提取）
   */
  getUserProfile: async (): Promise<UserProfileData> => {
    const { data } = await apiClient.get<UserProfileData>('/users/profile');
    return data;
  },

  /**
   * 更新用户画像
   * 
   * 旧路径: PUT /users/{userId}/profile（需要传递userId）
   * 新路径: PUT /users/profile（从JWT自动提取）
   */
  updateUserProfile: async (profile: UserProfileRequest): Promise<UserProfileData> => {
    const { data } = await apiClient.put<UserProfileData>(
      '/users/profile',
      profile
    );
    return data;
  },

  /**
   * 保存用户画像（别名函数，与updateUserProfile相同）
   */
  saveUserProfile: async (profile: UserProfileRequest): Promise<UserProfileData> => {
    return usersApi.updateUserProfile(profile);
  },
};

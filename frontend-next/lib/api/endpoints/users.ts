/**
 * 用户管理 API
 * 
 * 对应后端: backend/app/api/v1/endpoints/users/
 * 
 * 重构说明：
 * - ✅ 移除userId参数（后端从JWT自动提取）
 * - ✅ 路径更新：/users/{userId}/profile → /users/profile
 * - ✅ 使用生成的类型定义
 * - ✅ 新增 getCurrentUser / updateCurrentUser（对应 FastAPI Users 的 /users/me 端点）
 */

import { apiClient } from '../client';
import type { User } from '@/lib/services/auth-service';
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
 * 更新当前用户请求体
 * 
 * 对应后端 UserUpdate schema，所有字段均为可选
 */
export interface UpdateCurrentUserRequest {
  /** 新用户名 */
  username?: string;
  /** 新密码（明文，后端负责哈希） */
  password?: string;
  /** react-nice-avatar 头像配置 JSON */
  avatar_config?: Record<string, unknown> | null;
}

/**
 * 用户管理 API
 */
export const usersApi = {
  /**
   * 获取当前登录用户的完整信息
   * 
   * 对应后端: GET /users/me（FastAPI Users 内置端点）
   */
  getCurrentUser: async (): Promise<User> => {
    const { data } = await apiClient.get<User>('/users/me');
    return data;
  },

  /**
   * 更新当前登录用户信息
   * 
   * 支持更新用户名、密码、头像配置。
   * 对应后端: PATCH /users/me（FastAPI Users 内置端点）
   */
  updateCurrentUser: async (payload: UpdateCurrentUserRequest): Promise<User> => {
    const { data } = await apiClient.patch<User>('/users/me', payload);
    return data;
  },

  /**
   * 获取用户画像（学习偏好）
   * 
   * 旧路径: GET /users/{userId}/profile（需要传递userId）
   * 新路径: GET /users/profile（从JWT自动提取）
   */
  getUserProfile: async (): Promise<UserProfileData> => {
    const { data } = await apiClient.get<UserProfileData>('/users/profile');
    return data;
  },

  /**
   * 更新用户画像（学习偏好）
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

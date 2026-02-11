/**
 * useUserProfile - 用户画像相关的 Hooks
 * 
 * 功能:
 * - 获取用户画像
 * - 更新用户画像
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UserProfileResponse } from '@/types/generated';
type UserProfile = UserProfileResponse;

/**
 * 获取用户画像 Hook
 * 
 * 重构说明：
 * - ✅ 路径更新：/users/{userId}/profile → /users/profile
 * - ✅ 移除userId参数（后端从JWT自动提取）
 * 
 * @returns TanStack Query 查询结果
 */
export function useUserProfile() {
  return useQuery({
    queryKey: ['user-profile'],
    queryFn: async (): Promise<UserProfile> => {
      // ✅ 使用新的 usersApi.getUserProfile（无需userId参数）
      const { usersApi } = await import('@/lib/api/endpoints/users');
      return usersApi.getUserProfile();
    },
    staleTime: 30 * 60 * 1000, // 30分钟
  });
}

/**
 * 更新用户画像 Hook
 * 
 * 重构说明：
 * - ✅ 路径更新：/users/{userId}/profile → /users/profile
 * - ✅ 移除userId参数（后端从JWT自动提取）
 * 
 * @returns TanStack Query Mutation 结果
 */
export function useUpdateUserProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (profile: Partial<UserProfile>): Promise<UserProfile> => {
      // ✅ 使用新的 usersApi.updateUserProfile（无需userId参数）
      const { usersApi } = await import('@/lib/api/endpoints/users');
      return usersApi.updateUserProfile(profile as any);
    },
    onSuccess: (data) => {
      // 更新缓存（移除userId依赖）
      queryClient.setQueryData(['user-profile'], data);
    },
  });
}

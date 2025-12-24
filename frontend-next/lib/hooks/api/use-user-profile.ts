/**
 * useUserProfile - 用户画像相关的 Hooks
 * 
 * 功能:
 * - 获取用户画像
 * - 更新用户画像
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UserProfile } from '@/types/generated';

/**
 * 获取用户画像 Hook
 * @param userId - 用户 ID
 * @returns TanStack Query 查询结果
 */
export function useUserProfile(userId: string | undefined) {
  return useQuery({
    queryKey: ['user-profile', userId],
    queryFn: async (): Promise<UserProfile> => {
      if (!userId) {
        throw new Error('User ID is required');
      }

      const response = await fetch(`/api/v1/users/${userId}/profile`);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch user profile');
      }

      return response.json();
    },
    enabled: !!userId,
    staleTime: 30 * 60 * 1000, // 30分钟
  });
}

/**
 * 更新用户画像 Hook
 * @param userId - 用户 ID
 * @returns TanStack Query Mutation 结果
 */
export function useUpdateUserProfile(userId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (profile: Partial<UserProfile>): Promise<UserProfile> => {
      const response = await fetch(`/api/v1/users/${userId}/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(profile),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update user profile');
      }

      return response.json();
    },
    onSuccess: (data) => {
      // 更新缓存
      queryClient.setQueryData(['user-profile', userId], data);
    },
  });
}

'use client';

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { roadmapsApi } from '@/lib/api/endpoints/roadmaps';
import { tasksApi } from '@/lib/api/endpoints/tasks';

export const dashboardQueryKeys = {
  myRoadmaps: (params: { limit?: number; offset?: number }) => ['roadmaps', 'my', params] as const,
  featuredRoadmaps: (params: { limit?: number; offset?: number }) => ['roadmaps', 'featured', params] as const,
  myTasks: (params: { status?: string; limit?: number; offset?: number }) => ['tasks', 'my', params] as const,
};

export function useMyRoadmapsQuery(params: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: dashboardQueryKeys.myRoadmaps(params),
    queryFn: () => roadmapsApi.getMyRoadmaps(params),
    placeholderData: keepPreviousData,
  });
}

export function useFeaturedRoadmapsQuery(params: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: dashboardQueryKeys.featuredRoadmaps(params),
    queryFn: () => roadmapsApi.getFeatured(params),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
  });
}

export function useMyTasksQuery(params: { status?: string; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: dashboardQueryKeys.myTasks(params),
    queryFn: () => tasksApi.getMyTasks(params),
    placeholderData: keepPreviousData,
  });
}

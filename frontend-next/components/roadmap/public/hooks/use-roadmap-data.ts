'use client';

/**
 * 产品路书公开页数据 Hook
 */
import { useQuery } from '@tanstack/react-query';

import { getPublicRoadmapData, type PublicRoadmapDataResponse } from '@/lib/api/roadmap-public';
import type { Locale } from '@/i18n/config';

export function useRoadmapData(locale: Locale) {
  return useQuery({
    queryKey: ['public-roadmap-data', locale],
    queryFn: getPublicRoadmapData,
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    retry: 0,
  });
}

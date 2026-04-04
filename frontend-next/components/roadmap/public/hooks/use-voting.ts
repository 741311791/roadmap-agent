'use client';

/**
 * 产品路书投票与提交 Hook
 */
import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useLocale, useTranslations } from 'next-intl';
import { toast } from 'sonner';

import {
  createPlanningItem,
  getPlanningItems,
  votePlanningItem,
  type PlanningItemCreateRequest,
  type PublicPlanningItem,
  type PublicPlanningItemListResponse,
} from '@/lib/api/roadmap-public';
import type { Locale } from '@/i18n/config';

const VOTED_ITEM_STORAGE_KEY = 'public-roadmap-voted-item-ids';

function readVotedItemIds(): number[] {
  if (typeof window === 'undefined') {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(VOTED_ITEM_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((value) => typeof value === 'number') : [];
  } catch {
    return [];
  }
}

function writeVotedItemIds(itemIds: number[]): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(VOTED_ITEM_STORAGE_KEY, JSON.stringify(itemIds));
}

export function useVoting() {
  const locale = useLocale() as Locale;
  const t = useTranslations('publicRoadmap.toast');
  const queryClient = useQueryClient();
  const [votedItemIds, setVotedItemIds] = useState<number[]>([]);
  const planningItemsQueryKey = ['public-planning-items', locale] as const;

  useEffect(() => {
    setVotedItemIds(readVotedItemIds());
  }, []);

  const planningItemsQuery = useQuery({
    queryKey: planningItemsQueryKey,
    queryFn: getPlanningItems,
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: 0,
  });

  const voteMutation = useMutation({
    mutationFn: async (itemId: number) => {
      if (votedItemIds.includes(itemId)) {
        throw new Error('LOCAL_ALREADY_VOTED');
      }

      return votePlanningItem(itemId);
    },
    onSuccess: (payload) => {
      const nextIds = [...new Set([...votedItemIds, payload.item_id])];
      setVotedItemIds(nextIds);
      writeVotedItemIds(nextIds);

      queryClient.setQueryData<PublicPlanningItemListResponse>(
        planningItemsQueryKey,
        (current) => {
          if (!current) {
            return current;
          }
          return {
            ...current,
            items: current.items
              .map((item) =>
                item.id === payload.item_id
                  ? { ...item, vote_count: payload.vote_count }
                  : item
              )
              .sort((left, right) => right.vote_count - left.vote_count),
          };
        }
      );

      toast.success(t('voteRecorded'));
    },
    onError: (error, itemId) => {
      if (error instanceof Error && error.message === 'LOCAL_ALREADY_VOTED') {
        toast.info(t('alreadyVoted'));
        return;
      }

      if (axios.isAxiosError(error) && error.response?.status === 409) {
        const nextIds = [...new Set([...votedItemIds, itemId])];
        setVotedItemIds(nextIds);
        writeVotedItemIds(nextIds);
        toast.info(t('alreadyVoted'));
        return;
      }

      toast.error(t('voteFailed'));
    },
  });

  const submitIdeaMutation = useMutation({
    mutationFn: createPlanningItem,
    onSuccess: (item) => {
      queryClient.setQueryData<PublicPlanningItemListResponse>(
        planningItemsQueryKey,
        (current) => {
          const base = current ?? { items: [], total: 0 };
          return {
            total: base.total + 1,
            items: [item, ...base.items].sort((left, right) => right.vote_count - left.vote_count),
          };
        }
      );
      toast.success(t('ideaSubmitted'));
    },
    onError: () => {
      toast.error(t('ideaSubmitFailed'));
    },
  });

  const items = planningItemsQuery.data?.items ?? [];

  const topItems = useMemo(() => items.slice(0, 3), [items]);
  const remainingItems = useMemo(() => items.slice(3), [items]);

  const isVoted = (itemId: number) => votedItemIds.includes(itemId);

  return {
    items,
    topItems,
    remainingItems,
    votedItemIds,
    isVoted,
    isLoading: planningItemsQuery.isLoading,
    isFetching: planningItemsQuery.isFetching,
    isVoting: voteMutation.isPending,
    isSubmittingIdea: submitIdeaMutation.isPending,
    handleVote: (itemId: number) => voteMutation.mutate(itemId),
    handleSubmitIdea: (payload: PlanningItemCreateRequest) => submitIdeaMutation.mutateAsync(payload),
  };
}

export type UseVotingItem = PublicPlanningItem;

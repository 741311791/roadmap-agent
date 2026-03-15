'use client';

import { useCallback, useRef, type Dispatch, type SetStateAction } from 'react';
import { mapToDisplayStep } from '@/lib/constants/workflow-steps';
import type { TaskStatusType } from '@/types/generated/constants';

/**
 * 任务状态最小字段集合。
 *
 * 该类型只约束状态同步逻辑真正需要的字段，
 * 使 hook 可以复用于任务详情页之外的其他任务场景。
 */
export interface TaskStateSyncTarget {
  current_step?: string | null;
  status: TaskStatusType;
  roadmap_id?: string | null;
  error_message?: string | null;
  updated_at?: string | null;
  queue_ahead_count?: number | null;
  queue_position?: number | null;
}

/**
 * 实时任务状态更新参数。
 */
export interface RealtimeTaskUpdateOptions {
  eventAt?: string | null;
  step?: string | null;
  status?: TaskStatusType;
  roadmapId?: string | null;
  errorMessage?: string | null;
  deriveStatus?: (prevStatus: TaskStatusType) => TaskStatusType | undefined;
}

/**
 * 统一处理任务状态时序与合并逻辑。
 *
 * 设计目标：
 * 1. 避免旧的 WebSocket 事件覆盖较新的页面状态。
 * 2. 将 current_status / progress / completed / failed 的合并规则集中管理。
 * 3. 降低页面组件中的状态竞态复杂度。
 */
export function useTaskStateSync<T extends TaskStateSyncTarget>(
  setTaskInfo: Dispatch<SetStateAction<T | null>>
) {
  const latestTaskStateTimestampRef = useRef(0);

  /**
   * 解析任务状态事件时间戳。
   */
  const parseTaskStateTimestamp = useCallback((value?: string | null): number => {
    if (!value) {
      return 0;
    }

    const parsed = Date.parse(value);
    return Number.isNaN(parsed) ? 0 : parsed;
  }, []);

  /**
   * 记录当前页面已接受的最新任务状态时间戳。
   */
  const syncLatestTaskStateTimestamp = useCallback((value?: string | null): void => {
    const parsed = parseTaskStateTimestamp(value);
    if (parsed > 0) {
      latestTaskStateTimestampRef.current = Math.max(latestTaskStateTimestampRef.current, parsed);
    }
  }, [parseTaskStateTimestamp]);

  /**
   * 判断任务状态事件是否已经过期。
   */
  const isStaleTaskStateEvent = useCallback((value?: string | null): boolean => {
    const parsed = parseTaskStateTimestamp(value);
    if (parsed === 0) {
      return false;
    }

    return parsed < latestTaskStateTimestampRef.current;
  }, [parseTaskStateTimestamp]);

  /**
   * 统一合并实时任务状态，避免不同事件处理器之间相互覆盖。
   */
  const applyRealtimeTaskUpdate = useCallback((options: RealtimeTaskUpdateOptions): boolean => {
    const eventAt = options.eventAt ?? null;
    if (isStaleTaskStateEvent(eventAt)) {
      console.log('[TaskStateSync] Ignore stale task state event:', {
        eventAt,
        latestAcceptedAt: latestTaskStateTimestampRef.current,
        step: options.step,
        status: options.status,
      });
      return false;
    }

    const eventTimestamp = parseTaskStateTimestamp(eventAt);

    setTaskInfo((prev) => {
      if (!prev) {
        return null;
      }

      const next: T = { ...prev };

      if (options.step !== undefined) {
        next.current_step = mapToDisplayStep(options.step);
      }

      if (options.status !== undefined) {
        next.status = options.status;
        if (options.status !== 'pending') {
          next.queue_ahead_count = null;
          next.queue_position = null;
        }
      }

      if (options.deriveStatus) {
        const derivedStatus = options.deriveStatus(prev.status);
        if (derivedStatus !== undefined) {
          next.status = derivedStatus;
        }
      }

      if (options.roadmapId !== undefined) {
        next.roadmap_id = options.roadmapId;
      }

      if (options.errorMessage !== undefined) {
        next.error_message = options.errorMessage;
      }

      if (eventTimestamp > 0) {
        const prevTimestamp = parseTaskStateTimestamp(prev.updated_at);
        if (eventTimestamp >= prevTimestamp) {
          next.updated_at = eventAt;
        }
        latestTaskStateTimestampRef.current = Math.max(latestTaskStateTimestampRef.current, eventTimestamp);
      }

      return next;
    });

    return true;
  }, [isStaleTaskStateEvent, parseTaskStateTimestamp, setTaskInfo]);

  return {
    syncLatestTaskStateTimestamp,
    isStaleTaskStateEvent,
    applyRealtimeTaskUpdate,
  };
}

'use client';

/**
 * 任务详情页面 - 重构版
 * 
 * 三段式布局:
 * 1. 上部：Workflow Progress（增强版步进器 + Human Review 内嵌）
 * 2. 中部：Core Display Area（需求分析卡片 + 动态路线图）
 * 3. 下部：Timeline Log（垂直时间轴日志）
 * 
 * 功能:
 * - WebSocket 实时订阅任务状态更新
 * - 状态与 checkpoint 完全同步
 * - 路线图实时更新和交互
 */

import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslations, useLocale } from 'next-intl';
import { ArrowLeft, AlertCircle, CheckCircle2, Loader2, Clock, Eye, Target, UserRound, SlidersHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { TaskWebSocket } from '@/lib/api/websocket';
import type { TaskStatusResponse } from '@/lib/api/endpoints/tasks';
import { tasksApi, roadmapsApi } from '@/lib/api/endpoints';
import { useTaskStateSync } from '@/lib/hooks/use-task-state-sync';
import { WorkflowTopology } from '@/components/task/workflow-topology';
import { CoreDisplayArea } from '@/components/task/core-display-area';
import { ExecutionLogTimeline } from '@/components/task/execution-log-timeline';
import { limitLogsByStep, getLogStatsByStep } from '@/lib/utils/log-grouping';
import { extractRoadmapConceptStates } from '@/lib/utils/roadmap-concept-state';
import { WorkflowStep, mapToDisplayStep } from '@/lib/constants/workflow-steps';
import { getTaskStatusFromProgressEvent } from '@/lib/utils/task-progress-status';
import { TaskStatus } from '@/types/generated/constants';
import type { TaskStatusType } from '@/types/generated/constants';
import type {
  RoadmapFramework,
  ExecutionLogResponse,
  IntentAnalysisResponse,
  UserRequest,
} from '@/types/generated/models';

/**
 * 需求分析输出类型
 */
interface IntentAnalysisOutput {
  learning_goal: string;
  key_technologies: string[];
  difficulty_level: string;
  estimated_duration_weeks: number;
  estimated_hours_per_week?: number;
  skill_gaps?: Array<{
    skill_name: string;
    current_level: string;
    required_level: string;
  }>;
  learning_strategies?: string[];
}

/**
 * 执行日志类型（使用生成的类型）
 */
type ExecutionLog = ExecutionLogResponse;

/**
 * 任务拓扑图的节点耗时需要同时消费 workflow 与 content 两类日志。
 */
function collectNodeDurationLogs(logs: ExecutionLog[]) {
  return logs.filter((log) => log.category === 'workflow' || log.category === 'content');
}

interface TaskArtifactsRefreshOptions {
  refreshLogs?: boolean;
  refreshIntentAnalysis?: boolean;
  refreshRoadmap?: boolean;
  syncRoadmapId?: boolean;
}

function isTaskDetailRequestCancelled(error: unknown): boolean {
  if (!error || typeof error !== 'object') {
    return false;
  }

  const candidate = error as {
    name?: string;
    code?: string;
  };

  return (
    candidate.name === 'AbortError' ||
    candidate.name === 'CanceledError' ||
    candidate.code === 'ERR_CANCELED'
  );
}

/**
 * 任务信息类型（扩展生成的类型）
 * 注意：status 字段使用 TaskStatusType 以支持字符串字面量
 */
interface TaskInfo extends Omit<TaskStatusResponse, 'status'> {
  title: string;  // 额外添加的字段
  status: TaskStatusType;  // 使用联合类型而不是枚举
  user_request?: UserRequest | null;
}

// 辅助函数：格式化文本（去除下划线、首字母大写）
const formatText = (text?: string | null) => {
  if (!text || ['Not specified', 'not specified', 'null', 'undefined'].includes(text)) return null;
  return text
    .split(/[_: ]+/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

/**
 * 格式化语言标签（支持 i18n）
 */
function formatLanguage(tag: string, t: (key: string) => string): string {
  if (tag.includes('primary:zh') || tag === 'zh') return t('language.primaryZh');
  if (tag.includes('secondary:en') || tag === 'en') return t('language.secondaryEn');
  if (tag.includes('preferred:zh')) return t('language.preferredZh');
  if (tag.includes('primary:en')) return t('language.primaryEn');
  if (tag.includes('secondary:zh')) return t('language.secondaryZh');
  if (tag.includes('preferred:en')) return t('language.preferredEn');
  return formatText(tag.replace('primary:', '').replace('secondary:', '').replace('preferred:', '')) ?? tag;
}

/**
 * 格式化偏好标签（支持 i18n）
 */
function formatPreference(tag: string, t: (key: string) => string): string {
  const prefKeys = ['visual', 'text', 'hands_on', 'audio'] as const;
  if (prefKeys.includes(tag as any)) return t(`preference.${tag}`);
  return formatText(tag) ?? tag;
}

export default function TaskDetailPage() {
  const t = useTranslations('taskDetail');
  const locale = useLocale();
  const params = useParams();
  const router = useRouter();
  const taskId = params?.taskId as string;
  // TanStack Query Client - 用于预填充路线图缓存，加速页面跳转
  const queryClient = useQueryClient();

  // 任务基本信息
  const [taskInfo, setTaskInfo] = useState<TaskInfo | null>(null);

  // 执行日志
  const [executionLogs, setExecutionLogs] = useState<ExecutionLog[]>([]);
  const [workflowLogs, setWorkflowLogs] = useState<ExecutionLog[]>([]);

  // 需求分析输出
  const [intentAnalysis, setIntentAnalysis] = useState<IntentAnalysisOutput | null>(null);

  // 路线图框架
  const [roadmapFramework, setRoadmapFramework] = useState<RoadmapFramework | null>(null);

  // 修改过的节点 ID（用于 cyan 标注）
  const [modifiedNodeIds, setModifiedNodeIds] = useState<string[]>([]);

  // 加载中的 Concept ID
  const [loadingConceptIds, setLoadingConceptIds] = useState<string[]>([]);

  // 失败的 Concept ID
  const [failedConceptIds, setFailedConceptIds] = useState<string[]>([]);

  // 部分失败的 Concept ID
  const [partialFailedConceptIds, setPartialFailedConceptIds] = useState<string[]>([]);
  // 失败内容类型映射（用于详情卡片精确展示 tutorial/resources/quiz 哪一项失败）
  const [failedContentTypesMap, setFailedContentTypesMap] = useState<Record<string, Array<'tutorial' | 'resources' | 'quiz'>>>({});

  // 编辑来源（用于区分分支，追踪当前活跃分支）
  const [editSource, setEditSource] = useState<'validation_failed' | 'human_review' | null>(null);

  // 分支触发状态（独立维护，不依赖 DB 日志，避免日志缓冲区延迟导致状态丢失）
  // 从 WS 事件立即设置，从 DB 日志恢复（刷新场景）
  const [validationBranchTriggered, setValidationBranchTriggered] = useState(false);
  const [reviewBranchTriggered, setReviewBranchTriggered] = useState(false);

  // 加载状态
  const [isLoading, setIsLoading] = useState(true);
  const [, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 节点选中状态（用于侧边面板）
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // 取消任务确认对话框 - 已移除功能

  // WebSocket 连接
  const [ws, setWs] = useState<TaskWebSocket | null>(null);
  
  // 使用ref存储最新的roadmap_id，确保在WebSocket事件处理器中能获取到最新值
  const roadmapIdRef = useRef<string | null>(null);
  const refreshTaskArtifactsTimeoutRef = useRef<number | null>(null);
  const refreshTaskArtifactsInFlightRef = useRef<Promise<void> | null>(null);
  const pendingRefreshOptionsRef = useRef<TaskArtifactsRefreshOptions | null>(null);
  const {
    syncLatestTaskStateTimestamp,
    isStaleTaskStateEvent,
    applyRealtimeTaskUpdate,
  } = useTaskStateSync<TaskInfo>(setTaskInfo);

  /**
   * 使用接口返回的任务快照整体刷新页面状态。
   *
   * 该入口只用于“主动拉取”的场景，例如：
   * - 首次进入页面
   * - 人工审核完成后主动刷新
   *
   * 与 WebSocket 实时事件分开处理，可以让任务页只保留两种状态写入路径：
   * 1. applyTaskSnapshot：整包接口快照
   * 2. applyRealtimeTaskUpdate：实时增量事件
   */
  const applyTaskSnapshot = useCallback((
    taskData: TaskStatusResponse,
    title: string
  ): boolean => {
    if (isStaleTaskStateEvent(taskData.updated_at)) {
      console.log('[TaskDetail] Ignore stale task snapshot:', {
        updated_at: taskData.updated_at,
        current_step: taskData.current_step,
        status: taskData.status,
      });
      return false;
    }

    const displayStep = mapToDisplayStep(taskData.current_step || null);

    const nextTaskInfo: TaskInfo = {
      ...taskData,
      current_step: displayStep ?? undefined,
      title,
    };

    setTaskInfo(nextTaskInfo);
    syncLatestTaskStateTimestamp(taskData.updated_at);
    roadmapIdRef.current = taskData.roadmap_id || null;
    return true;
  }, [isStaleTaskStateEvent, syncLatestTaskStateTimestamp]);

  /**
   * 从time_constraint字符串中解析时间信息
   * 
   * 示例输入: "每周 10 小时，建议 8-10 个月完成转型"
   * 返回: { weeks: 36, hoursPerWeek: 10 }
   */
  const parseTimeConstraint = (timeConstraint: string): { weeks: number; hoursPerWeek: number } => {
    let weeks = 0;
    let hoursPerWeek = 0;
    
    // 解析每周小时数
    const hoursMatch = timeConstraint.match(/每周\s*(\d+\.?\d*)\s*小时|(\d+\.?\d*)\s*小时.*每周/);
    if (hoursMatch) {
      hoursPerWeek = parseFloat(hoursMatch[1] || hoursMatch[2]);
    }
    
    // 解析完成时间（优先匹配周数）
    const weeksMatch = timeConstraint.match(/(\d+)-?(\d+)?\s*周/);
    if (weeksMatch) {
      // 如果是范围（如 "8-10 周"），取平均值
      const minWeeks = parseInt(weeksMatch[1]);
      const maxWeeks = weeksMatch[2] ? parseInt(weeksMatch[2]) : minWeeks;
      weeks = Math.round((minWeeks + maxWeeks) / 2);
    } else {
      // 尝试解析月数
      const monthsMatch = timeConstraint.match(/(\d+)-?(\d+)?\s*个?月/);
      if (monthsMatch) {
        const minMonths = parseInt(monthsMatch[1]);
        const maxMonths = monthsMatch[2] ? parseInt(monthsMatch[2]) : minMonths;
        const avgMonths = (minMonths + maxMonths) / 2;
        weeks = Math.round(avgMonths * 4); // 1个月 ≈ 4周
      }
    }
    
    // 默认值（如果解析失败）
    return {
      weeks: weeks || 4,
      hoursPerWeek: hoursPerWeek || 5,
    };
  };

  /**
   * 加载需求分析数据（从数据库获取，而不是从日志中提取）
   * 优化：返回 Promise 以支持并行调用，支持请求取消
   * 
   * @param roadmapId - 路线图ID（注意：是roadmap_id，不是task_id）
   * @param signal - AbortSignal for request cancellation
   */
  const loadIntentAnalysis = useCallback(async (roadmapId: string, signal?: AbortSignal) => {
    try {
      const intentData: IntentAnalysisResponse = await roadmapsApi.getIntentAnalysis(roadmapId);
      
      console.log('[TaskDetail] Intent analysis loaded successfully:', {
        roadmap_id: roadmapId,
        has_data: !!intentData,
        available: intentData?.available,
        parsed_goal_length: intentData?.parsed_goal?.length,
        key_technologies_count: intentData?.key_technologies?.length,
      });
      
      // ✅ 检查数据是否可用
      if (!intentData || intentData.available === false) {
        console.log('[TaskDetail] Intent analysis data not available yet:', {
          status: intentData?.status,
          current_step: intentData?.current_step,
          message: intentData?.message,
        });
        // 数据未就绪，不设置状态
        return null;
      }

      // 从 time_constraint 解析时间信息
      const { weeks, hoursPerWeek } = parseTimeConstraint(intentData.time_constraint || '');
      
      // 转换为前端需要的格式
      const intentOutput: IntentAnalysisOutput = {
        learning_goal: intentData.parsed_goal || '',
        key_technologies: intentData.key_technologies || [],
        difficulty_level: intentData.difficulty_profile || '',
        estimated_duration_weeks: weeks,
        estimated_hours_per_week: hoursPerWeek,
        skill_gaps: (intentData.skill_gap_analysis || []).map(gap => ({
          skill_name: gap,
          current_level: 'beginner',
          required_level: 'intermediate',
        })),
        learning_strategies: intentData.personalized_suggestions || [],
      };
      
      setIntentAnalysis(intentOutput);
      return intentOutput;
    } catch (err: any) {
      // 如果是取消请求，不记录错误
      if (err.name === 'AbortError' || err.name === 'CanceledError') {
        console.log('[TaskDetail] Intent analysis request cancelled');
        return null;
      }
      
      // 增强错误日志，显示详细信息
      console.error('[TaskDetail] Failed to load intent analysis:', {
        roadmap_id: roadmapId,
        error: err,
        status: err.response?.status,
        message: err.response?.data?.detail || err.message,
      });
      
      // 如果获取失败，不设置数据（保持为 null）
      return null;
    }
  }, []);

  /**
   * 加载路线图框架
   * 
   * 优化策略:
   * - 支持请求取消
   * - 预填充 TanStack Query 缓存，加速跳转到路线图详情页
   *   原理：当用户点击 "View Roadmap" 时，路线图详情页使用 useRoadmap hook
   *   该 hook 基于 TanStack Query，预填充缓存后可实现近乎瞬时的页面加载
   */
  const loadRoadmapFramework = useCallback(async (roadmapId: string, updateConceptStates = false, signal?: AbortSignal) => {
    try {
      const roadmapDetail = await roadmapsApi.getById(roadmapId);
      if (roadmapDetail && roadmapDetail.framework) {
        const framework = roadmapDetail.framework;
        setRoadmapFramework(framework);
        
        // 🚀 关键优化：预填充 TanStack Query 缓存
        // 必须存入 framework（而非 roadmapDetail），因为 useRoadmap 的 queryFn
        // 返回的是提取后的 RoadmapFramework，缓存格式必须一致，
        // 否则跳转后 roadmapData.stages 为 undefined，KnowledgeRail 会一直 loading
        queryClient.setQueryData(['roadmap', roadmapId], framework);
        console.log('[TaskDetail] Prefilled roadmap cache for instant navigation');
        
        // 如果需要更新概念状态（刷新时使用）
        if (updateConceptStates) {
          const { loading, failed, partialFailed } = extractRoadmapConceptStates(framework);
          setLoadingConceptIds(loading);
          setFailedConceptIds(failed);
          setPartialFailedConceptIds(partialFailed);
          console.log('[TaskDetail] Updated concept states from roadmap:', { loading, failed, partialFailed });
        }
      }
    } catch (err: any) {
      // 如果是取消请求，不记录错误
      if (err.name === 'AbortError' || err.name === 'CanceledError') {
        console.log('[TaskDetail] Roadmap framework request cancelled');
        return;
      }
      console.error('Failed to load roadmap framework:', err);
    }
  }, [queryClient]);

  /**
   * 合并多次刷新请求，避免节点完成和 Concept 事件在短时间内重复全量拉取。
   */
  const executeTaskArtifactsRefresh = useCallback(async (options: TaskArtifactsRefreshOptions) => {
    let currentRoadmapId = roadmapIdRef.current;

    if (!currentRoadmapId && options.syncRoadmapId) {
      try {
        const latestTask = await tasksApi.getById(taskId);
        if (latestTask.roadmap_id) {
          currentRoadmapId = latestTask.roadmap_id;
          roadmapIdRef.current = latestTask.roadmap_id;
          applyRealtimeTaskUpdate({
            eventAt: latestTask.updated_at,
            roadmapId: latestTask.roadmap_id,
          });
        }
      } catch (error) {
        console.error('[TaskDetail] Failed to sync roadmap_id before artifacts refresh:', error);
      }
    }

    const refreshJobs: Promise<unknown>[] = [];

    if (options.refreshLogs) {
      refreshJobs.push(
        tasksApi.getLogs(
          taskId,
          undefined,
          ['agent', 'workflow', 'content'],
          1000,
          0,
          undefined,
          1000
        ).then((combinedLogsData) => {
          const allLogs = combinedLogsData.logs || [];
          const nextWorkflowLogs = collectNodeDurationLogs(allLogs);
          const limitedLogs = limitLogsByStep(allLogs, 100);
          setExecutionLogs(limitedLogs);
          setWorkflowLogs(nextWorkflowLogs);
        }).catch((error) => {
          console.error('[TaskDetail] Failed to refresh task logs:', error);
        })
      );
    }

    if (currentRoadmapId && options.refreshIntentAnalysis) {
      refreshJobs.push(
        loadIntentAnalysis(currentRoadmapId).catch((error) => {
          console.error('[TaskDetail] Failed to refresh intent analysis:', error);
        })
      );
    }

    if (currentRoadmapId && options.refreshRoadmap) {
      refreshJobs.push(
        loadRoadmapFramework(currentRoadmapId, true).catch((error) => {
          console.error('[TaskDetail] Failed to refresh roadmap framework:', error);
        })
      );
    }

    await Promise.all(refreshJobs);
  }, [applyRealtimeTaskUpdate, loadIntentAnalysis, loadRoadmapFramework, taskId]);

  const scheduleTaskArtifactsRefresh = useCallback((
    options: TaskArtifactsRefreshOptions,
    debounceMs: number = 250
  ) => {
    const pendingOptions = pendingRefreshOptionsRef.current || {};
    pendingRefreshOptionsRef.current = {
      refreshLogs: pendingOptions.refreshLogs || options.refreshLogs,
      refreshIntentAnalysis: pendingOptions.refreshIntentAnalysis || options.refreshIntentAnalysis,
      refreshRoadmap: pendingOptions.refreshRoadmap || options.refreshRoadmap,
      syncRoadmapId: pendingOptions.syncRoadmapId || options.syncRoadmapId,
    };

    if (refreshTaskArtifactsTimeoutRef.current !== null) {
      window.clearTimeout(refreshTaskArtifactsTimeoutRef.current);
    }

    refreshTaskArtifactsTimeoutRef.current = window.setTimeout(() => {
      refreshTaskArtifactsTimeoutRef.current = null;

      const runRefresh = async () => {
        if (refreshTaskArtifactsInFlightRef.current) {
          await refreshTaskArtifactsInFlightRef.current;
        }

        const nextOptions = pendingRefreshOptionsRef.current;
        if (!nextOptions) {
          return;
        }

        pendingRefreshOptionsRef.current = null;
        const refreshPromise = executeTaskArtifactsRefresh(nextOptions);
        refreshTaskArtifactsInFlightRef.current = refreshPromise;

        try {
          await refreshPromise;
        } finally {
          if (refreshTaskArtifactsInFlightRef.current === refreshPromise) {
            refreshTaskArtifactsInFlightRef.current = null;
          }
          if (pendingRefreshOptionsRef.current) {
            scheduleTaskArtifactsRefresh({}, 0);
          }
        }
      };

      void runRefresh();
    }, debounceMs);
  }, [executeTaskArtifactsRefresh]);

  /**
   * 任务进入终态后，立即清理本地 loading 残留，并用服务端快照对账 Concept 状态。
   */
  const reconcileTerminalTaskArtifacts = useCallback(() => {
    setLoadingConceptIds([]);
    scheduleTaskArtifactsRefresh(
      {
        refreshLogs: true,
        refreshRoadmap: true,
        syncRoadmapId: true,
      },
      0,
    );
  }, [scheduleTaskArtifactsRefresh]);

  /**
   * 加载任务信息和日志（提取为独立函数，供初始加载和刷新使用）
   * 优化：并行化所有独立的数据请求，减少日志数量，支持请求取消
   */
  const loadTaskData = useCallback(async (isInitialLoad = false, signal?: AbortSignal) => {
    if (!taskId) return;

    try {
      if (isInitialLoad) {
        setIsLoading(true);
      } else {
        setIsRefreshing(true);
      }
      setError(null);

      /**
       * 带重试的任务详情获取
       *
       * 说明：
       * - 刷新页面瞬间后端可能刚好在 reload，短时间返回 404/5xx；
       * - 这里做轻量重试，避免误判为“任务不存在”。
       */
      const fetchTaskWithRetry = async () => {
        let lastError: any = null;
        for (let attempt = 0; attempt < 3; attempt++) {
          try {
            return await tasksApi.getById(taskId);
          } catch (err: any) {
            if (signal?.aborted) throw err;
            lastError = err;
            const statusCode = err?.response?.status;
            const canRetry = attempt < 2 && (statusCode === 404 || statusCode >= 500 || !statusCode);
            if (!canRetry) {
              throw err;
            }
            await new Promise((resolve) => setTimeout(resolve, 500 * (attempt + 1)));
          }
        }
        throw lastError;
      };

      // 任务详情是关键请求，先确保成功拿到
      const taskData = await fetchTaskWithRetry();

      /**
       * 基于 taskData 立即并行启动后续请求，避免日志、需求分析、路线图互相等待。
       *
       * 设计原因：
       * - 首屏标题依赖 intent_analysis，但路线图和日志不需要等待它完成；
       * - 任务详情页此前会先等日志，再等 intent，再等 roadmap，形成不必要的瀑布流。
       */
      const combinedLogsPromise = tasksApi.getLogs(
        taskId,
        undefined,
        ['agent', 'workflow', 'content'],
        1000,
        0,
        signal,
        1000
      );
      const intentPromise = taskData.roadmap_id
        ? loadIntentAnalysis(taskData.roadmap_id, signal).catch(() => null)
        : Promise.resolve(null);
      const roadmapPromise = taskData.roadmap_id
        ? loadRoadmapFramework(taskData.roadmap_id, true, signal)
        : Promise.resolve();

      // 日志是非关键请求，失败不应让页面进入“任务不存在”
      const [combinedLogsResult, intentData] = await Promise.all([
        Promise.resolve(combinedLogsPromise).then(
          (value) => ({ status: 'fulfilled', value } as const),
          (reason) => ({ status: 'rejected', reason } as const),
        ),
        intentPromise,
      ]);

      if (
        combinedLogsResult.status === 'rejected' &&
        isTaskDetailRequestCancelled(combinedLogsResult.reason)
      ) {
        throw combinedLogsResult.reason;
      }

      const combinedLogsData = combinedLogsResult.status === 'fulfilled' ? combinedLogsResult.value : { logs: [] };
      if (combinedLogsResult.status === 'rejected') {
        console.warn('[TaskDetail] Failed to load combined task logs:', combinedLogsResult.reason);
      }

      // 添加 title 字段（从 intentAnalysis 或默认值获取）
      // 注意：这里不能使用 t()，因为是在回调函数中，需要在组件渲染时使用
      applyTaskSnapshot(
        taskData,
        intentData?.learning_goal || 'Generating Roadmap...'
      );
      
      const allLogs = combinedLogsData.logs || [];
      const nextWorkflowLogs = collectNodeDurationLogs(allLogs);
      
      // 按 step 分组，每个 step 最多 100 条
      const limitedLogs = limitLogsByStep(allLogs, 100);
      
      // 打印统计信息（开发调试用）
      if (process.env.NODE_ENV === 'development') {
        const stats = getLogStatsByStep(allLogs);
        console.log('[TaskDetail] Log stats by step:', stats);
        console.log('[TaskDetail] Total logs:', allLogs.length, '→ Limited to:', limitedLogs.length);
      }
      
      setExecutionLogs(limitedLogs);
      setWorkflowLogs(nextWorkflowLogs);
      
      // 从执行日志中提取分支触发状态（用于刷新场景恢复 UI 状态）
      // 注意：WS 实时场景下分支状态由 handleProgress 立即设置，不依赖此处
      const branchLogs = allLogs.filter(log => 
        (log.step === 'roadmap_edit' || log.step === 'edit_plan_analysis') && 
        log.details && typeof log.details === 'object' && 'edit_source' in log.details
      );
      
      const hasValidationBranch = branchLogs.some(
        log => log.details?.edit_source === 'validation_failed'
      );
      const hasReviewBranch = branchLogs.some(
        log => log.details?.edit_source === 'human_review'
      );
      
      if (hasValidationBranch) {
        setValidationBranchTriggered(true);
        console.log('[TaskDetail] Restored validationBranchTriggered=true from DB logs');
      }
      if (hasReviewBranch) {
        setReviewBranchTriggered(true);
        console.log('[TaskDetail] Restored reviewBranchTriggered=true from DB logs');
      }

      // 提取最新的 edit_source（用于 getStepLocation，区分当前活跃分支）
      const latestEditSource = branchLogs
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        [0]?.details?.edit_source || null;
      
      if (latestEditSource) {
        setEditSource(latestEditSource);
        console.log('[TaskDetail] Extracted edit_source from logs:', latestEditSource);
      }

      await roadmapPromise;

    } catch (err: any) {
      // 如果是取消请求，不设置错误状态
      if (err.name === 'AbortError' || err.name === 'CanceledError') {
        console.log('[TaskDetail] Request cancelled');
        // 仍需重置加载状态
        if (isInitialLoad) {
          setIsLoading(false);
        } else {
          setIsRefreshing(false);
        }
        return;
      }
      console.error('Failed to load task data:', err);
      setError(err.message || 'Failed to load task details');
    } finally {
      if (isInitialLoad) {
        setIsLoading(false);
      } else {
        setIsRefreshing(false);
      }
    }
  }, [taskId, loadIntentAnalysis, loadRoadmapFramework]);

  /**
   * 初始加载任务数据
   * 
   * 仅在 taskId 变化时触发，不依赖 loadTaskData 引用。
   * loadTaskData 的 useCallback 依赖链（loadIntentAnalysis, loadRoadmapFramework）
   * 可能因下游 setState 而频繁重建，如果放在 deps 里会导致重复加载，
   * 第二次加载时先 abort 第一次、再 setIsLoading(true)，造成日志/耗时短暂消失。
   */
  const loadTaskDataRef = useRef(loadTaskData);
  loadTaskDataRef.current = loadTaskData;

  useEffect(() => {
    if (!taskId) return;
    
    const controller = new AbortController();
    loadTaskDataRef.current(true, controller.signal);
    
    return () => {
      controller.abort();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);

  /**
   * 重试成功回调
   */
  const handleRetrySuccess = useCallback(() => {
    // 刷新任务数据以获取最新状态
    if (taskId) {
      loadTaskData(false);
    }
  }, [taskId, loadTaskData]);

  useEffect(() => {
    return () => {
      if (refreshTaskArtifactsTimeoutRef.current !== null) {
        window.clearTimeout(refreshTaskArtifactsTimeoutRef.current);
      }
    };
  }, []);

  /**
   * 取消任务 - 功能已移除
   */

  /**
   * WebSocket 实时订阅
   */
  useEffect(() => {
    if (!taskId || !taskInfo) return;

    // 只有正在处理中的任务才需要 WebSocket
    const isActiveTask = 
      taskInfo.status === 'processing' || 
      taskInfo.status === 'pending' ||
      taskInfo.status === 'human_review_pending';
    
    // 防御性处理：如果任务是 failed 但最近更新（10秒内），可能是刚刚 retry 的
    // 尝试建立 WebSocket 连接以接收最新状态（retry 后状态会变为 processing）
    const isRecentlyUpdated = taskInfo.updated_at 
      ? (Date.now() - new Date(taskInfo.updated_at).getTime()) < 10000 
      : false;
    const mightBeRetrying = taskInfo.status === 'failed' && isRecentlyUpdated;
    
    if (!isActiveTask && !mightBeRetrying) {
      return;
    }
    
    // 如果是可能正在 retry 的任务，记录日志
    if (mightBeRetrying) {
      console.log('[TaskDetail] Task might be retrying, establishing WebSocket to check for updates');
    }

    // 定义WebSocket事件处理器函数
    const handleStatus = (event: any) => {
      console.log('[TaskDetail] Status update:', event);
      const previousRoadmapId = roadmapIdRef.current;
      const accepted = applyRealtimeTaskUpdate({
        eventAt: event.updated_at,
        step: event.current_step,
        status: event.status,
        roadmapId: event.roadmap_id,
      });

      if (!accepted) {
        return;
      }

      if (event.roadmap_id) {
        roadmapIdRef.current = event.roadmap_id;
        
        // 仅在首次拿到 roadmap_id 时拉取需求分析，避免重复状态事件反复触发相同请求。
        if (event.roadmap_id !== previousRoadmapId) {
          loadIntentAnalysis(event.roadmap_id).catch((err) => {
            console.error('[TaskDetail] Failed to load intent analysis after roadmap_id update:', err);
          });
        }
      }
    };

    const handleProgress = async (event: any) => {
      console.log('[TaskDetail] Progress update:', event);
      if (isStaleTaskStateEvent(event.timestamp)) {
        console.log('[TaskDetail] Ignore stale progress event:', event);
        return;
      }

      const progressRoadmapId =
        typeof event.data?.roadmap_id === 'string' && event.data.roadmap_id.length > 0
          ? event.data.roadmap_id
          : undefined;
      const previousRoadmapId = roadmapIdRef.current;
      
      // ✅ 修复：不再添加临时 WebSocket 日志，避免与数据库日志重复
      // 所有日志都应该从数据库查询，WebSocket 只负责触发刷新
      // 这样可以确保日志的一致性和唯一性
      
      // 更新 current_step，同时处理 human_review 状态的进出转换
      // 🔧 优化：将后端步骤映射到前端显示步骤，避免中间步骤导致UI闪烁
      if (event.step) {
        applyRealtimeTaskUpdate({
          eventAt: event.timestamp,
          step: event.step,
          roadmapId: progressRoadmapId,
          // progress 里的 completed 仅表示“当前节点完成”，不能直接覆盖任务总状态。
          status: getTaskStatusFromProgressEvent(event.step, event.status),
          deriveStatus: (prevStatus) => {
            if (event.step === WorkflowStep.HUMAN_REVIEW) {
              // 进入人工审核时，以审核态覆盖普通 processing。
              return TaskStatus.HUMAN_REVIEW;
            }

            if (prevStatus === TaskStatus.HUMAN_REVIEW) {
              // 离开人工审核后，恢复到 processing，避免 UI 长时间卡在审核面板。
              return TaskStatus.PROCESSING;
            }

            return undefined;
          },
        });
      }

      if (progressRoadmapId) {
        roadmapIdRef.current = progressRoadmapId;
      }

      if (
        progressRoadmapId &&
        previousRoadmapId !== progressRoadmapId &&
        event.step === WorkflowStep.INTENT_ANALYSIS &&
        event.status === 'completed'
      ) {
        loadIntentAnalysis(progressRoadmapId).catch((error) => {
          console.error('[TaskDetail] Failed to load intent analysis from progress event:', error);
        });
      }

      // 更新 edit_source（用于区分当前活跃分支）
      if (event.data?.edit_source) {
        setEditSource(event.data.edit_source);
        
        // 关键修复：roadmap_edit 完成时立即标记分支已触发
        // 不依赖 DB 日志（存在缓冲区延迟），直接从 WS 事件设置
        // 这样即使 getLogs 还未取到带 edit_source 的日志，UI 也能正确显示
        if (event.step === 'roadmap_edit' && event.status === 'completed') {
          if (event.data.edit_source === 'validation_failed') {
            setValidationBranchTriggered(true);
            console.log('[TaskDetail] validationBranchTriggered=true (from WS event)');
          } else if (event.data.edit_source === 'human_review') {
            setReviewBranchTriggered(true);
            console.log('[TaskDetail] reviewBranchTriggered=true (from WS event)');
          }
        }
      }

      // 当节点完成时，刷新日志和路线图
      if (event.status === 'completed' && event.step) {
        const shouldRefreshIntentAnalysis = event.step === 'intent_analysis';
        const shouldRefreshRoadmap = ['curriculum_design', 'roadmap_edit'].includes(event.step);

        scheduleTaskArtifactsRefresh({
          refreshLogs: true,
          refreshIntentAnalysis: shouldRefreshIntentAnalysis,
          refreshRoadmap: shouldRefreshRoadmap,
          syncRoadmapId: shouldRefreshIntentAnalysis || shouldRefreshRoadmap,
        });

        if (event.step === 'roadmap_edit' && event.data?.modified_concept_ids) {
          setModifiedNodeIds(prev => [
            ...prev,
            ...(event.data?.modified_concept_ids || []),
          ]);
        }
      }

      const isTerminalCompletedEvent =
        event.status === TaskStatus.COMPLETED &&
        event.step === WorkflowStep.COMPLETED;
      const isTerminalPartialFailureEvent =
        event.status === TaskStatus.PARTIAL_FAILURE &&
        event.step === WorkflowStep.CONTENT_GENERATION;

      if (isTerminalCompletedEvent || isTerminalPartialFailureEvent) {
        reconcileTerminalTaskArtifacts();
      }
    };

    const handleConceptStart = (event: any) => {
      console.log('[TaskDetail] Concept start:', event);
      setLoadingConceptIds(prev => [...prev, event.concept_id]);
      
      // ✅ 修复：不添加临时日志，避免重复
    };

    const handleConceptComplete = async (event: any) => {
      console.log('[TaskDetail] Concept complete:', event);
      
      // 🔧 优化：单项内容完成，不从 loading 列表移除（等待全部完成事件）
      const { concept_id, concept_name, content_type, data } = event;
      
      // ✅ 修复：不添加临时日志，避免重复
      
      // 🔧 优化：只更新对应的单项状态，不是全部标记为 completed
      // 根据 content_type 判断更新哪个状态字段
      setRoadmapFramework(prevRoadmap => {
        if (!prevRoadmap) return prevRoadmap;
        
        let conceptFound = false;
        
        // 创建新的 stages 数组，深度克隆所有层级
        const updatedStages = prevRoadmap.stages.map(stage => {
          const updatedModules = stage.modules.map(module => {
            const updatedConcepts = module.concepts.map(concept => {
              if (concept.concept_id === concept_id) {
                conceptFound = true;
                
                // 根据 content_type 只更新对应的状态
                const updates: any = { ...concept };
                
                if (content_type === 'tutorial') {
                  updates.content_status = 'completed' as const;
                } else if (content_type === 'resources') {
                  updates.resources_status = 'completed' as const;
                } else if (content_type === 'quiz') {
                  updates.quiz_status = 'completed' as const;
                } else {
                  // 如果没有指定 content_type，降级为全部完成（向后兼容）
                  updates.content_status = 'completed' as const;
                  updates.resources_status = 'completed' as const;
                  updates.quiz_status = 'completed' as const;
                }
                
                return updates;
              }
              return concept;
            });
            
            // 如果 concepts 有变化，创建新的 module 对象
            if (updatedConcepts.some((c, i) => c !== module.concepts[i])) {
              return { ...module, concepts: updatedConcepts };
            }
            return module;
          });
          
          // 如果 modules 有变化，创建新的 stage 对象
          if (updatedModules.some((m, i) => m !== stage.modules[i])) {
            return { ...stage, modules: updatedModules };
          }
          return stage;
        });
        
        if (conceptFound) {
          console.log(`[TaskDetail] Updated ${content_type || 'all'} status to completed:`, concept_name);
          // 创建新的 roadmap 对象
          return {
            ...prevRoadmap,
            stages: updatedStages,
          };
        }
        
        return prevRoadmap;
      });
    };
    
    const handleConceptAllContentComplete = async (event: any) => {
      console.log('[TaskDetail] Concept all content complete:', event);
      
      // 🆕 全部内容完成时，才从 loading 列表移除
      setLoadingConceptIds(prev => prev.filter(id => id !== event.concept_id));
      
      // ✅ 修复：不添加临时日志，避免重复
      
      // 刷新路线图数据以验证状态（后台同步）
      const currentRoadmapId = roadmapIdRef.current;
      if (currentRoadmapId) {
        scheduleTaskArtifactsRefresh({ refreshRoadmap: true }, 300);
      }
    };

    const handleConceptFailed = async (event: any) => {
      console.log('[TaskDetail] Concept failed:', event);
      setLoadingConceptIds(prev => prev.filter(id => id !== event.concept_id));

      // 记录失败的具体内容类型（tutorial/resources/quiz）
      const failedContentType = event.content_type as 'tutorial' | 'resources' | 'quiz' | undefined;
      if (failedContentType) {
        setFailedContentTypesMap(prev => {
          const existing = prev[event.concept_id] || [];
          if (existing.includes(failedContentType)) {
            return prev;
          }
          return {
            ...prev,
            [event.concept_id]: [...existing, failedContentType],
          };
        });
      }

      // 立即将对应 concept 的内容状态更新为 failed，避免弹层仍显示 pending
      setRoadmapFramework(prevRoadmap => {
        if (!prevRoadmap || !failedContentType) return prevRoadmap;

        let conceptFound = false;
        const updatedStages = prevRoadmap.stages.map(stage => {
          const updatedModules = stage.modules.map(module => {
            const updatedConcepts = module.concepts.map(concept => {
              if (concept.concept_id !== event.concept_id) {
                return concept;
              }

              conceptFound = true;
              if (failedContentType === 'tutorial') {
                return { ...concept, content_status: 'failed' as const };
              }
              if (failedContentType === 'resources') {
                return { ...concept, resources_status: 'failed' as const };
              }
              return { ...concept, quiz_status: 'failed' as const };
            });

            if (updatedConcepts.some((c, i) => c !== module.concepts[i])) {
              return { ...module, concepts: updatedConcepts };
            }
            return module;
          });

          if (updatedModules.some((m, i) => m !== stage.modules[i])) {
            return { ...stage, modules: updatedModules };
          }
          return stage;
        });

        if (!conceptFound) {
          return prevRoadmap;
        }

        return {
          ...prevRoadmap,
          stages: updatedStages,
        };
      });
      
      // 检查是否是部分失败
      const isPartialFailure = event.partial_failure === true || 
                                (event.details && event.details.partial_failure === true);
      
      if (isPartialFailure) {
        setPartialFailedConceptIds(prev => {
          if (!prev.includes(event.concept_id)) {
            return [...prev, event.concept_id];
          }
          return prev;
        });
      } else {
        setFailedConceptIds(prev => {
          if (!prev.includes(event.concept_id)) {
            return [...prev, event.concept_id];
          }
          return prev;
        });
      }
      
      // ✅ 修复：不添加临时日志，避免重复
      
      // 刷新路线图数据以更新concept状态
      const currentRoadmapId = roadmapIdRef.current;
      if (currentRoadmapId) {
        scheduleTaskArtifactsRefresh({ refreshRoadmap: true }, 300);
      }
    };

    const handleHumanReview = (event: any) => {
      console.log('[TaskDetail] Human review required:', event);
      applyRealtimeTaskUpdate({
        eventAt: event.timestamp,
        status: TaskStatus.HUMAN_REVIEW,
        step: WorkflowStep.HUMAN_REVIEW,
      });
    };

    const handleCompleted = (event: any) => {
      console.log('[TaskDetail] Task completed:', event);
      applyRealtimeTaskUpdate({
        eventAt: event.timestamp,
        status: TaskStatus.COMPLETED,
        step: WorkflowStep.COMPLETED,
      });
      reconcileTerminalTaskArtifacts();
      
      // ✅ 修复：不添加临时日志，避免重复
      // 完成状态的日志会从数据库查询获取
    };

    const handleFailed = (event: any) => {
      console.log('[TaskDetail] Task failed:', event);
      
      // 优先使用 message（包含错误类型），其次使用 error_detail（完整堆栈），最后使用 error
      const errorMessage = event.message || event.error_detail || event.error || 'Task failed';
      
      applyRealtimeTaskUpdate({
        eventAt: event.timestamp,
        status: TaskStatus.FAILED,
        step: WorkflowStep.FAILED,
        errorMessage,
      });
      reconcileTerminalTaskArtifacts();
      
      // ✅ 修复：不添加临时日志，避免重复
      // 失败状态的日志会从数据库查询获取
    };

    const handleError = (event: any) => {
      console.error('[TaskDetail] WebSocket error:', event);
    };

    // 创建 WebSocket 实例，使用包装后的处理器
    const websocket = new TaskWebSocket(taskId, {
      onStatus: handleStatus,
      onProgress: handleProgress,
      onConceptStart: handleConceptStart,
      onConceptComplete: handleConceptComplete,
      onConceptAllContentComplete: handleConceptAllContentComplete,
      onConceptFailed: handleConceptFailed,
      onHumanReview: handleHumanReview,
      onCompleted: handleCompleted,
      onFailed: handleFailed,
      onError: handleError,
    });

    websocket.connect(true);
    setWs(websocket);

    return () => {
      websocket.disconnect();
    };
  // 优化：移除 taskInfo?.current_step 依赖
  // current_step 变化（每个节点完成）不应触发 WS 重连
  // WS 只需在 taskId 或任务状态（active/inactive 转换）变化时重建
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId, taskInfo?.status, taskInfo?.roadmap_id, loadIntentAnalysis, reconcileTerminalTaskArtifacts, scheduleTaskArtifactsRefresh]);

  /**
   * 在 starting 阶段启用短轮询兜底。
   *
   * 触发条件：
   * - 任务已进入 processing
   * - 前端仍显示 starting
   *
   * 目的：
   * - 如果 WebSocket 在极早期阶段漏掉了 intent_analysis 进度事件，
   *   通过数据库状态将 UI 迅速追平，避免长时间停留在 starting。
   */
  useEffect(() => {
    if (!taskId || !taskInfo) {
      return;
    }

    const shouldPollStartingState =
      taskInfo.status === TaskStatus.PROCESSING &&
      taskInfo.current_step === WorkflowStep.STARTING;

    if (!shouldPollStartingState) {
      return;
    }

    let isCancelled = false;

    const syncTaskStatus = async () => {
      try {
        const latestTask = await tasksApi.getById(taskId);
        if (isCancelled) {
          return;
        }

        const title = taskInfo.title || t('generatingRoadmap');
        applyTaskSnapshot(latestTask, title);
      } catch (err) {
        if (!isCancelled) {
          console.error('[TaskDetail] Failed to poll task status during starting phase:', err);
        }
      }
    };

    void syncTaskStatus();
    const intervalId = window.setInterval(syncTaskStatus, 2000);

    return () => {
      isCancelled = true;
      window.clearInterval(intervalId);
    };
  }, [applyTaskSnapshot, taskId, taskInfo, t]);

  /**
   * 获取编辑记录（modified_node_ids）
   * 
   * 注意：EditRecordResponse不包含modified_node_ids字段
   * 该字段通过WebSocket事件（progress事件中的modified_concept_ids）获取
   * 因此不再需要从API获取
   */
  // useEffect已禁用 - modified_node_ids通过WebSocket获取

  /**
   * Human Review 完成回调
   */
  const handleHumanReviewComplete = useCallback(async () => {
    // 刷新任务状态
    if (taskId) {
      try {
        const taskData = await tasksApi.getById(taskId);
        const title = taskInfo?.title || t('generatingRoadmap');
        applyTaskSnapshot(taskData, title);
      } catch (err) {
        console.error('Failed to refresh task after review:', err);
      }
    }
  }, [applyTaskSnapshot, taskId, taskInfo?.title, t]);


  /**
   * 判断是否正在编辑路线图
   */
  const isEditingRoadmap = useMemo(() => {
    return taskInfo?.current_step === 'roadmap_edit';
  }, [taskInfo?.current_step]);

  const isTaskQueued = useMemo(() => {
    if (!taskInfo) {
      return false;
    }

    return taskInfo.status === TaskStatus.PENDING || taskInfo.current_step === WorkflowStep.QUEUED;
  }, [taskInfo]);

  const requestPreferences = taskInfo?.user_request?.preferences;
  const requestPreferenceTags = useMemo(() => {
    if (!requestPreferences) {
      return [];
    }
    const tags: string[] = [];
    if (requestPreferences.content_preference?.length) {
      tags.push(...requestPreferences.content_preference);
    }
    if (requestPreferences.primary_language) {
      tags.push(`primary:${requestPreferences.primary_language}`);
    }
    if (requestPreferences.secondary_language) {
      tags.push(`secondary:${requestPreferences.secondary_language}`);
    }
    if (requestPreferences.preferred_language) {
      tags.push(`preferred:${requestPreferences.preferred_language}`);
    }
    return tags;
  }, [requestPreferences]);

  // ========================================
  // 优化：分区域骨架屏加载，提供更好的加载体验
  // ========================================
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        {/* Header Skeleton */}
        <header className="sticky top-0 z-50 border-b border-sage-200/60 bg-gradient-to-b from-sage-50/95 via-background/95 to-background/90 shadow-sm backdrop-blur-md dark:border-sage-900/40 dark:from-sage-950/80 dark:via-gray-950/85 dark:to-gray-950/75">
          <div className="max-w-7xl mx-auto px-6 py-5">
            {/* 顶部操作栏骨架 */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Skeleton className="h-9 w-24 rounded-md" />
                <div className="w-px h-5 bg-border" />
                <Skeleton className="h-9 w-24 rounded-md" />
              </div>
              <Skeleton className="h-8 w-32 rounded-full" />
            </div>
            
            {/* 标题区域骨架 */}
            <div className="space-y-2">
              <Skeleton className="h-8 w-full max-w-2xl" />
              <Skeleton className="h-5 w-48" />
            </div>
          </div>
        </header>

        {/* Main Content Skeleton */}
        <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
          {/* Workflow Progress Skeleton */}
          <Card className="p-6 border-sage-200/80 bg-gradient-to-r from-sage-50/60 to-white dark:from-sage-900/20 dark:to-gray-900">
            <div className="space-y-4">
              <Skeleton className="h-6 w-64" />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Skeleton className="h-24 rounded-lg" />
                <Skeleton className="h-24 rounded-lg" />
                <Skeleton className="h-24 rounded-lg" />
              </div>
            </div>
          </Card>

          {/* Workflow Progress Skeleton */}
          <Card className="p-6">
            <div className="space-y-4">
              <Skeleton className="h-6 w-48" />
              <div className="flex items-center justify-between gap-4">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="flex flex-col items-center space-y-2">
                    <Skeleton className="w-12 h-12 rounded-full" />
                    <Skeleton className="h-4 w-16" />
                  </div>
                ))}
              </div>
            </div>
          </Card>

          {/* Core Display Area Skeleton */}
          <Card className="p-6">
            <Skeleton className="h-6 w-56 mb-4" />
            <div className="flex gap-6">
              {/* Intent Analysis Skeleton */}
              <div className="w-[280px] space-y-4">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <div className="flex gap-2">
                  <Skeleton className="h-6 w-16 rounded-full" />
                  <Skeleton className="h-6 w-16 rounded-full" />
                  <Skeleton className="h-6 w-16 rounded-full" />
                </div>
                <div className="grid grid-cols-2 gap-4 pt-3">
                  <Skeleton className="h-16 rounded" />
                  <Skeleton className="h-16 rounded" />
                </div>
              </div>
              
              {/* Roadmap Skeleton */}
              <div className="flex-1 space-y-4">
                <Skeleton className="h-5 w-40" />
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-center gap-4">
                      <Skeleton className="h-8 w-24 rounded-full" />
                      <div className="flex gap-2">
                        <Skeleton className="h-7 w-20 rounded-full" />
                        <Skeleton className="h-7 w-20 rounded-full" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Card>

          {/* Execution Log Skeleton */}
          <Card className="p-6">
            <Skeleton className="h-6 w-40 mb-4" />
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </Card>
        </div>
      </div>
    );
  }

  // 错误状态
  if (error || !taskInfo) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <Card className="max-w-md w-full p-6">
          <div className="text-center space-y-4">
            <AlertCircle className="w-12 h-12 text-red-600 mx-auto" />
            <div>
              <h2 className="text-lg font-semibold">{t('taskNotFound')}</h2>
              <p className="text-sm text-muted-foreground mt-1">
                {error || t('taskNotFoundDesc')}
              </p>
            </div>
            <Button onClick={() => router.push('/tasks')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              {t('backToTasks')}
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header - 重新设计版 */}
      <header className="sticky top-0 z-50 border-b border-sage-200/60 bg-gradient-to-b from-sage-50/95 via-background/95 to-background/90 shadow-sm backdrop-blur-md dark:border-sage-900/40 dark:from-sage-950/80 dark:via-gray-950/85 dark:to-gray-950/75">
        <div className="max-w-7xl mx-auto px-6 py-5">
          {/* 顶部操作栏 */}
          <div className="flex items-center mb-4">
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push('/tasks')}
                className="gap-2 hover:bg-sage-50 dark:hover:bg-sage-900/20"
              >
                <ArrowLeft className="w-4 h-4" />
                {t('back')}
              </Button>
            </div>
            
          </div>
          
          {/* 标题区域 */}
          <div className="space-y-2">
            <h1 className="text-2xl font-serif font-bold text-foreground leading-tight line-clamp-2" title={taskInfo.title}>
              {taskInfo.title}
            </h1>
            
            {/* 元信息 */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="w-4 h-4" />
              <time>
                {taskInfo.created_at 
                  ? new Date(taskInfo.created_at).toLocaleDateString(locale === 'zh' ? 'zh-CN' : 'en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })
                  : t('userRequest.unknown')}
              </time>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - 三段式布局 */}
      <div className="max-w-7xl mx-auto space-y-6 bg-gradient-to-b from-sage-50/40 via-background to-background px-6 py-8 dark:from-sage-950/20">
        {/* 0. Original Request Info（原始请求信息） - Redesigned v2 */}
        <div className="group relative overflow-hidden rounded-xl border border-sage-200/70 bg-gradient-to-br from-sage-50/95 via-white/90 to-sage-100/60 shadow-sm backdrop-blur-sm transition-all hover:border-sage-300/80 hover:shadow-md dark:border-sage-900/40 dark:from-sage-950/35 dark:via-gray-900/75 dark:to-sage-900/20">
          {/* 装饰背景 */}
          <div className="absolute top-0 right-0 -mt-16 -mr-16 w-64 h-64 bg-sage-100/30 dark:bg-sage-900/10 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
          
          <div className="relative p-6 space-y-6">
            {/* Header: 学习目标 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                <Target className="w-4 h-4 text-sage-600 dark:text-sage-400" />
                <span>{t('userRequest.learningGoal')}</span>
              </div>
              <h2 className="text-xl md:text-2xl font-serif font-medium text-foreground leading-relaxed text-balance">
                “{requestPreferences?.learning_goal || taskInfo.title || t('userRequest.noGoalSet')}”
              </h2>
            </div>

            <div className="h-px w-full bg-gradient-to-r from-transparent via-border to-transparent opacity-50" />

            {/* Content Grid - 左右分栏优化 */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12">
              
              {/* Left Column: Profile & Stats (占比更大) */}
              <div className="lg:col-span-7 space-y-8">
                
                {/* User Persona & Motivation */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    <UserRound className="w-3.5 h-3.5" />
                    <span>{t('userRequest.profileMotivation')}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {/* 职业与行业 */}
                    {[
                      requestPreferences?.current_role,
                      requestPreferences?.career_background,
                      requestPreferences?.industry
                    ].map(formatText).filter(Boolean).map((tag, i) => (
                      <Badge 
                        key={`role-${i}`} 
                        variant="secondary" 
                        className="px-3 py-1 bg-sage-50/80 hover:bg-sage-100 text-sage-900 border-sage-200 dark:bg-sage-900/30 dark:text-sage-100 dark:border-sage-800 transition-colors"
                      >
                        {tag}
                      </Badge>
                    ))}
                    
                    {/* 动机 (作为特殊的 Badge) */}
                    {requestPreferences?.motivation && (
                      <Badge 
                        variant="outline" 
                        className="px-3 py-1 border-amber-200 bg-amber-50/50 text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-300 gap-1.5"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                        {requestPreferences.motivation}
                      </Badge>
                    )}

                    {![requestPreferences?.current_role, requestPreferences?.career_background, requestPreferences?.industry, requestPreferences?.motivation].some(Boolean) && (
                      <span className="text-sm text-muted-foreground italic">{t('userRequest.noProfileProvided')}</span>
                    )}
                  </div>
                </div>

                {/* Stats Grid (Moved here for better balance) */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  {/* Weekly Hours */}
                  <div className="flex min-h-[80px] flex-col justify-between rounded-xl border border-sage-200/60 bg-white/70 p-3.5 shadow-sm dark:border-sage-900/40 dark:bg-gray-900/60">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] uppercase text-muted-foreground font-medium tracking-wider">{t('userRequest.weeklyInput')}</span>
                      <Clock className="w-3.5 h-3.5 text-sage-500" />
                    </div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-2xl font-semibold tracking-tight tabular-nums text-foreground">
                        {requestPreferences?.available_hours_per_week || '-'}
                      </span>
                      <span className="text-xs text-muted-foreground font-medium">{t('userRequest.hrs')}</span>
                    </div>
                  </div>

                  {/* Current Level */}
                  <div className="flex min-h-[80px] flex-col justify-between rounded-xl border border-sage-200/60 bg-white/70 p-3.5 shadow-sm dark:border-sage-900/40 dark:bg-gray-900/60">
                     <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] uppercase text-muted-foreground font-medium tracking-wider">{t('userRequest.startLevel')}</span>
                      <div className="flex gap-0.5">
                        {[1, 2, 3].map(i => (
                          <div 
                            key={i} 
                            className={`w-1 h-2 rounded-[1px] ${
                              (requestPreferences?.current_level === 'advanced' && i <= 3) ||
                              (requestPreferences?.current_level === 'intermediate' && i <= 2) ||
                              (requestPreferences?.current_level === 'beginner' && i <= 1)
                                ? 'bg-sage-500' 
                                : 'bg-muted/50'
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                    <div className="text-sm font-medium text-foreground">
                      {formatText(requestPreferences?.current_level) || t('beginner')}
                    </div>
                  </div>

                  {/* Turbo Mode (If active) */}
                  {taskInfo.turbo_mode && (
                    <div className="p-3.5 rounded-xl bg-gradient-to-br from-blue-50/50 to-indigo-50/50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-100 dark:border-blue-900/50 shadow-sm flex flex-col justify-between min-h-[80px]">
                      <div className="flex items-center justify-between mb-2">
                         <span className="text-[10px] uppercase text-blue-600/70 dark:text-blue-400/70 font-medium tracking-wider">{t('userRequest.mode')}</span>
                         <span className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                        </span>
                      </div>
                      <div className="text-sm font-medium text-blue-700 dark:text-blue-300">
                        {t('userRequest.turboActive')}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Preferences & Context */}
              <div className="lg:col-span-5 space-y-6 lg:border-l lg:border-border/40 lg:pl-8">
                
                {/* Learning Preferences */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    <SlidersHorizontal className="w-3.5 h-3.5" />
                    <span>{t('userRequest.preferences')}</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {/* Content Formats */}
                    {(requestPreferences?.content_preference || []).map((item) => (
                      <Badge key={item} variant="outline" className="px-2.5 py-1 text-xs font-normal border-dashed text-muted-foreground bg-transparent hover:bg-muted/50">
                        {formatPreference(item, t)}
                      </Badge>
                    ))}
                    {/* Languages */}
                    {[
                      requestPreferences?.primary_language ? `primary:${requestPreferences.primary_language}` : null,
                      requestPreferences?.secondary_language ? `secondary:${requestPreferences.secondary_language}` : null
                    ].filter(Boolean).map((tag) => (
                      <Badge key={tag} variant="outline" className="px-2.5 py-1 text-xs font-normal border-amber-200/50 bg-amber-50/30 text-amber-700 dark:border-amber-900/50 dark:bg-amber-900/10 dark:text-amber-400">
                        {formatLanguage(tag!, t)}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Additional Context */}
                {taskInfo.user_request?.additional_context && (
                  <div className="space-y-3 pt-2">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{t('userRequest.context')}</p>
                    <p className="text-sm text-muted-foreground/90 leading-relaxed bg-muted/30 p-3.5 rounded-xl border border-border/50 text-justify">
                      {taskInfo.user_request.additional_context}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {isTaskQueued && (
          <Card className="border-amber-200 bg-amber-50/60 dark:border-amber-900/50 dark:bg-amber-900/10">
            <div className="p-4 sm:p-5">
              <div className="flex items-start gap-3">
                <Clock className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-amber-900 dark:text-amber-200">
                    {t('queueStatusTitle')}
                  </p>
                  <p className="text-sm text-amber-800/90 dark:text-amber-300/90">
                    {typeof taskInfo.queue_ahead_count === 'number' && taskInfo.queue_ahead_count > 0
                      ? t('queueAheadMessage', { count: taskInfo.queue_ahead_count })
                      : t('queueNoAheadMessage')}
                  </p>
                  <p className="text-xs text-amber-700/80 dark:text-amber-400/80">
                    {t('queueHint')}
                  </p>
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* 1. Workflow Progress（拓扑图版） */}
        <WorkflowTopology
          currentStep={taskInfo.current_step || null}
          status={taskInfo.status}
          editSource={editSource}
          taskId={taskId}
          roadmapId={taskInfo.roadmap_id || null}
          roadmapTitle={roadmapFramework?.title || taskInfo.title}
          stagesCount={roadmapFramework?.stages?.length || 0}
          totalConcepts={roadmapFramework?.stages?.reduce((acc, s) => acc + s.modules.reduce((ma, m) => ma + m.concepts.length, 0), 0) ?? 0}
          executionLogs={executionLogs}
          workflowLogs={workflowLogs}
          validationBranchTriggered={validationBranchTriggered}
          reviewBranchTriggered={reviewBranchTriggered}
          onHumanReviewComplete={handleHumanReviewComplete}
          selectedNodeId={selectedNodeId}
          onNodeSelect={setSelectedNodeId}
          turboMode={taskInfo.turbo_mode ?? true}
        />

        {/* 2. Core Display Area（需求分析 + 路线图） */}
        <CoreDisplayArea
          currentStep={taskInfo.current_step || null}
          status={taskInfo.status}
          taskId={taskId}
          roadmapId={taskInfo.roadmap_id || null}
          intentAnalysis={intentAnalysis}
          roadmapFramework={roadmapFramework}
          isEditingRoadmap={isEditingRoadmap}
          modifiedNodeIds={modifiedNodeIds}
          loadingConceptIds={loadingConceptIds}
          failedConceptIds={failedConceptIds}
          partialFailedConceptIds={partialFailedConceptIds}
          failedContentTypesMap={failedContentTypesMap}
          onRetrySuccess={handleRetrySuccess}
          maxHeight={500}
        />

        {/* 3. Execution Log Timeline（执行日志时间轴） */}
        <ExecutionLogTimeline
          logs={executionLogs}
        />

        {/* Error Message (if completely failed) */}
        {taskInfo.status === 'failed' && taskInfo.error_message && (
          <Card className="border-red-200 bg-red-50/50">
            <div className="p-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                <div className="space-y-1 flex-1">
                  <h3 className="font-medium text-red-900">{t('taskFailed')}</h3>
                  <p className="text-sm text-red-700">{taskInfo.error_message}</p>
                </div>
              </div>
            </div>
          </Card>
        )}
      </div>

    </div>
  );
}

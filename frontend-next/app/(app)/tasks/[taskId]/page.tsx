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
import { ArrowLeft, AlertCircle, CheckCircle2, Loader2, Clock, Eye, RefreshCw, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { TaskWebSocket } from '@/lib/api/websocket';
import { getTaskDetail, getTaskLogs, getRoadmap, getIntentAnalysis, getUserProfile, cancelTask } from '@/lib/api/endpoints';
import { WorkflowTopology } from '@/components/task/workflow-topology';
import { CoreDisplayArea } from '@/components/task/core-display-area';
import { ExecutionLogTimeline } from '@/components/task/execution-log-timeline';
import { cn } from '@/lib/utils';
import { limitLogsByStep, getLogStatsByStep } from '@/lib/utils/log-grouping';
import { useAuthStore } from '@/lib/store/auth-store';
import type { RoadmapFramework, LearningPreferences } from '@/types/generated/models';

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
 * 执行日志类型
 */
interface ExecutionLog {
  id: string;
  task_id: string;
  level: 'debug' | 'info' | 'success' | 'warning' | 'error';
  category: string;
  step: string | null;
  agent_name: string | null;
  message: string;
  details: any;
  duration_ms: number | null;
  created_at: string;
}

/**
 * 任务信息类型
 */
interface TaskInfo {
  task_id: string;
  title: string;
  status: string;
  current_step: string | null;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  error_message?: string | null;
  roadmap_id?: string | null;
}

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params?.taskId as string;
  const { getUserId } = useAuthStore();
  
  // TanStack Query Client - 用于预填充路线图缓存，加速页面跳转
  const queryClient = useQueryClient();

  // 任务基本信息
  const [taskInfo, setTaskInfo] = useState<TaskInfo | null>(null);

  // 用户学习偏好（用于重试功能）
  const [userPreferences, setUserPreferences] = useState<LearningPreferences | undefined>(undefined);

  // 执行日志
  const [executionLogs, setExecutionLogs] = useState<ExecutionLog[]>([]);

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

  // 编辑来源（用于区分分支）
  const [editSource, setEditSource] = useState<'validation_failed' | 'human_review' | null>(null);

  // 加载状态
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 节点选中状态（用于侧边面板）
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // 取消任务确认对话框
  const [showCancelDialog, setShowCancelDialog] = useState(false);

  // WebSocket 连接
  const [ws, setWs] = useState<TaskWebSocket | null>(null);
  
  // 使用ref存储最新的roadmap_id，确保在WebSocket事件处理器中能获取到最新值
  const roadmapIdRef = useRef<string | null>(null);

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
   */
  const loadIntentAnalysis = useCallback(async (taskId: string, signal?: AbortSignal) => {
    try {
      const intentData = await getIntentAnalysis(taskId, signal);
      
      console.log('[TaskDetail] Intent analysis loaded successfully:', {
        task_id: taskId,
        has_data: !!intentData,
        parsed_goal_length: intentData?.parsed_goal?.length,
        key_technologies_count: intentData?.key_technologies?.length,
      });
      
      // 从 time_constraint 解析时间信息
      const { weeks, hoursPerWeek } = parseTimeConstraint(intentData.time_constraint || '');
      
      // 转换为前端需要的格式
      const intentOutput: IntentAnalysisOutput = {
        learning_goal: intentData.parsed_goal,
        key_technologies: intentData.key_technologies,
        difficulty_level: intentData.difficulty_profile,
        estimated_duration_weeks: weeks,
        estimated_hours_per_week: hoursPerWeek,
        skill_gaps: intentData.skill_gap_analysis.map(gap => ({
          skill_name: gap,
          current_level: 'beginner',
          required_level: 'intermediate',
        })),
        learning_strategies: intentData.personalized_suggestions,
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
        task_id: taskId,
        error: err,
        status: err.response?.status,
        message: err.response?.data?.detail || err.message,
      });
      
      // 如果获取失败，不设置数据（保持为 null）
      return null;
    }
  }, []);

  /**
   * 从路线图框架中提取概念的加载/失败状态
   * 
   * 用于在刷新时从最新的路线图数据中重建状态，而不依赖 WebSocket 事件
   */
  const extractConceptStates = useCallback((roadmap: RoadmapFramework) => {
    const loading: string[] = [];
    const failed: string[] = [];
    const partialFailed: string[] = [];
    
    roadmap.stages.forEach(stage => {
      stage.modules.forEach(module => {
        module.concepts.forEach(concept => {
          const conceptId = concept.concept_id;
          const statuses = [
            concept.content_status,
            concept.resources_status,
            concept.quiz_status,
          ];
          
          // 判断是否有任何内容正在生成
          const isGenerating = statuses.some(s => s === 'generating');
          if (isGenerating) {
            loading.push(conceptId);
            return;
          }
          
          // 判断失败状态
          const failedCount = statuses.filter(s => s === 'failed').length;
          const completedCount = statuses.filter(s => s === 'completed').length;
          
          if (failedCount === 3) {
            // 全部失败
            failed.push(conceptId);
          } else if (failedCount > 0 && completedCount > 0) {
            // 部分失败（有成功有失败）
            partialFailed.push(conceptId);
          }
        });
      });
    });
    
    return { loading, failed, partialFailed };
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
      const roadmapData = await getRoadmap(roadmapId, signal);
      if (roadmapData) {
        setRoadmapFramework(roadmapData);
        
        // 🚀 关键优化：预填充 TanStack Query 缓存
        // 这样跳转到 /roadmap/[id] 时可以直接使用缓存数据，无需重新请求
        queryClient.setQueryData(['roadmap', roadmapId], roadmapData);
        console.log('[TaskDetail] Prefilled roadmap cache for instant navigation');
        
        // 如果需要更新概念状态（刷新时使用）
        if (updateConceptStates) {
          const { loading, failed, partialFailed } = extractConceptStates(roadmapData);
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
  }, [extractConceptStates, queryClient]);

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

      // ========================================
      // 优化：并行化所有独立请求，减少总加载时间
      // ========================================
      const [taskData, agentLogsData, workflowLogsData, intentData] = await Promise.all([
        getTaskDetail(taskId, signal),
        getTaskLogs(taskId, undefined, 'agent', 200, 0, signal),   // 从 1000 降至 200
        getTaskLogs(taskId, undefined, 'workflow', 200, 0, signal), // 从 1000 降至 200
        loadIntentAnalysis(taskId, signal).catch(() => null), // 允许失败，不阻塞主流程
      ]);
      
      setTaskInfo(taskData);
      // 更新ref中的roadmap_id
      roadmapIdRef.current = taskData.roadmap_id || null;
      
      const allLogs = [
        ...(agentLogsData.logs || []),
        ...(workflowLogsData.logs || []),
      ];
      
      // 按 step 分组，每个 step 最多 100 条
      const limitedLogs = limitLogsByStep(allLogs, 100);
      
      // 打印统计信息（开发调试用）
      if (process.env.NODE_ENV === 'development') {
        const stats = getLogStatsByStep(allLogs);
        console.log('[TaskDetail] Log stats by step:', stats);
        console.log('[TaskDetail] Total logs:', allLogs.length, '→ Limited to:', limitedLogs.length);
      }
      
      setExecutionLogs(limitedLogs);
      
      // 从执行日志中提取最新的 edit_source（用于区分工作流分支）
      const latestEditSource = allLogs
        .filter(log => 
          (log.step === 'roadmap_edit' || log.step === 'edit_plan_analysis') && 
          log.details?.edit_source
        )
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        [0]?.details?.edit_source || null;
      
      if (latestEditSource) {
        setEditSource(latestEditSource);
        console.log('[TaskDetail] Extracted edit_source from logs:', latestEditSource);
      }

      // 如果有 roadmap_id，并行加载路线图框架和编辑记录
      if (taskData.roadmap_id) {
        const loadRoadmapPromise = loadRoadmapFramework(taskData.roadmap_id, !isInitialLoad, signal);
        
        // 刷新时也重新加载修改记录
        const loadEditRecordPromise = !isInitialLoad && taskData.current_step && [
          'structure_validation',
          'human_review',
          'human_review_pending',
          'content_generation',
          'completed',
          'partial_failure'
        ].includes(taskData.current_step)
          ? (async () => {
              try {
                const { getLatestEdit } = await import('@/lib/api/endpoints');
                const editData = await getLatestEdit(taskId);
                if (editData?.modified_node_ids) {
                  setModifiedNodeIds(editData.modified_node_ids);
                  console.log('[TaskDetail] Refreshed modified_node_ids:', editData.modified_node_ids);
                }
              } catch (err) {
                console.log('[TaskDetail] No edit record found:', err);
              }
            })()
          : Promise.resolve();
        
        // 并行等待路线图和编辑记录加载
        await Promise.all([loadRoadmapPromise, loadEditRecordPromise]);
      }

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
   * 优化：添加请求取消机制，在组件卸载或taskId变化时取消请求
   */
  useEffect(() => {
    if (!taskId) return;
    
    const controller = new AbortController();
    loadTaskData(true, controller.signal);
    
    return () => {
      controller.abort();
    };
  }, [taskId, loadTaskData]);

  /**
   * 加载用户偏好（用于重试功能）
   */
  useEffect(() => {
    const loadUserPreferences = async () => {
      const userId = getUserId();
      if (!userId) return;
      
      try {
        const profile = await getUserProfile(userId);
        // 构建 LearningPreferences 对象
        setUserPreferences({
          learning_goal: taskInfo?.title || roadmapFramework?.title || 'Learning',
          available_hours_per_week: profile.weekly_commitment_hours || 10,
          current_level: 'intermediate', // 默认值
          career_background: profile.current_role || 'Not specified',
          motivation: 'Continue learning',
          content_preference: (profile.learning_style || ['text', 'visual']) as any,
          preferred_language: profile.primary_language || 'zh-CN',
        });
      } catch (error) {
        console.error('[TaskDetail] Failed to load user preferences:', error);
      }
    };
    
    if (taskInfo || roadmapFramework) {
      loadUserPreferences();
    }
  }, [taskInfo, roadmapFramework, getUserId]);

  /**
   * 重试成功回调
   */
  const handleRetrySuccess = useCallback(() => {
    // 刷新任务数据以获取最新状态
    if (taskId) {
      loadTaskData(false);
    }
  }, [taskId, loadTaskData]);

  /**
   * 手动刷新任务数据
   */
  const handleRefresh = useCallback(() => {
    loadTaskData(false);
  }, [loadTaskData]);

  /**
   * 取消任务
   */
  const handleCancelConfirm = useCallback(async () => {
    try {
      setShowCancelDialog(false);
      await cancelTask(taskId);
      
      // 更新本地状态（保留 current_step，只更新 status）
      setTaskInfo((prev) => prev ? {
        ...prev,
        status: 'cancelled',
        // 保留 current_step，不修改它
      } : null);
      
      // 断开 WebSocket 连接
      ws?.disconnect();
      
      // 刷新任务数据
      setTimeout(() => {
        loadTaskData(false);
      }, 1000);
      
    } catch (error: any) {
      console.error('Failed to cancel task:', error);
      alert('Failed to cancel task. Please try again later.');
    }
  }, [taskId, ws, loadTaskData]);

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

    // ========================================
    // 智能轮询兜底机制：仅在 WebSocket 连接失败时启用
    // ========================================
    // 策略：
    // 1. 只在 WebSocket 连接失败或长时间无消息时启用轮询
    // 2. 使用指数退避策略，减少轮询频率（30秒 -> 60秒 -> 120秒）
    // 3. 如果 WebSocket 连接成功，立即停止轮询
    let pollingInterval: NodeJS.Timeout | null = null;
    let lastWebSocketMessageTime = Date.now();
    let pollingAttempts = 0;
    const MAX_POLLING_INTERVAL = 120000; // 最大轮询间隔：2分钟
    const INITIAL_POLLING_INTERVAL = 30000; // 初始轮询间隔：30秒
    const WS_SILENCE_THRESHOLD = 180000; // WebSocket 静默阈值：3分钟无消息则启动轮询
    
    // 定义原始处理器函数
    const handleStatus = (event: any) => {
      console.log('[TaskDetail] Status update:', event);
      if (event.current_step) {
        setTaskInfo((prev) => prev ? { ...prev, current_step: event.current_step } : null);
      }
      if (event.status) {
        setTaskInfo((prev) => prev ? { ...prev, status: event.status } : null);
      }
      if (event.roadmap_id) {
        setTaskInfo((prev) => prev ? { ...prev, roadmap_id: event.roadmap_id } : null);
        roadmapIdRef.current = event.roadmap_id;
      }
    };

    const handleProgress = async (event: any) => {
      console.log('[TaskDetail] Progress update:', event);
      
      // 更新最后消息时间并停止轮询
      lastWebSocketMessageTime = Date.now();
      pollingAttempts = 0;
      if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
        console.log('[TaskDetail] WebSocket message received, stopped fallback polling');
      }
      
      // 添加实时日志
      const newLog: ExecutionLog = {
        id: `ws-${Date.now()}`,
        task_id: taskId,
        level: event.status === 'completed' ? 'success' : 'info',
        category: 'workflow',
        step: event.step || null,
        agent_name: null,
        message: event.message || `Step: ${event.step}`,
        details: event,
        duration_ms: null,
        created_at: new Date().toISOString(),
      };
      
      setExecutionLogs((prev) => [...prev, newLog]);
      
      // 更新 current_step
      if (event.step) {
        setTaskInfo((prev) => prev ? { ...prev, current_step: event.step } : null);
      }

      // 更新 edit_source（用于区分分支）
      if (event.data?.edit_source) {
        setEditSource(event.data.edit_source);
      }
      
      // 当节点完成时，刷新日志和路线图
      if (event.status === 'completed' && event.step) {
        try {
          // 只获取 agent 和 workflow 类型的日志，排除 concept 日志
          const [agentLogsData, workflowLogsData] = await Promise.all([
            getTaskLogs(taskId, undefined, 'agent', 1000),
            getTaskLogs(taskId, undefined, 'workflow', 1000),
          ]);
          const allLogs = [
            ...(agentLogsData.logs || []),
            ...(workflowLogsData.logs || []),
          ];
          const limitedLogs = limitLogsByStep(allLogs, 100);
          setExecutionLogs(limitedLogs);
          
          // 重新加载需求分析数据（使用最新的数据库数据）
          await loadIntentAnalysis(taskId);
          
          // 如果是 curriculum_design 或 roadmap_edit 完成，重新加载路线图
          if (['curriculum_design', 'roadmap_edit'].includes(event.step)) {
            const currentRoadmapId = taskInfo.roadmap_id;
            if (currentRoadmapId) {
              await loadRoadmapFramework(currentRoadmapId);
            }
            
            // 如果是 roadmap_edit 完成，从事件中提取修改的节点
            if (event.step === 'roadmap_edit' && event.data?.modified_concept_ids) {
              setModifiedNodeIds(prev => [
                ...prev,
                ...(event.data?.modified_concept_ids || []),
              ]);
            }
          }
        } catch (err) {
          console.error('Failed to refresh data after node completion:', err);
        }
      }
    };

    const handleConceptStart = (event: any) => {
      lastWebSocketMessageTime = Date.now();
      console.log('[TaskDetail] Concept start:', event);
      setLoadingConceptIds(prev => [...prev, event.concept_id]);
      
      const newLog: ExecutionLog = {
        id: `ws-concept-start-${Date.now()}`,
        task_id: taskId,
        level: 'info',
        category: 'workflow',
        step: 'content_generation',
        agent_name: null,
        message: `Started generating content for: ${event.concept_name}`,
        details: event,
        duration_ms: null,
        created_at: new Date().toISOString(),
      };
      setExecutionLogs((prev) => [...prev, newLog]);
    };

    const handleConceptComplete = async (event: any) => {
      lastWebSocketMessageTime = Date.now();
      console.log('[TaskDetail] Concept complete:', event);
      setLoadingConceptIds(prev => prev.filter(id => id !== event.concept_id));
      
      const newLog: ExecutionLog = {
        id: `ws-concept-complete-${Date.now()}`,
        task_id: taskId,
        level: 'success',
        category: 'workflow',
        step: 'content_generation',
        agent_name: null,
        message: `Completed: ${event.concept_name}`,
        details: event,
        duration_ms: null,
        created_at: new Date().toISOString(),
      };
      setExecutionLogs((prev) => [...prev, newLog]);
      
      // 立即更新本地状态，避免等待后端数据库更新
      setRoadmapFramework(prevRoadmap => {
        if (!prevRoadmap) return prevRoadmap;
        
        const updatedRoadmap = { ...prevRoadmap };
        // 查找并更新对应的 concept
        for (const stage of updatedRoadmap.stages) {
          for (const module of stage.modules) {
            const concept = module.concepts.find(c => c.concept_id === event.concept_id);
            if (concept) {
              // 将所有状态设置为 completed
              concept.content_status = 'completed';
              concept.resources_status = 'completed';
              concept.quiz_status = 'completed';
              console.log('[TaskDetail] Updated concept status to completed:', concept.name);
              return updatedRoadmap;
            }
          }
        }
        return prevRoadmap;
      });
      
      // 刷新路线图数据以验证状态（后台同步）
      const currentRoadmapId = roadmapIdRef.current;
      if (currentRoadmapId) {
        try {
          await loadRoadmapFramework(currentRoadmapId);
        } catch (err) {
          console.error('[TaskDetail] Failed to refresh roadmap after concept complete:', err);
        }
      }
    };

    const handleConceptFailed = async (event: any) => {
      lastWebSocketMessageTime = Date.now();
      console.log('[TaskDetail] Concept failed:', event);
      setLoadingConceptIds(prev => prev.filter(id => id !== event.concept_id));
      
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
      
      const newLog: ExecutionLog = {
        id: `ws-concept-failed-${Date.now()}`,
        task_id: taskId,
        level: isPartialFailure ? 'warning' : 'error',
        category: 'workflow',
        step: 'content_generation',
        agent_name: null,
        message: isPartialFailure 
          ? `Partially failed: ${event.concept_name} - ${event.error || 'Some content generation failed'}`
          : `Failed: ${event.concept_name} - ${event.error}`,
        details: event,
        duration_ms: null,
        created_at: new Date().toISOString(),
      };
      setExecutionLogs((prev) => [...prev, newLog]);
      
      // 刷新路线图数据以更新concept状态
      const currentRoadmapId = roadmapIdRef.current;
      if (currentRoadmapId) {
        try {
          await loadRoadmapFramework(currentRoadmapId);
        } catch (err) {
          console.error('[TaskDetail] Failed to refresh roadmap after concept failed:', err);
        }
      }
    };

    const handleHumanReview = (event: any) => {
      lastWebSocketMessageTime = Date.now();
      console.log('[TaskDetail] Human review required:', event);
      setTaskInfo((prev) => prev ? { 
        ...prev, 
        status: 'human_review_pending',
        current_step: 'human_review',
      } : null);
    };

    const handleCompleted = (event: any) => {
      lastWebSocketMessageTime = Date.now();
      if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
      }
      console.log('[TaskDetail] Task completed:', event);
      setTaskInfo((prev) => prev ? { 
        ...prev, 
        status: 'completed', 
        current_step: 'completed' 
      } : null);
      
      const newLog: ExecutionLog = {
        id: `ws-completed-${Date.now()}`,
        task_id: taskId,
        level: 'success',
        category: 'workflow',
        step: 'completed',
        agent_name: null,
        message: 'Task completed successfully!',
        details: event,
        duration_ms: null,
        created_at: new Date().toISOString(),
      };
      setExecutionLogs((prev) => [...prev, newLog]);
    };

    const handleFailed = (event: any) => {
      lastWebSocketMessageTime = Date.now();
      if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
      }
      console.log('[TaskDetail] Task failed:', event);
      setTaskInfo((prev) => prev ? { 
        ...prev, 
        status: 'failed', 
        current_step: 'failed',
        error_message: event.error || 'Task failed'
      } : null);
      
      const newLog: ExecutionLog = {
        id: `ws-failed-${Date.now()}`,
        task_id: taskId,
        level: 'error',
        category: 'workflow',
        step: 'failed',
        agent_name: null,
        message: event.error || 'Task failed',
        details: event,
        duration_ms: null,
        created_at: new Date().toISOString(),
      };
      setExecutionLogs((prev) => [...prev, newLog]);
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
      onConceptFailed: handleConceptFailed,
      onHumanReview: handleHumanReview,
      onCompleted: handleCompleted,
      onFailed: handleFailed,
      onError: handleError,
      onAnyEvent: (event: any) => {
        // 更新最后消息时间（任何事件都算作活跃消息）
        lastWebSocketMessageTime = Date.now();
      },
    });

    websocket.connect(true);
    setWs(websocket);
    
    // 检查 WebSocket 连接状态和消息活跃度
    const checkWebSocketHealth = () => {
      const isConnected = websocket.isConnected();
      const timeSinceLastMessage = Date.now() - lastWebSocketMessageTime;
      
      // 如果 WebSocket 未连接，或长时间无消息，启动轮询
      if (!isConnected || timeSinceLastMessage > WS_SILENCE_THRESHOLD) {
        if (!pollingInterval) {
          const currentStep = taskInfo?.current_step;
          // 只在处理中的任务阶段启用轮询
          if (currentStep && ['content_generation', 'tutorial_generation', 'resource_generation', 'quiz_generation'].includes(currentStep)) {
            const interval = Math.min(
              INITIAL_POLLING_INTERVAL * Math.pow(2, pollingAttempts),
              MAX_POLLING_INTERVAL
            );
            console.log(`[TaskDetail] WebSocket ${!isConnected ? 'disconnected' : 'silent'}, starting fallback polling with interval: ${interval}ms`);
            
            pollingInterval = setInterval(async () => {
              try {
                const latestTask = await getTaskDetail(taskId);
                
                // 如果任务已完成，更新状态并停止轮询
                if (latestTask.status === 'completed' || latestTask.status === 'partial_failure' || latestTask.status === 'failed') {
                  console.log('[TaskDetail] Polling detected task completion:', latestTask.status);
                  setTaskInfo(latestTask);
                  
                  // 刷新日志（只获取 agent 和 workflow 类型）
                  const [agentLogsData, workflowLogsData] = await Promise.all([
                    getTaskLogs(taskId, undefined, 'agent', 1000),
                    getTaskLogs(taskId, undefined, 'workflow', 1000),
                  ]);
                  const allLogs = [
                    ...(agentLogsData.logs || []),
                    ...(workflowLogsData.logs || []),
                  ];
                  const limitedLogs = limitLogsByStep(allLogs, 100);
                  setExecutionLogs(limitedLogs);
                  
                  // 停止轮询
                  if (pollingInterval) {
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                  }
                } else {
                  // 任务仍在进行中，增加轮询尝试次数（下次使用更长的间隔）
                  pollingAttempts++;
                }
              } catch (err) {
                console.error('[TaskDetail] Polling error:', err);
                pollingAttempts++;
              }
            }, interval);
          }
        }
      } else if (pollingInterval) {
        // WebSocket 已连接且有活跃消息，停止轮询
        console.log('[TaskDetail] WebSocket healthy, stopping fallback polling');
        clearInterval(pollingInterval);
        pollingInterval = null;
        pollingAttempts = 0;
      }
    };
    
    // 定期检查 WebSocket 健康状态（每30秒检查一次）
    const healthCheckInterval = setInterval(checkWebSocketHealth, 30000);
    
    // 初始检查（延迟5秒，给 WebSocket 时间建立连接）
    const initialHealthCheck = setTimeout(() => {
      checkWebSocketHealth();
    }, 5000);

    return () => {
      websocket.disconnect();
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
      if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
      }
      clearTimeout(initialHealthCheck);
    };
  }, [taskId, taskInfo?.status, taskInfo?.current_step, taskInfo?.roadmap_id, loadIntentAnalysis, loadRoadmapFramework]);

  /**
   * 获取编辑记录（modified_node_ids）
   * 
   * 当任务完成 roadmap_edit 阶段后，获取最新的编辑记录以高亮修改的节点
   */
  useEffect(() => {
    const shouldFetchEditRecord = 
      taskInfo?.current_step && 
      ['structure_validation', 'human_review', 'human_review_pending', 'content_generation', 'completed', 'partial_failure'].includes(taskInfo.current_step) &&
      taskInfo.roadmap_id;

    if (shouldFetchEditRecord) {
      const fetchEditRecord = async () => {
        try {
          const { getLatestEdit } = await import('@/lib/api/endpoints');
          const editData = await getLatestEdit(taskId);
          if (editData?.modified_node_ids) {
            setModifiedNodeIds(editData.modified_node_ids);
          }
        } catch (err) {
          // 如果没有编辑记录（例如首次验证就通过了），忽略错误
          console.log('[TaskDetail] No edit record found:', err);
        }
      };

      fetchEditRecord();
    }
  }, [taskId, taskInfo?.current_step, taskInfo?.roadmap_id]);

  /**
   * Human Review 完成回调
   */
  const handleHumanReviewComplete = useCallback(async () => {
    // 刷新任务状态
    if (taskId) {
      try {
        const taskData = await getTaskDetail(taskId);
        setTaskInfo(taskData);
      } catch (err) {
        console.error('Failed to refresh task after review:', err);
      }
    }
  }, [taskId]);

  /**
   * 获取任务状态配置
   */
  const getStatusConfig = (status: string) => {
    const configs: Record<string, { icon: any; label: string; className: string }> = {
      pending: {
        icon: Clock,
        label: 'Pending',
        className: 'bg-amber-50 text-amber-700 border-amber-200',
      },
      processing: {
        icon: Loader2,
        label: 'Processing',
        className: 'bg-blue-50 text-blue-700 border-blue-200',
      },
      human_review_pending: {
        icon: Eye,
        label: 'Review Required',
        className: 'bg-purple-50 text-purple-700 border-purple-200',
      },
      completed: {
        icon: CheckCircle2,
        label: 'Completed',
        className: 'bg-green-50 text-green-700 border-green-200',
      },
      partial_failure: {
        icon: CheckCircle2,
        label: 'Completed',
        className: 'bg-green-50 text-green-700 border-green-200',
      },
      failed: {
        icon: AlertCircle,
        label: 'Failed',
        className: 'bg-red-50 text-red-700 border-red-200',
      },
    };

    return configs[status] || configs.pending;
  };

  /**
   * 判断是否正在编辑路线图
   */
  const isEditingRoadmap = useMemo(() => {
    return taskInfo?.current_step === 'roadmap_edit';
  }, [taskInfo?.current_step]);

  // ========================================
  // 优化：分区域骨架屏加载，提供更好的加载体验
  // ========================================
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        {/* Header Skeleton */}
        <div className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Skeleton className="h-8 w-32" />
                <Skeleton className="h-8 w-24" />
              </div>
              <Skeleton className="h-8 w-96" />
              <div className="flex items-center gap-3">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-4 w-32" />
              </div>
            </div>
          </div>
        </div>

        {/* Main Content Skeleton */}
        <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
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
              <h2 className="text-lg font-semibold">Task Not Found</h2>
              <p className="text-sm text-muted-foreground mt-1">
                {error || 'The task you are looking for does not exist.'}
              </p>
            </div>
            <Button onClick={() => router.push('/tasks')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Tasks
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  const statusConfig = getStatusConfig(taskInfo.status);
  const StatusIcon = statusConfig.icon;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 space-y-1">
              <div className="flex items-center gap-2 mb-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => router.push('/tasks')}
                  className="-ml-2"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Tasks
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleRefresh}
                  disabled={isRefreshing || isLoading}
                  className="-ml-2"
                >
                  <RefreshCw className={cn('w-4 h-4 mr-2', isRefreshing && 'animate-spin')} />
                  Refresh
                </Button>
                {taskInfo.status === 'processing' && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowCancelDialog(true)}
                    className="-ml-2 text-orange-600 hover:text-orange-700 hover:bg-orange-50"
                  >
                    <XCircle className="w-4 h-4 mr-2" />
                    Cancel Task
                  </Button>
                )}
              </div>
              
              <h1 className="text-2xl font-serif font-semibold">{taskInfo.title}</h1>
              
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <span className="font-mono">ID: {taskInfo.task_id.substring(0, 16)}...</span>
                <span>·</span>
                <span>Created {new Date(taskInfo.created_at).toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - 三段式布局 */}
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* 1. Workflow Progress（拓扑图版） */}
        <WorkflowTopology
          currentStep={taskInfo.current_step}
          status={taskInfo.status}
          editSource={editSource}
          taskId={taskId}
          roadmapId={taskInfo.roadmap_id}
          roadmapTitle={roadmapFramework?.title || taskInfo.title}
          stagesCount={roadmapFramework?.stages?.length || 0}
          executionLogs={executionLogs}
          onHumanReviewComplete={handleHumanReviewComplete}
          selectedNodeId={selectedNodeId}
          onNodeSelect={setSelectedNodeId}
        />

        {/* 2. Core Display Area（需求分析 + 路线图） */}
        <CoreDisplayArea
          currentStep={taskInfo.current_step}
          status={taskInfo.status}
          taskId={taskId}
          roadmapId={taskInfo.roadmap_id}
          intentAnalysis={intentAnalysis}
          roadmapFramework={roadmapFramework}
          isEditingRoadmap={isEditingRoadmap}
          modifiedNodeIds={modifiedNodeIds}
          loadingConceptIds={loadingConceptIds}
          failedConceptIds={failedConceptIds}
          partialFailedConceptIds={partialFailedConceptIds}
          userPreferences={userPreferences}
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
                  <h3 className="font-medium text-red-900">Task Failed</h3>
                  <p className="text-sm text-red-700">{taskInfo.error_message}</p>
                </div>
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Cancel Task Confirmation Dialog */}
      <AlertDialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel Task?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to cancel this task? The task will be stopped immediately and you can retry it later.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleCancelConfirm} className="bg-orange-600 hover:bg-orange-700">
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

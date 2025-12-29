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
import { ArrowLeft, AlertCircle, CheckCircle2, Loader2, Clock, Eye, RefreshCw, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
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
   */
  const loadIntentAnalysis = useCallback(async (taskId: string) => {
    try {
      const intentData = await getIntentAnalysis(taskId);
      
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
    } catch (err) {
      console.error('Failed to load intent analysis:', err);
      // 如果获取失败，不设置数据（保持为 null）
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
   */
  const loadRoadmapFramework = useCallback(async (roadmapId: string, updateConceptStates = false) => {
    try {
      const roadmapData = await getRoadmap(roadmapId);
      if (roadmapData) {
        setRoadmapFramework(roadmapData);
        
        // 如果需要更新概念状态（刷新时使用）
        if (updateConceptStates) {
          const { loading, failed, partialFailed } = extractConceptStates(roadmapData);
          setLoadingConceptIds(loading);
          setFailedConceptIds(failed);
          setPartialFailedConceptIds(partialFailed);
          console.log('[TaskDetail] Updated concept states from roadmap:', { loading, failed, partialFailed });
        }
      }
    } catch (err) {
      console.error('Failed to load roadmap framework:', err);
    }
  }, [extractConceptStates]);

  /**
   * 加载任务信息和日志（提取为独立函数，供初始加载和刷新使用）
   */
  const loadTaskData = useCallback(async (isInitialLoad = false) => {
    if (!taskId) return;

    try {
      if (isInitialLoad) {
        setIsLoading(true);
      } else {
        setIsRefreshing(true);
      }
      setError(null);

      // 加载任务基本信息
      const taskData = await getTaskDetail(taskId);
      setTaskInfo(taskData);
      // 更新ref中的roadmap_id
      roadmapIdRef.current = taskData.roadmap_id || null;

      // 加载执行日志（只获取 agent 和 workflow 类型，排除 concept 日志以提升性能）
      // Concept 日志通常量大且 details 字段庞大，会严重影响加载速度
      const [agentLogsData, workflowLogsData] = await Promise.all([
        getTaskLogs(taskId, undefined, 'agent', 1000),
        getTaskLogs(taskId, undefined, 'workflow', 1000),
      ]);
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
      // 优先从 roadmap_edit 或 edit_plan_analysis 日志中读取 edit_source
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
      
      // 加载需求分析数据（从数据库获取，内容更丰富）
      await loadIntentAnalysis(taskId);

      // 如果有 roadmap_id，加载路线图框架
      if (taskData.roadmap_id) {
        // 刷新时更新概念状态（从路线图数据中提取）
        await loadRoadmapFramework(taskData.roadmap_id, !isInitialLoad);
        
        // 刷新时也重新加载修改记录
        if (!isInitialLoad) {
          // 需要先等 taskInfo 更新后再加载 modifiedNodeIds
          // 这里使用 taskData 而不是 taskInfo state
          const shouldFetchEditRecord = taskData.current_step && [
            'structure_validation',
            'human_review',
            'human_review_pending',
            'content_generation',
            'completed',
            'partial_failure'
          ].includes(taskData.current_step);
          
          if (shouldFetchEditRecord) {
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
          }
        }
      }

    } catch (err: any) {
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
   */
  useEffect(() => {
    if (!taskId) return;
    loadTaskData(true);
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
  const handleCancel = useCallback(async () => {
    if (!confirm('Are you sure you want to cancel this task? The task will be stopped immediately.')) {
      return;
    }
    
    try {
      await cancelTask(taskId);
      
      // 更新本地状态
      setTaskInfo((prev) => prev ? {
        ...prev,
        status: 'cancelled',
        current_step: 'cancelled',
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
    
    if (!isActiveTask) {
      return;
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
      
      // 刷新路线图数据以更新concept状态
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

  // 加载状态
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 border-4 border-sage-200 border-t-sage-600 rounded-full animate-spin mx-auto" />
          <p className="text-sm text-muted-foreground">Loading task details...</p>
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
                    onClick={handleCancel}
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
    </div>
  );
}

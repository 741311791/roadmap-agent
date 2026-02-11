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
import { ArrowLeft, AlertCircle, CheckCircle2, Loader2, Clock, Eye, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { TaskWebSocket } from '@/lib/api/websocket';
import { tasksApi, roadmapsApi, usersApi } from '@/lib/api/endpoints';
import { WorkflowTopology } from '@/components/task/workflow-topology';
import { CoreDisplayArea } from '@/components/task/core-display-area';
import { ExecutionLogTimeline } from '@/components/task/execution-log-timeline';
import { cn } from '@/lib/utils';
import { limitLogsByStep, getLogStatsByStep } from '@/lib/utils/log-grouping';
import { useAuthStore } from '@/lib/store/auth-store';
import { mapToDisplayStep } from '@/lib/constants/workflow-steps';
import type { 
  RoadmapFramework, 
  LearningPreferences, 
  ExecutionLogResponse,
  TaskStatusDetailResponse 
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
 * 任务信息类型（扩展生成的类型）
 */
interface TaskInfo extends TaskStatusDetailResponse {
  title: string;  // 额外添加的字段
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

  // 取消任务确认对话框 - 已移除功能

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
   * 
   * @param roadmapId - 路线图ID（注意：是roadmap_id，不是task_id）
   * @param signal - AbortSignal for request cancellation
   */
  const loadIntentAnalysis = useCallback(async (roadmapId: string, signal?: AbortSignal) => {
    try {
      const intentData = await roadmapsApi.getIntentAnalysis(roadmapId);
      
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
          
          // ✅ 修复：只有明确为'pending'状态才标记为loading
          // null/undefined状态表示内容尚未开始生成，应显示为初始状态而非loading
          const isGenerating = statuses.some(s => s === 'pending');
          if (isGenerating) {
            loading.push(conceptId);
            return;
          }
          
          // ✅ 过滤掉null/undefined状态，只统计有效状态
          const validStatuses = statuses.filter(s => s !== null && s !== undefined);
          
          // 如果所有状态都是null/undefined，说明还未开始生成，不需要标记为任何特殊状态
          if (validStatuses.length === 0) {
            return;
          }
          
          // 判断失败状态
          const failedCount = validStatuses.filter(s => s === 'failed').length;
          const completedCount = validStatuses.filter(s => s === 'completed').length;
          
          if (failedCount === validStatuses.length) {
            // 全部失败（所有有效状态都是failed）
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
      const roadmapDetail = await roadmapsApi.getById(roadmapId);
      if (roadmapDetail && roadmapDetail.framework) {
        const framework = roadmapDetail.framework;
        setRoadmapFramework(framework);
        
        // 🚀 关键优化：预填充 TanStack Query 缓存
        // 这样跳转到 /roadmap/[id] 时可以直接使用缓存数据，无需重新请求
        queryClient.setQueryData(['roadmap', roadmapId], roadmapDetail);
        console.log('[TaskDetail] Prefilled roadmap cache for instant navigation');
        
        // 如果需要更新概念状态（刷新时使用）
        if (updateConceptStates) {
          const { loading, failed, partialFailed } = extractConceptStates(framework);
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
      const [taskData, agentLogsData, workflowLogsData] = await Promise.all([
        tasksApi.getById(taskId),
        tasksApi.getLogs(taskId, undefined, 'agent', 200, 0, signal),   // level, category, limit, offset, signal
        tasksApi.getLogs(taskId, undefined, 'workflow', 200, 0, signal), // level, category, limit, offset, signal
      ]);
      
      // 获取 taskData 后再加载 intentAnalysis（需要 roadmap_id）
      let intentData = null;
      if (taskData.roadmap_id) {
        intentData = await loadIntentAnalysis(taskData.roadmap_id, signal).catch(() => null);
      }
      
      // 🔧 优化：应用步骤映射
      const displayStep = mapToDisplayStep(taskData.current_step || null);
      // 添加title字段（从intentAnalysis或默认值获取）
      const taskInfo: TaskInfo = {
        ...taskData,
        current_step: displayStep,
        title: intentData?.learning_goal || 'Generating Roadmap...',
      };
      setTaskInfo(taskInfo);
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
          log.details && typeof log.details === 'object' && 'edit_source' in log.details
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
        // 注意：EditRecordResponse不包含modified_node_ids字段
        // 该字段通过WebSocket事件获取
        const loadEditRecordPromise = Promise.resolve();
        
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
        const profile = await usersApi.getUserProfile();
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
      if (event.current_step) {
        // 🔧 优化：将后端步骤映射到前端显示步骤，避免中间步骤导致UI闪烁
        const displayStep = mapToDisplayStep(event.current_step);
        setTaskInfo((prev) => prev ? { ...prev, current_step: displayStep } : null);
      }
      if (event.status) {
        setTaskInfo((prev) => prev ? { ...prev, status: event.status } : null);
      }
      if (event.roadmap_id) {
        setTaskInfo((prev) => prev ? { ...prev, roadmap_id: event.roadmap_id } : null);
        roadmapIdRef.current = event.roadmap_id;
        
        // ✅ 修复：当收到 roadmap_id 时，立即加载 intent_analysis 数据
        // 这确保在 intent_analysis 完成后能立即显示数据
        loadIntentAnalysis(event.roadmap_id).catch((err) => {
          console.error('[TaskDetail] Failed to load intent analysis after roadmap_id update:', err);
        });
      }
    };

    const handleProgress = async (event: any) => {
      console.log('[TaskDetail] Progress update:', event);
      
      // ✅ 修复：不再添加临时 WebSocket 日志，避免与数据库日志重复
      // 所有日志都应该从数据库查询，WebSocket 只负责触发刷新
      // 这样可以确保日志的一致性和唯一性
      
      // 更新 current_step
      // 🔧 优化：将后端步骤映射到前端显示步骤，避免中间步骤导致UI闪烁
      if (event.step) {
        const displayStep = mapToDisplayStep(event.step);
        setTaskInfo((prev) => prev ? { ...prev, current_step: displayStep } : null);
      }

      // 更新 edit_source（用于区分分支）
      if (event.data?.edit_source) {
        setEditSource(event.data.edit_source);
      }
      
      // 当节点完成时，刷新日志和路线图
      if (event.status === 'completed' && event.step) {
        try {
          // 只获取 agent 和 workflow 类型的日志，排除 concept 日志
          // getLogs(taskId, level, category, limit, offset, signal)
          // 🔧 优化：减少日志查询数量（1000→500），提升性能
          const [agentLogsData, workflowLogsData] = await Promise.all([
            tasksApi.getLogs(taskId, undefined, 'agent', 500, 0),
            tasksApi.getLogs(taskId, undefined, 'workflow', 500, 0),
          ]);
          const allLogs = [
            ...(agentLogsData.logs || []),
            ...(workflowLogsData.logs || []),
          ];
          const limitedLogs = limitLogsByStep(allLogs, 100);
          setExecutionLogs(limitedLogs);
          
          // 重新加载需求分析数据（使用最新的数据库数据）
          const currentRoadmapId = roadmapIdRef.current;
          if (currentRoadmapId) {
            console.log('[TaskDetail] Reloading intent analysis after node completion:', {
              step: event.step,
              roadmap_id: currentRoadmapId,
            });
            await loadIntentAnalysis(currentRoadmapId);
          } else {
            console.warn('[TaskDetail] Cannot reload intent analysis: roadmap_id is null', {
              step: event.step,
            });
          }
          
          // 如果是 curriculum_design 或 roadmap_edit 完成，重新加载路线图
          if (['curriculum_design', 'roadmap_edit'].includes(event.step)) {
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
        try {
          await loadRoadmapFramework(currentRoadmapId);
        } catch (err) {
          console.error('[TaskDetail] Failed to refresh roadmap after all content complete:', err);
        }
      }
    };

    const handleConceptFailed = async (event: any) => {
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
      
      // ✅ 修复：不添加临时日志，避免重复
      
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
      console.log('[TaskDetail] Human review required:', event);
      setTaskInfo((prev) => prev ? { 
        ...prev, 
        status: 'human_review_pending',
        current_step: 'human_review',
      } : null);
    };

    const handleCompleted = (event: any) => {
      console.log('[TaskDetail] Task completed:', event);
      setTaskInfo((prev) => prev ? { 
        ...prev, 
        status: 'completed', 
        current_step: 'completed' 
      } : null);
      
      // ✅ 修复：不添加临时日志，避免重复
      // 完成状态的日志会从数据库查询获取
    };

    const handleFailed = (event: any) => {
      console.log('[TaskDetail] Task failed:', event);
      
      // 优先使用 message（包含错误类型），其次使用 error_detail（完整堆栈），最后使用 error
      const errorMessage = event.message || event.error_detail || event.error || 'Task failed';
      
      setTaskInfo((prev) => prev ? { 
        ...prev, 
        status: 'failed', 
        current_step: 'failed',
        error_message: errorMessage
      } : null);
      
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
  }, [taskId, taskInfo?.status, taskInfo?.current_step, taskInfo?.roadmap_id, loadIntentAnalysis, loadRoadmapFramework]);

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
        // 🔧 优化：应用步骤映射
        const displayStep = mapToDisplayStep(taskData.current_step || null);
        // 保留原有title
        setTaskInfo((prev) => prev ? { 
          ...taskData, 
          current_step: displayStep,
          title: prev.title 
        } : null);
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
        <header className="border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur-md sticky top-0 z-50 shadow-sm">
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
      {/* Header - 重新设计版 */}
      <header className="border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur-md sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-5">
          {/* 顶部操作栏 */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push('/tasks')}
                className="gap-2 hover:bg-sage-50 dark:hover:bg-sage-900/20"
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </Button>
              <div className="w-px h-5 bg-border" />
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRefresh}
                disabled={isRefreshing || isLoading}
                className="gap-2"
              >
                <RefreshCw className={cn('w-4 h-4', isRefreshing && 'animate-spin')} />
                {isRefreshing ? 'Refreshing...' : 'Refresh'}
              </Button>
            </div>
            
            {/* 状态徽章 */}
            <Badge 
              variant="outline" 
              className={cn(
                'px-3 py-1 text-sm font-medium border',
                statusConfig.className
              )}
            >
              <StatusIcon className={cn(
                'w-4 h-4 mr-2',
                taskInfo.status === 'processing' && 'animate-spin'
              )} />
              {statusConfig.label}
            </Badge>
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
                  ? new Date(taskInfo.created_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })
                  : 'Unknown'}
              </time>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - 三段式布局 */}
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-6 bg-[#F8F5F0]">
        {/* 1. Workflow Progress（拓扑图版） */}
        <WorkflowTopology
          currentStep={taskInfo.current_step || null}
          status={taskInfo.status}
          editSource={editSource}
          taskId={taskId}
          roadmapId={taskInfo.roadmap_id || null}
          roadmapTitle={roadmapFramework?.title || taskInfo.title}
          stagesCount={roadmapFramework?.stages?.length || 0}
          executionLogs={executionLogs}
          onHumanReviewComplete={handleHumanReviewComplete}
          selectedNodeId={selectedNodeId}
          onNodeSelect={setSelectedNodeId}
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

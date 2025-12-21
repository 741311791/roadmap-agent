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

import { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, AlertCircle, CheckCircle2, Loader2, Clock, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { TaskWebSocket } from '@/lib/api/websocket';
import { getTaskDetail, getTaskLogs, getRoadmap, getIntentAnalysis } from '@/lib/api/endpoints';
import { WorkflowProgressEnhanced } from '@/components/task/workflow-progress-enhanced';
import { CoreDisplayArea } from '@/components/task/core-display-area';
import { ExecutionLogTimeline } from '@/components/task/execution-log-timeline';
import { cn } from '@/lib/utils';
import { limitLogsByStep, getLogStatsByStep } from '@/lib/utils/log-grouping';
import type { RoadmapFramework } from '@/types/generated/models';

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
  level: string;
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
  current_step: string;
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

  // 任务基本信息
  const [taskInfo, setTaskInfo] = useState<TaskInfo | null>(null);

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

  // 加载状态
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // WebSocket 连接
  const [ws, setWs] = useState<TaskWebSocket | null>(null);

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
   * 加载路线图框架
   */
  const loadRoadmapFramework = useCallback(async (roadmapId: string) => {
    try {
      const roadmapData = await getRoadmap(roadmapId);
      if (roadmapData) {
        setRoadmapFramework(roadmapData);
      }
    } catch (err) {
      console.error('Failed to load roadmap framework:', err);
    }
  }, []);

  /**
   * 加载任务信息和日志
   */
  useEffect(() => {
    if (!taskId) return;

    const loadTaskData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // 加载任务基本信息
        const taskData = await getTaskDetail(taskId);
        setTaskInfo(taskData);

        // 加载执行日志（获取大量日志，然后按 step 分组并限制每个阶段最多 100 条）
        const logsData = await getTaskLogs(taskId, undefined, undefined, 2000);
        const allLogs = logsData.logs || [];
        
        // 按 step 分组，每个 step 最多 100 条
        const limitedLogs = limitLogsByStep(allLogs, 100);
        
        // 打印统计信息（开发调试用）
        if (process.env.NODE_ENV === 'development') {
          const stats = getLogStatsByStep(allLogs);
          console.log('[TaskDetail] Log stats by step:', stats);
          console.log('[TaskDetail] Total logs:', allLogs.length, '→ Limited to:', limitedLogs.length);
        }
        
        setExecutionLogs(limitedLogs);
        
        // 加载需求分析数据（从数据库获取，内容更丰富）
        await loadIntentAnalysis(taskId);

        // 如果有 roadmap_id，加载路线图框架
        if (taskData.roadmap_id) {
          await loadRoadmapFramework(taskData.roadmap_id);
        }

      } catch (err: any) {
        console.error('Failed to load task data:', err);
        setError(err.message || 'Failed to load task details');
      } finally {
        setIsLoading(false);
      }
    };

    loadTaskData();
  }, [taskId, loadIntentAnalysis, loadRoadmapFramework]);

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

    const websocket = new TaskWebSocket(taskId, {
      onStatus: (event) => {
        console.log('[TaskDetail] Status update:', event);
        if (event.current_step) {
          setTaskInfo((prev) => prev ? { ...prev, current_step: event.current_step } : null);
        }
        if (event.status) {
          setTaskInfo((prev) => prev ? { ...prev, status: event.status } : null);
        }
        if (event.roadmap_id) {
          setTaskInfo((prev) => prev ? { ...prev, roadmap_id: event.roadmap_id } : null);
        }
      },

      onProgress: async (event) => {
        console.log('[TaskDetail] Progress update:', event);
        
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
        
        // 当节点完成时，刷新日志和路线图
        if (event.status === 'completed' && event.step) {
          try {
            const logsData = await getTaskLogs(taskId, undefined, undefined, 2000);
            const allLogs = logsData.logs || [];
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
      },

      onConceptStart: (event) => {
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
      },

      onConceptComplete: (event) => {
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
      },

      onConceptFailed: (event) => {
        console.log('[TaskDetail] Concept failed:', event);
        setLoadingConceptIds(prev => prev.filter(id => id !== event.concept_id));
        setFailedConceptIds(prev => [...prev, event.concept_id]);
        
        const newLog: ExecutionLog = {
          id: `ws-concept-failed-${Date.now()}`,
          task_id: taskId,
          level: 'error',
          category: 'workflow',
          step: 'content_generation',
          agent_name: null,
          message: `Failed: ${event.concept_name} - ${event.error}`,
          details: event,
          duration_ms: null,
          created_at: new Date().toISOString(),
        };
        setExecutionLogs((prev) => [...prev, newLog]);
      },

      onHumanReview: (event) => {
        console.log('[TaskDetail] Human review required:', event);
        setTaskInfo((prev) => prev ? { 
          ...prev, 
          status: 'human_review_pending',
          current_step: 'human_review',
        } : null);
      },

      onCompleted: (event) => {
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
      },

      onFailed: (event) => {
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
      },

      onError: (event) => {
        console.error('[TaskDetail] WebSocket error:', event);
      },
    });

    websocket.connect(true);
    setWs(websocket);
    
    // ========================================
    // 轮询兜底机制：防止 WebSocket 通知丢失
    // ========================================
    // 在 content_generation 阶段，每 10 秒轮询一次任务状态
    // 如果发现任务已完成但前端未收到通知，手动更新状态
    let pollingInterval: NodeJS.Timeout | null = null;
    
    const startPollingIfNeeded = () => {
      // 只在 content_generation 阶段启动轮询（这是最可能出现超时的阶段）
      if (taskInfo?.current_step === 'content_generation') {
        console.log('[TaskDetail] Starting fallback polling for content_generation');
        pollingInterval = setInterval(async () => {
          try {
            const latestTask = await getTaskDetail(taskId);
            if (latestTask.status === 'completed' || latestTask.status === 'partial_failure') {
              console.log('[TaskDetail] Polling detected task completion:', latestTask.status);
              setTaskInfo(latestTask);
              
              // 刷新日志
              const logsData = await getTaskLogs(taskId, undefined, undefined, 2000);
              const allLogs = logsData.logs || [];
              const limitedLogs = limitLogsByStep(allLogs, 100);
              setExecutionLogs(limitedLogs);
              
              // 停止轮询
              if (pollingInterval) {
                clearInterval(pollingInterval);
                pollingInterval = null;
              }
            }
          } catch (err) {
            console.error('[TaskDetail] Polling error:', err);
          }
        }, 10000); // 每 10 秒轮询一次
      }
    };
    
    // 延迟启动轮询（给 WebSocket 一些时间建立连接）
    const pollingStartTimer = setTimeout(startPollingIfNeeded, 5000);

    return () => {
      websocket.disconnect();
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
      clearTimeout(pollingStartTimer);
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
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push('/tasks')}
                className="mb-2 -ml-2"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Tasks
              </Button>
              
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
        {/* 1. Workflow Progress（增强版） */}
        <WorkflowProgressEnhanced
          currentStep={taskInfo.current_step}
          status={taskInfo.status}
          taskId={taskId}
          roadmapId={taskInfo.roadmap_id}
          roadmapTitle={roadmapFramework?.title || taskInfo.title}
          stagesCount={roadmapFramework?.stages?.length || 0}
          onHumanReviewComplete={handleHumanReviewComplete}
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

'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Clock, Activity, AlertCircle, CheckCircle2, Loader2, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { TaskWebSocket } from '@/lib/api/websocket';
import { getTaskDetail, getTaskLogs } from '@/lib/api/endpoints';
import { HorizontalWorkflowStepper } from '@/components/task/horizontal-workflow-stepper';
import { ExecutionLogTimeline } from '@/components/task/execution-log-timeline';
import { ContentGenerationOverview } from '@/components/task/content-generation';
import { cn } from '@/lib/utils';

/**
 * 任务详情页面
 * 
 * 功能:
 * - 横向步进器展示任务所有阶段
 * - WebSocket实时订阅任务状态更新
 * - 每个阶段的详细执行日志
 * - 支持按阶段筛选日志
 */
export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params?.taskId as string;

  // 任务基本信息
  const [taskInfo, setTaskInfo] = useState<{
    task_id: string;
    title: string;
    status: string;
    current_step: string;
    created_at: string;
    updated_at: string;
    completed_at?: string | null;
    error_message?: string | null;
    roadmap_id?: string | null;
  } | null>(null);

  // 执行日志
  const [executionLogs, setExecutionLogs] = useState<Array<{
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
  }>>([]);

  // 日志过滤器（初始显示全部）
  const [selectedPhaseFilter, setSelectedPhaseFilter] = useState<string | null>(null);

  // 加载状态
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // WebSocket连接
  const [ws, setWs] = useState<TaskWebSocket | null>(null);

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

        // 加载执行日志
        const logsData = await getTaskLogs(taskId);
        setExecutionLogs(logsData.logs || []);

      } catch (err: any) {
        console.error('Failed to load task data:', err);
        setError(err.message || 'Failed to load task details');
      } finally {
        setIsLoading(false);
      }
    };

    loadTaskData();
  }, [taskId]);

  /**
   * 设置WebSocket实时订阅
   */
  useEffect(() => {
    if (!taskId || !taskInfo) return;

    // 只有正在处理中的任务才需要WebSocket
    // 已完成（包括 completed/partial_failure）和失败的任务不需要订阅
    const isActiveTask = taskInfo.status === 'processing' || taskInfo.status === 'pending';
    if (!isActiveTask) {
      return;
    }

    const websocket = new TaskWebSocket(taskId, {
      onStatus: (event) => {
        console.log('[TaskDetail] Status update:', event);
        if (event.current_step) {
          setTaskInfo((prev) => prev ? { ...prev, current_step: event.current_step } : null);
        }
      },

      onProgress: async (event) => {
        console.log('[TaskDetail] Progress update:', event);
        
        // 添加实时日志
        const newLog = {
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
        
        // 始终更新current_step（当step字段存在时）
        // WorkflowBrain会在每个节点开始和结束时发送通知
        // 前端应该反映最新的节点状态
        if (event.step) {
          setTaskInfo((prev) => prev ? { ...prev, current_step: event.step } : null);
        }
        
        // 🎯 关键改进：当节点完成时，立即获取最新日志
        // 这样可以实时显示带有log_type的专用卡片（如CurriculumDesignCard）
        if (event.status === 'completed' && event.step) {
          try {
            const logsData = await getTaskLogs(taskId);
            setExecutionLogs(logsData.logs || []);
          } catch (err) {
            console.error('Failed to refresh logs after node completion:', err);
          }
        }
      },

      onConceptStart: (event) => {
        console.log('[TaskDetail] Concept start:', event);
        const newLog = {
          id: `ws-concept-start-${Date.now()}`,
          task_id: taskId,
          level: 'info',
          category: 'workflow',
          step: 'content_generation',
          agent_name: null,
          message: `Started generating content for concept: ${event.concept_id}`,
          details: event,
          duration_ms: null,
          created_at: new Date().toISOString(),
        };
        setExecutionLogs((prev) => [...prev, newLog]);
      },

      onConceptComplete: (event) => {
        console.log('[TaskDetail] Concept complete:', event);
        const newLog = {
          id: `ws-concept-complete-${Date.now()}`,
          task_id: taskId,
          level: 'success',
          category: 'workflow',
          step: 'content_generation',
          agent_name: null,
          message: `Completed generating content for concept: ${event.concept_id}`,
          details: event,
          duration_ms: null,
          created_at: new Date().toISOString(),
        };
        setExecutionLogs((prev) => [...prev, newLog]);
      },

      onCompleted: (event) => {
        console.log('[TaskDetail] Task completed:', event);
        setTaskInfo((prev) => prev ? { ...prev, status: 'completed', current_step: 'completed' } : null);
        
        const newLog = {
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
        
        const newLog = {
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

    websocket.connect(true); // include_history = true
    setWs(websocket);

    return () => {
      websocket.disconnect();
    };
  }, [taskId, taskInfo?.status]);

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
      completed: {
        icon: CheckCircle2,
        label: 'Completed',
        className: 'bg-green-50 text-green-700 border-green-200',
      },
      partial_failure: {
        icon: CheckCircle2,  // ✅ 简化：使用绿色对勾
        label: 'Completed',  // ✅ 简化：显示为 Completed
        className: 'bg-green-50 text-green-700 border-green-200',  // ✅ 使用绿色样式
      },
      failed: {
        icon: AlertCircle,
        label: 'Failed',
        className: 'bg-red-50 text-red-700 border-red-200',
      },
    };

    return configs[status] || configs.pending;
  };

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

            <Badge
              variant="outline"
              className={cn('gap-1.5 px-3 py-1.5', statusConfig.className)}
            >
              <StatusIcon
                className={cn('w-4 h-4', taskInfo.status === 'processing' && 'animate-spin')}
              />
              {statusConfig.label}
            </Badge>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* Horizontal Stepper - 可点击阶段 */}
        <HorizontalWorkflowStepper
          currentStep={taskInfo.current_step}
          status={taskInfo.status}
          selectedPhase={selectedPhaseFilter || undefined}
          onPhaseSelect={(phaseId) => {
            // 点击同一个阶段则切换为显示全部，否则显示该阶段
            setSelectedPhaseFilter(selectedPhaseFilter === phaseId ? null : phaseId);
          }}
        />

        {/* Content Generation 专属视图 - 点击 Content 阶段时显示 */}
        {selectedPhaseFilter === 'content_generation' && taskInfo.roadmap_id ? (
          <ContentGenerationOverview
            taskId={taskId}
            roadmapId={taskInfo.roadmap_id}
            initialLogs={executionLogs}
            onShowAllLogs={() => setSelectedPhaseFilter(null)}
          />
        ) : (
          /* 其他阶段使用原有的 Execution Logs Timeline */
          <ExecutionLogTimeline
            logs={executionLogs}
            selectedPhaseFilter={selectedPhaseFilter}
            taskStatus={taskInfo.status}
            roadmapId={taskInfo.roadmap_id}
            taskTitle={taskInfo.title}
            onShowAllLogs={() => setSelectedPhaseFilter(null)}
          />
        )}

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


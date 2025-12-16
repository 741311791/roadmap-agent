'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChevronLeft, ListTodo, RefreshCw, Loader2 } from 'lucide-react';
import { getUserTasks, retryTask, deleteTask, TaskItem, RetryTaskResponse } from '@/lib/api/endpoints';
import { TaskList } from '@/components/task';
import { useAuthStore } from '@/lib/store/auth-store';
import { useRoadmapGenerationWS } from '@/lib/hooks/websocket/use-roadmap-generation-ws';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

type TaskStatus = 'all' | 'pending' | 'processing' | 'completed' | 'failed';

interface TaskStats {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
}

export default function TasksPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [stats, setStats] = useState<TaskStats>({
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0,
  });
  const [activeFilter, setActiveFilter] = useState<TaskStatus>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [isRetrying, setIsRetrying] = useState<string | null>(null);
  const [retryingTaskId, setRetryingTaskId] = useState<string | null>(null);
  const [retryRoadmapId, setRetryRoadmapId] = useState<string | null>(null);
  const [retryType, setRetryType] = useState<'checkpoint' | 'content_retry' | null>(null);
  const { getUserId } = useAuthStore();

  const fetchTasks = async (status?: string) => {
    const userId = getUserId();
    if (!userId) {
      setIsLoading(false);
      return;
    }
    
    try {
      setIsLoading(true);
      const response = await getUserTasks(
        userId,
        status === 'all' ? undefined : status
      );
      setTasks(response.tasks);
      setStats({
        pending: response.pending_count,
        processing: response.processing_count,
        completed: response.completed_count,
        failed: response.failed_count,
      });
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks(activeFilter);
  }, [activeFilter]);

  // 订阅重试任务的进度
  const { connectionType, isConnected } = useRoadmapGenerationWS(
    retryingTaskId,
    {
      autoNavigate: false, // 不自动导航，让用户选择
      onComplete: (roadmapId) => {
        toast.success('Task retry completed!', {
          action: {
            label: 'View Details',
            onClick: () => retryingTaskId && router.push(`/tasks/${retryingTaskId}`),
          },
        });
        setRetryingTaskId(null);
        setRetryRoadmapId(null);
        setRetryType(null);
        fetchTasks(activeFilter); // 刷新任务列表
      },
      onError: (error) => {
        toast.error(`Retry failed: ${error}`);
        setRetryingTaskId(null);
        setRetryRoadmapId(null);
        setRetryType(null);
      },
    }
  );

  const handleRetry = async (taskId: string) => {
    const userId = getUserId();
    if (!userId) return;
    
    try {
      setIsRetrying(taskId);
      
      // 调用智能重试 API
      const result: RetryTaskResponse = await retryTask(taskId, userId);
      
      // 根据恢复类型显示不同的提示
      if (result.recovery_type === 'checkpoint') {
        // Checkpoint 恢复
        const taskIdForCheckpoint = result.task_id || taskId;
        
        toast.info(
          `Recovering from ${result.checkpoint_step || 'last checkpoint'}...`,
          {
            description: 'The workflow will continue from where it left off.',
            duration: 5000,
            action: {
              label: 'View Progress',
              onClick: () => router.push(`/tasks/${taskIdForCheckpoint}`),
            },
          }
        );
        
        // 使用原 task_id 订阅进度
        setRetryingTaskId(taskIdForCheckpoint);
        setRetryRoadmapId(result.roadmap_id);
        setRetryType('checkpoint');
        
      } else if (result.recovery_type === 'content_retry') {
        // 内容重试
        const newTaskId = result.new_task_id;
        
        toast.info(
          `Retrying ${result.total_items || 0} failed items...`,
          {
            description: 'Only failed content will be regenerated.',
            duration: 5000,
            action: {
              label: 'View Progress',
              onClick: () => newTaskId && router.push(`/tasks/${newTaskId}`),
            },
          }
        );
        
        // 使用新 task_id 订阅进度
        setRetryingTaskId(newTaskId || null);
        setRetryRoadmapId(result.roadmap_id);
        setRetryType('content_retry');
      }
      
    } catch (error: any) {
      console.error('Failed to retry task:', error);
      
      // 显示详细的错误信息
      const errorMessage = error.response?.data?.detail || 'Failed to retry task. Please try again later.';
      toast.error('Retry Failed', {
        description: errorMessage,
        duration: 7000,
      });
    } finally {
      setIsRetrying(null);
    }
  };

  const handleDelete = async (taskId: string) => {
    if (!confirm('Are you sure you want to delete this task? This action cannot be undone.')) {
      return;
    }

    const userId = getUserId();
    if (!userId) return;
    
    try {
      await deleteTask(taskId, userId);
      // 刷新列表
      await fetchTasks(activeFilter);
    } catch (error) {
      console.error('Failed to delete task:', error);
      alert('Failed to delete task. Please try again later.');
    }
  };

  const handleRefresh = () => {
    fetchTasks(activeFilter);
  };

  return (
    <ScrollArea className="h-full">
      <div className="max-w-6xl mx-auto py-8 px-6">
        {/* Back Navigation */}
        <Link
          href="/home"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" /> Back to Home
        </Link>

        {/* Retry Progress Banner */}
        {retryingTaskId && retryRoadmapId && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                <div>
                  <p className="font-medium text-blue-900">
                    {retryType === 'checkpoint' 
                      ? 'Recovering from checkpoint...' 
                      : 'Retrying failed content...'}
                  </p>
                  <p className="text-sm text-blue-600">
                    Connection: {connectionType === 'ws' ? 'WebSocket' : 'Polling'} 
                    {isConnected && ' • Connected'}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => retryingTaskId && router.push(`/tasks/${retryingTaskId}`)}
              >
                View Details
              </Button>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-sage-100 flex items-center justify-center">
              <ListTodo size={24} className="text-sage-600" />
            </div>
            <div>
              <h1 className="text-2xl font-serif font-bold text-foreground">
                Generation Tasks
              </h1>
              <p className="text-sm text-muted-foreground">
                Track the status of your roadmap generation tasks
              </p>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
            className="gap-2"
          >
            <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
            Refresh
          </Button>
        </div>

        {/* Status Filters */}
        <div className="flex flex-wrap gap-2 mb-6">
          <Button
            variant={activeFilter === 'all' ? 'default' : 'outline'}
            onClick={() => setActiveFilter('all')}
            className="gap-2"
          >
            All
            <Badge variant="secondary" className="ml-1">
              {stats.pending + stats.processing + stats.completed + stats.failed}
            </Badge>
          </Button>
          <Button
            variant={activeFilter === 'processing' ? 'default' : 'outline'}
            onClick={() => setActiveFilter('processing')}
            className="gap-2"
          >
            Processing
            {stats.processing > 0 && (
              <Badge variant="secondary" className="ml-1">
                {stats.processing}
              </Badge>
            )}
          </Button>
          <Button
            variant={activeFilter === 'failed' ? 'default' : 'outline'}
            onClick={() => setActiveFilter('failed')}
            className="gap-2"
          >
            Failed
            {stats.failed > 0 && (
              <Badge variant="destructive" className="ml-1">
                {stats.failed}
              </Badge>
            )}
          </Button>
          <Button
            variant={activeFilter === 'completed' ? 'default' : 'outline'}
            onClick={() => setActiveFilter('completed')}
            className="gap-2"
          >
            Completed
            {stats.completed > 0 && (
              <Badge variant="secondary" className="ml-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                {stats.completed}
              </Badge>
            )}
          </Button>
          <Button
            variant={activeFilter === 'pending' ? 'default' : 'outline'}
            onClick={() => setActiveFilter('pending')}
            className="gap-2"
          >
            Pending
            {stats.pending > 0 && (
              <Badge variant="secondary" className="ml-1">
                {stats.pending}
              </Badge>
            )}
          </Button>
        </div>

        {/* Task List */}
        <TaskList
          tasks={tasks}
          isLoading={isLoading}
          onRetry={handleRetry}
          onDelete={handleDelete}
        />
      </div>
    </ScrollArea>
  );
}


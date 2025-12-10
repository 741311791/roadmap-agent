'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChevronLeft, ListTodo, RefreshCw } from 'lucide-react';
import { getUserTasks, retryTask, TaskItem } from '@/lib/api/endpoints';
import { TaskList } from '@/components/task';
import { useAuthStore } from '@/lib/store/auth-store';
import { cn } from '@/lib/utils';

type TaskStatus = 'all' | 'pending' | 'processing' | 'completed' | 'failed';

interface TaskStats {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
}

export default function TasksPage() {
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

  const handleRetry = async (taskId: string) => {
    const userId = getUserId();
    if (!userId) return;
    
    try {
      setIsRetrying(taskId);
      await retryTask(taskId, userId);
      // 刷新列表
      await fetchTasks(activeFilter);
      // 可选：显示成功消息
    } catch (error) {
      console.error('Failed to retry task:', error);
      alert('Failed to retry task. Please try again later.');
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
      // TODO: 实现删除任务的 API 调用
      // await deleteTask(taskId, userId);
      console.log('Delete task:', taskId);
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


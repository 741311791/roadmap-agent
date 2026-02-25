'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChevronLeft, ListTodo, RefreshCw } from 'lucide-react';
import { tasksApi } from '@/lib/api/endpoints';
import type { TaskStatusResponse, TaskItemResponse } from '@/lib/api/endpoints';
import { TaskList } from '@/components/task';
import { useAuthStore } from '@/lib/store/auth-store';
import { cn } from '@/lib/utils';
import { TaskStatus } from '@/types/generated/constants';

type TaskFilterStatus = 'all' | 'pending' | 'processing' | 'completed' | 'failed';

interface TaskStats {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
}

export default function TasksPage() {
  const t = useTranslations('tasks');
  const router = useRouter();
  const [tasks, setTasks] = useState<TaskItemResponse[]>([]);
  const [stats, setStats] = useState<TaskStats>({
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0,
  });
  const [activeFilter, setActiveFilter] = useState<TaskFilterStatus>('all');
  const [isLoading, setIsLoading] = useState(true);
  const { getUserId } = useAuthStore();

  const fetchTasks = async (status?: string) => {
    const userId = getUserId();
    try {
      setIsLoading(true);
      const response = await tasksApi.getMyTasks(
        { status: status === 'all' ? undefined : status }
      );
      setTasks(response.tasks);
      setStats({
        pending: response.pending_count ?? 0,
        processing: response.processing_count ?? 0,
        completed: response.completed_count ?? 0,
        failed: response.failed_count ?? 0,
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
      // 乐观更新：立即将任务状态更新为 processing
      setTasks(prevTasks => 
        prevTasks.map(task => 
          task.task_id === taskId 
            ? { ...task, status: TaskStatus.PROCESSING, current_step: 'Retrying...' }
            : task
        )
      );
      
      // 更新统计数据
      setStats(prevStats => ({
        ...prevStats,
        failed: Math.max(0, prevStats.failed - 1),
        processing: prevStats.processing + 1,
      }));
      
      // 调用智能重试 API
      await tasksApi.retry(taskId);
      
      // ✅ 修复：立即刷新任务列表以获取最新状态（移除延迟）
      // 这样用户点击进入详情页时，能看到最新的 processing 状态
      await fetchTasks(activeFilter);
      
    } catch (error: any) {
      console.error('Failed to retry task:', error);
      
      // 重试失败，恢复原状态
      setTasks(prevTasks => 
        prevTasks.map(task => 
          task.task_id === taskId 
            ? { ...task, status: TaskStatus.FAILED, current_step: 'Failed' }
            : task
        )
      );
      
      setStats(prevStats => ({
        ...prevStats,
        failed: prevStats.failed + 1,
        processing: Math.max(0, prevStats.processing - 1),
      }));
    }
  };

  const handleCancel = async (taskId: string) => {
    if (!confirm(t('cancelConfirm'))) {
      return;
    }
    
    try {
      // 乐观更新：立即将任务状态更新为 cancelled
      setTasks(prevTasks => 
        prevTasks.map(task => 
          task.task_id === taskId 
            ? { ...task, status: TaskStatus.CANCELLED, current_step: 'Cancelled' }
            : task
        )
      );
      
      // 更新统计数据
      setStats(prevStats => ({
        ...prevStats,
        processing: Math.max(0, prevStats.processing - 1),
      }));
      
      // 调用取消 API
      await tasksApi.cancel(taskId);
      
      // 成功后刷新任务列表以获取最新状态
      setTimeout(() => {
        fetchTasks(activeFilter);
      }, 1000);
      
    } catch (error: any) {
      console.error('Failed to cancel task:', error);
      alert(t('cancelFailed'));
      
      // 取消失败，恢复原状态
      setTasks(prevTasks => 
        prevTasks.map(task => 
          task.task_id === taskId 
            ? { ...task, status: TaskStatus.PROCESSING }
            : task
        )
      );
      
      setStats(prevStats => ({
        ...prevStats,
        processing: prevStats.processing + 1,
      }));
    }
  };

  const handleDelete = async (taskId: string) => {
    if (!confirm(t('deleteConfirm'))) {
      return;
    }

    const userId = getUserId();
    if (!userId) return;
    
    try {
      // ✅ 修复：调用专门的删除接口
      // 后端会自动处理：如果任务是processing状态，会先取消再删除
      await tasksApi.delete(taskId);
      // 刷新列表
      await fetchTasks(activeFilter);
    } catch (error) {
      console.error('Failed to delete task:', error);
      alert(t('deleteFailed'));
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
          <ChevronLeft className="w-4 h-4" /> {t('backToHome')}
        </Link>

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-sage-100 flex items-center justify-center">
              <ListTodo size={24} className="text-sage-600" />
            </div>
            <div>
              <h1 className="text-2xl font-serif font-bold text-foreground">
                {t('title')}
              </h1>
              <p className="text-sm text-muted-foreground">
                {t('description')}
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
            {t('refresh')}
          </Button>
        </div>

        {/* Status Filters */}
        <div className="flex flex-wrap gap-2 mb-6">
          <Button
            variant={activeFilter === 'all' ? 'default' : 'outline'}
            onClick={() => setActiveFilter('all')}
            className="gap-2"
          >
            {t('all')}
            <Badge variant="secondary" className="ml-1">
              {stats.pending + stats.processing + stats.completed + stats.failed}
            </Badge>
          </Button>
          <Button
            variant={activeFilter === 'processing' ? 'default' : 'outline'}
            onClick={() => setActiveFilter('processing')}
            className="gap-2"
          >
            {t('processing')}
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
            {t('failed')}
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
            {t('completed')}
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
            {t('pending')}
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
          onCancel={handleCancel}
        />
      </div>
    </ScrollArea>
  );
}


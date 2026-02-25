/**
 * TaskList - 响应式任务列表组件（重构示例）
 * 
 * 移动端：卡片布局
 * 桌面端：表格布局
 * 
 * 这是对原 task-list.tsx 的响应式重构示例
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { EmptyState } from '@/components/common/empty-state';
import { ResponsiveTable, MobileCardWrapper, MobileCardRow } from '@/components/common/responsive-table';
import { TaskItem } from '@/lib/api/endpoints';
import { 
  ListTodo, 
  RefreshCw, 
  Eye, 
  AlertCircle, 
  Clock, 
  CheckCircle2, 
  Loader2, 
  FileText, 
  Trash2, 
  XCircle 
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { ErrorLogDialog } from './error-log-dialog';
import { useIsMobile } from '@/lib/hooks';
import { cn } from '@/lib/utils';

interface TaskListProps {
  tasks: TaskItem[];
  isLoading: boolean;
  onRetry: (taskId: string) => void;
  onDelete?: (taskId: string) => void;
  onCancel?: (taskId: string) => void;
}

export function TaskListResponsive({ 
  tasks, 
  isLoading, 
  onRetry, 
  onDelete, 
  onCancel 
}: TaskListProps) {
  const isMobile = useIsMobile();
  const [selectedErrorLog, setSelectedErrorLog] = useState<{
    title: string;
    message: string;
  } | null>(null);

  // 格式化日期时间
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    if (isMobile) {
      // 移动端：更紧凑的格式
      const month = date.toLocaleString('en-US', { month: 'short' });
      const day = date.getDate();
      return `${month} ${day}`;
    }
    // 桌面端：完整格式
    const month = date.toLocaleString('en-US', { month: 'short' });
    const day = date.getDate();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${month} ${day}, ${hours}:${minutes}`;
  };

  // 获取状态显示配置
  const getStatusConfig = (status: string) => {
    const config = {
      pending: { 
        variant: 'secondary' as const, 
        label: 'Pending', 
        icon: Clock,
        className: 'border-sage-200 text-sage-700 bg-sage-50'
      },
      processing: { 
        variant: 'default' as const, 
        label: 'Processing', 
        icon: Loader2,
        className: 'border-sage-300 text-sage-700 bg-sage-100 animate-pulse'
      },
      running: { 
        variant: 'default' as const, 
        label: 'Running', 
        icon: Loader2,
        className: 'border-sage-300 text-sage-700 bg-sage-100 animate-pulse'
      },
      human_review_pending: { 
        variant: 'secondary' as const, 
        label: 'Pending', 
        icon: Clock,
        className: 'border-amber-200 text-amber-700 bg-amber-50'
      },
      human_review_required: { 
        variant: 'secondary' as const, 
        label: 'Pending', 
        icon: Clock,
        className: 'border-amber-200 text-amber-700 bg-amber-50'
      },
      approved: { 
        variant: 'default' as const, 
        label: 'Approved', 
        icon: CheckCircle2,
        className: 'border-emerald-200 text-emerald-700 bg-emerald-50'
      },
      rejected: { 
        variant: 'secondary' as const, 
        label: 'Rejected', 
        icon: AlertCircle,
        className: 'border-orange-200 text-orange-700 bg-orange-50'
      },
      completed: { 
        variant: 'default' as const, 
        label: 'Completed', 
        icon: CheckCircle2,
        className: 'border-emerald-200 text-emerald-700 bg-emerald-50'
      },
      partial_failure: { 
        variant: 'default' as const, 
        label: 'Completed',
        icon: CheckCircle2,
        className: 'border-emerald-200 text-emerald-700 bg-emerald-50'
      },
      failed: { 
        variant: 'destructive' as const, 
        label: 'Failed', 
        icon: AlertCircle,
        className: 'border-red-200 text-red-700 bg-red-50'
      },
      cancelled: { 
        variant: 'destructive' as const, 
        label: 'Cancelled', 
        icon: XCircle,
        className: 'border-stone-200 text-stone-700 bg-stone-50'
      },
    };
    
    return config[status as keyof typeof config] || config.failed;
  };

  // Loading 状态
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-sage-200 border-t-sage-600 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-sm text-muted-foreground">Loading tasks...</p>
        </div>
      </div>
    );
  }

  // 空状态
  if (tasks.length === 0) {
    return (
      <EmptyState
        icon={ListTodo}
        title="No tasks yet"
        description="You haven't created any roadmap generation tasks."
        action={{
          label: 'Create Roadmap',
          onClick: () => {
            window.location.href = '/new';
          },
        }}
      />
    );
  }

  // 渲染移动端卡片
  const renderMobileCard = (task: TaskItem, index: number) => {
    const statusConfig = getStatusConfig(task.status);
    const StatusIcon = statusConfig.icon;

    return (
      <MobileCardWrapper>
        {/* 标题和序号 */}
        <div className="flex items-start gap-3">
          <span className="text-xs font-bold text-muted-foreground bg-sage-50 px-2 py-1 rounded">
            #{index + 1}
          </span>
          <Link
            href={`/tasks/${task.task_id}`}
            className="flex-1 font-semibold text-sm hover:text-sage-600 hover:underline transition-colors line-clamp-2"
          >
            {task.title}
          </Link>
        </div>

        {/* 状态徽章 */}
        <div className="flex items-center justify-between">
          <Badge 
            variant="outline" 
            className={cn('gap-1.5', statusConfig.className)}
          >
            <StatusIcon className={cn('w-3 h-3', task.status === 'processing' && 'animate-spin')} />
            {statusConfig.label}
          </Badge>
        </div>

        {/* 详细信息 */}
        <div className="space-y-2 text-xs">
          <MobileCardRow 
            label="Step" 
            value={task.current_step || '-'} 
          />
          <MobileCardRow 
            label="Created" 
            value={formatDate(task.created_at)} 
          />
          {task.completed_at && (
            <MobileCardRow 
              label="Completed" 
              value={formatDate(task.completed_at)} 
            />
          )}
        </div>

        {/* 操作按钮 */}
        <div className="flex flex-wrap gap-2 pt-2 border-t">
          {/* Cancel Button */}
          {task.status === 'processing' && onCancel && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onCancel(task.task_id)}
              className="flex-1 text-orange-600 border-orange-300 hover:bg-orange-50"
            >
              <XCircle className="h-3.5 w-3.5 mr-1.5" />
              Cancel
            </Button>
          )}

          {/* View Error Logs */}
          {(task.status === 'failed' || task.status === 'partial_failure') && task.error_message && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setSelectedErrorLog({
                title: task.title || 'Unknown Task',
                message: task.error_message || 'No error message'
              })}
              className="flex-1"
            >
              <FileText className="h-3.5 w-3.5 mr-1.5" />
              Logs
            </Button>
          )}

          {/* Retry Button */}
          {(task.status === 'failed' || task.status === 'cancelled') && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onRetry(task.task_id)}
              className="flex-1"
            >
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Retry
            </Button>
          )}

          {/* View Roadmap */}
          {(task.status === 'completed' || task.status === 'partial_failure') && task.roadmap_id && (
            <Link href={`/roadmap/${task.roadmap_id}`} className="flex-1">
              <Button size="sm" variant="outline" className="w-full">
                <Eye className="h-3.5 w-3.5 mr-1.5" />
                View
              </Button>
            </Link>
          )}

          {/* Delete Button */}
          {onDelete && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onDelete(task.task_id)}
              className="flex-1 text-red-600 border-red-300 hover:bg-red-50"
            >
              <Trash2 className="h-3.5 w-3.5 mr-1.5" />
              Delete
            </Button>
          )}
        </div>
      </MobileCardWrapper>
    );
  };

  // 表格列定义
  const columns = [
    {
      header: '#',
      className: 'w-[50px]',
      cell: (task: TaskItem) => (
        <span className="text-sm text-muted-foreground font-medium">
          {tasks.findIndex(t => t.task_id === task.task_id) + 1}
        </span>
      ),
    },
    {
      header: 'Task Title',
      className: 'min-w-[200px]',
      cell: (task: TaskItem) => (
        <Link
          href={`/tasks/${task.task_id}`}
          className="font-medium hover:text-sage-600 hover:underline transition-colors line-clamp-1"
          title={task.title || undefined}
        >
          {task.title}
        </Link>
      ),
    },
    {
      header: 'Status',
      className: 'w-[120px]',
      cell: (task: TaskItem) => {
        const statusConfig = getStatusConfig(task.status);
        const StatusIcon = statusConfig.icon;
        return (
          <Badge variant="outline" className={cn('gap-1', statusConfig.className)}>
            <StatusIcon className={cn('w-3 h-3', task.status === 'processing' && 'animate-spin')} />
            {statusConfig.label}
          </Badge>
        );
      },
    },
    {
      header: 'Current Step',
      className: 'min-w-[140px]',
      cell: (task: TaskItem) => (
        <span className="text-sm text-muted-foreground">
          {task.current_step || '-'}
        </span>
      ),
    },
    {
      header: 'Created',
      className: 'min-w-[130px]',
      cell: (task: TaskItem) => (
        <span className="text-sm text-muted-foreground">
          {formatDate(task.created_at)}
        </span>
      ),
    },
    {
      header: 'Completed',
      className: 'min-w-[130px]',
      cell: (task: TaskItem) => (
        <span className="text-sm text-muted-foreground">
          {task.completed_at ? formatDate(task.completed_at) : '-'}
        </span>
      ),
    },
    {
      header: 'Actions',
      className: 'w-[120px] text-right',
      cell: (task: TaskItem) => (
        <TooltipProvider>
          <div className="flex items-center justify-end gap-1">
            {/* Cancel */}
            {task.status === 'processing' && onCancel && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => onCancel(task.task_id)}
                    className="h-8 w-8 text-orange-600 hover:text-orange-700 hover:bg-orange-50"
                  >
                    <XCircle className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent><p>Cancel task</p></TooltipContent>
              </Tooltip>
            )}

            {/* View Error Logs */}
            {(task.status === 'failed' || task.status === 'partial_failure') && task.error_message && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => setSelectedErrorLog({
                      title: task.title || 'Unknown Task',
                      message: task.error_message || 'No error message'
                    })}
                    className="h-8 w-8"
                  >
                    <FileText className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent><p>View error logs</p></TooltipContent>
              </Tooltip>
            )}

            {/* Retry */}
            {(task.status === 'failed' || task.status === 'cancelled') && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => onRetry(task.task_id)}
                    className="h-8 w-8"
                  >
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent><p>Retry task</p></TooltipContent>
              </Tooltip>
            )}

            {/* View Roadmap */}
            {(task.status === 'completed' || task.status === 'partial_failure') && task.roadmap_id && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Link href={`/roadmap/${task.roadmap_id}`}>
                    <Button size="icon" variant="ghost" className="h-8 w-8">
                      <Eye className="h-4 w-4" />
                    </Button>
                  </Link>
                </TooltipTrigger>
                <TooltipContent><p>View roadmap</p></TooltipContent>
              </Tooltip>
            )}

            {/* Delete */}
            {onDelete && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => onDelete(task.task_id)}
                    className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent><p>Delete task</p></TooltipContent>
              </Tooltip>
            )}
          </div>
        </TooltipProvider>
      ),
    },
  ];

  return (
    <>
      <ResponsiveTable
        data={tasks}
        columns={columns}
        renderMobileCard={(task, index) => renderMobileCard(task, index)}
        getRowKey={(task) => task.task_id}
      />

      {/* Error Log Dialog */}
      <ErrorLogDialog
        open={selectedErrorLog !== null}
        onOpenChange={(open) => !open && setSelectedErrorLog(null)}
        taskTitle={selectedErrorLog?.title || ''}
        errorMessage={selectedErrorLog?.message || ''}
      />
    </>
  );
}

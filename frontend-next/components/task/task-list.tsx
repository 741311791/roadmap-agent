'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { EmptyState } from '@/components/common/empty-state';
import { TaskItem } from '@/lib/api/endpoints';
import { ListTodo, RefreshCw, Eye, AlertCircle, Clock, CheckCircle2, Loader2, FileText, Trash2, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { ErrorLogDialog } from './error-log-dialog';

interface TaskListProps {
  tasks: TaskItem[];
  isLoading: boolean;
  offset?: number;
  onRetry: (taskId: string) => void;
  onDelete?: (taskId: string) => void;
  onCancel?: (taskId: string) => void;
}

export function TaskList({ tasks, isLoading, offset = 0, onRetry, onDelete, onCancel }: TaskListProps) {
  const t = useTranslations('taskList');
  const tCommon = useTranslations('common');
  const [selectedErrorLog, setSelectedErrorLog] = useState<{
    title: string;
    message: string;
  } | null>(null);

  // 格式化日期时间（超紧凑格式，避免换行）
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const month = date.toLocaleString('en-US', { month: 'short' });
    const day = date.getDate();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    
    // 格式: Jan 5, 01:04 （移除年份和 AM/PM，更紧凑）
    return `${month} ${day}, ${hours}:${minutes}`;
  };

  const getQueueHint = (queueAheadCount?: number | null) => {
    if (typeof queueAheadCount !== 'number') {
      return null;
    }

    if (queueAheadCount > 0) {
      return t('queueAhead', { count: queueAheadCount });
    }

    return t('queueNoAhead');
  };

  // 获取状态显示配置（优化后的 sage 主题色系）
  const getStatusConfig = (status: string) => {
    const config = {
      pending: { 
        variant: 'secondary' as const, 
        label: t('pending'), 
        icon: Clock,
        className: 'border-sage-200 text-sage-700 bg-sage-50 dark:border-sage-800 dark:text-sage-300 dark:bg-sage-950'
      },
      processing: { 
        variant: 'default' as const, 
        label: t('processing'), 
        icon: Loader2,
        className: 'border-sage-300 text-sage-700 bg-sage-100 dark:border-sage-700 dark:text-sage-300 dark:bg-sage-900 animate-pulse'
      },
      running: { 
        variant: 'default' as const, 
        label: t('running'), 
        icon: Loader2,
        className: 'border-sage-300 text-sage-700 bg-sage-100 dark:border-sage-700 dark:text-sage-300 dark:bg-sage-900 animate-pulse'
      },
      human_review_pending: { 
        variant: 'secondary' as const, 
        label: t('humanReviewPending'), 
        icon: Clock,
        className: 'border-amber-200 text-amber-700 bg-amber-50 dark:border-amber-800 dark:text-amber-300 dark:bg-amber-950 whitespace-nowrap'
      },
      human_review_required: { 
        variant: 'secondary' as const, 
        label: t('humanReviewRequired'), 
        icon: Clock,
        className: 'border-amber-200 text-amber-700 bg-amber-50 dark:border-amber-800 dark:text-amber-300 dark:bg-amber-950 whitespace-nowrap'
      },
      approved: { 
        variant: 'default' as const, 
        label: t('approved'), 
        icon: CheckCircle2,
        className: 'border-emerald-200 text-emerald-700 bg-emerald-50 dark:border-emerald-800 dark:text-emerald-300 dark:bg-emerald-950'
      },
      rejected: { 
        variant: 'secondary' as const, 
        label: t('rejected'), 
        icon: AlertCircle,
        className: 'border-orange-200 text-orange-700 bg-orange-50 dark:border-orange-800 dark:text-orange-300 dark:bg-orange-950'
      },
      completed: { 
        variant: 'default' as const, 
        label: t('completed'), 
        icon: CheckCircle2,
        className: 'border-emerald-200 text-emerald-700 bg-emerald-50 dark:border-emerald-800 dark:text-emerald-300 dark:bg-emerald-950'
      },
      partial_failure: { 
        variant: 'default' as const, 
        label: t('completed'),
        icon: CheckCircle2,
        className: 'border-emerald-200 text-emerald-700 bg-emerald-50 dark:border-emerald-800 dark:text-emerald-300 dark:bg-emerald-950'
      },
      failed: { 
        variant: 'destructive' as const, 
        label: t('failed'), 
        icon: AlertCircle,
        className: 'border-red-200 text-red-700 bg-red-50 dark:border-red-800 dark:text-red-300 dark:bg-red-950'
      },
      cancelled: { 
        variant: 'destructive' as const, 
        label: t('cancelled'), 
        icon: XCircle,
        className: 'border-stone-200 text-stone-700 bg-stone-50 dark:border-stone-800 dark:text-stone-300 dark:bg-stone-950'
      },
    };
    
    return config[status as keyof typeof config] || config.failed;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-sage-200 border-t-sage-600 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-sm text-muted-foreground">{t('loading')}</p>
        </div>
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <EmptyState
        icon={ListTodo}
        title={t('noTasksYet')}
        description={t('noTasksDesc')}
        action={{
          label: tCommon('createRoadmap'),
          onClick: () => {
            window.location.href = '/new';
          },
        }}
      />
    );
  }

  return (
    <TooltipProvider>
      <div className="rounded-lg border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[50px]">#</TableHead>
              <TableHead className="w-[240px]">{t('taskTitle')}</TableHead>
              <TableHead className="w-[120px]">{t('status')}</TableHead>
              <TableHead className="w-[140px]">{t('currentStep')}</TableHead>
              <TableHead className="w-[130px]">{t('created')}</TableHead>
              <TableHead className="w-[130px]">{t('completedTime')}</TableHead>
              <TableHead className="w-[120px] text-right">{t('actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.map((task, index) => {
              const statusConfig = getStatusConfig(task.status);
              const StatusIcon = statusConfig.icon;

              return (
                <TableRow key={task.task_id}>
                  {/* Index Number */}
                  <TableCell className="text-sm text-muted-foreground font-medium">
                    {offset + index + 1}
                  </TableCell>

                  {/* Task Title */}
                  <TableCell className="font-medium">
                    <Link
                      href={`/tasks/${task.task_id}`}
                      className="block truncate max-w-[220px] hover:text-sage-600 hover:underline transition-colors"
                      title={task.title || undefined}
                    >
                      {task.title}
                    </Link>
                  </TableCell>

                  {/* Status Badge */}
                  <TableCell>
                    <Badge 
                      variant="outline" 
                      className={`gap-1 ${statusConfig.className}`}
                    >
                      <StatusIcon className={`w-3 h-3 ${task.status === 'processing' ? 'animate-spin' : ''}`} />
                      {statusConfig.label}
                    </Badge>
                  </TableCell>

                  {/* Current Step */}
                  <TableCell>
                    <div className="space-y-1">
                      <span className="text-sm text-muted-foreground">
                        {task.current_step || '-'}
                      </span>
                      {task.status === 'pending' && (
                        <p className="text-xs text-amber-700 dark:text-amber-400">
                          {getQueueHint(task.queue_ahead_count)}
                        </p>
                      )}
                    </div>
                  </TableCell>

                  {/* Created Date */}
                  <TableCell>
                    <span className="text-sm text-muted-foreground">
                      {formatDate(task.created_at)}
                    </span>
                  </TableCell>

                  {/* Completed Date */}
                  <TableCell>
                    {task.completed_at ? (
                      <span className="text-sm text-muted-foreground">
                        {formatDate(task.completed_at)}
                      </span>
                    ) : (
                      <span className="text-sm text-muted-foreground">-</span>
                    )}
                  </TableCell>

                  {/* Actions */}
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      {/* Cancel Button - 正在处理时显示 */}
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
                          <TooltipContent>
                            <p>{t('cancelTask')}</p>
                          </TooltipContent>
                        </Tooltip>
                      )}

                      {/* View Logs Button - 失败和部分失败时显示 */}
                      {(task.status === 'failed' || task.status === 'partial_failure') && task.error_message && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              size="icon"
                              variant="ghost"
                              onClick={() => setSelectedErrorLog({
                                title: task.title || 'Unknown Task',
                                message: task.error_message || 'No error message available'
                              })}
                              className="h-8 w-8"
                            >
                              <FileText className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>{t('viewErrorLog')}</p>
                          </TooltipContent>
                        </Tooltip>
                      )}

                      {/* Retry Button - 失败和取消状态时显示 */}
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
                          <TooltipContent>
                            <p>{t('retryTask')}</p>
                          </TooltipContent>
                        </Tooltip>
                      )}
                      
                      {/* View Roadmap Button - 完成后显示（包括部分失败） */}
                      {(task.status === 'completed' || task.status === 'partial_failure') && task.roadmap_id && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Link href={`/roadmap/${task.roadmap_id}`}>
                              <Button 
                                size="icon" 
                                variant="ghost" 
                                className="h-8 w-8"
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                            </Link>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>{task.status === 'partial_failure' ? t('viewRoadmapRetry') : t('viewRoadmap')}</p>
                          </TooltipContent>
                        </Tooltip>
                      )}

                      {/* Delete Button - 显示在所有任务 */}
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
                          <TooltipContent>
                            <p>{t('deleteTask')}</p>
                          </TooltipContent>
                        </Tooltip>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Error Log Dialog */}
      <ErrorLogDialog
        open={selectedErrorLog !== null}
        onOpenChange={(open) => !open && setSelectedErrorLog(null)}
        taskTitle={selectedErrorLog?.title || ''}
        errorMessage={selectedErrorLog?.message || ''}
      />
    </TooltipProvider>
  );
}

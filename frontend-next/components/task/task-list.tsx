'use client';

import { useState } from 'react';
import Link from 'next/link';
import { EmptyState } from '@/components/common/empty-state';
import { TaskItem } from '@/lib/api/endpoints';
import { ListTodo, RefreshCw, Eye, AlertCircle, Clock, CheckCircle2, Loader2, FileText, Trash2 } from 'lucide-react';
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
  onRetry: (taskId: string) => void;
  onDelete?: (taskId: string) => void;
}

export function TaskList({ tasks, isLoading, onRetry, onDelete }: TaskListProps) {
  const [selectedErrorLog, setSelectedErrorLog] = useState<{
    title: string;
    message: string;
  } | null>(null);

  // 格式化日期时间
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 获取状态显示配置
  const getStatusConfig = (status: string) => {
    const config = {
      pending: { 
        variant: 'secondary' as const, 
        label: 'Pending', 
        icon: Clock,
        className: 'border-amber-300 text-amber-600 bg-amber-50'
      },
      processing: { 
        variant: 'default' as const, 
        label: 'Processing', 
        icon: Loader2,
        className: 'border-blue-300 text-blue-600 bg-blue-50 animate-pulse'
      },
      running: { 
        variant: 'default' as const, 
        label: 'Running', 
        icon: Loader2,
        className: 'border-blue-300 text-blue-600 bg-blue-50 animate-pulse'
      },
      human_review_pending: { 
        variant: 'secondary' as const, 
        label: 'Review Pending', 
        icon: Clock,
        className: 'border-purple-300 text-purple-600 bg-purple-50'
      },
      human_review_required: { 
        variant: 'secondary' as const, 
        label: 'Review Required', 
        icon: Clock,
        className: 'border-purple-300 text-purple-600 bg-purple-50'
      },
      approved: { 
        variant: 'default' as const, 
        label: 'Approved', 
        icon: CheckCircle2,
        className: 'border-green-300 text-green-600 bg-green-50'
      },
      rejected: { 
        variant: 'secondary' as const, 
        label: 'Rejected', 
        icon: AlertCircle,
        className: 'border-orange-300 text-orange-600 bg-orange-50'
      },
      completed: { 
        variant: 'default' as const, 
        label: 'Completed', 
        icon: CheckCircle2,
        className: 'border-green-300 text-green-600 bg-green-50'
      },
      partial_failure: { 
        variant: 'default' as const, 
        label: 'Completed',  // ✅ 简化：显示为 Completed
        icon: CheckCircle2,  // ✅ 使用绿色对勾图标
        className: 'border-green-300 text-green-600 bg-green-50'  // ✅ 使用绿色样式
      },
      failed: { 
        variant: 'destructive' as const, 
        label: 'Failed', 
        icon: AlertCircle,
        className: 'border-red-300 text-red-600 bg-red-50'
      },
    };
    
    return config[status as keyof typeof config] || config.failed;
  };

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

  return (
    <TooltipProvider>
      <div className="rounded-lg border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[300px]">Task Title</TableHead>
              <TableHead className="w-[120px]">Status</TableHead>
              <TableHead className="w-[150px]">Current Step</TableHead>
              <TableHead className="w-[180px]">Created</TableHead>
              <TableHead className="w-[180px]">Completed</TableHead>
              <TableHead className="w-[150px] text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.map((task) => {
              const statusConfig = getStatusConfig(task.status);
              const StatusIcon = statusConfig.icon;

              return (
                <TableRow key={task.task_id}>
                  {/* Task Title */}
                  <TableCell className="font-medium">
                    <div className="flex flex-col gap-1">
                      <Link
                        href={`/tasks/${task.task_id}`}
                        className="truncate max-w-[280px] hover:text-sage-600 hover:underline transition-colors"
                      >
                        {task.title}
                      </Link>
                      <span className="text-xs text-muted-foreground font-mono">
                        ID: {task.task_id.substring(0, 8)}...
                      </span>
                    </div>
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
                    <span className="text-sm text-muted-foreground">
                      {task.current_step || '-'}
                    </span>
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
                      {/* View Logs Button - 失败和部分失败时显示 */}
                      {(task.status === 'failed' || task.status === 'partial_failure') && task.error_message && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              size="icon"
                              variant="ghost"
                              onClick={() => setSelectedErrorLog({
                                title: task.title,
                                message: task.error_message || 'No error message available'
                              })}
                              className="h-8 w-8"
                            >
                              <FileText className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>View error logs</p>
                          </TooltipContent>
                        </Tooltip>
                      )}

                      {/* Retry Button - 仅完全失败时显示 */}
                      {task.status === 'failed' && (
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
                            <p>Retry task</p>
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
                            <p>{task.status === 'partial_failure' ? 'View roadmap & retry failed concepts' : 'View roadmap'}</p>
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
                            <p>Delete task</p>
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

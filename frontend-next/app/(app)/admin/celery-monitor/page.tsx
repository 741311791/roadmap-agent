/**
 * Celery 任务队列监控页面
 * 
 * 超级管理员专用页面，用于实时监控 Celery 任务队列状态
 * 
 * 功能：
 * - 查看任务队列总览（活跃、待处理、失败任务统计）
 * - 按状态和队列筛选任务
 * - 查看任务详情（参数、结果、错误信息）
 * - 实时自动刷新（每 5 秒）
 */
'use client';

import { useEffect, useState } from 'react';
import { useAuthStore } from '@/lib/store/auth-store';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { TableSkeleton } from '@/components/common/loading-skeleton';
import { Activity, RefreshCw, Search, Clock, CheckCircle2, XCircle, AlertCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import {
  getCeleryOverview,
  getCeleryTasks,
  getCeleryTaskDetail,
  type CeleryOverview,
  type CeleryTask,
  type CeleryTasksParams,
} from '@/lib/api/celery-monitor';

// ============================================================
// 类型定义
// ============================================================

type StatusFilter = 'all' | 'active' | 'scheduled' | 'reserved';

// ============================================================
// 工具函数
// ============================================================

/**
 * 获取任务状态对应的徽章样式
 */
function getStatusBadgeVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'SUCCESS':
      return 'default';
    case 'STARTED':
    case 'SCHEDULED':
    case 'RESERVED':
      return 'secondary';
    case 'FAILURE':
      return 'destructive';
    case 'PENDING':
    case 'RETRY':
    default:
      return 'outline';
  }
}

/**
 * 获取任务状态对应的图标
 */
function getStatusIcon(status: string) {
  switch (status) {
    case 'SUCCESS':
      return <CheckCircle2 size={14} className="text-green-600" />;
    case 'STARTED':
      return <Loader2 size={14} className="text-blue-600 animate-spin" />;
    case 'FAILURE':
      return <XCircle size={14} className="text-red-600" />;
    case 'SCHEDULED':
    case 'RESERVED':
      return <Clock size={14} className="text-yellow-600" />;
    case 'PENDING':
    case 'RETRY':
    default:
      return <AlertCircle size={14} className="text-gray-600" />;
  }
}

/**
 * 格式化时间戳
 */
function formatTimestamp(timestamp?: string): string {
  if (!timestamp) return '-';
  try {
    return format(new Date(timestamp), 'yyyy-MM-dd HH:mm:ss');
  } catch {
    return timestamp;
  }
}

/**
 * 格式化执行耗时
 */
function formatDuration(duration?: number): string {
  if (!duration) return '-';
  if (duration < 60) {
    return `${duration.toFixed(1)}s`;
  }
  const minutes = Math.floor(duration / 60);
  const seconds = Math.floor(duration % 60);
  return `${minutes}m ${seconds}s`;
}

/**
 * 截断任务 ID 显示
 */
function truncateTaskId(taskId: string): string {
  if (taskId.length <= 16) return taskId;
  return `${taskId.slice(0, 8)}...${taskId.slice(-4)}`;
}

// ============================================================
// 统计卡片组件
// ============================================================

interface StatCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  variant: 'success' | 'warning' | 'danger' | 'info';
}

function StatCard({ title, value, icon, variant }: StatCardProps) {
  const colorClasses = {
    success: 'bg-green-50 text-green-700 border-green-200',
    warning: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    danger: 'bg-red-50 text-red-700 border-red-200',
    info: 'bg-blue-50 text-blue-700 border-blue-200',
  };

  return (
    <div className={`rounded-lg border p-4 ${colorClasses[variant]}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium opacity-80">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <div className="opacity-80">{icon}</div>
      </div>
    </div>
  );
}

// ============================================================
// 任务详情对话框组件
// ============================================================

interface TaskDetailDialogProps {
  task: CeleryTask | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function TaskDetailDialog({ task, open, onOpenChange }: TaskDetailDialogProps) {
  if (!task) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Activity size={20} />
            Task Detail
          </DialogTitle>
          <DialogDescription>
            Detailed information about Celery task
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* 基本信息 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Task ID</p>
              <p className="text-sm font-mono mt-1">{task.task_id}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Task Name</p>
              <p className="text-sm font-mono mt-1">{task.task_name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Queue</p>
              <p className="text-sm mt-1">{task.queue || '-'}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Status</p>
              <div className="mt-1">
                <Badge variant={getStatusBadgeVariant(task.status)} className="flex items-center gap-1 w-fit">
                  {getStatusIcon(task.status)}
                  {task.status}
                </Badge>
              </div>
            </div>
            {task.worker && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">Worker</p>
                <p className="text-sm font-mono mt-1">{task.worker}</p>
              </div>
            )}
          </div>

          {/* 时间信息 */}
          <div className="border-t pt-4">
            <h4 className="text-sm font-semibold mb-3">Time Information</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Started At</p>
                <p className="text-sm mt-1">{formatTimestamp(task.started_at)}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Completed At</p>
                <p className="text-sm mt-1">{formatTimestamp(task.completed_at)}</p>
              </div>
              {task.duration !== undefined && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Duration</p>
                  <p className="text-sm mt-1">{formatDuration(task.duration)}</p>
                </div>
              )}
            </div>
          </div>

          {/* 参数信息 */}
          {(task.args || task.kwargs) && (
            <div className="border-t pt-4">
              <h4 className="text-sm font-semibold mb-3">Arguments</h4>
              {task.args && task.args.length > 0 && (
                <div className="mb-3">
                  <p className="text-sm font-medium text-muted-foreground mb-1">Args</p>
                  <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto">
                    {JSON.stringify(task.args, null, 2)}
                  </pre>
                </div>
              )}
              {task.kwargs && Object.keys(task.kwargs).length > 0 && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">Kwargs</p>
                  <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto">
                    {JSON.stringify(task.kwargs, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* 结果信息 */}
          {task.result && (
            <div className="border-t pt-4">
              <h4 className="text-sm font-semibold mb-3">Result</h4>
              <pre className="text-xs bg-green-50 p-3 rounded-md overflow-x-auto border border-green-200">
                {JSON.stringify(task.result, null, 2)}
              </pre>
            </div>
          )}

          {/* 错误信息 */}
          {task.error && (
            <div className="border-t pt-4">
              <h4 className="text-sm font-semibold mb-3 text-red-600">Error</h4>
              <pre className="text-xs bg-red-50 p-3 rounded-md overflow-x-auto border border-red-200 text-red-800">
                {task.error}
              </pre>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================
// 主组件
// ============================================================

export default function CeleryMonitorPage() {
  const { user } = useAuthStore();

  // 状态管理
  const [mounted, setMounted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [overview, setOverview] = useState<CeleryOverview | null>(null);
  const [tasks, setTasks] = useState<CeleryTask[]>([]);
  const [totalTasks, setTotalTasks] = useState(0);
  const [selectedTask, setSelectedTask] = useState<CeleryTask | null>(null);
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false);

  // 筛选和搜索
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [queueFilter, setQueueFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // 自动刷新
  const [autoRefresh, setAutoRefresh] = useState(true);

  // 加载总览数据
  const loadOverview = async () => {
    try {
      const data = await getCeleryOverview();
      setOverview(data);
    } catch (error) {
      console.error('Failed to load overview:', error);
      toast.error('Failed to load overview');
    }
  };

  // 加载任务列表
  const loadTasks = async () => {
    try {
      const params: CeleryTasksParams = {
        status: statusFilter === 'all' ? undefined : statusFilter,
        queue: queueFilter === 'all' ? undefined : queueFilter,
        limit: 50,
        offset: 0,
      };

      const data = await getCeleryTasks(params);
      setTasks(data.tasks);
      setTotalTasks(data.total);
    } catch (error) {
      console.error('Failed to load tasks:', error);
      toast.error('Failed to load tasks');
    }
  };

  // 初始加载
  const loadData = async () => {
    setIsLoading(true);
    try {
      await Promise.all([loadOverview(), loadTasks()]);
    } finally {
      setIsLoading(false);
    }
  };

  // 手动刷新
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([loadOverview(), loadTasks()]);
      toast.success('Data refreshed');
    } finally {
      setIsRefreshing(false);
    }
  };

  // 查看任务详情
  const handleViewDetail = async (taskId: string) => {
    try {
      const task = await getCeleryTaskDetail(taskId);
      setSelectedTask(task);
      setIsDetailDialogOpen(true);
    } catch (error) {
      console.error('Failed to load task detail:', error);
      toast.error('Failed to load task detail');
    }
  };

  // 确保组件已挂载（避免 hydration 错误）
  useEffect(() => {
    setMounted(true);
  }, []);

  // 初始加载
  useEffect(() => {
    if (mounted) {
      loadData();
    }
  }, [mounted]);

  // 筛选器变化时重新加载
  useEffect(() => {
    if (mounted && !isLoading) {
      loadTasks();
    }
  }, [mounted, statusFilter, queueFilter]);

  // 自动刷新
  useEffect(() => {
    if (!mounted || !autoRefresh) return;

    const interval = setInterval(() => {
      loadOverview();
      loadTasks();
    }, 5000); // 每 5 秒刷新

    return () => clearInterval(interval);
  }, [mounted, autoRefresh, statusFilter, queueFilter]);

  // 客户端搜索过滤
  const filteredTasks = tasks.filter((task) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      task.task_id.toLowerCase().includes(query) ||
      task.task_name.toLowerCase().includes(query)
    );
  });

  // 获取可用的队列列表
  const availableQueues = overview?.queue_lengths
    ? ['all', ...Object.keys(overview.queue_lengths)]
    : ['all', 'logs', 'content_generation'];

  // 在组件挂载前显示加载状态（避免 hydration 错误）
  if (!mounted) {
    return (
      <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-center min-h-[60vh]">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      {/* 页面标题 */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
            <Activity size={20} className="text-blue-600" />
          </div>
          <div>
            <h1 className="text-3xl font-serif font-bold text-foreground">Celery Task Monitor</h1>
            <p className="text-sm text-muted-foreground">Real-time task queue monitoring</p>
          </div>
        </div>
      </div>

      {/* 统计卡片 */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      ) : overview ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <StatCard
            title="Active Tasks"
            value={overview.active_count}
            icon={<Loader2 size={24} className="animate-spin" />}
            variant="info"
          />
          <StatCard
            title="Pending Tasks"
            value={overview.pending_count}
            icon={<Clock size={24} />}
            variant="warning"
          />
          <StatCard
            title="Scheduled Tasks"
            value={overview.scheduled_count}
            icon={<Clock size={24} />}
            variant="warning"
          />
          <StatCard
            title="Reserved Tasks"
            value={overview.reserved_count}
            icon={<AlertCircle size={24} />}
            variant="info"
          />
        </div>
      ) : null}

      {/* 队列长度统计 */}
      {overview && Object.keys(overview.queue_lengths).length > 0 && (
        <div className="mb-8 p-4 bg-muted rounded-lg">
          <h3 className="text-sm font-semibold mb-3">Queue Lengths</h3>
          <div className="flex flex-wrap gap-3">
            {Object.entries(overview.queue_lengths).map(([queue, length]) => (
              <div key={queue} className="flex items-center gap-2 px-3 py-1.5 bg-background rounded-md border">
                <span className="text-sm font-medium">{queue}</span>
                <Badge variant="secondary">{length}</Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 筛选和搜索 */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="flex-1 flex gap-3">
          <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as StatusFilter)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="scheduled">Scheduled</SelectItem>
              <SelectItem value="reserved">Reserved</SelectItem>
            </SelectContent>
          </Select>

          <Select value={queueFilter} onValueChange={setQueueFilter}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Filter by queue" />
            </SelectTrigger>
            <SelectContent>
              {availableQueues.map((queue) => (
                <SelectItem key={queue} value={queue}>
                  {queue === 'all' ? 'All Queues' : queue}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={18} />
            <Input
              placeholder="Search by Task ID or Name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
            Refresh
          </Button>
          <Button
            variant={autoRefresh ? 'default' : 'outline'}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
          </Button>
        </div>
      </div>

      {/* 任务列表 */}
      {isLoading ? (
        <TableSkeleton rows={5} columns={7} />
      ) : (
        <>
          <div className="rounded-lg border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Task ID</TableHead>
                  <TableHead>Task Name</TableHead>
                  <TableHead>Queue</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Worker</TableHead>
                  <TableHead>Started At</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTasks.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                      No tasks found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredTasks.map((task) => (
                    <TableRow key={task.task_id}>
                      <TableCell className="font-mono text-xs">
                        {truncateTaskId(task.task_id)}
                      </TableCell>
                      <TableCell className="font-mono text-sm">{task.task_name}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{task.queue || '-'}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getStatusBadgeVariant(task.status)} className="flex items-center gap-1 w-fit">
                          {getStatusIcon(task.status)}
                          {task.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{task.worker || '-'}</TableCell>
                      <TableCell className="text-sm">{formatTimestamp(task.started_at)}</TableCell>
                      <TableCell className="text-sm">{formatDuration(task.duration)}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewDetail(task.task_id)}
                        >
                          View Detail
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* 分页信息 */}
          <div className="mt-4 text-sm text-muted-foreground text-center">
            Showing {filteredTasks.length} of {totalTasks} tasks
          </div>
        </>
      )}

      {/* 任务详情对话框 */}
      <TaskDetailDialog
        task={selectedTask}
        open={isDetailDialogOpen}
        onOpenChange={setIsDetailDialogOpen}
      />
    </div>
  );
}


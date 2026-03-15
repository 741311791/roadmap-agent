/**
 * 管理员任务监控页面
 *
 * 重构说明：
 * - 主数据源改为 DB 业务历史任务，不再依赖瞬时 Celery 队列
 * - 总览区分为 DB 业务统计（始终有值）和 runtime 统计（inspect 可用时有值）
 * - 当 inspect 不可用时显示降级提示，而不是伪装成"0 任务"
 * - 状态筛选项对应真实业务状态
 * - 详情弹窗优先展示业务字段，再展示 Celery runtime 字段
 */
'use client';

import { useEffect, useState } from 'react';
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
import { Alert, AlertDescription } from '@/components/ui/alert';
import { TableSkeleton } from '@/components/common/loading-skeleton';
import {
  Activity,
  RefreshCw,
  Search,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  WifiOff,
  Database,
  Cpu,
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import {
  cleanupStaleTask,
  cleanupStaleTasks,
  forceCleanupStaleTask,
  forceCleanupStaleTasks,
  getCeleryOverview,
  getCeleryTasks,
  getCeleryTaskDetail,
  type CeleryOverview,
  type CeleryTaskCleanupBatchResponse,
  type CeleryTask,
  type CeleryTasksParams,
} from '@/lib/api/celery-monitor';
import { cn } from '@/lib/utils';

// ============================================================
// 类型定义
// ============================================================

/** 业务状态筛选 */
type StatusFilter = 'all' | 'active' | 'pending' | 'processing' | 'human_review_pending' | 'completed' | 'failed';

const STATUS_FILTER_LABELS: Record<StatusFilter, string> = {
  all: 'All Statuses',
  active: 'Active',
  pending: 'Pending',
  processing: 'Processing',
  human_review_pending: 'Human Review',
  completed: 'Completed',
  failed: 'Failed',
};

// ============================================================
// 工具函数
// ============================================================

/**
 * 根据任务展示状态返回徽章样式
 * 优先使用业务 workflow_status，fallback 到 status
 */
function getStatusBadgeVariant(task: CeleryTask): 'default' | 'secondary' | 'destructive' | 'outline' {
  const s = task.workflow_status || task.status;
  switch (s) {
    case 'completed':
    case 'approved':
    case 'partial_failure':
    case 'SUCCESS':
      return 'default';
    case 'processing':
    case 'running':
    case 'human_review_pending':
    case 'human_review_required':
    case 'STARTED':
    case 'SCHEDULED':
    case 'RESERVED':
      return 'secondary';
    case 'failed':
    case 'rejected':
    case 'FAILURE':
      return 'destructive';
    default:
      return 'outline';
  }
}

/** 根据任务状态返回图标 */
function getStatusIcon(task: CeleryTask) {
  const s = task.workflow_status || task.status;
  switch (s) {
    case 'completed':
    case 'approved':
    case 'SUCCESS':
      return <CheckCircle2 size={14} className="text-green-600" />;
    case 'processing':
    case 'running':
    case 'STARTED':
      return <Loader2 size={14} className="text-blue-600 animate-spin" />;
    case 'human_review_pending':
    case 'human_review_required':
      return <AlertCircle size={14} className="text-yellow-600" />;
    case 'failed':
    case 'rejected':
    case 'FAILURE':
      return <XCircle size={14} className="text-red-600" />;
    case 'SCHEDULED':
    case 'RESERVED':
      return <Clock size={14} className="text-yellow-600" />;
    default:
      return <Clock size={14} className="text-gray-500" />;
  }
}

/** 获取对外展示的状态文字 */
function getStatusLabel(task: CeleryTask): string {
  const labelMap: Record<string, string> = {
    pending: 'Pending',
    processing: 'Processing',
    running: 'Running',
    human_review_pending: 'Human Review',
    human_review_required: 'Human Review',
    completed: 'Completed',
    approved: 'Approved',
    partial_failure: 'Partial',
    failed: 'Failed',
    rejected: 'Rejected',
    cancelled: 'Cancelled',
    PENDING: 'Pending',
    STARTED: 'Started',
    SUCCESS: 'Success',
    FAILURE: 'Failure',
    RETRY: 'Retry',
    REVOKED: 'Revoked',
    SCHEDULED: 'Scheduled',
    RESERVED: 'Reserved',
  };
  const s = task.workflow_status || task.status;
  return labelMap[s] || s;
}

/** 格式化时间戳 */
function formatTimestamp(timestamp?: string): string {
  if (!timestamp) return '-';
  try {
    return format(new Date(timestamp), 'MM-dd HH:mm:ss');
  } catch {
    return timestamp;
  }
}

/** 格式化执行耗时 */
function formatDuration(duration?: number): string {
  if (!duration) return '-';
  if (duration < 60) return `${duration.toFixed(1)}s`;
  const minutes = Math.floor(duration / 60);
  const seconds = Math.floor(duration % 60);
  return `${minutes}m ${seconds}s`;
}

/** 格式化卡住时长 */
function formatStaleDuration(duration?: number): string {
  if (!duration) return '-';
  if (duration < 60) return `${Math.floor(duration)}s`;
  if (duration < 3600) return `${Math.floor(duration / 60)}m`;
  return `${(duration / 3600).toFixed(1)}h`;
}

/** 截断任务 ID 显示 */
function truncateId(id: string): string {
  if (id.length <= 16) return id;
  return `${id.slice(0, 8)}...${id.slice(-4)}`;
}

/** 格式化任务类型显示 */
function formatTaskType(taskType?: string): string {
  const map: Record<string, string> = {
    creation: 'Create',
    retry_tutorial: 'Tutorial',
    retry_resources: 'Resources',
    retry_quiz: 'Quiz',
    retry_batch: 'Batch',
  };
  return taskType ? (map[taskType] || taskType) : '-';
}

// ============================================================
// 统计卡片组件
// ============================================================

interface StatCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  subtitle?: string;
  isActive?: boolean;
  onClick?: () => void;
}

function StatCard({ title, value, icon, variant, subtitle, isActive = false, onClick }: StatCardProps) {
  const colorClasses = {
    success: 'bg-green-50 text-green-700 border-green-200',
    warning: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    danger: 'bg-red-50 text-red-700 border-red-200',
    info: 'bg-blue-50 text-blue-700 border-blue-200',
    neutral: 'bg-muted/60 text-foreground border-border',
  };

  const isClickable = typeof onClick === 'function';
  const cardClassName = cn(
    'rounded-lg border p-4 text-left transition-all',
    colorClasses[variant],
    isClickable && 'cursor-pointer hover:-translate-y-0.5 hover:shadow-sm',
    isActive && 'ring-2 ring-primary ring-offset-2 shadow-sm'
  );

  if (isClickable) {
    return (
      <button
        type="button"
        onClick={onClick}
        aria-pressed={isActive}
        className={cardClassName}
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium opacity-80">{title}</p>
            <p className="text-2xl font-bold mt-1">{value}</p>
            {subtitle && <p className="text-xs opacity-60 mt-0.5">{subtitle}</p>}
          </div>
          <div className="opacity-70">{icon}</div>
        </div>
      </button>
    );
  }

  return (
    <div className={cardClassName}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium opacity-80">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
          {subtitle && <p className="text-xs opacity-60 mt-0.5">{subtitle}</p>}
        </div>
        <div className="opacity-70">{icon}</div>
      </div>
    </div>
  );
}

// ============================================================
// 任务详情弹窗组件
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
            <Badge variant="outline" className="ml-auto text-xs font-normal">
              {task.source}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            Detailed information about task <span className="font-mono text-xs">{task.task_id}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* 业务核心信息 */}
          <div>
            <h4 className="text-sm font-semibold mb-3 flex items-center gap-1.5">
              <Database size={14} />
              Business Info
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-medium text-muted-foreground">Task ID</p>
                <p className="text-xs font-mono mt-1 break-all">{task.task_id}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground">Task Type</p>
                <p className="text-sm mt-1">{task.task_name}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground">Workflow Status</p>
                <div className="mt-1">
                  <Badge variant={getStatusBadgeVariant(task)} className="flex items-center gap-1 w-fit text-xs">
                    {getStatusIcon(task)}
                    {getStatusLabel(task)}
                  </Badge>
                </div>
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground">Current Step</p>
                <p className="text-sm mt-1 font-mono">
                  {task.live_step ? (
                    <span className="text-blue-600">{task.live_step} <span className="text-xs opacity-60">(live)</span></span>
                  ) : (task.current_step || '-')}
                </p>
              </div>
              {task.roadmap_id && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground">Roadmap ID</p>
                  <p className="text-xs font-mono mt-1 break-all">{task.roadmap_id}</p>
                </div>
              )}
              {task.content_generation_status && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground">Content Generation</p>
                  <p className="text-sm mt-1">{task.content_generation_status}</p>
                </div>
              )}
            </div>
          </div>

          {/* 时间信息 */}
          <div className="border-t pt-4">
            <h4 className="text-sm font-semibold mb-3">Time Information</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-medium text-muted-foreground">Started At</p>
                <p className="text-sm mt-1">{formatTimestamp(task.started_at)}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground">Completed At</p>
                <p className="text-sm mt-1">{formatTimestamp(task.completed_at)}</p>
              </div>
              {task.duration !== undefined && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground">Duration</p>
                  <p className="text-sm mt-1">{formatDuration(task.duration)}</p>
                </div>
              )}
            </div>
          </div>

          {/* 错误信息（业务） */}
          {task.error_message && (
            <div className="border-t pt-4">
              <h4 className="text-sm font-semibold mb-3 text-red-600">Business Error</h4>
              <pre className="text-xs bg-red-50 p-3 rounded-md overflow-x-auto border border-red-200 text-red-800 whitespace-pre-wrap">
                {task.error_message}
              </pre>
            </div>
          )}

          {/* Celery runtime 信息 */}
          {(task.celery_task_id || task.worker || task.queue) && (
            <div className="border-t pt-4">
              <h4 className="text-sm font-semibold mb-3 flex items-center gap-1.5">
                <Cpu size={14} />
                Celery Runtime
              </h4>
              <div className="grid grid-cols-2 gap-4">
                {task.celery_task_id && (
                  <div className="col-span-2">
                    <p className="text-xs font-medium text-muted-foreground">Celery Task ID</p>
                    <p className="text-xs font-mono mt-1 break-all">{task.celery_task_id}</p>
                  </div>
                )}
                {task.worker && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground">Worker</p>
                    <p className="text-xs font-mono mt-1">{task.worker}</p>
                  </div>
                )}
                {task.queue && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground">Queue</p>
                    <p className="text-sm mt-1">{task.queue}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Celery 错误（runtime） */}
          {task.error && !task.error_message && (
            <div className="border-t pt-4">
              <h4 className="text-sm font-semibold mb-3 text-red-600">Celery Error</h4>
              <pre className="text-xs bg-red-50 p-3 rounded-md overflow-x-auto border border-red-200 text-red-800">
                {task.error}
              </pre>
            </div>
          )}

          {/* 任务结果 */}
          {task.result && (
            <div className="border-t pt-4">
              <h4 className="text-sm font-semibold mb-3">Result</h4>
              <pre className="text-xs bg-green-50 p-3 rounded-md overflow-x-auto border border-green-200">
                {JSON.stringify(task.result, null, 2)}
              </pre>
            </div>
          )}

          {/* 任务参数 */}
          {(task.args || task.kwargs) && (
            <div className="border-t pt-4">
              <h4 className="text-sm font-semibold mb-3">Arguments</h4>
              {task.args && task.args.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Args</p>
                  <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto">
                    {JSON.stringify(task.args, null, 2)}
                  </pre>
                </div>
              )}
              {task.kwargs && Object.keys(task.kwargs).length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Kwargs</p>
                  <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto">
                    {JSON.stringify(task.kwargs, null, 2)}
                  </pre>
                </div>
              )}
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
  const [mounted, setMounted] = useState(false);
  const [isOverviewLoading, setIsOverviewLoading] = useState(true);
  const [isTasksLoading, setIsTasksLoading] = useState(true);
  const [isApplyingFilters, setIsApplyingFilters] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isBulkCleaning, setIsBulkCleaning] = useState(false);
  const [isBulkForceCleaning, setIsBulkForceCleaning] = useState(false);
  const [cleaningTaskId, setCleaningTaskId] = useState<string | null>(null);
  const [forceCleaningTaskId, setForceCleaningTaskId] = useState<string | null>(null);
  const [overview, setOverview] = useState<CeleryOverview | null>(null);
  const [tasks, setTasks] = useState<CeleryTask[]>([]);
  const [totalTasks, setTotalTasks] = useState(0);
  const [selectedTask, setSelectedTask] = useState<CeleryTask | null>(null);
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false);

  // 筛选
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [taskTypeFilter, setTaskTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // 自动刷新（只刷新 overview，列表不做高频刷新避免抖动）
  const [autoRefresh, setAutoRefresh] = useState(false);

  /** 加载总览数据 */
  const loadOverview = async (showLoading = false) => {
    if (showLoading) setIsOverviewLoading(true);
    try {
      const data = await getCeleryOverview();
      setOverview(data);
    } catch (error) {
      console.error('Failed to load overview:', error);
    } finally {
      if (showLoading) setIsOverviewLoading(false);
    }
  };

  /** 加载任务列表 */
  const loadTasks = async (options?: { showLoading?: boolean; isFilterChange?: boolean }) => {
    const showLoading = options?.showLoading ?? false;
    const isFilterChange = options?.isFilterChange ?? false;

    if (showLoading) setIsTasksLoading(true);
    if (isFilterChange) setIsApplyingFilters(true);

    try {
      const params: CeleryTasksParams = {
        status: statusFilter === 'all' ? undefined : statusFilter,
        task_type: taskTypeFilter === 'all' ? undefined : taskTypeFilter,
        limit: 50,
        offset: 0,
      };

      const data = await getCeleryTasks(params);
      setTasks(data.tasks);
      setTotalTasks(data.total);
    } catch (error) {
      console.error('Failed to load tasks:', error);
      toast.error('Failed to load tasks');
    } finally {
      if (showLoading) setIsTasksLoading(false);
      if (isFilterChange) setIsApplyingFilters(false);
    }
  };

  /** 初始加载（总览 + 列表并发） */
  const loadData = async () => {
    await Promise.all([
      loadOverview(true),
      loadTasks({ showLoading: true }),
    ]);
  };

  /** 手动刷新 */
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([loadOverview(), loadTasks({ showLoading: true })]);
      toast.success('Data refreshed');
    } finally {
      setIsRefreshing(false);
    }
  };

  /** 批量清理卡住任务 */
  const handleCleanupStaleTasks = async () => {
    setIsBulkCleaning(true);
    try {
      const result: CeleryTaskCleanupBatchResponse = await cleanupStaleTasks();
      if (result.cleaned > 0) {
        toast.success(`Cleaned ${result.cleaned} stale tasks`);
      } else {
        toast.message(result.message);
      }
      await Promise.all([loadOverview(), loadTasks({ showLoading: true })]);
    } catch (error) {
      console.error('Failed to cleanup stale tasks:', error);
      toast.error('Failed to cleanup stale tasks');
    } finally {
      setIsBulkCleaning(false);
    }
  };

  /** 批量强制清理卡住任务 */
  const handleForceCleanupStaleTasks = async () => {
    setIsBulkForceCleaning(true);
    try {
      const result: CeleryTaskCleanupBatchResponse = await forceCleanupStaleTasks();
      if (result.cleaned > 0) {
        toast.success(`Force cleaned ${result.cleaned} stale tasks`);
      } else {
        toast.message(result.message);
      }
      await Promise.all([loadOverview(), loadTasks({ showLoading: true })]);
    } catch (error) {
      console.error('Failed to force cleanup stale tasks:', error);
      toast.error('Failed to force cleanup stale tasks');
    } finally {
      setIsBulkForceCleaning(false);
    }
  };

  /** 清理单个卡住任务 */
  const handleCleanupStaleTask = async (taskId: string) => {
    setCleaningTaskId(taskId);
    try {
      const result = await cleanupStaleTask(taskId);
      toast.success(`Task cleaned: ${formatStaleDuration(result.stale_for_seconds)}`);

      if (selectedTask?.task_id === taskId) {
        setIsDetailDialogOpen(false);
        setSelectedTask(null);
      }

      await Promise.all([loadOverview(), loadTasks({ showLoading: true })]);
    } catch (error) {
      console.error('Failed to cleanup stale task:', error);
      toast.error('Failed to cleanup stale task');
    } finally {
      setCleaningTaskId(null);
    }
  };

  /** 强制清理单个卡住任务 */
  const handleForceCleanupStaleTask = async (taskId: string) => {
    setForceCleaningTaskId(taskId);
    try {
      const result = await forceCleanupStaleTask(taskId);
      toast.success(`Task force cleaned: ${formatStaleDuration(result.stale_for_seconds)}`);

      if (selectedTask?.task_id === taskId) {
        setIsDetailDialogOpen(false);
        setSelectedTask(null);
      }

      await Promise.all([loadOverview(), loadTasks({ showLoading: true })]);
    } catch (error) {
      console.error('Failed to force cleanup stale task:', error);
      toast.error('Failed to force cleanup stale task');
    } finally {
      setForceCleaningTaskId(null);
    }
  };

  /** 查看任务详情 */
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

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted) loadData();
  }, [mounted]);

  // 筛选变化时重新加载列表
  useEffect(() => {
    if (mounted) {
      void loadTasks({ showLoading: true, isFilterChange: true });
    }
  }, [statusFilter, taskTypeFilter]);

  // 自动刷新 overview（每 10 秒，比原来更保守）
  useEffect(() => {
    if (!mounted || !autoRefresh) return;
    const interval = setInterval(loadOverview, 10000);
    return () => clearInterval(interval);
  }, [mounted, autoRefresh]);

  // 客户端搜索过滤
  const filteredTasks = tasks.filter((task) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      task.task_id.toLowerCase().includes(q) ||
      task.task_name.toLowerCase().includes(q) ||
      (task.roadmap_id || '').toLowerCase().includes(q) ||
      (task.celery_task_id || '').toLowerCase().includes(q)
    );
  });
  const currentPageSafeCleanableTasks = tasks.filter((task) => task.can_safe_cleanup).length;
  const currentPageForceCleanableTasks = tasks.filter((task) => task.can_force_cleanup).length;
  const isInitialLoading = overview === null && isOverviewLoading;

  const handleStatusCardClick = (
    nextFilter: Extract<StatusFilter, 'active' | 'processing' | 'completed' | 'failed'>
  ) => {
    const shouldReset = statusFilter === nextFilter;
    setStatusFilter(shouldReset ? 'all' : nextFilter);
  };

  if (!mounted) {
    return (
      <div className="max-w-7xl mx-auto py-8 px-4">
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
            <h1 className="text-3xl font-serif font-bold text-foreground">Task Monitor</h1>
            <p className="text-sm text-muted-foreground">Admin task management & Celery monitoring</p>
          </div>
        </div>
      </div>

      {/* Worker 监控降级提示 */}
      {overview && !overview.inspect_available && (
        <Alert className="mb-6 border-yellow-200 bg-yellow-50">
          <WifiOff className="h-4 w-4 text-yellow-600" />
          <AlertDescription className="text-yellow-700">
            {overview.heartbeat_workers_online > 0 ? (
              <>
                Celery inspect is currently unavailable, but {overview.heartbeat_workers_online} worker
                {overview.heartbeat_workers_online > 1 ? 's are' : ' is'} still online by heartbeat.
                Runtime queue details are degraded, while database task history remains available.
              </>
            ) : (
              <>
                Celery runtime monitoring is currently unavailable. Showing database task history only
                until heartbeat or inspect becomes reachable again.
              </>
            )}
          </AlertDescription>
        </Alert>
      )}

      {overview && overview.heartbeat_workers_online > 0 && (
        <Alert className="mb-6 border-blue-200 bg-blue-50">
          <Activity className="h-4 w-4 text-blue-700" />
          <AlertDescription className="text-blue-900">
            Worker heartbeat online: {overview.heartbeat_workers.join(', ')}.
          </AlertDescription>
        </Alert>
      )}

      {overview && overview.stale_processing_count > 0 && (
        <Alert className="mb-6 border-amber-300 bg-amber-50">
          <AlertCircle className="h-4 w-4 text-amber-700" />
          <AlertDescription className="text-amber-900">
            <span className="font-semibold">
              Detected {overview.stale_processing_count} stale processing task
              {overview.stale_processing_count > 1 ? 's' : ''}.
            </span>{' '}
            <span>
              {overview.cleanable_stale_processing_count} can be cleaned safely right now
              {currentPageSafeCleanableTasks > 0 ? `, including ${currentPageSafeCleanableTasks} on this page` : ''}.
            </span>{' '}
            {!overview.inspect_available && (
              <span>
                Celery inspect is unavailable, so safe cleanup may be skipped. You can still use force cleanup
                for confirmed stale test tasks.
              </span>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* 统计卡片区 */}
      {isInitialLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      ) : overview ? (
        <>
          {/* DB 业务统计（始终有值） */}
          <div className="mb-2">
            <p className="text-xs font-medium text-muted-foreground flex items-center gap-1.5 mb-3">
              <Database size={12} />
              Database Stats
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard
                title="Active Tasks"
                value={overview.db_total_active}
                icon={<Loader2 size={24} className={overview.db_total_active > 0 ? 'animate-spin' : ''} />}
                variant="info"
                subtitle="pending + processing"
                isActive={statusFilter === 'active'}
                onClick={() => handleStatusCardClick('active')}
              />
              <StatCard
                title="Processing"
                value={overview.db_processing_count}
                icon={<Activity size={24} />}
                variant="info"
                isActive={statusFilter === 'processing'}
                onClick={() => handleStatusCardClick('processing')}
              />
              <StatCard
                title="Completed (24h)"
                value={overview.db_completed_24h}
                icon={<CheckCircle2 size={24} />}
                variant="success"
                isActive={statusFilter === 'completed'}
                onClick={() => handleStatusCardClick('completed')}
              />
              <StatCard
                title="Failed (24h)"
                value={overview.db_failed_24h}
                icon={<XCircle size={24} />}
                variant={overview.db_failed_24h > 0 ? 'danger' : 'neutral'}
                isActive={statusFilter === 'failed'}
                onClick={() => handleStatusCardClick('failed')}
              />
            </div>
          </div>

          {/* Celery runtime 统计（inspect 可用时显示） */}
          {overview.inspect_available && (
            <div className="mb-8 mt-4">
              <p className="text-xs font-medium text-muted-foreground flex items-center gap-1.5 mb-3">
                <Cpu size={12} />
                Runtime Stats
                <span className="text-green-600 font-medium">• Live</span>
              </p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  title="Active (Queue)"
                  value={overview.runtime_active_count}
                  icon={<Loader2 size={24} className={overview.runtime_active_count > 0 ? 'animate-spin' : ''} />}
                  variant="info"
                />
                <StatCard
                  title="Pending (Queue)"
                  value={overview.runtime_pending_count}
                  icon={<Clock size={24} />}
                  variant="warning"
                />
                <StatCard
                  title="Workers Online"
                  value={overview.workers_online}
                  icon={<Activity size={24} />}
                  variant={overview.workers_online > 0 ? 'success' : 'danger'}
                />
                <StatCard
                  title="Scheduled"
                  value={overview.scheduled_count}
                  icon={<Clock size={24} />}
                  variant="neutral"
                />
              </div>
            </div>
          )}

          {/* 队列长度（有数据时显示） */}
          {overview.inspect_available && Object.keys(overview.queue_lengths).length > 0 && (
            <div className="mb-6 p-4 bg-muted/60 rounded-lg">
              <h3 className="text-xs font-semibold text-muted-foreground mb-3">Queue Lengths</h3>
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
        </>
      ) : null}

      {/* 筛选和搜索 */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="flex flex-wrap gap-3 flex-1">
          {/* 业务状态筛选 */}
          <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="processing">Processing</SelectItem>
              <SelectItem value="human_review_pending">Human Review</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>

          {/* 任务类型筛选 */}
          <Select value={taskTypeFilter} onValueChange={setTaskTypeFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="creation">Create Roadmap</SelectItem>
              <SelectItem value="retry_tutorial">Retry Tutorial</SelectItem>
              <SelectItem value="retry_resources">Retry Resources</SelectItem>
              <SelectItem value="retry_quiz">Retry Quiz</SelectItem>
              <SelectItem value="retry_batch">Retry Batch</SelectItem>
            </SelectContent>
          </Select>

          {/* 搜索框 */}
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
            <Input
              placeholder="Search task ID, roadmap ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCleanupStaleTasks}
            disabled={isBulkCleaning || isTasksLoading}
            className="border-amber-300 text-amber-700 hover:bg-amber-50 hover:text-amber-800"
          >
            <AlertCircle size={16} className={isBulkCleaning ? 'animate-pulse mr-1' : 'mr-1'} />
            Clean Stale
            {overview && overview.stale_processing_count > 0 && (
              <span className="ml-1 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800">
                {overview.cleanable_stale_processing_count}/{overview.stale_processing_count}
              </span>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleForceCleanupStaleTasks}
            disabled={isBulkForceCleaning || isTasksLoading || !overview || overview.force_cleanable_stale_processing_count === 0}
            className="border-red-300 text-red-700 hover:bg-red-50 hover:text-red-800"
          >
            <AlertCircle size={16} className={isBulkForceCleaning ? 'animate-pulse mr-1' : 'mr-1'} />
            Force Cleanup
            {overview && overview.force_cleanable_stale_processing_count > 0 && (
              <span className="ml-1 rounded-full bg-red-100 px-1.5 py-0.5 text-[10px] font-semibold text-red-800">
                {overview.force_cleanable_stale_processing_count}
              </span>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw size={16} className={isRefreshing ? 'animate-spin mr-1' : 'mr-1'} />
            Refresh
          </Button>
          <Button
            variant={autoRefresh ? 'default' : 'outline'}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? 'Auto ON' : 'Auto OFF'}
          </Button>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span>Current filters:</span>
        <Badge variant="secondary">{STATUS_FILTER_LABELS[statusFilter]}</Badge>
        <Badge variant="outline">Last 1 day</Badge>
        {taskTypeFilter !== 'all' && <Badge variant="outline">Type: {formatTaskType(taskTypeFilter)}</Badge>}
        {searchQuery && <Badge variant="outline">Search: {searchQuery}</Badge>}
        {isTasksLoading && (
          <span className="inline-flex items-center gap-1 text-blue-600">
            <Loader2 size={12} className="animate-spin" />
            {isApplyingFilters ? 'Applying filters...' : 'Loading tasks...'}
          </span>
        )}
      </div>

      {/* 任务列表 */}
      {isInitialLoading ? (
        <TableSkeleton rows={5} columns={8} />
      ) : (
        <>
          <div className="relative rounded-lg border bg-card">
            {isTasksLoading && (
              <div className="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-background/75 backdrop-blur-[1px]">
                <div className="inline-flex items-center gap-2 rounded-full border bg-background px-4 py-2 text-sm shadow-sm">
                  <Loader2 size={16} className="animate-spin text-blue-600" />
                  <span>{isApplyingFilters ? 'Applying filters...' : 'Loading tasks...'}</span>
                </div>
              </div>
            )}
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Task ID</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Step</TableHead>
                  <TableHead>Roadmap ID</TableHead>
                  <TableHead>Created At</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTasks.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                      <Database className="mx-auto mb-3 opacity-40" size={32} />
                      <p className="text-sm">No tasks found for the current filters.</p>
                      <p className="text-xs mt-1 opacity-60">Try changing the status, date range, or search keyword.</p>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredTasks.map((task) => (
                    <TableRow key={task.task_id}>
                      <TableCell className="font-mono text-xs">
                        {truncateId(task.task_id)}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {formatTaskType(task.task_type)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={getStatusBadgeVariant(task)}
                          className="flex items-center gap-1 w-fit text-xs"
                        >
                          {getStatusIcon(task)}
                          {getStatusLabel(task)}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground max-w-[120px] truncate">
                        {task.live_step ? (
                          <span className="text-blue-600 font-medium">{task.live_step}</span>
                        ) : (task.current_step || '-')}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {task.roadmap_id ? truncateId(task.roadmap_id) : '-'}
                      </TableCell>
                      <TableCell className="text-xs">{formatTimestamp(task.started_at)}</TableCell>
                      <TableCell className="text-xs">{formatDuration(task.duration)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          {task.can_safe_cleanup && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs border-amber-300 text-amber-700 hover:bg-amber-50 hover:text-amber-800"
                              onClick={() => handleCleanupStaleTask(task.task_id)}
                              disabled={cleaningTaskId === task.task_id}
                            >
                              {cleaningTaskId === task.task_id ? 'Cleaning...' : 'Cleanup'}
                            </Button>
                          )}
                          {task.can_force_cleanup && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs border-red-300 text-red-700 hover:bg-red-50 hover:text-red-800"
                              onClick={() => handleForceCleanupStaleTask(task.task_id)}
                              disabled={forceCleaningTaskId === task.task_id}
                            >
                              {forceCleaningTaskId === task.task_id ? 'Forcing...' : 'Force'}
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => handleViewDetail(task.task_id)}
                          >
                            Detail
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* 分页信息 */}
          <div className="mt-4 text-xs text-muted-foreground text-center">
            Showing {filteredTasks.length} of {totalTasks} tasks
            {searchQuery && ` (filtered from ${tasks.length})`}
          </div>
        </>
      )}

      {/* 任务详情弹窗 */}
      <TaskDetailDialog
        task={selectedTask}
        open={isDetailDialogOpen}
        onOpenChange={setIsDetailDialogOpen}
      />
    </div>
  );
}

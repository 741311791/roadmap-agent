'use client';

import { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Info,
  Clock,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { LogCardRouter } from './log-cards';

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

interface ExecutionLogTimelineProps {
  logs: ExecutionLog[];
  selectedPhaseFilter: string | null;
  taskStatus?: string;
  roadmapId?: string | null;
  taskTitle?: string;
  onShowAllLogs?: () => void;
}

/**
 * 阶段映射配置
 */
const PHASE_MAPPING: Record<string, { label: string; color: string; steps: string[] }> = {
  intent_analysis: {
    label: 'Intent Analysis',
    color: 'blue',
    steps: ['init', 'queued', 'starting', 'intent_analysis'],
  },
  curriculum_design: {
    label: 'Curriculum Design',
    color: 'purple',
    steps: ['curriculum_design', 'framework_generation'],
  },
  structure_validation: {
    label: 'Structure Validation',
    color: 'indigo',
    steps: ['structure_validation'],
  },
  human_review: {
    label: 'Human Review',
    color: 'amber',
    steps: ['human_review', 'roadmap_edit'],
  },
  content_generation: {
    label: 'Content Generation',
    color: 'green',
    steps: ['content_generation', 'tutorial_generation', 'resource_recommendation', 'quiz_generation'],
  },
  finalizing: {
    label: 'Finalizing',
    color: 'teal',
    steps: ['finalizing', 'completed'],
  },
};

/**
 * 执行日志时间轴
 * 
 * 设计特色:
 * - 按阶段分组展示
 * - 支持阶段筛选
 * - 时间轴视觉设计
 * - 日志级别色彩区分
 * - 可折叠的阶段卡片
 */
export function ExecutionLogTimeline({
  logs,
  selectedPhaseFilter,
  taskStatus,
  roadmapId,
  taskTitle,
  onShowAllLogs,
}: ExecutionLogTimelineProps) {
  /**
   * 将步骤映射到阶段
   */
  const mapStepToPhase = (step: string | null): string => {
    if (!step) return 'unknown';

    for (const [phase, config] of Object.entries(PHASE_MAPPING)) {
      if (config.steps.includes(step)) {
        return phase;
      }
    }

    return 'unknown';
  };

  /**
   * 按阶段分组日志
   */
  const groupedLogs = useMemo(() => {
    const groups: Record<string, ExecutionLog[]> = {};

    logs.forEach((log) => {
      const phase = mapStepToPhase(log.step);
      if (!groups[phase]) {
        groups[phase] = [];
      }
      groups[phase].push(log);
    });

    return groups;
  }, [logs]);

  /**
   * 获取所有阶段（按顺序）
   */
  const phases = useMemo(() => {
    const allPhases = Object.keys(PHASE_MAPPING);
    return allPhases.filter((phase) => groupedLogs[phase]?.length > 0);
  }, [groupedLogs]);

  /**
   * 过滤后的日志
   */
  const filteredLogs = useMemo(() => {
    if (!selectedPhaseFilter) {
      return logs;
    }
    return logs.filter((log) => mapStepToPhase(log.step) === selectedPhaseFilter);
  }, [logs, selectedPhaseFilter]);

  /**
   * 获取当前阶段的配置
   */
  const getCurrentPhaseConfig = () => {
    if (!selectedPhaseFilter) return null;
    return PHASE_MAPPING[selectedPhaseFilter];
  };

  /**
   * 获取日志级别图标
   */
  const getLogLevelIcon = (level: string) => {
    switch (level) {
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-600" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-amber-600" />;
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-sage-600" />;
      default:
        return <Info className="w-4 h-4 text-sage-600" />;
    }
  };

  /**
   * 格式化时间戳
   */
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  /**
   * 格式化持续时间
   */
  const formatDuration = (ms: number | null) => {
    if (!ms) return null;
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  /**
   * 获取阶段的统计信息
   */
  const getPhaseStats = (phase: string) => {
    const phaseLogs = groupedLogs[phase] || [];
    const totalDuration = phaseLogs.reduce((sum, log) => sum + (log.duration_ms || 0), 0);
    const errorCount = phaseLogs.filter((log) => log.level === 'error').length;
    const warningCount = phaseLogs.filter((log) => log.level === 'warning').length;

    return {
      count: phaseLogs.length,
      duration: formatDuration(totalDuration),
      errors: errorCount,
      warnings: warningCount,
    };
  };

  if (logs.length === 0) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="text-center space-y-2">
            <Clock className="w-12 h-12 text-muted-foreground mx-auto" />
            <p className="text-sm text-muted-foreground">
              No execution logs available yet.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const currentPhaseConfig = getCurrentPhaseConfig();

  return (
    <div className="space-y-4">
      {/* 日志标题 - 显示当前选中的阶段 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-serif font-semibold">
            {currentPhaseConfig ? currentPhaseConfig.label : 'All Execution Logs'}
          </h2>
          <Badge variant="outline" className="text-xs">
            {filteredLogs.length} {filteredLogs.length === 1 ? 'log' : 'logs'}
          </Badge>
        </div>
        {currentPhaseConfig ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={onShowAllLogs}
            className="text-sm text-sage-600 hover:text-sage-700 hover:underline"
          >
            ← Show All Logs
          </Button>
        ) : (
          <p className="text-sm text-muted-foreground">
            Click on a stage above to view its logs
          </p>
        )}
      </div>

      {/* 日志列表 */}
      {!selectedPhaseFilter ? (
        // 显示所有阶段（按阶段分组）
        <div className="space-y-4">
          {phases.map((phase) => {
            const config = PHASE_MAPPING[phase];
            const stats = getPhaseStats(phase);
            const phaseLogs = groupedLogs[phase] || [];

            return (
              <PhaseLogCard
                key={phase}
                phase={phase}
                label={config.label}
                color={config.color}
                logs={phaseLogs}
                stats={stats}
                getLogLevelIcon={getLogLevelIcon}
                formatTimestamp={formatTimestamp}
                formatDuration={formatDuration}
              />
            );
          })}
        </div>
      ) : (
        // 显示单个阶段的日志
        <Card className="border-sage-200">
          <CardContent className="pt-6">
            <ScrollArea className="h-[600px] pr-4">
              <div className="space-y-3">
                {filteredLogs.length > 0 ? (
                  filteredLogs.map((log, index) => (
                    <LogEntry
                      key={log.id || index}
                      log={log}
                      getLogLevelIcon={getLogLevelIcon}
                      formatTimestamp={formatTimestamp}
                      formatDuration={formatDuration}
                    />
                  ))
                ) : (
                  <div className="text-center py-12">
                    <Clock className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
                    <p className="text-sm text-muted-foreground">
                      No logs available for this stage yet.
                    </p>
                  </div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/**
 * 阶段日志卡片（可折叠）
 */
function PhaseLogCard({
  phase,
  label,
  color,
  logs,
  stats,
  getLogLevelIcon,
  formatTimestamp,
  formatDuration,
}: {
  phase: string;
  label: string;
  color: string;
  logs: ExecutionLog[];
  stats: any;
  getLogLevelIcon: (level: string) => JSX.Element;
  formatTimestamp: (timestamp: string) => string;
  formatDuration: (ms: number | null) => string | null;
}) {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <Card>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CardHeader className="pb-3">
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              className="w-full justify-between p-0 hover:bg-transparent"
            >
              <div className="flex items-center gap-3">
                {isOpen ? (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                )}
                <CardTitle className="text-base font-serif">{label}</CardTitle>
                <Badge variant="outline" className="ml-2">
                  {stats.count} logs
                </Badge>
              </div>

              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                {stats.duration && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {stats.duration}
                  </span>
                )}
                {stats.errors > 0 && (
                  <Badge variant="destructive" className="h-5 text-xs">
                    {stats.errors} errors
                  </Badge>
                )}
                {stats.warnings > 0 && (
                  <Badge variant="outline" className="h-5 text-xs border-amber-300 text-amber-700">
                    {stats.warnings} warnings
                  </Badge>
                )}
              </div>
            </Button>
          </CollapsibleTrigger>
        </CardHeader>

        <CollapsibleContent>
          <CardContent>
            <div className="space-y-3">
              {logs.map((log, index) => (
                <LogEntry
                  key={log.id || index}
                  log={log}
                  getLogLevelIcon={getLogLevelIcon}
                  formatTimestamp={formatTimestamp}
                  formatDuration={formatDuration}
                />
              ))}
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}

/**
 * 单条日志条目
 */
function LogEntry({
  log,
  getLogLevelIcon,
  formatTimestamp,
  formatDuration,
}: {
  log: ExecutionLog;
  getLogLevelIcon: (level: string) => JSX.Element;
  formatTimestamp: (timestamp: string) => string;
  formatDuration: (ms: number | null) => string | null;
}) {
  // 尝试使用专用卡片渲染
  const specialCard = LogCardRouter({ log });

  // 如果有专用卡片，直接返回
  if (specialCard) {
    return <div className="space-y-2">{specialCard}</div>;
  }

  // 否则使用默认的日志条目样式
  return (
    <div
      className={cn(
        'flex items-start gap-3 p-3 rounded-lg border transition-colors',
        log.level === 'error' && 'bg-red-50 border-red-200',
        log.level === 'warning' && 'bg-amber-50 border-amber-200',
        log.level === 'success' && 'bg-sage-50 border-sage-200',
        log.level === 'info' && 'bg-muted border-border'
      )}
    >
      {/* 图标 */}
      <div className="shrink-0 mt-0.5">{getLogLevelIcon(log.level)}</div>

      {/* 内容 */}
      <div className="flex-1 min-w-0 space-y-1">
        {/* 时间戳和分类 */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-mono">{formatTimestamp(log.created_at)}</span>
          {log.category && (
            <>
              <span>·</span>
              <Badge variant="outline" className="h-4 text-[10px] px-1.5">
                {log.category}
              </Badge>
            </>
          )}
          {log.agent_name && (
            <>
              <span>·</span>
              <Badge variant="outline" className="h-4 text-[10px] px-1.5">
                {log.agent_name}
              </Badge>
            </>
          )}
          {log.duration_ms && formatDuration(log.duration_ms) && (
            <>
              <span>·</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatDuration(log.duration_ms)}
              </span>
            </>
          )}
        </div>

        {/* 消息 */}
        <p className="text-sm text-foreground break-words">{log.message}</p>

        {/* 详细信息（如果有） */}
        {log.details && Object.keys(log.details).length > 0 && (
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer hover:text-foreground">
              View details
            </summary>
            <pre className="mt-2 p-2 bg-background rounded border overflow-x-auto">
              {JSON.stringify(log.details, null, 2)}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}


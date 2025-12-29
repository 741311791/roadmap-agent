'use client';

/**
 * ExecutionLogTimeline - 执行日志时间轴组件（重新设计版）
 * 
 * 数据来源：roadmap.public.execution_logs 表
 * 
 * 功能:
 * - 从 /trace/{task_id}/logs API 获取日志
 * - 按 Step 分组展示
 * - Level 级别过滤器（info, success, warning, error）
 * - 每组固定高度，防止某些阶段日志过多
 * - 使用 Sage 主题配色
 */

import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  AlertCircle,
  CheckCircle2,
  Info,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Filter,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

/**
 * 执行日志类型
 */
interface ExecutionLog {
  id: string;
  task_id: string;
  level: 'debug' | 'info' | 'success' | 'warning' | 'error';
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
  className?: string;
}

/**
 * Step 配置映射
 */
const STEP_CONFIG: Record<string, { label: string; color: string; bgColor: string }> = {
  // 初始化阶段
  init: { label: 'Initialize', color: 'text-gray-700', bgColor: 'bg-gray-50' },
  queued: { label: 'Queued', color: 'text-gray-700', bgColor: 'bg-gray-50' },
  starting: { label: 'Starting', color: 'text-gray-700', bgColor: 'bg-gray-50' },
  
  // 主路节点
  intent_analysis: { label: 'Intent Analysis', color: 'text-sage-700', bgColor: 'bg-sage-50' },
  curriculum_design: { label: 'Curriculum Design', color: 'text-sage-700', bgColor: 'bg-sage-50' },
  framework_generation: { label: 'Framework Generation', color: 'text-sage-700', bgColor: 'bg-sage-50' },
  structure_validation: { label: 'Structure Validation', color: 'text-sage-700', bgColor: 'bg-sage-50' },
  human_review: { label: 'Human Review', color: 'text-amber-700', bgColor: 'bg-amber-50' },
  human_review_pending: { label: 'Awaiting Review', color: 'text-amber-700', bgColor: 'bg-amber-50' },
  
  // 验证分支节点（验证失败触发）
  validation_edit_plan_analysis: { label: 'Validation Edit Plan', color: 'text-amber-700', bgColor: 'bg-amber-50' },
  
  // 审核分支节点（用户拒绝触发）
  edit_plan_analysis: { label: 'Review Edit Plan', color: 'text-blue-700', bgColor: 'bg-blue-50' },
  
  // 共享的编辑节点（由 edit_source 区分来源）
  roadmap_edit: { label: 'Roadmap Edit', color: 'text-purple-700', bgColor: 'bg-purple-50' },
  
  // 内容生成阶段
  content_generation: { label: 'Content Generation', color: 'text-sage-700', bgColor: 'bg-sage-50' },
  tutorial_generation: { label: 'Tutorial Generation', color: 'text-sage-700', bgColor: 'bg-sage-50' },
  resource_recommendation: { label: 'Resource Recommendation', color: 'text-sage-700', bgColor: 'bg-sage-50' },
  quiz_generation: { label: 'Quiz Generation', color: 'text-sage-700', bgColor: 'bg-sage-50' },
  
  // 完成阶段
  finalizing: { label: 'Finalizing', color: 'text-sage-700', bgColor: 'bg-sage-50' },
  completed: { label: 'Completed', color: 'text-sage-700', bgColor: 'bg-sage-50' },
};

/**
 * 获取 Level 配置
 */
function getLevelConfig(level: string) {
  const configs: Record<string, { icon: React.ElementType; color: string; label: string }> = {
    error: { icon: AlertCircle, color: 'text-red-600', label: 'Error' },
    warning: { icon: AlertTriangle, color: 'text-amber-600', label: 'Warning' },
    success: { icon: CheckCircle2, color: 'text-sage-600', label: 'Success' },
    info: { icon: Info, color: 'text-gray-600', label: 'Info' },
    debug: { icon: Info, color: 'text-gray-500', label: 'Debug' },
  };
  return configs[level] || configs.info;
}

/**
 * 格式化时间戳
 */
function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

/**
 * 单个日志项组件
 */
interface LogItemProps {
  log: ExecutionLog;
}

function LogItem({ log }: LogItemProps) {
  const levelConfig = getLevelConfig(log.level);
  const Icon = levelConfig.icon;
  
  // 统一使用纯文本日志格式
  return (
    <div className="flex items-start gap-3 px-4 py-2.5 hover:bg-sage-50/30 transition-colors group">
      {/* 左侧：时间 */}
      <div className="w-20 flex-shrink-0 text-xs text-muted-foreground font-mono pt-0.5">
        {formatTime(log.created_at)}
      </div>
      
      {/* 中间：图标 + 消息 */}
      <div className="flex-1 min-w-0 flex items-start gap-2">
        <Icon className={cn('w-4 h-4 flex-shrink-0 mt-0.5', levelConfig.color)} />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-foreground break-words leading-relaxed">
            {log.message}
          </p>
          {/* Agent 名称 */}
          {log.agent_name && (
            <span className="text-xs text-muted-foreground mt-0.5 inline-block">
              by {log.agent_name}
            </span>
          )}
        </div>
      </div>
      
      {/* 右侧：Level badge */}
      <Badge 
        variant="outline" 
        className={cn(
          'text-xs shrink-0 opacity-0 group-hover:opacity-100 transition-opacity',
          levelConfig.color
        )}
      >
        {levelConfig.label}
      </Badge>
    </div>
  );
}

/**
 * Step 分组组件
 */
interface StepGroupProps {
  step: string;
  logs: ExecutionLog[];
  isExpanded: boolean;
  onToggle: () => void;
}

function StepGroup({ step, logs, isExpanded, onToggle }: StepGroupProps) {
  const config = STEP_CONFIG[step] || { 
    label: step || 'Unknown', 
    color: 'text-gray-700',
    bgColor: 'bg-gray-50'
  };
  
  // 统计不同级别的日志数量
  const stats = useMemo(() => {
    const counts = {
      error: 0,
      warning: 0,
      success: 0,
      info: 0,
    };
    logs.forEach(log => {
      if (log.level in counts) {
        counts[log.level as keyof typeof counts]++;
      }
    });
    return counts;
  }, [logs]);
  
  return (
    <div className="border-b border-border last:border-b-0">
      {/* Step 标题栏 */}
      <button
        onClick={onToggle}
        className={cn(
          'w-full flex items-center justify-between px-4 py-3',
          'hover:bg-sage-50/50 transition-colors',
          config.bgColor
        )}
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )}
          <span className={cn('font-medium text-sm', config.color)}>
            {config.label}
          </span>
          <Badge variant="secondary" className="text-xs">
            {logs.length}
          </Badge>
        </div>
        
        {/* 右侧统计 */}
        <div className="flex items-center gap-2">
          {stats.error > 0 && (
            <Badge variant="outline" className="text-xs text-red-600 border-red-200">
              {stats.error} errors
            </Badge>
          )}
          {stats.warning > 0 && (
            <Badge variant="outline" className="text-xs text-amber-600 border-amber-200">
              {stats.warning} warnings
            </Badge>
          )}
        </div>
      </button>
      
      {/* 日志列表 - 固定高度 */}
      {isExpanded && (
        <ScrollArea className="h-[240px] bg-card">
          <div className="divide-y divide-border/50">
            {logs.map((log) => (
              <LogItem key={log.id} log={log} />
            ))}
          </div>
        </ScrollArea>
      )}
    </div>
  );
}

/**
 * 主组件
 */
export function ExecutionLogTimeline({ logs, className }: ExecutionLogTimelineProps) {
  // Level 过滤状态
  const [selectedLevels, setSelectedLevels] = useState<Set<string>>(
    new Set(['info', 'success', 'warning', 'error'])
  );
  
  // Step 排序配置
  const stepOrder = useMemo(() => [
    'init', 'queued', 'starting',
    'intent_analysis',
    'curriculum_design', 'framework_generation',
    'structure_validation',
    'roadmap_edit',
    'human_review', 'human_review_pending',
    'content_generation', 'tutorial_generation', 'resource_recommendation', 'quiz_generation',
    'finalizing',
    'completed',
  ], []);
  
  // 按 Step 分组并过滤
  const groupedLogs = useMemo(() => {
    // 过滤 level
    const filteredLogs = logs.filter(log => selectedLevels.has(log.level));
    
    // 按 step 分组
    const groups: Record<string, ExecutionLog[]> = {};
    filteredLogs.forEach(log => {
      const step = log.step || 'unknown';
      if (!groups[step]) {
        groups[step] = [];
      }
      groups[step].push(log);
    });
    
    // 排序（按时间倒序 - 最新的在上面）
    Object.keys(groups).forEach(step => {
      groups[step].sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
    });
    
    return groups;
  }, [logs, selectedLevels]);
  
  // 获取所有有日志的步骤
  const orderedSteps = useMemo(() => {
    const steps = Object.keys(groupedLogs);
    return steps.sort((a, b) => {
      const indexA = stepOrder.indexOf(a);
      const indexB = stepOrder.indexOf(b);
      if (indexA === -1 && indexB === -1) return 0;
      if (indexA === -1) return 1;
      if (indexB === -1) return -1;
      return indexA - indexB;
    });
  }, [groupedLogs, stepOrder]);
  
  // 展开状态（默认展开所有步骤）
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(() => {
    // 初始化时获取所有步骤并展开
    const filteredLogs = logs.filter(log => selectedLevels.has(log.level));
    const steps = new Set<string>();
    filteredLogs.forEach(log => {
      steps.add(log.step || 'unknown');
    });
    return steps;
  });
  
  
  // 切换 Level 过滤
  const toggleLevel = (level: string) => {
    const newLevels = new Set(selectedLevels);
    if (newLevels.has(level)) {
      newLevels.delete(level);
    } else {
      newLevels.add(level);
    }
    setSelectedLevels(newLevels);
  };
  
  // 切换 Step 展开状态
  const toggleStep = (step: string) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(step)) {
      newExpanded.delete(step);
    } else {
      newExpanded.add(step);
    }
    setExpandedSteps(newExpanded);
  };
  
  // 展开所有/折叠所有
  const expandAll = () => {
    setExpandedSteps(new Set(orderedSteps));
  };
  
  const collapseAll = () => {
    setExpandedSteps(new Set());
  };
  
  // 空状态
  if (logs.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="py-12">
          <div className="text-center space-y-2">
            <Info className="w-12 h-12 text-muted-foreground mx-auto" />
            <p className="text-sm text-muted-foreground">
              No execution logs available.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }
  
  return (
    <Card className={className}>
      <CardHeader className="pb-3 border-b">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg font-serif font-semibold">
              Execution Logs
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              Grouped by workflow step · {logs.length} total logs
            </p>
          </div>
          
          {/* 操作按钮 */}
          <div className="flex items-center gap-2">
            {/* Level 过滤器 */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-8">
                  <Filter className="w-3.5 h-3.5 mr-2" />
                  Filter
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuCheckboxItem
                  checked={selectedLevels.has('error')}
                  onCheckedChange={() => toggleLevel('error')}
                >
                  <AlertCircle className="w-3.5 h-3.5 mr-2 text-red-600" />
                  Errors
                </DropdownMenuCheckboxItem>
                <DropdownMenuCheckboxItem
                  checked={selectedLevels.has('warning')}
                  onCheckedChange={() => toggleLevel('warning')}
                >
                  <AlertTriangle className="w-3.5 h-3.5 mr-2 text-amber-600" />
                  Warnings
                </DropdownMenuCheckboxItem>
                <DropdownMenuCheckboxItem
                  checked={selectedLevels.has('success')}
                  onCheckedChange={() => toggleLevel('success')}
                >
                  <CheckCircle2 className="w-3.5 h-3.5 mr-2 text-sage-600" />
                  Success
                </DropdownMenuCheckboxItem>
                <DropdownMenuCheckboxItem
                  checked={selectedLevels.has('info')}
                  onCheckedChange={() => toggleLevel('info')}
                >
                  <Info className="w-3.5 h-3.5 mr-2 text-gray-600" />
                  Info
                </DropdownMenuCheckboxItem>
              </DropdownMenuContent>
            </DropdownMenu>
            
            {/* 展开/折叠所有 */}
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 text-xs"
                onClick={expandAll}
              >
                Expand All
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 text-xs"
                onClick={collapseAll}
              >
                Collapse All
              </Button>
            </div>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="p-0">
        {/* Step 分组列表 */}
        <div className="divide-y divide-border">
          {orderedSteps.map((step) => (
            <StepGroup
              key={step}
              step={step}
              logs={groupedLogs[step]}
              isExpanded={expandedSteps.has(step)}
              onToggle={() => toggleStep(step)}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

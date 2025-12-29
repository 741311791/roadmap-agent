'use client';

/**
 * NodeDetailPanel - 节点详情侧边面板
 * 
 * 功能：
 * - 从右侧滑入的侧边面板
 * - 根据选中的节点ID筛选并展示对应的执行日志详情
 * - 只展示最新一条日志的 details 数据
 * - 步骤式布局，优雅的视觉设计
 */

import { useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { 
  X, 
  CheckCircle2, 
  AlertCircle, 
  Info, 
  Clock,
  FileText,
  AlertTriangle,
  Target,
  BookOpen,
  Shield,
  Eye,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ExecutionLog } from '@/types/content-generation';

interface NodeDetailPanelProps {
  /** 当前选中的节点ID */
  selectedNodeId: string | null;
  /** 全部执行日志 */
  executionLogs: ExecutionLog[];
  /** 关闭回调 */
  onClose: () => void;
}

/**
 * 节点ID到Step的映射配置
 */
const NODE_TO_STEPS: Record<string, { steps: string[]; label: string; editSource?: string; icon: React.ElementType; color: string }> = {
  analysis: {
    steps: ['intent_analysis'],
    label: 'Intent Analysis',
    icon: Target,
    color: 'text-sage-600',
  },
  design: {
    steps: ['curriculum_design', 'framework_generation'],
    label: 'Curriculum Design',
    icon: BookOpen,
    color: 'text-sage-600',
  },
  validate: {
    steps: ['structure_validation'],
    label: 'Structure Validation',
    icon: Shield,
    color: 'text-sage-600',
  },
  review: {
    steps: ['human_review', 'human_review_pending'],
    label: 'Human Review',
    icon: Eye,
    color: 'text-amber-600',
  },
  content: {
    steps: ['content_generation', 'tutorial_generation', 'resource_recommendation', 'quiz_generation'],
    label: 'Content Generation',
    icon: Sparkles,
    color: 'text-sage-600',
  },
  plan1: {
    steps: ['validation_edit_plan_analysis'],
    label: 'Validation Edit Plan',
    icon: FileText,
    color: 'text-amber-600',
    editSource: 'validation_failed',
  },
  edit1: {
    steps: ['roadmap_edit'],
    label: 'Roadmap Edit',
    icon: FileText,
    color: 'text-purple-600',
    editSource: 'validation_failed',
  },
  plan2: {
    steps: ['edit_plan_analysis'],
    label: 'Review Edit Plan',
    icon: FileText,
    color: 'text-blue-600',
    editSource: 'human_review',
  },
  edit2: {
    steps: ['roadmap_edit'],
    label: 'Roadmap Edit',
    icon: FileText,
    color: 'text-purple-600',
    editSource: 'human_review',
  },
};

/**
 * 格式化时间戳
 */
function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

/**
 * 获取Level对应的图标和颜色
 */
function getLevelConfig(level: string) {
  const configs: Record<string, { icon: React.ElementType; color: string; bgColor: string; borderColor: string }> = {
    error: { icon: AlertCircle, color: 'text-red-600', bgColor: 'bg-red-50', borderColor: 'border-red-200' },
    warning: { icon: AlertTriangle, color: 'text-amber-600', bgColor: 'bg-amber-50', borderColor: 'border-amber-200' },
    success: { icon: CheckCircle2, color: 'text-sage-600', bgColor: 'bg-sage-50', borderColor: 'border-sage-200' },
    info: { icon: Info, color: 'text-blue-600', bgColor: 'bg-blue-50', borderColor: 'border-blue-200' },
    debug: { icon: Info, color: 'text-gray-500', bgColor: 'bg-gray-50', borderColor: 'border-gray-200' },
  };
  return configs[level] || configs.info;
}

/**
 * LogSummaryContent 组件
 */
function LogSummaryContent({ log }: { log: ExecutionLog }) {
  const levelConfig = getLevelConfig(log.level);
  
  return (
    <div className="w-full space-y-2.5">
      <div className="flex items-center gap-2 flex-wrap">
        <Badge variant="outline" className={cn('text-xs', levelConfig.color, levelConfig.borderColor)}>
          {log.level.toUpperCase()}
        </Badge>
        {log.agent_name && (
          <span className="text-xs text-muted-foreground">
            by {log.agent_name}
          </span>
        )}
        {log.duration_ms !== null && (
          <span className="text-xs text-muted-foreground">
            {log.duration_ms}ms
          </span>
        )}
      </div>
      <p className="text-sm leading-relaxed text-foreground tracking-[-0.006em]">
        {log.message}
      </p>
    </div>
  );
}

/**
 * DetailsContent 组件 - 优化的 details 展示
 */
function DetailsContent({ details }: { details: any }) {
  if (!details || Object.keys(details).length === 0) {
    return (
      <div className="text-center py-4">
        <p className="text-xs text-muted-foreground">No additional details available.</p>
      </div>
    );
  }
  
  // 提取关键字段
  const { edit_source, validation_errors, output_summary, error, log_type, ...rest } = details;
  
  return (
    <div className="space-y-3 w-full">
      {/* 编辑来源 */}
      {edit_source && (
        <div className="px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-xs font-medium text-amber-700 tracking-[-0.006em]">
            Edit Source: <span className="font-semibold">{edit_source}</span>
          </p>
        </div>
      )}
      
      {/* 错误信息 */}
      {error && (
        <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-xs font-medium text-red-700 mb-1 tracking-[-0.006em]">Error</p>
          <p className="text-xs text-red-600 leading-relaxed tracking-[-0.006em]">{error}</p>
        </div>
      )}
      
      {/* 验证错误 */}
      {validation_errors && Array.isArray(validation_errors) && validation_errors.length > 0 && (
        <div className="px-3 py-2 bg-orange-50 border border-orange-200 rounded-lg">
          <p className="text-xs font-medium text-orange-700 mb-2 tracking-[-0.006em]">
            Validation Errors ({validation_errors.length})
          </p>
          <ul className="space-y-1">
            {validation_errors.map((err: any, idx: number) => (
              <li key={idx} className="text-xs text-orange-600 leading-relaxed tracking-[-0.006em] flex gap-1.5">
                <span className="text-orange-500 shrink-0">•</span>
                <span>{typeof err === 'string' ? err : JSON.stringify(err)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* 输出摘要 */}
      {output_summary && (
        <div className="px-3 py-2 bg-sage-50 border border-sage-200 rounded-lg">
          <p className="text-xs font-medium text-sage-700 mb-1.5 tracking-[-0.006em]">Output Summary</p>
          <div className="text-xs text-sage-600 space-y-1">
            {typeof output_summary === 'object' ? (
              Object.entries(output_summary).map(([key, value]) => (
                <div key={key} className="flex gap-2">
                  <span className="font-medium shrink-0">{key}:</span>
                  <span className="text-sage-500">{String(value)}</span>
                </div>
              ))
            ) : (
              <pre className="whitespace-pre-wrap font-mono text-[10px]">{JSON.stringify(output_summary, null, 2)}</pre>
            )}
          </div>
        </div>
      )}
      
      {/* 其他字段 */}
      {Object.keys(rest).length > 0 && (
        <details className="group">
          <summary className="cursor-pointer text-xs font-medium text-sage-600 hover:text-sage-700 tracking-[-0.006em] flex items-center gap-1.5">
            <span>View all fields</span>
            <Badge variant="outline" className="text-[10px] h-4 px-1.5">
              {Object.keys(rest).length}
            </Badge>
          </summary>
          <div className="mt-2 px-3 py-2 bg-muted rounded-lg">
            <pre className="text-[10px] text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed">
              {JSON.stringify(rest, null, 2)}
            </pre>
          </div>
        </details>
      )}
    </div>
  );
}

export function NodeDetailPanel({
  selectedNodeId,
  executionLogs,
  onClose,
}: NodeDetailPanelProps) {
  // 筛选当前节点的日志
  const filteredLogs = useMemo(() => {
    if (!selectedNodeId) return [];
    
    const nodeConfig = NODE_TO_STEPS[selectedNodeId];
    if (!nodeConfig) return [];
    
    // 筛选日志：只保留 category === 'agent' 的日志
    const logs = executionLogs.filter(log => {
      if (!log.step) return false;
      
      // 必须是 agent 类型的日志
      if (log.category !== 'agent') return false;
      
      // 检查 step 是否匹配
      const stepMatches = nodeConfig.steps.includes(log.step);
      
      // 如果节点有 editSource 要求，需要额外过滤
      if (nodeConfig.editSource && log.details?.edit_source) {
        return stepMatches && log.details.edit_source === nodeConfig.editSource;
      }
      
      return stepMatches;
    });
    
    // 按时间倒序排列
    return logs.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [selectedNodeId, executionLogs]);
  
  // 获取最新一条日志
  const latestLog = filteredLogs[0];
  
  // 获取节点配置
  const nodeConfig = selectedNodeId ? NODE_TO_STEPS[selectedNodeId] : null;
  
  if (!selectedNodeId || !nodeConfig) {
    return null;
  }
  
  const NodeIcon = nodeConfig.icon;
  
  // 构建步骤内容
  const detailSections = latestLog ? [
    {
      title: 'Log Summary',
      description: 'Basic execution information',
      content: <LogSummaryContent log={latestLog} />,
    },
    {
      title: 'Execution Details',
      description: 'Detailed output data',
      content: <DetailsContent details={latestLog.details} />,
    },
  ] : [];
  
  return (
    <>
      {/* 遮罩层 */}
      <div 
        className="fixed inset-0 bg-black/20 z-40 animate-in fade-in duration-300"
        onClick={onClose}
      />
      
      {/* 侧边面板 */}
      <div className="fixed top-0 right-0 h-full w-[480px] bg-card border-l-2 border-border shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-300">
        <Card className="flex w-full shadow-none flex-col gap-6 p-5 md:p-8 border-0 h-full">
          {/* 头部区域 - 居中布局 */}
          <CardHeader className="flex flex-col items-center gap-2 p-0">
            {/* 大图标 - 带渐变背景环 */}
            <div className="relative flex size-[68px] shrink-0 items-center justify-center rounded-full backdrop-blur-xl md:size-20 before:absolute before:inset-0 before:rounded-full before:bg-gradient-to-b before:from-sage-500 before:to-transparent before:opacity-10">
              <div className="relative z-10 flex size-12 items-center justify-center rounded-full bg-background shadow-xs ring-1 ring-inset ring-sage-200 md:size-14">
                <NodeIcon className={cn('w-6 h-6 md:w-8 md:h-8', nodeConfig.color)} />
              </div>
            </div>
            
            {/* 标题和描述 */}
            <div className="flex flex-col space-y-1.5 text-center">
              <CardTitle className="text-lg md:text-xl font-medium tracking-[-0.006em]">
                {nodeConfig.label}
              </CardTitle>
              {latestLog && (
                <CardDescription className="tracking-[-0.006em] text-xs">
                  {formatTime(latestLog.created_at)}
                </CardDescription>
              )}
            </div>
            
            {/* 关闭按钮 - 绝对定位到右上角 */}
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="absolute right-0 top-0 h-8 w-8 p-0 hover:bg-sage-100 text-sage-600"
            >
              <X className="w-4 h-4" />
            </Button>
          </CardHeader>
          
          <Separator />
          
          {/* 内容区域 - 步骤式布局 */}
          <ScrollArea className="flex-1 -mx-5 md:-mx-8 px-5 md:px-8">
            <CardContent className="p-0">
              {!latestLog ? (
                /* 空状态 */
                <div className="flex flex-col items-center justify-center py-12 text-center space-y-3">
                  <div className="relative flex size-16 items-center justify-center rounded-full bg-muted/50">
                    <Clock className="w-8 h-8 text-muted-foreground/50" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground tracking-[-0.006em]">No Data Available</p>
                    <p className="text-xs text-muted-foreground mt-1 tracking-[-0.006em]">
                      This step hasn't been executed yet.
                    </p>
                  </div>
                </div>
              ) : (
                /* 步骤式内容 */
                <div className="grid items-start justify-start grid-cols-1">
                  {detailSections.map((section, index) => (
                    <div
                      key={index}
                      className={cn(
                        'relative flex flex-row items-start gap-3',
                        'before:absolute before:start-0',
                        'last:after:hidden after:absolute after:top-9 after:bottom-2 after:start-3.5 after:w-px after:-translate-x-[0.5px] after:bg-border',
                        index !== detailSections.length - 1 && 'pb-6'
                      )}
                    >
                      {/* 数字圆圈 */}
                      <span className="z-10 text-xs font-semibold flex shrink-0 items-center justify-center rounded-full bg-sage-50 ring-1 ring-inset ring-sage-200 text-sage-700 size-7">
                        {index + 1}
                      </span>
                      
                      {/* 步骤内容 */}
                      <div className="flex flex-col items-start flex-1">
                        <p className="text-sm leading-5 tracking-[-0.006em] font-semibold text-foreground">
                          {section.title}
                        </p>
                        <p className="text-xs leading-5 tracking-[-0.006em] text-muted-foreground">
                          {section.description}
                        </p>
                        <div className="mt-2.5 w-full">
                          {section.content}
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  {/* 历史记录统计 */}
                  {filteredLogs.length > 1 && (
                    <div className="pt-4 mt-4 border-t">
                      <p className="text-xs text-muted-foreground text-center tracking-[-0.006em]">
                        Showing latest of {filteredLogs.length} log entries for this step
                      </p>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </ScrollArea>
        </Card>
      </div>
    </>
  );
}

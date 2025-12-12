'use client';

import { useMemo } from 'react';
import {
  Stepper,
  StepperDescription,
  StepperIndicator,
  StepperItem,
  StepperSeparator,
  StepperTitle,
  StepperTrigger,
} from '@/components/ui/stepper';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AlertCircle, CheckCircle2, Clock, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { GenerationPhase } from '@/lib/store/roadmap-store';

interface GenerationProgressStepperProps {
  phase: GenerationPhase;
  progress?: number;
  currentStep?: string | null;
  logs?: GenerationLog[];
  className?: string;
}

export interface GenerationLog {
  timestamp: string;
  phase: string;
  message: string;
  level: 'info' | 'success' | 'warning' | 'error';
}

/**
 * 阶段配置 - 简化版
 */
const PHASE_STEPS = [
  {
    step: 1,
    phase: 'intent_analysis' as GenerationPhase,
    title: 'Intent Analysis',
    description: 'Analyzing learning goals and requirements',
  },
  {
    step: 2,
    phase: 'curriculum_design' as GenerationPhase,
    title: 'Curriculum Design',
    description: 'Designing roadmap structure',
  },
  {
    step: 3,
    phase: 'structure_validation' as GenerationPhase,
    title: 'Structure Validation',
    description: 'Validating roadmap logic',
  },
  {
    step: 4,
    phase: 'human_review' as GenerationPhase,
    title: 'Human Review',
    description: 'Awaiting user confirmation',
  },
  {
    step: 5,
    phase: 'content_generation' as GenerationPhase,
    title: 'Content Generation',
    description: 'Generating tutorials, resources, and quizzes',
  },
];

/**
 * 获取日志等级对应的图标
 */
const getLogIcon = (level: string) => {
  switch (level) {
    case 'success':
      return <CheckCircle2 className="w-3.5 h-3.5 text-green-600" />;
    case 'error':
      return <AlertCircle className="w-3.5 h-3.5 text-red-600" />;
    case 'warning':
      return <AlertCircle className="w-3.5 h-3.5 text-amber-600" />;
    default:
      return <Info className="w-3.5 h-3.5 text-blue-600" />;
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
  });
};

/**
 * GenerationProgressStepper - 极简风格的生成进度组件
 * 
 * 功能:
 * - 垂直步进器展示生成阶段
 * - 实时日志流显示
 * - 当前进度百分比
 * - 简洁优雅的 UI 设计
 */
export function GenerationProgressStepper({
  phase,
  progress = 0,
  currentStep,
  logs = [],
  className,
}: GenerationProgressStepperProps) {
  // 计算当前处于第几步
  const currentStepIndex = useMemo(() => {
    if (phase === 'completed') return PHASE_STEPS.length;
    if (phase === 'failed') return -1;
    if (phase === 'idle') return 0;
    
    const index = PHASE_STEPS.findIndex(s => s.phase === phase);
    return index === -1 ? 0 : index + 1;
  }, [phase]);

  // 判断是否失败
  const isFailed = phase === 'failed';
  const isCompleted = phase === 'completed';

  return (
    <div className={cn('space-y-6', className)}>
      {/* 头部状态 */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-xl font-serif">Generation Progress</CardTitle>
            {isFailed && (
              <Badge variant="destructive">
                Failed
              </Badge>
            )}
            {isCompleted && (
              <Badge className="bg-green-600">
                Completed
              </Badge>
            )}
            {!isFailed && !isCompleted && (
              <Badge variant="secondary" className="animate-pulse">
                In Progress
              </Badge>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* 进度百分比 */}
          {!isFailed && !isCompleted && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Overall Progress</span>
                <span className="font-medium">{Math.round(progress)}%</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-sage-600 transition-all duration-500 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {/* 当前步骤描述 */}
          {currentStep && !isFailed && !isCompleted && (
            <div className="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <Clock className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
              <p className="text-sm text-blue-700 dark:text-blue-300">
                {currentStep}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 步进器 */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-base font-serif">Generation Stages</CardTitle>
        </CardHeader>

        <CardContent>
          <Stepper
            value={currentStepIndex}
            orientation="vertical"
            className="w-full"
          >
            {PHASE_STEPS.map(({ step, title, description }) => {
              const isStepCompleted = step < currentStepIndex;
              const isStepActive = step === currentStepIndex;
              const isStepLoading = isStepActive && !isFailed && !isCompleted;

              return (
                <StepperItem
                  key={step}
                  step={step}
                  completed={isStepCompleted}
                  loading={isStepLoading}
                  className="relative items-start [&:not(:last-child)]:flex-1"
                >
                  <StepperTrigger
                    asChild
                    className="items-start pb-12 last:pb-0 cursor-default"
                  >
                    <div className="flex items-start gap-3">
                      <StepperIndicator />
                      <div className="mt-0.5 space-y-0.5 text-left">
                        <StepperTitle
                          className={cn(
                            'font-medium',
                            isStepActive && 'text-foreground',
                            isStepCompleted && 'text-muted-foreground',
                            !isStepActive && !isStepCompleted && 'text-muted-foreground'
                          )}
                        >
                          {title}
                        </StepperTitle>
                        <StepperDescription
                          className={cn(
                            'text-xs',
                            isStepActive && 'text-muted-foreground'
                          )}
                        >
                          {description}
                        </StepperDescription>
                      </div>
                    </div>
                  </StepperTrigger>
                  {step < PHASE_STEPS.length && (
                    <StepperSeparator className="absolute inset-y-0 left-3 top-[calc(1.5rem+0.125rem)] -order-1 m-0 -translate-x-1/2 group-data-[orientation=vertical]/stepper:h-[calc(100%-1.5rem-0.25rem)] group-data-[orientation=horizontal]/stepper:w-[calc(100%-1.5rem-0.25rem)] group-data-[orientation=horizontal]/stepper:flex-none" />
                  )}
                </StepperItem>
              );
            })}
          </Stepper>
        </CardContent>
      </Card>

      {/* 日志流 */}
      {logs.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-serif">Generation Logs</CardTitle>
          </CardHeader>

          <CardContent>
            <ScrollArea className="h-[300px] w-full pr-4">
              <div className="space-y-2">
                {logs.map((log, index) => (
                  <div
                    key={index}
                    className={cn(
                      'flex items-start gap-2 p-2 rounded-md text-xs',
                      log.level === 'error' && 'bg-red-50 dark:bg-red-900/20',
                      log.level === 'warning' && 'bg-amber-50 dark:bg-amber-900/20',
                      log.level === 'success' && 'bg-green-50 dark:bg-green-900/20',
                      log.level === 'info' && 'bg-muted'
                    )}
                  >
                    {getLogIcon(log.level)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline gap-2 mb-0.5">
                        <span className="text-[10px] text-muted-foreground font-mono">
                          {formatTimestamp(log.timestamp)}
                        </span>
                        <Badge
                          variant="outline"
                          className="h-4 text-[10px] px-1.5 border-0 bg-background/50"
                        >
                          {log.phase}
                        </Badge>
                      </div>
                      <p className="text-foreground/90 break-words">
                        {log.message}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* 失败提示 */}
      {isFailed && (
        <Card className="border-red-200 dark:border-red-800">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-medium text-red-700 dark:text-red-300">
                  Generation Failed
                </p>
                <p className="text-sm text-red-600 dark:text-red-400">
                  An error occurred during generation. Please check the logs above for details or retry the operation.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 完成提示 */}
      {isCompleted && (
        <Card className="border-green-200 dark:border-green-800">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-green-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-medium text-green-700 dark:text-green-300">
                  Generation Complete
                </p>
                <p className="text-sm text-green-600 dark:text-green-400">
                  Your roadmap has been successfully generated! You can now start learning.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

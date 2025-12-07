'use client';

import { CheckCircle2, Circle, Loader2, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { GenerationPhase } from '@/lib/store/roadmap-store';

interface GenerationProgressProps {
  phase: GenerationPhase;
  progress?: number;
  currentStep?: string | null;
  className?: string;
}

/**
 * 阶段配置
 */
const PHASE_CONFIG: Record<GenerationPhase, {
  label: string;
  description: string;
  icon: React.ReactNode;
  order: number;
}> = {
  idle: {
    label: '准备中',
    description: '正在初始化...',
    icon: <Circle className="w-5 h-5" />,
    order: 0
  },
  intent_analysis: {
    label: '意图分析',
    description: '分析学习目标和需求',
    icon: <Loader2 className="w-5 h-5 animate-spin" />,
    order: 1
  },
  curriculum_design: {
    label: '课程设计',
    description: '设计路线图框架结构',
    icon: <Loader2 className="w-5 h-5 animate-spin" />,
    order: 2
  },
  structure_validation: {
    label: '结构验证',
    description: '验证路线图逻辑性和完整性',
    icon: <Loader2 className="w-5 h-5 animate-spin" />,
    order: 3
  },
  human_review: {
    label: '人工审核',
    description: '等待用户审核确认',
    icon: <Loader2 className="w-5 h-5 animate-spin" />,
    order: 4
  },
  content_generation: {
    label: '内容生成',
    description: '并行生成教程、资源、测验',
    icon: <Loader2 className="w-5 h-5 animate-spin" />,
    order: 5
  },
  completed: {
    label: '生成完成',
    description: '路线图已生成完成',
    icon: <CheckCircle2 className="w-5 h-5 text-green-500" />,
    order: 6
  },
  failed: {
    label: '生成失败',
    description: '生成过程中出现错误',
    icon: <AlertCircle className="w-5 h-5 text-red-500" />,
    order: 7
  }
};

/**
 * GenerationProgress - 路线图生成进度组件
 * 
 * 功能:
 * - 显示当前阶段
 * - 进度条动画
 * - 阶段列表展示
 * - 实时状态更新
 */
export function GenerationProgress({
  phase,
  progress = 0,
  currentStep,
  className
}: GenerationProgressProps) {
  const currentPhaseConfig = PHASE_CONFIG[phase];
  const currentOrder = currentPhaseConfig?.order || 0;

  // 过滤掉 idle 和 failed，因为它们不在正常流程中
  const phaseList = Object.entries(PHASE_CONFIG)
    .filter(([key]) => key !== 'idle' && key !== 'failed')
    .sort(([, a], [, b]) => a.order - b.order);

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">生成进度</CardTitle>
          {phase !== 'completed' && phase !== 'failed' && (
            <Badge variant="secondary" className="animate-pulse">
              处理中
            </Badge>
          )}
          {phase === 'completed' && (
            <Badge variant="default" className="bg-green-500">
              已完成
            </Badge>
          )}
          {phase === 'failed' && (
            <Badge variant="destructive">
              失败
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* 当前阶段信息 */}
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className={cn(
              'shrink-0',
              phase === 'completed' && 'text-green-500',
              phase === 'failed' && 'text-red-500',
              phase !== 'completed' && phase !== 'failed' && 'text-primary'
            )}>
              {currentPhaseConfig.icon}
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold">
                {currentPhaseConfig.label}
              </h4>
              <p className="text-sm text-muted-foreground">
                {currentStep || currentPhaseConfig.description}
              </p>
            </div>
          </div>

          {/* 进度条 */}
          {phase !== 'completed' && phase !== 'failed' && (
            <div className="space-y-2">
              <Progress value={progress} className="h-2" />
              <p className="text-xs text-muted-foreground text-right">
                {Math.round(progress)}%
              </p>
            </div>
          )}
        </div>

        {/* 阶段列表 */}
        <div className="space-y-3">
          <h5 className="text-sm font-medium text-muted-foreground">
            生成流程
          </h5>
          <div className="space-y-2">
            {phaseList.map(([key, config]) => {
              const phaseKey = key as GenerationPhase;
              const isCompleted = config.order < currentOrder || phase === 'completed';
              const isCurrent = phaseKey === phase;
              const isPending = config.order > currentOrder && phase !== 'completed';

              return (
                <div
                  key={key}
                  className={cn(
                    'flex items-center gap-3 p-2 rounded-lg transition-colors',
                    isCurrent && 'bg-primary/10 border border-primary/20',
                    isCompleted && 'opacity-60'
                  )}
                >
                  {/* 状态图标 */}
                  <div className={cn(
                    'shrink-0',
                    isCompleted && 'text-green-500',
                    isCurrent && 'text-primary',
                    isPending && 'text-muted-foreground'
                  )}>
                    {isCompleted ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : isCurrent ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Circle className="w-4 h-4" />
                    )}
                  </div>

                  {/* 阶段信息 */}
                  <div className="flex-1 min-w-0">
                    <p className={cn(
                      'text-sm font-medium',
                      isCompleted && 'text-muted-foreground',
                      isCurrent && 'text-foreground',
                      isPending && 'text-muted-foreground'
                    )}>
                      {config.label}
                    </p>
                    {isCurrent && (
                      <p className="text-xs text-muted-foreground">
                        {config.description}
                      </p>
                    )}
                  </div>

                  {/* 状态标签 */}
                  {isCompleted && (
                    <Badge variant="outline" className="text-xs bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300">
                      已完成
                    </Badge>
                  )}
                  {isCurrent && (
                    <Badge variant="outline" className="text-xs">
                      进行中
                    </Badge>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* 失败提示 */}
        {phase === 'failed' && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
              <div className="text-sm text-red-700 dark:text-red-300">
                生成过程中出现错误，请重试或联系支持团队
              </div>
            </div>
          </div>
        )}

        {/* 完成提示 */}
        {phase === 'completed' && (
          <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <div className="flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
              <div className="text-sm text-green-700 dark:text-green-300">
                路线图已成功生成！现在可以开始学习了
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * CompactGenerationProgress - 紧凑版进度显示
 * 用于页面头部或侧边栏
 */
export function CompactGenerationProgress({
  phase,
  progress = 0,
  className
}: Pick<GenerationProgressProps, 'phase' | 'progress' | 'className'>) {
  const currentPhaseConfig = PHASE_CONFIG[phase];

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <div className="text-muted-foreground">
            {currentPhaseConfig.icon}
          </div>
          <span className="font-medium">{currentPhaseConfig.label}</span>
        </div>
        <span className="text-muted-foreground">
          {Math.round(progress)}%
        </span>
      </div>
      {phase !== 'completed' && phase !== 'failed' && (
        <Progress value={progress} className="h-1.5" />
      )}
    </div>
  );
}


'use client';

import { CheckCircle2, Circle, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { GenerationPhase } from '@/types/custom/phases';

interface PhaseStep {
  id: GenerationPhase;
  label: string;
  description: string;
}

const PHASE_STEPS: PhaseStep[] = [
  {
    id: 'intent_analysis',
    label: '需求分析',
    description: '分析学习目标和技术栈',
  },
  {
    id: 'curriculum_design',
    label: '课程设计',
    description: '设计学习路线框架',
  },
  {
    id: 'human_review',
    label: '人工审核',
    description: '等待用户确认方案',
  },
  {
    id: 'content_generation',
    label: '内容生成',
    description: '生成教程和资源',
  },
  {
    id: 'completed',
    label: '完成',
    description: '路线图已生成',
  },
];

interface PhaseIndicatorProps {
  currentPhase: GenerationPhase | null;
  failedCount?: number;
  className?: string;
}

export function PhaseIndicator({ currentPhase, failedCount = 0, className }: PhaseIndicatorProps) {
  if (!currentPhase) {
    return null;
  }

  const currentIndex = PHASE_STEPS.findIndex((step) => step.id === currentPhase);

  const getStepStatus = (index: number) => {
    if (index < currentIndex) return 'completed';
    if (index === currentIndex) return 'current';
    return 'pending';
  };

  return (
    <div className={cn('w-full', className)}>
      <div className="flex items-center justify-between">
        {PHASE_STEPS.map((step, index) => {
          const status = getStepStatus(index);
          const isLast = index === PHASE_STEPS.length - 1;

          return (
            <div key={step.id} className="flex items-center flex-1">
              {/* Step Circle */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    'relative flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all',
                    {
                      'border-green-500 bg-green-500': status === 'completed',
                      'border-blue-500 bg-blue-500': status === 'current',
                      'border-gray-300 bg-white dark:bg-gray-800 dark:border-gray-600':
                        status === 'pending',
                    }
                  )}
                >
                  {status === 'completed' && (
                    <CheckCircle2 className="w-5 h-5 text-white" />
                  )}
                  {status === 'current' && (
                    <Loader2 className="w-5 h-5 text-white animate-spin" />
                  )}
                  {status === 'pending' && (
                    <Circle className="w-5 h-5 text-gray-400 dark:text-gray-500" />
                  )}
                </div>

                {/* Step Label */}
                <div className="mt-2 text-center">
                  <p
                    className={cn('text-sm font-medium', {
                      'text-green-600 dark:text-green-400': status === 'completed',
                      'text-blue-600 dark:text-blue-400': status === 'current',
                      'text-gray-500 dark:text-gray-400': status === 'pending',
                    })}
                  >
                    {step.label}
                  </p>
                  <p
                    className={cn('text-xs mt-1', {
                      'text-gray-600 dark:text-gray-400': status === 'completed' || status === 'current',
                      'text-gray-400 dark:text-gray-500': status === 'pending',
                    })}
                  >
                    {step.description}
                  </p>
                </div>
              </div>

              {/* Connector Line */}
              {!isLast && (
                <div className="flex-1 h-0.5 mx-2 mt-[-40px]">
                  <div
                    className={cn('h-full transition-all', {
                      'bg-green-500': index < currentIndex,
                      'bg-blue-500 animate-pulse': index === currentIndex,
                      'bg-gray-300 dark:bg-gray-600': index > currentIndex,
                    })}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Failed Count Warning */}
      {failedCount > 0 && currentPhase === 'completed' && (
        <div className="mt-4 flex items-center gap-2 text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded-lg px-4 py-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span className="text-sm">
            {failedCount} 个概念生成失败，您可以点击右上角的重试按钮重新生成
          </span>
        </div>
      )}
    </div>
  );
}


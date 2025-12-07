'use client';

import { CheckCircle2, Circle, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { GenerationPhase } from '@/types/custom/phases';

interface PhaseStep {
  id: GenerationPhase;
  label: string;
}

const PHASE_STEPS: PhaseStep[] = [
  { id: 'intent_analysis', label: 'Analysis' },
  { id: 'curriculum_design', label: 'Design' },
  { id: 'human_review', label: 'Review' },
  { id: 'content_generation', label: 'Content' },
  { id: 'completed', label: 'Done' },
];

interface CompactPhaseIndicatorProps {
  currentPhase: GenerationPhase | null;
  failedCount?: number;
  className?: string;
}

export function CompactPhaseIndicator({ 
  currentPhase, 
  failedCount = 0, 
  className 
}: CompactPhaseIndicatorProps) {
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
      {/* Compact Progress Bar */}
      <div className="flex items-center gap-1.5">
        {PHASE_STEPS.map((step, index) => {
          const status = getStepStatus(index);
          const isLast = index === PHASE_STEPS.length - 1;

          return (
            <div key={step.id} className="flex items-center flex-1 group">
              {/* Step Indicator */}
              <div className="flex flex-col items-center min-w-fit">
                <div
                  className={cn(
                    'relative flex items-center justify-center w-6 h-6 rounded-full border transition-all duration-300',
                    {
                      'border-sage-500 bg-sage-500 dark:border-sage-600 dark:bg-sage-600': status === 'completed',
                      'border-blue-500 bg-blue-500 dark:border-blue-400 dark:bg-blue-400 animate-pulse-subtle': status === 'current',
                      'border-zinc-300 bg-white dark:bg-zinc-800 dark:border-zinc-700': status === 'pending',
                    }
                  )}
                >
                  {status === 'completed' && (
                    <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                  )}
                  {status === 'current' && (
                    <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />
                  )}
                  {status === 'pending' && (
                    <Circle className="w-3.5 h-3.5 text-zinc-400 dark:text-zinc-600" />
                  )}
                </div>

                {/* Step Label */}
                <p
                  className={cn('mt-1.5 text-xs font-medium transition-colors', {
                    'text-sage-600 dark:text-sage-400': status === 'completed',
                    'text-blue-600 dark:text-blue-400': status === 'current',
                    'text-zinc-400 dark:text-zinc-600': status === 'pending',
                  })}
                >
                  {step.label}
                </p>
              </div>

              {/* Connector Line */}
              {!isLast && (
                <div className="flex-1 h-px mx-2 -mt-5">
                  <div
                    className={cn('h-full transition-all duration-300', {
                      'bg-sage-500 dark:bg-sage-600': index < currentIndex,
                      'bg-blue-500 dark:bg-blue-400': index === currentIndex,
                      'bg-zinc-300 dark:bg-zinc-700': index > currentIndex,
                    })}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Failed Count Warning (Glass Alert) */}
      {failedCount > 0 && currentPhase === 'completed' && (
        <div className="mt-4 flex items-start gap-2 p-3 rounded-lg bg-amber-50/60 dark:bg-amber-900/20 backdrop-blur-sm border-l-2 border-amber-500 dark:border-amber-600 text-amber-800 dark:text-amber-300">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span className="text-xs leading-relaxed">
            {failedCount} concepts failed to generate. Use the retry button to regenerate.
          </span>
        </div>
      )}
    </div>
  );
}


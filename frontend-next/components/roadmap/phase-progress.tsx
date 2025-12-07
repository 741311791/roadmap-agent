'use client';

import { cn } from '@/lib/utils';
import { Check, Loader2, Edit, AlertCircle } from 'lucide-react';
import { 
  GenerationPhase, 
  GENERATION_PHASES, 
  isPhaseCompleted, 
  isPhaseActive,
  getPhaseIndex,
  HumanReviewSubStatus,
  getSubStatusLabel,
  PhaseConfig,
} from '@/types/custom/phases';

interface PhaseProgressProps {
  currentPhase: GenerationPhase | null;
  subStatus?: HumanReviewSubStatus;
  skippedPhases?: GenerationPhase[];  // 跳过的阶段（如 structure_validation, human_review）
  failedCount?: number;  // number of failed items (shown in completed phase)
  className?: string;
}

/**
 * PhaseProgress - Linear progress indicator for roadmap generation phases
 * 
 * Displays up to 6 phases:
   * 1. Intent Analysis
   * 2. Curriculum Design
   * 3. Structure Validation [optional]
   * 4. Human Review [optional]
   * 5. Content Generation
   * 6. Completed
 */
export function PhaseProgress({ 
  currentPhase, 
  subStatus,
  skippedPhases = [],
  failedCount,
  className 
}: PhaseProgressProps) {
  const currentIndex = getPhaseIndex(currentPhase);
  
  // 过滤掉跳过的阶段
  const visiblePhases = GENERATION_PHASES.filter(
    phase => !skippedPhases.includes(phase.id)
  );
  
  // 获取阶段显示的额外信息
  const getPhaseExtra = (phase: PhaseConfig): string | null => {
    if (phase.id === 'human_review' && isPhaseActive(phase.id, currentPhase) && subStatus) {
      return getSubStatusLabel(subStatus);
    }
    if (phase.id === 'completed' && currentPhase === 'completed' && failedCount && failedCount > 0) {
      return `${failedCount} failed`;
    }
    return null;
  };
  
  // 获取阶段图标
  const getPhaseIcon = (phase: PhaseConfig, completed: boolean, active: boolean, index: number) => {
    if (completed) {
      return <Check className="w-5 h-5" strokeWidth={3} />;
    }
    if (active) {
      if (phase.id === 'human_review' && subStatus === 'editing') {
        return <Edit className="w-4 h-4" />;
      }
      if (phase.id === 'completed' && failedCount && failedCount > 0) {
        return <AlertCircle className="w-4 h-4" />;
      }
      return <Loader2 className="w-4 h-4 animate-spin" />;
    }
    return <span className="text-sm font-medium">{index + 1}</span>;
  };

  // 计算可见阶段的当前索引
  const visibleCurrentIndex = visiblePhases.findIndex(p => p.id === currentPhase);

  return (
    <div className={cn('w-full', className)}>
      {/* Desktop view */}
      <div className="hidden sm:flex items-center justify-center">
        {visiblePhases.map((phase, index) => {
          const completed = isPhaseCompleted(phase.id, currentPhase);
          const active = isPhaseActive(phase.id, currentPhase);
          const isLast = index === visiblePhases.length - 1;
          const extra = getPhaseExtra(phase);
          const hasError = phase.id === 'completed' && failedCount && failedCount > 0;

          return (
            <div key={phase.id} className="flex items-center">
              {/* Phase node */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    'w-10 h-10 rounded-full flex items-center justify-center transition-all duration-500',
                    'border-2',
                    completed && !hasError && 'bg-green-500 border-green-500 text-white',
                    completed && hasError && 'bg-amber-500 border-amber-500 text-white',
                    active && 'bg-blue-500 border-blue-500 text-white',
                    !completed && !active && 'bg-muted border-border text-muted-foreground'
                  )}
                >
                  {getPhaseIcon(phase, completed, active, index)}
                </div>
                <span
                  className={cn(
                    'mt-2 text-xs font-medium whitespace-nowrap transition-colors duration-300',
                    completed && !hasError && 'text-green-600',
                    completed && hasError && 'text-amber-600',
                    active && 'text-blue-600',
                    !completed && !active && 'text-muted-foreground'
                  )}
                >
                  {phase.label}
                </span>
                {/* Sub-status label */}
                {extra && (
                  <span className={cn(
                    'text-[10px] whitespace-nowrap',
                    active && 'text-blue-500',
                    hasError && 'text-amber-500'
                  )}>
                    {extra}
                  </span>
                )}
              </div>

              {/* Connector line */}
              {!isLast && (
                <div
                  className={cn(
                    'w-12 lg:w-20 h-0.5 mx-2 transition-all duration-500',
                    index < visibleCurrentIndex ? 'bg-green-500' : 'bg-border'
                  )}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Mobile view - compact */}
      <div className="sm:hidden">
        <div className="flex items-center justify-between mb-2">
          {visiblePhases.map((phase, index) => {
            const completed = isPhaseCompleted(phase.id, currentPhase);
            const active = isPhaseActive(phase.id, currentPhase);
            const isLast = index === visiblePhases.length - 1;
            const hasError = phase.id === 'completed' && failedCount && failedCount > 0;

            return (
              <div key={phase.id} className="flex items-center flex-1">
                {/* Phase dot */}
                <div
                  className={cn(
                    'w-6 h-6 rounded-full flex items-center justify-center transition-all duration-500',
                    'flex-shrink-0',
                    completed && !hasError && 'bg-green-500 text-white',
                    completed && hasError && 'bg-amber-500 text-white',
                    active && 'bg-blue-500 text-white',
                    !completed && !active && 'bg-muted border border-border'
                  )}
                >
                  {completed ? (
                    hasError ? <AlertCircle className="w-3 h-3" /> : <Check className="w-3 h-3" strokeWidth={3} />
                  ) : active ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <span className="text-[10px] font-medium">{index + 1}</span>
                  )}
                </div>
                
                {/* Connector */}
                {!isLast && (
                  <div
                    className={cn(
                      'flex-1 h-0.5 mx-1 transition-all duration-500',
                      index < visibleCurrentIndex ? 'bg-green-500' : 'bg-border'
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>
        
        {/* Current phase label with sub-status */}
        {currentPhase && (
          <p className="text-center text-sm text-muted-foreground">
            {visiblePhases.find(p => p.id === currentPhase)?.label}
            {subStatus && currentPhase === 'human_review' && (
              <span className="text-blue-500 ml-1">({getSubStatusLabel(subStatus)})</span>
            )}
            {failedCount && failedCount > 0 && currentPhase === 'completed' && (
              <span className="text-amber-500 ml-1">({failedCount} failed)</span>
            )}
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * PhaseProgressCompact - Minimal version for tight spaces
 */
export function PhaseProgressCompact({ 
  currentPhase, 
  subStatus,
  skippedPhases = [],
  failedCount,
  className 
}: PhaseProgressProps) {
  // 过滤掉跳过的阶段
  const visiblePhases = GENERATION_PHASES.filter(
    phase => !skippedPhases.includes(phase.id)
  );
  
  const currentIndex = visiblePhases.findIndex(p => p.id === currentPhase);
  const totalPhases = visiblePhases.length;
  const progress = currentPhase === 'completed' 
    ? 100 
    : currentIndex >= 0 ? ((currentIndex + 0.5) / totalPhases) * 100 : 0;
  
  const hasError = failedCount && failedCount > 0;

  return (
    <div className={cn('w-full', className)}>
      <div className="flex items-center gap-3">
        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full transition-all duration-500 ease-out",
              hasError && currentPhase === 'completed' 
                ? "bg-gradient-to-r from-blue-500 to-amber-500"
                : "bg-gradient-to-r from-blue-500 to-green-500"
            )}
            style={{ width: `${progress}%` }}
          />
        </div>
        {currentPhase && (
          <span className={cn(
            "text-xs font-medium whitespace-nowrap",
            hasError && currentPhase === 'completed' ? "text-amber-600" : "text-muted-foreground"
          )}>
            {visiblePhases.find(p => p.id === currentPhase)?.label}
            {subStatus && currentPhase === 'human_review' && (
              <span className="text-blue-500 ml-1">({getSubStatusLabel(subStatus)})</span>
            )}
            {hasError && currentPhase === 'completed' && (
              <span className="text-amber-500 ml-1">({failedCount} failed)</span>
            )}
          </span>
        )}
      </div>
    </div>
  );
}


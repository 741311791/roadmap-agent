'use client';

import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { 
  Lock, 
  Loader2, 
  CheckCircle2, 
  AlertCircle,
  Clock 
} from 'lucide-react';
import type { Concept } from '@/types/generated/models';
import type { ConceptContentStatus } from '@/types/custom/phases';

interface ConceptCardProps {
  concept: Concept;
  onClick?: () => void;
  className?: string;
  showMetadata?: boolean;
}

/**
 * ConceptCard - Reactive concept card with status-based styling
 * 
 * States:
 * - pending: Gray dashed border, locked, "排队中..."
 * - generating: Animated border, spinner, "AI 正在生成内容..."
 * - completed: Solid border, clickable, shows difficulty badge
 * - failed: Red border, error state
 */
export function ConceptCard({ 
  concept, 
  onClick,
  className,
  showMetadata = true 
}: ConceptCardProps) {
  const status = (concept.content_status || 'pending') as ConceptContentStatus;
  const isClickable = status === 'completed';

  const handleClick = () => {
    if (isClickable && onClick) {
      onClick();
    }
  };

  return (
    <div
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg transition-all duration-300',
        // Status-based styles
        status === 'pending' && [
          'border-2 border-dashed border-gray-300 dark:border-gray-600',
          'bg-gray-50/50 dark:bg-gray-800/30',
          'opacity-60',
          'cursor-not-allowed',
        ],
        status === 'generating' && [
          'border-2 border-solid',
          'bg-blue-50/50 dark:bg-blue-900/20',
          'animate-pulse-border',
        ],
        status === 'completed' && [
          'border border-gray-200 dark:border-gray-700',
          'bg-white dark:bg-gray-800',
          'shadow-sm hover:shadow-md',
          'hover:-translate-y-0.5',
          'cursor-pointer',
        ],
        status === 'failed' && [
          'border border-red-200 dark:border-red-800',
          'bg-red-50/50 dark:bg-red-900/20',
          'opacity-75',
        ],
        className
      )}
      onClick={handleClick}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={(e) => {
        if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      {/* Status Icon */}
      <div className="shrink-0">
        <StatusIcon status={status} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className={cn(
          'font-medium truncate',
          status === 'pending' && 'text-gray-500 dark:text-gray-400',
          status === 'generating' && 'text-blue-700 dark:text-blue-300',
          status === 'completed' && 'text-foreground',
          status === 'failed' && 'text-red-700 dark:text-red-300',
        )}>
          {concept.name}
        </p>
        
        {/* Status text or description */}
        <p className={cn(
          'text-xs truncate mt-0.5',
          status === 'pending' && 'text-gray-400 dark:text-gray-500',
          status === 'generating' && 'text-blue-600 dark:text-blue-400',
          status === 'completed' && 'text-muted-foreground',
          status === 'failed' && 'text-red-600 dark:text-red-400',
        )}>
          {status === 'pending' && 'Queued...'}
          {status === 'generating' && 'AI is generating content...'}
          {status === 'completed' && concept.description}
          {status === 'failed' && 'Generation failed'}
        </p>
      </div>

      {/* Metadata */}
      {showMetadata && status === 'completed' && (
        <div className="flex items-center gap-2 shrink-0">
          {concept.difficulty && (
            <Badge
              variant="secondary"
              className={cn(
                'text-xs',
                getDifficultyColor(concept.difficulty)
              )}
            >
              {concept.difficulty}
            </Badge>
          )}
          {concept.estimated_hours && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="w-3 h-3" />
              {concept.estimated_hours}h
            </span>
          )}
        </div>
      )}

      {/* Generating progress indicator */}
      {status === 'generating' && (
        <div className="shrink-0">
          <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * StatusIcon - Icon based on concept status
 */
function StatusIcon({ status }: { status: ConceptContentStatus }) {
  switch (status) {
    case 'pending':
      return <Lock className="w-4 h-4 text-gray-400 dark:text-gray-500" />;
    case 'generating':
      return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
    case 'completed':
      return <CheckCircle2 className="w-4 h-4 text-green-500" />;
    case 'failed':
      return <AlertCircle className="w-4 h-4 text-red-500" />;
    default:
      return <Lock className="w-4 h-4 text-gray-400" />;
  }
}

/**
 * Get difficulty badge color
 */
function getDifficultyColor(difficulty: string): string {
  switch (difficulty) {
    case 'easy':
      return 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300';
    case 'medium':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-300';
    case 'hard':
      return 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300';
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300';
  }
}

/**
 * ConceptCardCompact - Minimal version for tight layouts
 */
export function ConceptCardCompact({ 
  concept, 
  onClick,
  className 
}: ConceptCardProps) {
  const status = (concept.content_status || 'pending') as ConceptContentStatus;
  const isClickable = status === 'completed';

  return (
    <div
      className={cn(
        'flex items-center gap-2 p-2 rounded-md transition-all duration-200',
        status === 'pending' && 'opacity-50 cursor-not-allowed',
        status === 'generating' && 'bg-blue-50/50 dark:bg-blue-900/20',
        status === 'completed' && 'hover:bg-muted cursor-pointer',
        status === 'failed' && 'opacity-60 bg-red-50/30 dark:bg-red-900/10',
        className
      )}
      onClick={() => isClickable && onClick?.()}
      role={isClickable ? 'button' : undefined}
    >
      <StatusIcon status={status} />
      <span className={cn(
        'text-sm truncate',
        status === 'completed' ? 'text-foreground' : 'text-muted-foreground'
      )}>
        {concept.name}
      </span>
    </div>
  );
}


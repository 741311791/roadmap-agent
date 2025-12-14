'use client';

import { CheckCircle2, XCircle, Loader2, RefreshCw, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ContentTypeBadge } from './content-type-badge';
import type { ConceptGenerationStatus } from '@/types/content-generation';

interface ConceptStatusCardProps {
  concept: ConceptGenerationStatus;
  onRetry?: (conceptId: string) => void;
}

/**
 * Concept 状态卡片
 * 
 * 显示单个概念的内容生成状态，包括：
 * - 概念名称
 * - 三种内容类型的状态（Tutorial/Resources/Quiz）
 * - 失败时的错误信息和重试按钮
 */
export function ConceptStatusCard({ concept, onRetry }: ConceptStatusCardProps) {
  // 判断状态
  const hasFailure =
    concept.tutorial.status === 'failed' ||
    concept.resources.status === 'failed' ||
    concept.quiz.status === 'failed';

  const allCompleted =
    concept.tutorial.status === 'completed' &&
    concept.resources.status === 'completed' &&
    concept.quiz.status === 'completed';

  const isGenerating =
    concept.tutorial.status === 'generating' ||
    concept.resources.status === 'generating' ||
    concept.quiz.status === 'generating';

  // 获取错误信息
  const errorMessage =
    concept.tutorial.error || concept.resources.error || concept.quiz.error;

  return (
    <div
      className={cn(
        'rounded-md border transition-all',
        allCompleted && 'bg-green-50/50 border-green-200',
        hasFailure && 'bg-red-50/50 border-red-200',
        isGenerating && 'bg-blue-50/30 border-blue-200',
        !allCompleted && !hasFailure && !isGenerating && 'bg-muted/30 border-border'
      )}
    >
      {/* Main Content */}
      <div className="flex items-center justify-between p-3">
        {/* Left: Concept Name & Status Icon */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {allCompleted && (
            <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0" />
          )}
          {hasFailure && (
            <XCircle className="w-4 h-4 text-red-600 shrink-0" />
          )}
          {isGenerating && (
            <Loader2 className="w-4 h-4 text-blue-600 animate-spin shrink-0" />
          )}
          {!allCompleted && !hasFailure && !isGenerating && (
            <Clock className="w-4 h-4 text-gray-400 shrink-0" />
          )}

          <span className="text-sm font-medium truncate">{concept.concept_name}</span>
        </div>

        {/* Right: Content Type Badges */}
        <div className="flex items-center gap-2 shrink-0">
          <ContentTypeBadge label="Tutorial" status={concept.tutorial.status} />
          <ContentTypeBadge label="Resources" status={concept.resources.status} />
          <ContentTypeBadge label="Quiz" status={concept.quiz.status} />

          {/* Retry Button (if failed and handler provided) */}
          {hasFailure && onRetry && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onRetry(concept.concept_id)}
              className="h-7 px-2 text-red-600 hover:text-red-700 hover:bg-red-50"
              title="Retry failed content generation"
            >
              <RefreshCw className="w-3 h-3" />
            </Button>
          )}
        </div>
      </div>

      {/* Error Message (if any) */}
      {hasFailure && errorMessage && (
        <div className="px-3 pb-3 pt-0">
          <div className="pt-2 border-t border-red-200">
            <p className="text-xs text-red-700 line-clamp-2">{errorMessage}</p>
          </div>
        </div>
      )}
    </div>
  );
}

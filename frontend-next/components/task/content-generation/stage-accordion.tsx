'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { ModuleSection } from './module-section';
import type { StageGenerationStatus } from '@/types/content-generation';

interface StageAccordionProps {
  stage: StageGenerationStatus;
  onRetry?: (conceptId: string) => void;
  defaultOpen?: boolean;
}

/**
 * Stage 折叠面板
 * 
 * 显示单个 Stage 下的所有模块和概念，支持折叠/展开
 */
export function StageAccordion({ stage, onRetry, defaultOpen = true }: StageAccordionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  // 计算进度百分比
  const progressPercentage = stage.total_concepts > 0
    ? Math.round((stage.completed_concepts / stage.total_concepts) * 100)
    : 0;

  return (
    <div className="border rounded-lg overflow-hidden transition-all">
      {/* Stage Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 bg-muted/50 hover:bg-muted/70 flex items-center justify-between transition-colors group"
      >
        {/* Left: Title & Icon */}
        <div className="flex items-center gap-3">
          {isOpen ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors" />
          )}
          <h4 className="font-medium text-left">{stage.stage_name}</h4>
        </div>

        {/* Right: Stats & Progress */}
        <div className="flex items-center gap-3">
          {/* Concepts Count */}
          <Badge variant="outline" className="bg-background">
            {stage.completed_concepts}/{stage.total_concepts} concepts
          </Badge>

          {/* Failed Count (if any) */}
          {stage.failed_concepts > 0 && (
            <Badge variant="destructive" className="bg-red-100 text-red-700 border-red-200">
              {stage.failed_concepts} failed
            </Badge>
          )}

          {/* Progress Bar */}
          <div className="flex items-center gap-2 min-w-[120px]">
            <Progress value={progressPercentage} className="h-2" />
            <span className="text-xs text-muted-foreground w-10 text-right">
              {progressPercentage}%
            </span>
          </div>
        </div>
      </button>

      {/* Modules (collapsible content) */}
      {isOpen && (
        <div className={cn(
          'p-4 space-y-3 animate-in slide-in-from-top-2 duration-200'
        )}>
          {stage.modules.map((module) => (
            <ModuleSection
              key={module.module_id}
              module={module}
              onRetry={onRetry}
            />
          ))}
        </div>
      )}
    </div>
  );
}

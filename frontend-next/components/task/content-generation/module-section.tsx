'use client';

import { ConceptStatusCard } from './concept-status-card';
import type { ModuleGenerationStatus } from '@/types/content-generation';

interface ModuleSectionProps {
  module: ModuleGenerationStatus;
  onRetry?: (conceptId: string) => void;
}

/**
 * Module 列表组件
 * 
 * 显示单个模块下的所有概念及其内容生成状态
 */
export function ModuleSection({ module, onRetry }: ModuleSectionProps) {
  return (
    <div className="border-l-2 border-sage-200 pl-4 space-y-2">
      {/* Module Header */}
      <div className="flex items-center justify-between mb-2">
        <h5 className="text-sm font-medium text-muted-foreground">
          {module.module_name}
        </h5>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {module.completed_concepts}/{module.total_concepts}
          </span>
          {module.failed_concepts > 0 && (
            <span className="text-xs text-red-600 font-medium">
              {module.failed_concepts} failed
            </span>
          )}
        </div>
      </div>

      {/* Concepts */}
      <div className="space-y-2">
        {module.concepts.map((concept) => (
          <ConceptStatusCard
            key={concept.concept_id}
            concept={concept}
            onRetry={onRetry}
          />
        ))}
      </div>
    </div>
  );
}

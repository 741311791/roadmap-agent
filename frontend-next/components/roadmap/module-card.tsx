'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, BookOpen, Target } from 'lucide-react';
import { ConceptCard } from './concept-card';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { Module } from '@/types/custom/store';

interface ModuleCardProps {
  module: Module;
  moduleNumber: number;
  onConceptClick?: (conceptId: string) => void;
  defaultExpanded?: boolean;
  className?: string;
}

/**
 * ModuleCard - Module 卡片组件
 * 
 * 功能:
 * - 折叠/展开
 * - 显示学习目标
 * - 渲染概念列表
 * - 进度统计
 */
export function ModuleCard({
  module,
  moduleNumber,
  onConceptClick,
  defaultExpanded = true,
  className
}: ModuleCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // 计算概念统计
  const totalConcepts = module.concepts?.length || 0;
  const completedConcepts = module.concepts.filter(
    c => c.content_status === 'completed'
  ).length;
  const progressPercent = totalConcepts > 0
    ? Math.round((completedConcepts / totalConcepts) * 100)
    : 0;

  // 计算总时长
  const totalHours = module.concepts.reduce(
    (acc, concept) => acc + (concept.estimated_hours || 0),
    0
  );

  return (
    <Card className={cn('border-l-4 border-l-primary/30', className)}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {/* 标题行 */}
            <div className="flex items-center gap-3 mb-2">
              <Badge variant="outline" className="shrink-0">
                模块 {moduleNumber}
              </Badge>
              <h4 className="font-semibold text-base truncate">
                {module.name}
              </h4>
            </div>

            {/* 描述 */}
            <p className="text-sm text-muted-foreground line-clamp-2">
              {module.description}
            </p>

            {/* 学习目标 */}
            {module.learning_objectives && module.learning_objectives.length > 0 && (
              <div className="mt-3 space-y-1">
                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <Target className="w-3 h-3" />
                  学习目标
                </div>
                <ul className="text-xs text-muted-foreground space-y-1 ml-5">
                  {module.learning_objectives.slice(0, isExpanded ? undefined : 2).map((objective, idx) => (
                    <li key={idx} className="list-disc">
                      {objective}
                    </li>
                  ))}
                  {!isExpanded && module.learning_objectives.length > 2 && (
                    <li className="text-primary">
                      +{module.learning_objectives.length - 2} 更多...
                    </li>
                  )}
                </ul>
              </div>
            )}
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="shrink-0"
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
        </div>

        {/* 统计信息 */}
        <div className="flex flex-wrap items-center gap-4 mt-3 text-xs">
          <div className="flex items-center gap-1.5">
            <BookOpen className="w-3 h-3 text-muted-foreground" />
            <span className="text-muted-foreground">概念:</span>
            <span className="font-medium">{totalConcepts}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground">时长:</span>
            <span className="font-medium">{totalHours.toFixed(1)}h</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground">完成:</span>
            <span className="font-medium">
              {completedConcepts}/{totalConcepts} ({progressPercent}%)
            </span>
          </div>
        </div>

        {/* 进度条 */}
        {!isExpanded && (
          <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        )}
      </CardHeader>

      {/* 概念列表 */}
      {isExpanded && (
        <CardContent className="pt-0">
          <div className="space-y-2">
            {module.concepts.map((concept) => (
              <ConceptCard
                key={concept.concept_id}
                concept={concept}
                onClick={() => onConceptClick?.(concept.concept_id)}
                showMetadata
              />
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}


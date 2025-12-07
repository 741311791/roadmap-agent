'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { ModuleCard } from './module-card';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { Stage } from '@/types/custom/store';

interface StageCardProps {
  stage: Stage;
  stageNumber: number;
  onConceptClick?: (conceptId: string) => void;
  defaultExpanded?: boolean;
  className?: string;
}

/**
 * StageCard - Stage 卡片组件
 * 
 * 功能:
 * - 折叠/展开
 * - 显示进度统计
 * - 渲染模块列表
 * - 显示预计时长
 */
export function StageCard({
  stage,
  stageNumber,
  onConceptClick,
  defaultExpanded = true,
  className
}: StageCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // 计算进度统计
  const totalConcepts = stage.modules.reduce(
    (acc, module) => acc + (module.concepts?.length || 0),
    0
  );

  const completedConcepts = stage.modules.reduce(
    (acc, module) => 
      acc + module.concepts.filter(c => c.content_status === 'completed').length,
    0
  );

  const generatingConcepts = stage.modules.reduce(
    (acc, module) => 
      acc + module.concepts.filter(c => c.content_status === 'generating').length,
    0
  );

  const failedConcepts = stage.modules.reduce(
    (acc, module) => 
      acc + module.concepts.filter(c => c.content_status === 'failed').length,
    0
  );

  const progressPercent = totalConcepts > 0 
    ? Math.round((completedConcepts / totalConcepts) * 100) 
    : 0;

  // 计算总时长
  const totalHours = stage.modules.reduce(
    (acc, module) => 
      acc + module.concepts.reduce((cAcc, concept) => 
        cAcc + (concept.estimated_hours || 0), 0
      ),
    0
  );

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <Badge variant="secondary" className="shrink-0">
                阶段 {stageNumber}
              </Badge>
              <CardTitle className="text-xl truncate">
                {stage.name}
              </CardTitle>
            </div>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {stage.description}
            </p>
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
        <div className="flex flex-wrap items-center gap-4 mt-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">模块:</span>
            <span className="font-medium">{stage.modules.length}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">概念:</span>
            <span className="font-medium">{totalConcepts}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">预计时长:</span>
            <span className="font-medium">{totalHours.toFixed(1)}h</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">进度:</span>
            <span className="font-medium">
              {completedConcepts}/{totalConcepts} ({progressPercent}%)
            </span>
          </div>
        </div>

        {/* 进度条 */}
        <div className="mt-3 space-y-2">
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* 状态指示器 */}
          {(generatingConcepts > 0 || failedConcepts > 0) && (
            <div className="flex items-center gap-4 text-xs">
              {generatingConcepts > 0 && (
                <span className="text-blue-600 dark:text-blue-400">
                  生成中: {generatingConcepts}
                </span>
              )}
              {failedConcepts > 0 && (
                <span className="text-red-600 dark:text-red-400">
                  失败: {failedConcepts}
                </span>
              )}
            </div>
          )}
        </div>
      </CardHeader>

      {/* 模块列表 */}
      {isExpanded && (
        <CardContent className="pt-0">
          <div className="space-y-4">
            {stage.modules.map((module, index) => (
              <ModuleCard
                key={module.module_id}
                module={module}
                moduleNumber={index + 1}
                onConceptClick={onConceptClick}
              />
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}


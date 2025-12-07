'use client';

import { useState } from 'react';
import { StageCard } from './stage-card';
import { Button } from '@/components/ui/button';
import { LayoutList, Network } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { RoadmapFramework } from '@/types/custom/store';

interface RoadmapViewProps {
  framework: RoadmapFramework;
  onConceptClick?: (conceptId: string) => void;
  className?: string;
}

type ViewMode = 'list' | 'flow';

/**
 * RoadmapView - 路线图整体视图
 * 
 * 功能:
 * - Supports Knowledge Outline and Knowledge Graph (placeholder)
 * - 视图切换
 * - 渲染所有 Stage
 * - 统计信息展示
 */
export function RoadmapView({
  framework,
  onConceptClick,
  className
}: RoadmapViewProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('list');

  // 计算统计信息
  const stats = {
    totalStages: framework.stages?.length || 0,
    totalModules: framework.stages?.reduce((acc, stage) => acc + (stage.modules?.length || 0), 0) || 0,
    totalConcepts: framework.stages?.reduce((acc, stage) => 
      acc + stage.modules.reduce((mAcc, module) => 
        mAcc + (module.concepts?.length || 0), 0
      ), 0
    ) || 0,
    totalHours: framework.total_estimated_hours || 0,
    weeks: framework.recommended_completion_weeks || 0
  };

  return (
    <div className={cn('space-y-6', className)}>
      {/* 头部统计和视图切换 */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 bg-card rounded-lg border">
        {/* 统计信息 */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 text-sm">
          <div>
            <div className="text-muted-foreground">阶段</div>
            <div className="text-lg font-semibold">{stats.totalStages}</div>
          </div>
          <div>
            <div className="text-muted-foreground">模块</div>
            <div className="text-lg font-semibold">{stats.totalModules}</div>
          </div>
          <div>
            <div className="text-muted-foreground">概念</div>
            <div className="text-lg font-semibold">{stats.totalConcepts}</div>
          </div>
          <div>
            <div className="text-muted-foreground">总时长</div>
            <div className="text-lg font-semibold">{stats.totalHours}h</div>
          </div>
          <div>
            <div className="text-muted-foreground">建议周期</div>
            <div className="text-lg font-semibold">{stats.weeks}周</div>
          </div>
        </div>

        {/* 视图切换 */}
        <div className="flex items-center gap-2">
          <Button
            variant={viewMode === 'list' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('list')}
            className="flex items-center gap-2"
          >
            <LayoutList className="w-4 h-4" />
            Knowledge Outline
          </Button>
          <Button
            variant={viewMode === 'flow' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('flow')}
            className="flex items-center gap-2"
          >
            <Network className="w-4 h-4" />
            Knowledge Graph (coming soon)
          </Button>
        </div>
      </div>

      {/* 内容区域 */}
      {viewMode === 'list' ? (
        <ListView framework={framework} onConceptClick={onConceptClick} />
      ) : (
        <FlowView framework={framework} onConceptClick={onConceptClick} />
      )}
    </div>
  );
}

/**
 * ListView - Knowledge Outline
 */
function ListView({
  framework,
  onConceptClick
}: {
  framework: RoadmapFramework;
  onConceptClick?: (conceptId: string) => void;
}) {
  if (!framework.stages || framework.stages.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        暂无路线图内容
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {framework.stages.map((stage, index) => (
        <StageCard
          key={stage.stage_id}
          stage={stage}
          stageNumber={index + 1}
          onConceptClick={onConceptClick}
        />
      ))}
    </div>
  );
}

/**
 * FlowView - Knowledge Graph (placeholder, coming soon)
 * TODO: 使用 reactflow 或其他图形库实现完整的 Knowledge Graph 视图
 */
function FlowView({
  framework,
  onConceptClick
}: {
  framework: RoadmapFramework;
  onConceptClick?: (conceptId: string) => void;
}) {
  return (
    <div className="p-12 bg-muted/30 rounded-lg border-2 border-dashed text-center">
      <Network className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
      <h3 className="text-lg font-semibold mb-2">Knowledge Graph</h3>
      <p className="text-muted-foreground">
        Knowledge Graph view is under development. Please use Knowledge Outline.
      </p>
      <Button
        variant="outline"
        className="mt-4"
        onClick={() => {
          // 这里可以触发视图切换回列表模式
        }}
      >
        Back to Knowledge Outline
      </Button>
    </div>
  );
}


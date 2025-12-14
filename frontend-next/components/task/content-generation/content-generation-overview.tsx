'use client';

import { useState, useMemo } from 'react';
import { RefreshCw, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { StageAccordion } from './stage-accordion';
import { parseContentGenerationStatus, formatRelativeTime } from '@/lib/utils/parse-content-status';
import { getTaskLogs } from '@/lib/api/endpoints';
import { useRoadmap } from '@/lib/hooks/api';
import type { ExecutionLog } from '@/types/content-generation';

interface ContentGenerationOverviewProps {
  taskId: string;
  roadmapId: string;
  initialLogs: ExecutionLog[];
  onRetry?: (conceptId: string) => void;
  onShowAllLogs?: () => void;
}

/**
 * Content Generation 概览组件
 * 
 * 显示整个路线图的内容生成状态，按照 Stage -> Module -> Concept 三层结构组织
 * 
 * 特性：
 * - 分层展示内容生成状态
 * - 手动刷新按钮
 * - 统计信息和进度条
 * - 支持重试失败的概念
 */
export function ContentGenerationOverview({
  taskId,
  roadmapId,
  initialLogs,
  onRetry,
  onShowAllLogs,
}: ContentGenerationOverviewProps) {
  const [logs, setLogs] = useState<ExecutionLog[]>(initialLogs);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  // 获取路线图框架
  const { data: roadmap, isLoading: isLoadingRoadmap } = useRoadmap(roadmapId);

  // 解析内容生成状态
  const overview = useMemo(() => {
    if (!roadmap) return null;
    return parseContentGenerationStatus(logs, roadmap);
  }, [logs, roadmap]);

  // 刷新状态
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      const logsData = await getTaskLogs(taskId);
      setLogs(logsData.logs || []);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to refresh logs:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  // 加载状态
  if (isLoadingRoadmap) {
    return (
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-serif font-semibold">Content Generation Overview</h2>
          </div>
          {onShowAllLogs && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onShowAllLogs}
              className="text-sm text-sage-600 hover:text-sage-700 hover:underline"
            >
              ← Show All Logs
            </Button>
          )}
        </div>
        
        {/* Loading Card */}
        <Card className="p-6">
          <div className="flex items-center justify-center py-12">
            <div className="text-center space-y-3">
              <Loader2 className="w-8 h-8 animate-spin text-sage-600 mx-auto" />
              <p className="text-sm text-muted-foreground">Loading roadmap data...</p>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  // 数据未就绪
  if (!overview) {
    return (
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-serif font-semibold">Content Generation Overview</h2>
          </div>
          {onShowAllLogs && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onShowAllLogs}
              className="text-sm text-sage-600 hover:text-sage-700 hover:underline"
            >
              ← Show All Logs
            </Button>
          )}
        </div>
        
        {/* Error Card */}
        <Card className="p-6">
          <div className="text-center py-12">
            <p className="text-sm text-muted-foreground">
              Unable to load content generation overview
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header - 在卡片外部，与其他阶段保持一致 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-serif font-semibold">Content Generation Overview</h2>
          <Badge variant="outline" className="text-xs">
            {overview.completed_concepts}/{overview.total_concepts} concepts
          </Badge>
          {overview.failed_concepts > 0 && (
            <Badge variant="destructive" className="text-xs">
              {overview.failed_concepts} failed
            </Badge>
          )}
        </div>
        {onShowAllLogs && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onShowAllLogs}
            className="text-sm text-sage-600 hover:text-sage-700 hover:underline"
          >
            ← Show All Logs
          </Button>
        )}
      </div>

      {/* Content Card */}
      <Card className="p-6 space-y-6">
        {/* Overall Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Overall Progress</span>
            <span className="font-medium">{overview.progress_percentage}%</span>
          </div>
          <Progress value={overview.progress_percentage} className="h-2" />
        </div>

        {/* Refresh Button */}
        <div className="flex justify-end">
          <Button
            onClick={handleRefresh}
            disabled={isRefreshing}
            variant="outline"
            size="sm"
          >
            {isRefreshing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Refreshing...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh Status
              </>
            )}
          </Button>
        </div>

        {/* Stages */}
        <div className="space-y-3">
          {overview.stages.map((stage, index) => (
            <StageAccordion
              key={stage.stage_id}
              stage={stage}
              onRetry={onRetry}
              defaultOpen={index === 0 || stage.failed_concepts > 0}
            />
          ))}
        </div>

        {/* Last Updated */}
        <div className="pt-4 border-t text-xs text-muted-foreground text-right">
          Last updated: {formatRelativeTime(lastUpdated)}
        </div>
      </Card>
    </div>
  );
}

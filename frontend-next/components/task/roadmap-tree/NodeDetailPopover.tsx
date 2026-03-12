'use client';

/**
 * NodeDetailPopover - 节点详情弹出层
 * 
 * 点击节点时显示详细信息
 */

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { X, Clock, BookOpen, Layers, Box, RefreshCw, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { TreeNodeData, TreeNodeType, TreeNodeStatus, NodeDetailPopoverProps } from './types';
import type { Concept, Module, Stage } from '@/types/generated/models';
import { contentApi, type RetryContentRequest } from '@/lib/api/endpoints';
import { TaskWebSocket } from '@/lib/api/websocket';

// Props 类型已在 types.ts 中定义，这里不再重复定义

/**
 * 获取节点类型图标
 */
function getTypeIcon(type: TreeNodeType) {
  switch (type) {
    case 'stage':
      return <Layers className="w-4 h-4" />;
    case 'module':
      return <BookOpen className="w-4 h-4" />;
    case 'concept':
      return <Box className="w-4 h-4" />;
  }
}

/**
 * 获取节点类型标签
 */
function getTypeLabel(type: TreeNodeType, t: ReturnType<typeof useTranslations>): string {
  switch (type) {
    case 'start':
      return t('nodeDetail.typeStart');
    case 'stage':
      return t('nodeDetail.typeStage');
    case 'module':
      return t('nodeDetail.typeModule');
    case 'concept':
      return t('nodeDetail.typeConcept');
    default:
      return t('nodeDetail.typeUnknown');
  }
}

/**
 * 获取状态标签配置
 */
function getStatusBadge(
  status: TreeNodeStatus,
  t: ReturnType<typeof useTranslations>,
): { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' } {
  switch (status) {
    case 'completed':
      return { label: t('nodeDetail.statusCompleted'), variant: 'default' };
    case 'loading':
      return { label: t('nodeDetail.statusGenerating'), variant: 'secondary' };
    case 'failed':
      return { label: t('nodeDetail.statusFailed'), variant: 'destructive' };
    case 'partial_failure':
      return { label: t('nodeDetail.statusPartialFailure'), variant: 'outline' };
    case 'modified':
      return { label: t('nodeDetail.statusModified'), variant: 'outline' };
    case 'pending':
    default:
      return { label: t('nodeDetail.statusPending'), variant: 'outline' };
  }
}

export function NodeDetailPopover({
  node,
  isOpen,
  onClose,
  anchorPosition,
  roadmapId,
  failedContentTypesMap,
  taskStatus,
  onRetrySuccess,
}: NodeDetailPopoverProps) {
  const t = useTranslations('taskDetail');
  const popoverRef = useRef<HTMLDivElement>(null);
  const [isRetrying, setIsRetrying] = useState<string | null>(null); // 正在重试的内容类型
  const wsRef = useRef<TaskWebSocket | null>(null);
  
  // 点击外部关闭
  useEffect(() => {
    if (!isOpen) return;
    
    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    
    // 延迟添加监听，避免立即触发
    const timer = setTimeout(() => {
      document.addEventListener('click', handleClickOutside);
    }, 100);
    
    return () => {
      clearTimeout(timer);
      document.removeEventListener('click', handleClickOutside);
    };
  }, [isOpen, onClose]);

  // 组件销毁时清理 WebSocket 连接
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
        wsRef.current = null;
      }
    };
  }, []);
  
  // ESC 关闭
  useEffect(() => {
    if (!isOpen) return;
    
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    
    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  if (!isOpen || !node) return null;
  
  const statusBadge = getStatusBadge(node.status, t);
  
  // 计算弹出位置（在节点右侧或下方）
  const popoverStyle: React.CSSProperties = {
    position: 'fixed',
    zIndex: 60,
  };

  if (anchorPosition) {
    const rightSideLeft = anchorPosition.x + anchorPosition.width + 12;
    const estimatedWidth = 360;
    const estimatedHeight = 420;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // 优先显示在节点右侧，右侧空间不足时自动翻转到左侧
    const nextLeft = rightSideLeft + estimatedWidth > viewportWidth - 16
      ? Math.max(16, anchorPosition.x - estimatedWidth - 12)
      : rightSideLeft;
    const nextTop = Math.min(
      Math.max(16, anchorPosition.y),
      Math.max(16, viewportHeight - estimatedHeight - 16),
    );

    popoverStyle.left = nextLeft;
    popoverStyle.top = nextTop;
  }
  
  // 获取原始数据中的额外信息
  const originalData = node.originalData;
  const conceptData = node.type === 'concept' ? originalData as Concept : null;
  const moduleData = node.type === 'module' ? originalData as Module : null;
  const stageData = node.type === 'stage' ? originalData as Stage : null;

  /**
   * 检查 Concept 是否有失败的内容类型
   */
  const getFailedContentTypes = (concept: Concept): Array<'tutorial' | 'resources' | 'quiz'> => {
    const failed: Array<'tutorial' | 'resources' | 'quiz'> = [];
    if (concept.content_status === 'failed') failed.push('tutorial');
    if (concept.resources_status === 'failed') failed.push('resources');
    if (concept.quiz_status === 'failed') failed.push('quiz');
    return failed;
  };

  /**
   * 获取 Concept 三类内容状态
   */
  const getContentStatuses = (concept: Concept): Array<{
    key: 'tutorial' | 'resources' | 'quiz';
    label: string;
    status: string | null | undefined;
  }> => {
    return [
      { key: 'tutorial', label: t('nodeDetail.contentTypeTutorial'), status: concept.content_status },
      { key: 'resources', label: t('nodeDetail.contentTypeResources'), status: concept.resources_status },
      { key: 'quiz', label: t('nodeDetail.contentTypeQuiz'), status: concept.quiz_status },
    ];
  };

  const getContentTypeLabel = (contentType: 'tutorial' | 'resources' | 'quiz'): string => {
    switch (contentType) {
      case 'tutorial':
        return t('nodeDetail.contentTypeTutorial');
      case 'resources':
        return t('nodeDetail.contentTypeResources');
      case 'quiz':
      default:
        return t('nodeDetail.contentTypeQuiz');
    }
  };

  const getContentStatusLabel = (status: string | null | undefined): string => {
    switch (status) {
      case 'completed':
        return t('nodeDetail.statusCompleted');
      case 'failed':
        return t('nodeDetail.statusFailed');
      case 'generating':
        return t('nodeDetail.statusGenerating');
      case 'pending':
      default:
        return t('nodeDetail.statusPending');
    }
  };

  /**
   * 处理重试操作
   */
  const handleRetry = async (contentType: 'tutorial' | 'resources' | 'quiz') => {
    if (!conceptData || !roadmapId) {
      console.warn('[NodeDetailPopover] Missing required data for retry:', { conceptData, roadmapId });
      return;
    }

    setIsRetrying(contentType);

    try {
      const request: RetryContentRequest = {};

      let response: Awaited<ReturnType<typeof contentApi.regenerateTutorial>> | undefined;
      switch (contentType) {
        case 'tutorial':
          response = await contentApi.regenerateTutorial(roadmapId, conceptData.concept_id, request);
          break;
        case 'resources':
          response = await contentApi.regenerateResources(roadmapId, conceptData.concept_id, request);
          break;
        case 'quiz':
          response = await contentApi.regenerateQuiz(roadmapId, conceptData.concept_id, request);
          break;
      }

      if (response && response.success) {
        // 后端返回 task_id 时，订阅该重试任务的 WebSocket 事件，确保前端实时更新
        const retryTaskId = (response.data as { task_id?: string } | null | undefined)?.task_id;
        if (retryTaskId) {
          if (wsRef.current) {
            wsRef.current.disconnect();
            wsRef.current = null;
          }

          const currentConceptId = conceptData.concept_id;
          const retryWs = new TaskWebSocket(retryTaskId, {
            onConceptComplete: (event) => {
              // 仅处理本次重试对应的 concept + content_type
              if (event.concept_id !== currentConceptId || event.content_type !== contentType) return;
              setIsRetrying(null);
              onRetrySuccess?.();
              retryWs.disconnect();
              if (wsRef.current === retryWs) {
                wsRef.current = null;
              }
            },
            onConceptFailed: (event) => {
              if (event.concept_id !== currentConceptId || event.content_type !== contentType) return;
              console.error(`[NodeDetailPopover] Retry ${contentType} failed via WebSocket:`, event.error);
              setIsRetrying(null);
              retryWs.disconnect();
              if (wsRef.current === retryWs) {
                wsRef.current = null;
              }
            },
            onStatus: (event) => {
              // 兜底：若错过 concept 事件，仍可从 current_status 感知最终状态
              if (event.status === 'completed') {
                setIsRetrying(null);
                onRetrySuccess?.();
                retryWs.disconnect();
                if (wsRef.current === retryWs) {
                  wsRef.current = null;
                }
              } else if (event.status === 'failed') {
                setIsRetrying(null);
                retryWs.disconnect();
                if (wsRef.current === retryWs) {
                  wsRef.current = null;
                }
              }
            },
          });

          retryWs.connect(true);
          wsRef.current = retryWs;
          return;
        }

        // 未返回 task_id 的向后兼容分支
        console.log(`[NodeDetailPopover] ${contentType} regenerate succeeded without task_id`, response);
        setIsRetrying(null);
        onRetrySuccess?.();
      } else {
        setIsRetrying(null);
        throw new Error(response.message || '重新生成失败');
      }
    } catch (error) {
      console.error(`[NodeDetailPopover] Failed to retry ${contentType}:`, error);
      setIsRetrying(null);
    }
  };

  // 检查是否有失败的内容需要重试
  const failedContentTypes = conceptData ? getFailedContentTypes(conceptData) : [];
  const failedContentTypesFromMap = conceptData
    ? (failedContentTypesMap?.[conceptData.concept_id] || [])
    : [];
  const effectiveFailedContentTypes = Array.from(new Set([
    ...failedContentTypes,
    ...failedContentTypesFromMap,
  ]));

  const conceptContentStatuses = conceptData
    ? getContentStatuses(conceptData).map((item) => {
        const mappedFailed = failedContentTypesFromMap.includes(item.key);
        const normalizedStatus = item.status ?? 'pending';
        // 如果后端状态暂未落库，但 WS 已明确该类型失败，则以前端实时状态为准
        return {
          ...item,
          status: mappedFailed && normalizedStatus !== 'completed' ? 'failed' : normalizedStatus,
        };
      })
    : [];

  const pendingContentTypesInCompletedTask = conceptData && (
    taskStatus === 'completed' ||
    taskStatus === 'partial_failure' ||
    taskStatus === 'failed'
  )
    ? conceptContentStatuses
        .filter((item) => item.status === 'pending')
        .map((item) => item.key)
    : [];

  const retryableContentTypes = Array.from(new Set([
    ...effectiveFailedContentTypes,
    ...pendingContentTypesInCompletedTask,
  ]));

  const canRetry = conceptData && roadmapId && retryableContentTypes.length > 0;
  
  return (
    <div
      ref={popoverRef}
      className={cn(
        'bg-white rounded-lg shadow-xl border border-gray-200',
        'min-w-[280px] max-w-[360px]',
        'animate-in fade-in-0 zoom-in-95 duration-200',
      )}
      style={popoverStyle}
    >
      {/* Header */}
      <div className="flex items-start justify-between p-3 border-b">
        <div className="flex items-center gap-2">
          <span className="text-sage-600">{getTypeIcon(node.type)}</span>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground uppercase tracking-wide">
                {getTypeLabel(node.type, t)}
              </span>
              {node.isModified && (
                <Badge variant="outline" className="text-[10px] h-4 px-1 border-cyan-300 text-cyan-600">
                  {t('nodeDetail.statusModified')}
                </Badge>
              )}
            </div>
            <h4 className="font-semibold text-sm">{node.name}</h4>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0"
          onClick={onClose}
        >
          <X className="w-4 h-4" />
        </Button>
      </div>
      
      {/* Content */}
      <div className="p-3 space-y-3">
        {/* Description */}
        <p className="text-sm text-muted-foreground leading-relaxed">
          {node.description}
        </p>
        
        {/* Status Badge */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">{t('nodeDetail.labelStatus')}:</span>
          <Badge
            variant={statusBadge.variant}
            className={cn(
              'text-xs',
              node.status === 'completed' && 'bg-sage-100 text-sage-700 border-sage-300',
              node.status === 'modified' && 'bg-cyan-50 text-cyan-700 border-cyan-300',
            )}
          >
            {statusBadge.label}
          </Badge>
        </div>
        
        {/* Estimated Time */}
        {node.estimatedHours !== undefined && (
          <div className="flex items-center gap-2 text-sm">
            <Clock className="w-4 h-4 text-muted-foreground" />
            <span className="text-muted-foreground">{t('nodeDetail.labelEstimated')}:</span>
            <span className="font-medium">{node.estimatedHours}h</span>
          </div>
        )}
        
        {/* Concept 额外信息 */}
        {conceptData && (
          <div className="pt-2 border-t space-y-2">
            {/* Difficulty */}
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground">Difficulty:</span>
              <span className="text-muted-foreground">{t('nodeDetail.labelDifficulty')}:</span>
              <Badge variant="outline" className="text-xs capitalize">
                {conceptData.difficulty}
              </Badge>
            </div>
            
            {/* Keywords */}
            {conceptData.keywords && conceptData.keywords.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {conceptData.keywords.slice(0, 5).map((keyword, i) => (
                  <Badge
                    key={i}
                    variant="secondary"
                    className="text-[10px] h-5 px-1.5"
                  >
                    {keyword}
                  </Badge>
                ))}
                {conceptData.keywords.length > 5 && (
                  <span className="text-[10px] text-muted-foreground">
                    {t('nodeDetail.moreKeywords', { count: conceptData.keywords.length - 5 })}
                  </span>
                )}
              </div>
            )}

            {/* 内容生成状态（用于精确显示失败类型） */}
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">{t('nodeDetail.contentStatus')}:</p>
              <div className="flex flex-wrap gap-1.5">
                {conceptContentStatuses.map((item) => {
                  const normalizedStatus = item.status ?? 'pending';
                  const isFailed = normalizedStatus === 'failed';
                  const isCompleted = normalizedStatus === 'completed';
                  const isGenerating = normalizedStatus === 'pending';

                  return (
                    <Badge
                      key={item.key}
                      variant="outline"
                      className={cn(
                        'text-[10px] h-5 px-1.5 capitalize',
                        isFailed && 'border-red-300 text-red-700 bg-red-50',
                        isCompleted && 'border-emerald-300 text-emerald-700 bg-emerald-50',
                        isGenerating && 'border-amber-300 text-amber-700 bg-amber-50',
                      )}
                    >
                      {item.label}: {getContentStatusLabel(normalizedStatus)}
                    </Badge>
                  );
                })}
              </div>
            </div>
          </div>
        )}
        
        {/* Module 额外信息 */}
        {moduleData && (moduleData as any).learning_objectives && (moduleData as any).learning_objectives.length > 0 && (
          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground mb-1">{t('nodeDetail.learningObjectives')}:</p>
            <ul className="text-xs space-y-0.5 pl-3">
              {(moduleData as any).learning_objectives.slice(0, 3).map((obj: string, i: number) => (
                <li key={i} className="text-muted-foreground list-disc">
                  {obj}
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* 子节点统计 */}
        {node.children && node.children.length > 0 && (
          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground">
              {t('nodeDetail.contains', {
                count: node.children.length,
                unit: node.type === 'stage' ? t('nodeDetail.typeModule').toLowerCase() : t('nodeDetail.typeConcept').toLowerCase(),
              })}
            </p>
          </div>
        )}

        {/* 重试按钮区域 - 仅对失败的 Concept 节点显示 */}
        {canRetry && (
          <div className="pt-2 border-t space-y-2">
            <p className="text-xs font-medium text-muted-foreground">{t('nodeDetail.failedContent')}:</p>
            <div className="flex flex-col gap-1.5">
              {retryableContentTypes.map((contentType) => (
                <Button
                  key={contentType}
                  variant="outline"
                  size="sm"
                  onClick={() => handleRetry(contentType)}
                  disabled={isRetrying !== null}
                  className={cn(
                    'h-7 text-xs justify-start',
                    contentType === 'tutorial' && 'border-red-200 text-red-700 hover:bg-red-50',
                    contentType === 'resources' && 'border-red-200 text-red-700 hover:bg-red-50',
                    contentType === 'quiz' && 'border-red-200 text-red-700 hover:bg-red-50',
                  )}
                >
                  {isRetrying === contentType ? (
                    <>
                      <Loader2 className="w-3 h-3 mr-2 animate-spin" />
                      {t('nodeDetail.retrying')}
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-3 h-3 mr-2" />
                      {t('nodeDetail.retry')} {getContentTypeLabel(contentType)}
                    </>
                  )}
                </Button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


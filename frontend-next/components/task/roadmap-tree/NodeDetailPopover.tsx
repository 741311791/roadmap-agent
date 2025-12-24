'use client';

/**
 * NodeDetailPopover - 节点详情弹出层
 * 
 * 点击节点时显示详细信息
 */

import { useEffect, useRef } from 'react';
import { X, Clock, BookOpen, Layers, Box } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { TreeNodeData, TreeNodeType, TreeNodeStatus } from './types';
import type { Concept, Module, Stage } from '@/types/generated/models';

interface NodeDetailPopoverProps {
  node: TreeNodeData | null;
  isOpen: boolean;
  onClose: () => void;
  /** 锚点位置（节点位置） */
  anchorPosition?: { x: number; y: number };
  /** 容器边界（用于计算弹出方向） */
  containerRect?: DOMRect;
}

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
function getTypeLabel(type: TreeNodeType): string {
  switch (type) {
    case 'start':
      return 'Start';
    case 'stage':
      return 'Stage';
    case 'module':
      return 'Module';
    case 'concept':
      return 'Concept';
    default:
      return 'Unknown';
  }
}

/**
 * 获取状态标签配置
 */
function getStatusBadge(status: TreeNodeStatus): { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' } {
  switch (status) {
    case 'completed':
      return { label: 'Completed', variant: 'default' };
    case 'loading':
      return { label: 'Generating...', variant: 'secondary' };
    case 'failed':
      return { label: 'Failed', variant: 'destructive' };
    case 'partial_failure':
      return { label: 'Partial Failure', variant: 'outline' };
    case 'modified':
      return { label: 'Modified', variant: 'outline' };
    case 'pending':
    default:
      return { label: 'Pending', variant: 'outline' };
  }
}

export function NodeDetailPopover({
  node,
  isOpen,
  onClose,
  anchorPosition,
  containerRect,
}: NodeDetailPopoverProps) {
  const popoverRef = useRef<HTMLDivElement>(null);
  
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
  
  const statusBadge = getStatusBadge(node.status);
  
  // 计算弹出位置（在节点右侧或下方）
  const popoverStyle: React.CSSProperties = {
    position: 'absolute',
    zIndex: 50,
  };
  
  if (anchorPosition) {
    popoverStyle.left = anchorPosition.x + (node.position?.width ?? 0) + 12;
    popoverStyle.top = anchorPosition.y;
  }
  
  // 获取原始数据中的额外信息
  const originalData = node.originalData;
  const conceptData = node.type === 'concept' ? originalData as Concept : null;
  const moduleData = node.type === 'module' ? originalData as Module : null;
  const stageData = node.type === 'stage' ? originalData as Stage : null;
  
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
                {getTypeLabel(node.type)}
              </span>
              {node.isModified && (
                <Badge variant="outline" className="text-[10px] h-4 px-1 border-cyan-300 text-cyan-600">
                  Modified
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
          <span className="text-xs text-muted-foreground">Status:</span>
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
            <span className="text-muted-foreground">Estimated:</span>
            <span className="font-medium">{node.estimatedHours}h</span>
          </div>
        )}
        
        {/* Concept 额外信息 */}
        {conceptData && (
          <div className="pt-2 border-t space-y-2">
            {/* Difficulty */}
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground">Difficulty:</span>
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
                    +{conceptData.keywords.length - 5} more
                  </span>
                )}
              </div>
            )}
          </div>
        )}
        
        {/* Module 额外信息 */}
        {moduleData && moduleData.learning_objectives && moduleData.learning_objectives.length > 0 && (
          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground mb-1">Learning Objectives:</p>
            <ul className="text-xs space-y-0.5 pl-3">
              {moduleData.learning_objectives.slice(0, 3).map((obj, i) => (
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
              Contains {node.children.length} {node.type === 'stage' ? 'modules' : 'concepts'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}


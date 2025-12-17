'use client';

/**
 * TreeNode - 树节点组件
 * 
 * 胶囊/徽章样式的节点，支持不同类型和状态
 */

import { ChevronRight, ChevronDown, Check, Loader2, AlertTriangle, XCircle, Sparkles } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { TreeNodeData, TreeNodeProps, TreeNodeStatus, TreeNodeType, calculateNodeProgress } from './types';

/**
 * 获取节点状态样式配置
 */
function getStatusStyles(status: TreeNodeStatus): {
  border: string;
  bg: string;
  text: string;
  icon: React.ReactNode;
} {
  switch (status) {
    case 'completed':
      return {
        border: 'border-sage-500',
        bg: 'bg-sage-50',
        text: 'text-sage-700',
        icon: <Check className="w-3.5 h-3.5 text-sage-600" />,
      };
    case 'loading':
      return {
        border: 'border-sage-400 animate-pulse',
        bg: 'bg-sage-50/50',
        text: 'text-sage-600',
        icon: <Loader2 className="w-3.5 h-3.5 text-sage-500 animate-spin" />,
      };
    case 'failed':
      return {
        border: 'border-red-400',
        bg: 'bg-red-50',
        text: 'text-red-700',
        icon: <XCircle className="w-3.5 h-3.5 text-red-500" />,
      };
    case 'partial_failure':
      return {
        border: 'border-amber-400',
        bg: 'bg-amber-50',
        text: 'text-amber-700',
        icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />,
      };
    case 'modified':
      return {
        border: 'border-cyan-400',
        bg: 'bg-cyan-50',
        text: 'text-cyan-700',
        icon: <Sparkles className="w-3.5 h-3.5 text-cyan-500" />,
      };
    case 'pending':
    default:
      return {
        border: 'border-gray-300',
        bg: 'bg-gray-50',
        text: 'text-gray-600',
        icon: null,
      };
  }
}

/**
 * 获取节点类型样式配置
 */
function getTypeStyles(type: TreeNodeType): {
  fontSize: string;
  fontWeight: string;
  padding: string;
} {
  switch (type) {
    case 'start':
      return {
        fontSize: 'text-sm',
        fontWeight: 'font-medium',
        padding: 'px-3 py-1.5',
      };
    case 'stage':
      return {
        fontSize: 'text-sm',
        fontWeight: 'font-semibold',
        padding: 'px-3 py-1.5',
      };
    case 'module':
      return {
        fontSize: 'text-xs',
        fontWeight: 'font-medium',
        padding: 'px-2.5 py-1',
      };
    case 'concept':
      return {
        fontSize: 'text-xs',
        fontWeight: 'font-normal',
        padding: 'px-2 py-1',
      };
  }
}

export function TreeNode({
  node,
  onToggleExpand,
  onClick,
  isSelected,
}: TreeNodeProps) {
  const statusStyles = getStatusStyles(node.status);
  const typeStyles = getTypeStyles(node.type);
  
  const hasChildren = node.children && node.children.length > 0;
  const canExpand = hasChildren && node.type !== 'concept';
  
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onClick?.(node);
  };
  
  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (canExpand) {
      onToggleExpand?.(node.id);
    }
  };
  
  return (
    <TooltipProvider delayDuration={300}>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              // 基础样式 - 胶囊形状
              'absolute flex items-center gap-1.5 rounded-full border-2 cursor-pointer',
              'transition-all duration-200 ease-out',
              'hover:shadow-md hover:scale-105',
              'select-none whitespace-nowrap',
              // 状态样式
              statusStyles.border,
              statusStyles.bg,
              statusStyles.text,
              // 类型样式
              typeStyles.fontSize,
              typeStyles.fontWeight,
              typeStyles.padding,
              // 选中样式
              isSelected && 'ring-2 ring-sage-400 ring-offset-2',
            )}
            style={{
              left: node.position?.x ?? 0,
              top: node.position?.y ?? 0,
              minWidth: node.position?.width ?? 'auto',
              height: node.position?.height ?? 'auto',
            }}
            onClick={handleClick}
          >
            {/* 展开/折叠按钮 */}
            {canExpand && (
              <button
                onClick={handleToggle}
                className={cn(
                  'flex items-center justify-center w-5 h-5 -ml-0.5',
                  'rounded-full transition-all duration-200',
                  'hover:bg-sage-200/60 hover:scale-110',
                  'border border-transparent hover:border-sage-300',
                )}
              >
                {node.isExpanded ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </button>
            )}
            
            {/* 状态图标 */}
            {statusStyles.icon && (
              <span className="flex-shrink-0">{statusStyles.icon}</span>
            )}
            
            {/* 节点名称 - 完整显示，不截断 */}
            <span className="whitespace-nowrap">
              {node.name}
            </span>
            
            {/* 子节点数量和进度提示（收起时显示） */}
            {canExpand && !node.isExpanded && hasChildren && (
              <Badge 
                variant="outline" 
                className={cn(
                  "text-[10px] h-4 px-1.5 ml-1 font-medium border-current/30",
                  // 根据进度显示不同颜色
                  calculateNodeProgress(node.children) === 100 && "bg-sage-100 text-sage-700 border-sage-300",
                  calculateNodeProgress(node.children) > 0 && calculateNodeProgress(node.children) < 100 && "bg-amber-50 text-amber-700 border-amber-300",
                  calculateNodeProgress(node.children) === 0 && "bg-gray-100 text-gray-600 border-gray-300"
                )}
              >
                {calculateNodeProgress(node.children)}% · +{node.children!.length}
              </Badge>
            )}
          </div>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs z-50">
          <div className="space-y-1.5">
            <p className="font-medium text-sm">{node.name}</p>
            {node.description && (
              <p className="text-xs text-muted-foreground leading-relaxed">{node.description}</p>
            )}
            <div className="flex items-center gap-3 text-xs pt-1 border-t">
              {node.estimatedHours && (
                <span className="flex items-center gap-1">
                  ⏱️ ~{node.estimatedHours}h
                </span>
              )}
              {hasChildren && (
                <span className="flex items-center gap-1">
                  📦 {node.children!.length} {node.type === 'stage' ? 'modules' : 'items'}
                </span>
              )}
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}


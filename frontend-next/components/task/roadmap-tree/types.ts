/**
 * Roadmap Tree 组件类型定义
 * 
 * 用于水平树状图的类型系统
 */

import type { Stage, Module, Concept, ContentStatus } from '@/types/generated/models';

// ============================================================
// 节点状态枚举
// ============================================================

/**
 * 树节点状态
 * 
 * - pending: 等待处理（灰色）
 * - loading: 正在加载（动画边框）
 * - completed: 已完成（sage 绿色）
 * - partial_failure: 部分失败（amber 橙色）
 * - failed: 失败（红色）
 * - modified: 已修改（cyan 青色，永久标注）
 */
export type TreeNodeStatus = 
  | 'pending'
  | 'loading'
  | 'completed'
  | 'partial_failure'
  | 'failed'
  | 'modified';

/**
 * 树节点类型
 */
export type TreeNodeType = 'start' | 'stage' | 'module' | 'concept';

// ============================================================
// 布局相关类型
// ============================================================

/**
 * 节点位置信息
 */
export interface NodePosition {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * 连接线信息
 */
export interface ConnectionLine {
  id: string;
  fromNodeId: string;
  toNodeId: string;
  fromPosition: { x: number; y: number };
  toPosition: { x: number; y: number };
}

// ============================================================
// 树节点数据类型
// ============================================================

/**
 * 统一的树节点数据结构
 */
export interface TreeNodeData {
  id: string;
  type: TreeNodeType;
  name: string;
  description: string;
  status: TreeNodeStatus;
  
  /** 预估时间（小时） */
  estimatedHours?: number;
  
  /** 子节点 */
  children?: TreeNodeData[];
  
  /** 是否展开（仅 stage/module 有效） */
  isExpanded?: boolean;
  
  /** 是否被修改过（用于 cyan 标注） */
  isModified?: boolean;
  
  /** 原始数据引用 */
  originalData?: Stage | Module | Concept;
  
  /** 节点位置（由布局算法计算） */
  position?: NodePosition;
}

/**
 * 展开状态映射
 * key: nodeId, value: isExpanded
 */
export type ExpansionState = Record<string, boolean>;

// ============================================================
// 组件 Props 类型
// ============================================================

/**
 * RoadmapTree 主组件 Props
 */
export interface RoadmapTreeProps {
  /** 路线图框架数据 */
  stages: Stage[];
  
  /** 是否显示起始节点 */
  showStartNode?: boolean;
  
  /** 当前编辑模式（显示蒙版加载动画） */
  isEditing?: boolean;
  
  /** 任务 ID（用于获取验证结果） */
  taskId?: string;
  
  /** 路线图 ID（用于获取历史版本） */
  roadmapId?: string | null;
  
  /** 是否显示历史版本按钮 */
  showHistoryButton?: boolean;
  
  /** 修改过的节点 ID 列表 */
  modifiedNodeIds?: string[];
  
  /** 内容生成中的 Concept ID 列表 */
  loadingConceptIds?: string[];
  
  /** 失败的 Concept ID 列表 */
  failedConceptIds?: string[];
  
  /** 部分失败的 Concept ID 列表 */
  partialFailedConceptIds?: string[];
  
  /** 节点点击回调 */
  onNodeClick?: (node: TreeNodeData) => void;
  
  /** 用户学习偏好（用于重试功能） */
  userPreferences?: any;
  
  /** 重试成功回调 */
  onRetrySuccess?: () => void;
  
  /** 自定义类名 */
  className?: string;
}

/**
 * TreeNode 节点组件 Props
 */
export interface TreeNodeProps {
  node: TreeNodeData;
  onToggleExpand?: (nodeId: string) => void;
  onClick?: (node: TreeNodeData) => void;
  isSelected?: boolean;
}

/**
 * NodeDetailPopover Props
 */
export interface NodeDetailPopoverProps {
  node: TreeNodeData | null;
  isOpen: boolean;
  onClose: () => void;
  anchorPosition?: { x: number; y: number };
  /** 路线图 ID（用于重试功能） */
  roadmapId?: string | null;
  /** 用户学习偏好（用于重试功能） */
  userPreferences?: any;
  /** 重试成功回调 */
  onRetrySuccess?: () => void;
}

/**
 * 全屏对话框 Props
 */
export interface FullscreenDialogProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

// ============================================================
// 布局配置常量
// ============================================================

/**
 * 布局配置
 */
export const TREE_LAYOUT_CONFIG = {
  /** 节点最小宽度 */
  minNodeWidth: {
    start: 140,
    stage: 120,
    module: 110,
    concept: 100,
  },
  /** 节点最大宽度 - 不限制，让文本完整显示 */
  maxNodeWidth: {
    start: 9999,
    stage: 9999,
    module: 9999,
    concept: 9999,
  },
  /** 节点高度 */
  nodeHeight: 36,
  /** 水平间距（节点之间） */
  horizontalGap: 60,
  /** 垂直间距（同层级节点之间） */
  verticalGap: 12,
  /** 层级缩进 */
  levelIndent: 80,
  /** 连接线圆角 */
  connectionRadius: 8,
  /** 每个字符的大致宽度（用于计算节点宽度） */
  charWidth: {
    start: 8,    // text-sm
    stage: 9,    // text-sm
    module: 7.5, // text-xs
    concept: 7.5, // text-xs
  },
  /** padding 占用的宽度 */
  paddingWidth: {
    start: 24,  // px-3 = 12*2
    stage: 24,  // px-3 = 12*2
    module: 20, // px-2.5 = 10*2
    concept: 16, // px-2 = 8*2
  },
  /** 展开图标和状态图标占用的宽度 */
  iconWidth: {
    withExpand: 28,
    withStatus: 24,
    withBoth: 40,
    none: 0,
  },
} as const;

// ============================================================
// 工具函数类型
// ============================================================

/**
 * 从 Concept 计算节点状态
 * 
 * 优先使用 overall_status（来自 concept_metadata 表），如果不存在则根据三个状态字段推断
 */
export function getConceptNodeStatus(
  concept: Concept,
  loadingIds?: string[],
  failedIds?: string[],
  partialFailedIds?: string[],
  modifiedIds?: string[],
): TreeNodeStatus {
  const conceptId = concept.concept_id;
  
  // 优先检查修改状态
  if (modifiedIds?.includes(conceptId)) {
    return 'modified';
  }
  
  // 检查加载状态
  if (loadingIds?.includes(conceptId)) {
    return 'loading';
  }
  
  // 检查失败状态
  if (failedIds?.includes(conceptId)) {
    return 'failed';
  }
  
  // 检查部分失败状态
  if (partialFailedIds?.includes(conceptId)) {
    return 'partial_failure';
  }
  
  // 🆕 优先使用 overall_status（来自 concept_metadata 表，更准确）
  if (concept.overall_status) {
    switch (concept.overall_status) {
      case 'completed':
        return 'completed';
      case 'generating':
        return 'loading';
      case 'failed':
        return 'failed';
      case 'partial_failed':
        return 'partial_failure';
      case 'pending':
        return 'pending';
      default:
        // 继续使用旧逻辑
        break;
    }
  }
  
  // 向后兼容：根据三个状态字段推断（如果 overall_status 不存在）
  const allCompleted = 
    concept.content_status === 'completed' &&
    concept.resources_status === 'completed' &&
    concept.quiz_status === 'completed';
  
  if (allCompleted) {
    return 'completed';
  }
  
  const anyGenerating = 
    concept.content_status === 'generating' ||
    concept.resources_status === 'generating' ||
    concept.quiz_status === 'generating';
  
  if (anyGenerating) {
    return 'loading';
  }
  
  return 'pending';
}

/**
 * 计算 Module 状态（基于子 Concept 状态）
 */
export function getModuleNodeStatus(childStatuses: TreeNodeStatus[]): TreeNodeStatus {
  if (childStatuses.length === 0) return 'pending';
  
  // 如果有任何修改的子节点，Module 也标记为修改
  if (childStatuses.some(s => s === 'modified')) {
    return 'modified';
  }
  
  // 如果有任何加载中
  if (childStatuses.some(s => s === 'loading')) {
    return 'loading';
  }
  
  // 如果全部失败
  if (childStatuses.every(s => s === 'failed')) {
    return 'failed';
  }
  
  // 如果有部分失败
  if (childStatuses.some(s => s === 'failed' || s === 'partial_failure')) {
    return 'partial_failure';
  }
  
  // 如果全部完成
  if (childStatuses.every(s => s === 'completed')) {
    return 'completed';
  }
  
  return 'pending';
}

/**
 * 计算 Stage 状态（基于子 Module 状态）
 */
export function getStageNodeStatus(childStatuses: TreeNodeStatus[]): TreeNodeStatus {
  return getModuleNodeStatus(childStatuses);
}

/**
 * 计算节点完成进度（基于子节点状态）
 * 
 * @param children 子节点列表
 * @returns 完成百分比 (0-100)
 */
export function calculateNodeProgress(children?: TreeNodeData[]): number {
  if (!children || children.length === 0) return 0;
  
  const completedCount = children.filter(child => child.status === 'completed').length;
  return Math.round((completedCount / children.length) * 100);
}


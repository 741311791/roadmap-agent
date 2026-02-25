/**
 * 前端专用API类型扩展
 * 
 * 在自动生成类型的基础上添加前端UI相关字段
 */

import type { 
  RoadmapFramework, 
  Concept,
  Module,
  Stage,
} from '@/types/generated';

/**
 * 带UI状态的路线图
 */
export interface RoadmapWithUI extends RoadmapFramework {
  /** 是否收藏 */
  isFavorite?: boolean;
  /** 是否展开（用于列表视图） */
  isExpanded?: boolean;
  /** 本地缓存时间 */
  cachedAt?: number;
  /** UI展开的Stage ID列表 */
  expandedStages?: string[];
}

/**
 * 带UI状态的Concept
 */
export interface ConceptWithUI extends Concept {
  /** 是否被选中（用于编辑模式） */
  isSelected?: boolean;
  /** 是否展开详情 */
  isExpanded?: boolean;
  /** 加载状态 */
  isLoading?: boolean;
}

/**
 * 带UI状态的Module
 */
export interface ModuleWithUI extends Module {
  /** 是否展开 */
  isExpanded?: boolean;
  /** 完成进度（0-100） */
  progress?: number;
}

/**
 * 带UI状态的Stage
 */
export interface StageWithUI extends Stage {
  /** 是否展开 */
  isExpanded?: boolean;
  /** 完成进度（0-100） */
  progress?: number;
}

/**
 * 分页参数
 */
export interface PaginationParams {
  page?: number;
  size?: number;
  limit?: number;
  offset?: number;
}

/**
 * 分页响应
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

/**
 * API调用选项
 */
export interface ApiCallOptions {
  /** 是否显示加载提示 */
  showLoading?: boolean;
  /** 是否显示成功提示 */
  showSuccess?: boolean;
  /** 是否显示错误提示 */
  showError?: boolean;
  /** 自定义成功消息 */
  successMessage?: string;
  /** 自定义错误上下文 */
  errorContext?: string;
}


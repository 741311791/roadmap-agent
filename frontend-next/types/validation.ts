/**
 * 验证和编辑记录相关类型定义
 * 
 * 对应后端的 StructureValidationRecord 和 RoadmapEditRecord 模型
 */

/**
 * 问题类别（新增）
 */
export type IssueCategory = 'knowledge_gap' | 'structural_flaw' | 'user_mismatch';

/**
 * 验证问题（只包含 critical 和 warning，移除 suggestion）
 */
export interface ValidationIssue {
  /** 严重级别（移除 'suggestion'） */
  severity: 'critical' | 'warning';
  /** 问题类别（新增） */
  category: IssueCategory;
  /** 问题位置（如 'Stage 2 > Module 1 > Concept X'） */
  location: string;
  /** 问题描述 */
  issue: string;
  /** 改进建议 */
  suggestion: string;
  /** 结构化建议（可选） */
  structural_suggestion?: StructuralSuggestion;
}

/**
 * 维度评分（新增）
 */
export interface DimensionScore {
  /** 维度名称 */
  dimension: 'knowledge_completeness' | 'knowledge_progression' | 'stage_coherence' | 'module_clarity' | 'user_alignment';
  /** 分数 (0-100) */
  score: number;
  /** 评分理由 */
  rationale: string;
}

/**
 * 结构化改进建议（新增）
 */
export interface StructuralSuggestion {
  /** 操作类型 */
  action: 'add_concept' | 'add_module' | 'add_stage' | 'modify_concept' | 'reorder_stage' | 'merge_modules';
  /** 目标位置 */
  target_location: string;
  /** 建议内容 */
  content: string;
  /** 原因 */
  reason: string;
}

/**
 * 验证结果
 */
export interface ValidationResult {
  /** 记录 ID */
  id: string;
  /** 任务 ID */
  task_id: string;
  /** 路线图 ID */
  roadmap_id: string;
  /** 是否通过验证 */
  is_valid: boolean;
  /** 总体评分 (0-100) */
  overall_score: number;
  /** 问题列表（只包含 critical 和 warning） */
  issues: ValidationIssue[];
  /** 维度评分列表（新增） */
  dimension_scores: DimensionScore[];
  /** 改进建议列表（新增） */
  improvement_suggestions: StructuralSuggestion[];
  /** 验证摘要（新增） */
  validation_summary: string;
  /** 验证轮次 */
  validation_round: number;
  /** 严重问题数量 */
  critical_count: number;
  /** 警告问题数量 */
  warning_count: number;
  /** 建议数量（来自 improvement_suggestions） */
  suggestion_count: number;
  /** 创建时间 */
  created_at: string;
}

/**
 * 编辑记录
 */
export interface EditRecord {
  /** 记录 ID */
  id: string;
  /** 任务 ID */
  task_id: string;
  /** 路线图 ID */
  roadmap_id: string;
  /** 修改摘要 */
  modification_summary: string;
  /** 修改的节点 ID 列表（用于前端高亮） */
  modified_node_ids: string[];
  /** 编辑轮次 */
  edit_round: number;
  /** 创建时间 */
  created_at: string;
}

/**
 * 编辑记录（历史记录简化版）
 */
export interface EditRecordSummary {
  /** 记录 ID */
  id: string;
  /** 任务 ID */
  task_id: string;
  /** 路线图 ID */
  roadmap_id: string;
  /** 修改摘要 */
  modification_summary: string;
  /** 修改的节点数量 */
  modified_nodes_count: number;
  /** 编辑轮次 */
  edit_round: number;
  /** 创建时间 */
  created_at: string;
}

/**
 * 编辑差异对比数据
 */
export interface EditDiff {
  /** 记录 ID */
  id: string;
  /** 任务 ID */
  task_id: string;
  /** 路线图 ID */
  roadmap_id: string;
  /** 编辑轮次 */
  edit_round: number;
  /** 原始框架数据 */
  origin_framework_data: any;
  /** 修改后框架数据 */
  modified_framework_data: any;
  /** 修改的节点 ID 列表 */
  modified_node_ids: string[];
  /** 修改摘要 */
  modification_summary: string;
  /** 创建时间 */
  created_at: string;
}






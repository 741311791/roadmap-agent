'use client';

/**
 * WorkflowTopology - 工作流拓扑图组件（优化版）
 * 
 * 功能：
 * - 展示主路节点：Analysis → Design → Validate → Review → Content
 * - 展示验证分支：Validate → Plan1 → Edit1 → 回到 Validate（显示在下方）
 * - 展示审核分支：Review → Plan2 → Edit2 → 回到 Review（显示在上方）
 * - 根据 edit_source 区分当前激活的分支
 * - 支持实时状态更新
 * - 已完成路径显示电流脉冲动画
 * - 虚线连接主路和分支节点
 * 
 * 优化：使用动态导入减少初始加载体积
 */

import { useState, useEffect, useRef, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { AnimatePresence, motion } from 'framer-motion';
import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  CheckCircle2,
  Loader2,
  XCircle,
  Clock,
  Edit3,
  Check,
  X,
  AlertCircle,
  FileSearch,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { tasksApi } from '@/lib/api/endpoints';
import { NodeDetailPanel } from './node-detail-panel';
import type { ExecutionLog } from '@/types/content-generation';
import {
  collectWorkflowNodeDurations,
  formatWorkflowDuration,
  type WorkflowNodeDurationStat,
} from '@/lib/utils/workflow-node-duration';

// ========================================
// 优化：动态导入 GradientTracing 组件
// ========================================
const GradientTracing = dynamic(
  () => import('@/components/ui/gradient-tracing').then(mod => ({ default: mod.GradientTracing })),
  { 
    ssr: false,  // 动画组件不需要SSR
    loading: () => <div className="w-full h-1 bg-sage-600 rounded-full" />
  }
);

// ============================================================================
// 类型定义
// ============================================================================

/** 节点状态类型 */
type NodeStatus = 'completed' | 'current' | 'pending' | 'failed' | 'skipped';

/** 编辑来源类型 */
type EditSource = 'validation_failed' | 'human_review' | null;

/** 节点定义 */
interface WorkflowNode {
  id: string;
  label: string;
  shortLabel: string;
  description: string;
  steps: string[];
}

/** 分支定义 */
interface WorkflowBranch {
  id: string;
  triggerNode: string;
  returnNode: string;
  editSource: EditSource;
  nodes: WorkflowNode[];
  position: 'top' | 'bottom'; // 分支位置：上方或下方
}

// ============================================================================
// 工作流拓扑数据结构
// ============================================================================

/**
 * 主路节点（使用翻译key）
 * Analysis → Design → Validate → Review → Content
 * 
 * 注意：这些是配置数据，label需要在使用时动态翻译
 */
const MAIN_STAGES_KEYS = [
  {
    id: 'analysis',
    labelKey: 'intentAnalysis',
    shortLabelKey: 'analysis',
    descriptionKey: 'analyzingGoals',
    steps: ['init', 'queued', 'starting', 'intent_analysis'],
  },
  {
    id: 'design',
    labelKey: 'curriculumDesign',
    shortLabelKey: 'design',
    descriptionKey: 'designingStructure',
    steps: ['curriculum_design'],
  },
  {
    id: 'validate',
    labelKey: 'structureValidation',
    shortLabelKey: 'validate',
    descriptionKey: 'validatingLogic',
    steps: ['structure_validation'],
  },
  {
    id: 'review',
    labelKey: 'humanReview',
    shortLabelKey: 'review',
    descriptionKey: 'awaitingConfirmation',
    steps: ['human_review'],
  },
  {
    id: 'content',
    labelKey: 'contentGeneration',
    shortLabelKey: 'content',
    descriptionKey: 'generatingMaterials',
    // auto_content_generation 是极速模式的内部节点名，WS 可能短暂推送此步骤，映射到 content 阶段
    steps: ['auto_content_generation', 'content_generation_queued', 'content_generation'],
  },
];

/**
 * 验证分支配置（使用翻译key）
 * Validate → Plan1 → Edit1 → 回到 Validate
 */
const VALIDATION_BRANCH_KEYS = {
  id: 'validation_branch',
  triggerNode: 'validate',
  returnNode: 'validate',
  editSource: 'validation_failed' as const,
  position: 'bottom' as const,
  nodes: [
    {
      id: 'plan1',
      labelKey: 'editPlanAnalysis',
      shortLabelKey: 'plan',
      descriptionKey: 'analyzingIssues',
      steps: ['edit_plan_analysis'],
    },
    {
      id: 'edit1',
      labelKey: 'roadmapEdit',
      shortLabelKey: 'edit',
      descriptionKey: 'fixingIssues',
      steps: ['roadmap_edit'],
    },
  ],
};

/**
 * 审核分支配置（使用翻译key）
 * Review → Plan2 → Edit2 → 回到 Review
 */
const REVIEW_BRANCH_KEYS = {
  id: 'review_branch',
  triggerNode: 'review',
  returnNode: 'review',
  editSource: 'human_review' as const,
  position: 'top' as const,
  nodes: [
    {
      id: 'plan2',
      labelKey: 'editPlanAnalysis',
      shortLabelKey: 'plan',
      descriptionKey: 'analyzingFeedback',
      steps: ['edit_plan_analysis'],
    },
    {
      id: 'edit2',
      labelKey: 'roadmapEdit',
      shortLabelKey: 'edit',
      descriptionKey: 'applyingChanges',
      steps: ['roadmap_edit'],
    },
  ],
};

/**
 * 主路节点（默认版本，用于工具函数）
 * 这些是不需要翻译的版本，用于 getStepLocation 等工具函数
 */
const MAIN_STAGES: WorkflowNode[] = MAIN_STAGES_KEYS.map(stage => ({
  id: stage.id,
  label: stage.labelKey,
  shortLabel: stage.shortLabelKey,
  description: stage.descriptionKey,
  steps: stage.steps,
}));

/**
 * 验证分支（默认版本，用于工具函数）
 */
const VALIDATION_BRANCH: WorkflowBranch = {
  id: VALIDATION_BRANCH_KEYS.id,
  triggerNode: VALIDATION_BRANCH_KEYS.triggerNode,
  returnNode: VALIDATION_BRANCH_KEYS.returnNode,
  editSource: VALIDATION_BRANCH_KEYS.editSource,
  position: VALIDATION_BRANCH_KEYS.position,
  nodes: VALIDATION_BRANCH_KEYS.nodes.map(node => ({
    id: node.id,
    label: node.labelKey,
    shortLabel: node.shortLabelKey,
    description: node.descriptionKey,
    steps: node.steps,
  })),
};

/**
 * 审核分支（默认版本，用于工具函数）
 */
const REVIEW_BRANCH: WorkflowBranch = {
  id: REVIEW_BRANCH_KEYS.id,
  triggerNode: REVIEW_BRANCH_KEYS.triggerNode,
  returnNode: REVIEW_BRANCH_KEYS.returnNode,
  editSource: REVIEW_BRANCH_KEYS.editSource,
  position: REVIEW_BRANCH_KEYS.position,
  nodes: REVIEW_BRANCH_KEYS.nodes.map(node => ({
    id: node.id,
    label: node.labelKey,
    shortLabel: node.shortLabelKey,
    description: node.descriptionKey,
    steps: node.steps,
  })),
};

/**
 * 运行中文案轮播配置。
 *
 * 说明：
 * - 仅在当前执行节点上展示；
 * - 使用翻译 key，避免把展示文案硬编码进渲染逻辑。
 */
const NODE_LOADING_MESSAGE_KEYS: Record<string, string[]> = {
  analysis: [
    'nodeLoadingAnalysisProfile',
    'nodeLoadingAnalysisGoal',
    'nodeLoadingAnalysisConstraint',
  ],
  design: [
    'nodeLoadingDesignStages',
    'nodeLoadingDesignPath',
    'nodeLoadingDesignDifficulty',
  ],
  validate: [
    'nodeLoadingValidatePrerequisites',
    'nodeLoadingValidateDependencies',
    'nodeLoadingValidateRisks',
  ],
  plan1: [
    'nodeLoadingPlanValidationIssues',
    'nodeLoadingPlanValidationFixes',
    'nodeLoadingPlanValidationImpact',
  ],
  edit1: [
    'nodeLoadingEditValidationStructure',
    'nodeLoadingEditValidationDependencies',
    'nodeLoadingEditValidationConsistency',
  ],
  plan2: [
    'nodeLoadingPlanReviewFeedback',
    'nodeLoadingPlanReviewIntent',
    'nodeLoadingPlanReviewRevision',
  ],
  edit2: [
    'nodeLoadingEditReviewUpdates',
    'nodeLoadingEditReviewStructure',
    'nodeLoadingEditReviewConsistency',
  ],
  content: [
    'nodeLoadingContentTutorials',
    'nodeLoadingContentResources',
    'nodeLoadingContentQuiz',
  ],
};

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 获取步骤所在位置
 * 
 * @param currentStep - 当前步骤
 * @param editSource - 编辑来源（用于区分 roadmap_edit 属于哪个分支）
 * @returns 步骤位置信息
 */
export function getStepLocation(
  currentStep: string | null,
  editSource?: EditSource
): {
  stageId: string;
  isOnBranch: boolean;
  branchType?: 'validation' | 'review';
  branchNodeIndex?: number;
} {
  // 处理 null 值
  if (!currentStep) {
    return { stageId: 'START', isOnBranch: false };
  }

  // 终态步骤不参与正常节点匹配，但拓扑图仍需要一个稳定锚点。
  // completed / failed 都锚定到最后一个主路节点，避免在控制台产生无意义警告。
  if (currentStep === 'completed' || currentStep === 'failed') {
    return { stageId: 'content', isOnBranch: false };
  }
  
  // 检查主路节点
  for (const stage of MAIN_STAGES) {
    if (stage.steps.includes(currentStep)) {
      return { stageId: stage.id, isOnBranch: false };
    }
  }

  // 检查验证分支
  // 注意：edit_plan_analysis 和 roadmap_edit 同时存在于两个分支中，
  // 必须通过 editSource 来区分当前属于哪个分支。
  // editSource='human_review' → 属于审核分支，跳过验证分支检查
  // editSource='validation_failed' 或 null → 属于验证分支
  for (let i = 0; i < VALIDATION_BRANCH.nodes.length; i++) {
    const node = VALIDATION_BRANCH.nodes[i];
    if (node.steps.includes(currentStep)) {
      if (editSource === 'human_review') {
        // 明确来自审核分支，跳出循环去检查审核分支
        break;
      }
      return { stageId: node.id, isOnBranch: true, branchType: 'validation', branchNodeIndex: i };
    }
  }

  // 检查审核分支
  for (let i = 0; i < REVIEW_BRANCH.nodes.length; i++) {
    const node = REVIEW_BRANCH.nodes[i];
    if (node.steps.includes(currentStep)) {
      if (editSource === 'validation_failed') {
        // 明确来自验证分支，跳出循环（不应进入审核分支）
        break;
      }
      return { stageId: node.id, isOnBranch: true, branchType: 'review', branchNodeIndex: i };
    }
  }

  // 防御性处理：未识别的步骤
  // 如果步骤名称未在预定义列表中，尝试智能推断位置
  console.warn(`[WorkflowTopology] Unrecognized currentStep: "${currentStep}", falling back to first node`);
  
  // 默认返回第一个主路节点（用于兜底，防止显示错误）
  return { stageId: 'analysis', isOnBranch: false };
}

/**
 * 获取主路节点索引
 */
function getMainStageIndex(stageId: string): number {
  return MAIN_STAGES.findIndex(s => s.id === stageId);
}

// ============================================================================
// 组件 Props
// ============================================================================

interface WorkflowTopologyProps {
  /** 当前步骤 */
  currentStep: string | null;
  /** 任务状态 */
  status: string;
  /** 编辑来源（用于区分分支） */
  editSource?: EditSource;
  /** 任务 ID（用于 Human Review 操作） */
  taskId?: string;
  /** 路线图 ID */
  roadmapId?: string | null;
  /** 路线图标题 */
  roadmapTitle?: string;
  /** 阶段数量（用于 Human Review 展示） */
  stagesCount?: number;
  /** 执行日志（时间轴展示用，不再用于判断分支触发状态） */
  executionLogs?: ExecutionLog[];
  /** 节点耗时原始日志（包含 workflow/content，避免被时间轴截断影响） */
  workflowLogs?: ExecutionLog[];
  /**
   * 验证分支是否已被触发（由父组件维护，避免依赖存在写入延迟的 DB 日志）
   * 真实来源：WS progress 事件（实时）+ DB 日志（刷新恢复）
   */
  validationBranchTriggered?: boolean;
  /**
   * 审核分支是否已被触发（由父组件维护，避免依赖存在写入延迟的 DB 日志）
   * 真实来源：WS progress 事件（实时）+ DB 日志（刷新恢复）
   */
  reviewBranchTriggered?: boolean;
  /** Human Review 完成回调 */
  onHumanReviewComplete?: () => void;
  /** 当前选中的节点ID */
  selectedNodeId?: string | null;
  /** 节点选择回调 */
  onNodeSelect?: (nodeId: string | null) => void;
  /** 是否为极速模式（跳过结构验证节点） */
  turboMode?: boolean;
  /** 路线图总 Concept 节点数（用于内容生成阶段时间估算） */
  totalConcepts?: number;
}

// ============================================================================
// 主组件
// ============================================================================

export function WorkflowTopology({
  currentStep,
  status,
  editSource,
  taskId,
  roadmapId,
  roadmapTitle,
  stagesCount = 0,
  executionLogs = [],
  workflowLogs = [],
  validationBranchTriggered: validationBranchTriggeredProp = false,
  reviewBranchTriggered: reviewBranchTriggeredProp = false,
  onHumanReviewComplete,
  selectedNodeId = null,
  onNodeSelect,
  turboMode = true,
  totalConcepts = 0,
}: WorkflowTopologyProps) {
  const t = useTranslations('taskDetail');
  
  // Human Review 状态
  const [reviewStatus, setReviewStatus] = useState<'waiting' | 'submitting' | 'approved' | 'rejected'>('waiting');
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  
  // 动态翻译主路节点（组件内使用的翻译版本）
  // 极速模式下过滤掉 validate（结构验证）和 review（人工审查）节点
  // 极速模式拓扑：Analysis → Design → Content
  // 普通模式拓扑：Analysis → Design → Validate → Review → Content
  const mainStagesTranslated: WorkflowNode[] = useMemo(() => MAIN_STAGES_KEYS
    .filter(stage => !(turboMode && (stage.id === 'validate' || stage.id === 'review')))
    .map(stage => ({
      id: stage.id,
      label: t(stage.labelKey as any),
      shortLabel: t(stage.shortLabelKey as any),
      description: t(stage.descriptionKey as any),
      steps: stage.steps,
    })), [t, turboMode]);
  
  // 动态翻译验证分支（组件内使用的翻译版本）
  const validationBranchTranslated: WorkflowBranch = useMemo(() => ({
    id: VALIDATION_BRANCH_KEYS.id,
    triggerNode: VALIDATION_BRANCH_KEYS.triggerNode,
    returnNode: VALIDATION_BRANCH_KEYS.returnNode,
    editSource: VALIDATION_BRANCH_KEYS.editSource,
    position: VALIDATION_BRANCH_KEYS.position,
    nodes: VALIDATION_BRANCH_KEYS.nodes.map(node => ({
      id: node.id,
      label: t(node.labelKey as any),
      shortLabel: t(node.shortLabelKey as any),
      description: t(node.descriptionKey as any),
      steps: node.steps,
    })),
  }), [t]);
  
  // 动态翻译审核分支（组件内使用的翻译版本）
  const reviewBranchTranslated: WorkflowBranch = useMemo(() => ({
    id: REVIEW_BRANCH_KEYS.id,
    triggerNode: REVIEW_BRANCH_KEYS.triggerNode,
    returnNode: REVIEW_BRANCH_KEYS.returnNode,
    editSource: REVIEW_BRANCH_KEYS.editSource,
    position: REVIEW_BRANCH_KEYS.position,
    nodes: REVIEW_BRANCH_KEYS.nodes.map(node => ({
      id: node.id,
      label: t(node.labelKey as any),
      shortLabel: t(node.shortLabelKey as any),
      description: t(node.descriptionKey as any),
      steps: node.steps,
    })),
  }), [t]);

  // 获取当前步骤位置
  const stepLocation = getStepLocation(currentStep, editSource);
  
  // 状态判断（需要在 useEffect 之前定义）
  const isFailed = status === 'failed';
  const isCompleted = status === 'completed' || status === 'partial_failure';
  const isHumanReviewActive = 
    currentStep === 'human_review' || 
    currentStep === 'human_review_pending' ||
    status === 'human_review_pending';

  /**
   * 跟踪上一次的 Human Review 状态，用于检测状态变化
   */
  const prevHumanReviewActiveRef = useRef<boolean>(false);
  
  /**
   * 跟踪上一次离开 human_review 的时间，用于防止快速循环时的状态丢失
   */
  const lastExitTimeRef = useRef<number>(0);

  /**
   * 当任务重新进入 Human Review 状态时，重置审核状态
   * 场景：用户reject后，编辑完成，工作流再次回到review节点
   * 
   * 修复逻辑：
   * 1. 当进入 human_review 状态时，如果 reviewStatus 是 approved/rejected，重置为 waiting
   * 2. 增加时间窗口检测：如果最近 1 秒内离开过 human_review，且现在又进入，则强制重置
   *    这可以处理快速循环的情况（后端执行很快）
   */
  useEffect(() => {
    const now = Date.now();
    
    // 检测：从非human_review状态 → 进入human_review状态
    const isReenteringHumanReview = !prevHumanReviewActiveRef.current && isHumanReviewActive;
    
    // 检测：是否在短时间内（1秒）重新进入
    // 这处理了后端快速执行导致状态变化几乎同时发生的情况
    const isQuickReentry = isHumanReviewActive && (now - lastExitTimeRef.current < 1000);
    
    // 当重新进入 human_review 状态时，重置审核状态（如果已经完成审核）
    // 条件：正常重新进入 或 快速重新进入（且已完成审核）
    if ((isReenteringHumanReview || isQuickReentry) && 
        (reviewStatus === 'approved' || reviewStatus === 'rejected')) {
      console.log('[WorkflowTopology] Resetting reviewStatus to waiting', {
        isReenteringHumanReview,
        isQuickReentry,
        prevActive: prevHumanReviewActiveRef.current,
        currentActive: isHumanReviewActive,
        reviewStatus,
      });
      setReviewStatus('waiting');
      setFeedback('');
      setShowFeedback(false);
      setReviewError(null);
    }
    
    // 当离开 human_review 状态时，记录时间
    if (prevHumanReviewActiveRef.current && !isHumanReviewActive) {
      lastExitTimeRef.current = now;
    }
    
    // 更新上一次的状态
    prevHumanReviewActiveRef.current = isHumanReviewActive;
  }, [isHumanReviewActive, reviewStatus]); // 监听human_review状态和审核状态变化

  // 分支触发状态
  // 优先使用父组件传入的 prop（由 WS 事件实时设置，无 DB 日志延迟）
  // 降级兜底：从 executionLogs 检测（适用于父组件未传入 prop 的场景）
  const validationBranchTriggered = validationBranchTriggeredProp || executionLogs.some(
    log => 
      (log.step === 'edit_plan_analysis' || log.step === 'roadmap_edit') &&
      log.details?.edit_source === 'validation_failed'
  );
  const reviewBranchTriggered = reviewBranchTriggeredProp || executionLogs.some(
    log => 
      (log.step === 'edit_plan_analysis' || log.step === 'roadmap_edit') &&
      log.details?.edit_source === 'human_review'
  );

  const nodeDurationStats = useMemo(
    () => collectWorkflowNodeDurations(workflowLogs),
    [workflowLogs]
  );

  /**
   * 为当前节点生成轻量的轮播加载提示。
   */
  const renderNodeLoadingHint = (
    nodeId: string,
    nodeStatus: NodeStatus,
    suppressHint: boolean = false
  ) => {
    if (nodeStatus !== 'current' || suppressHint) {
      return null;
    }

    const messageKeys = NODE_LOADING_MESSAGE_KEYS[nodeId];
    if (!messageKeys || messageKeys.length === 0) {
      return null;
    }

    return (
      <NodeLoadingHint
        messages={messageKeys.map((key) => t(key as any))}
      />
    );
  };

  /**
   * 获取主路节点状态
   * 
   * 注意：必须使用 mainStagesTranslated（渲染用的数组）而非 MAIN_STAGES（全量数组）来计算索引。
   * 原因：turboMode 会过滤掉 validate 节点，导致两个数组的索引不一致：
   *   MAIN_STAGES:         [analysis(0), design(1), validate(2), review(3), content(4)]
   *   mainStagesTranslated: [analysis(0), design(1), review(2), content(3)]  ← validate 被移除
   * 若用 MAIN_STAGES 的 review 索引(3)与 mainStagesTranslated 的 nodeIndex(2) 比较，
   * review 会被错判为 'completed'，content 被错判为 'current'。
   */
  const getMainNodeStatus = (nodeIndex: number, nodeId: string): NodeStatus => {
    if (isCompleted) return 'completed';
    if (isFailed && stepLocation.stageId === nodeId && !stepLocation.isOnBranch) return 'failed';

    const anchorId = stepLocation.isOnBranch
      ? (stepLocation.branchType === 'validation' ? 'validate' : 'review')
      : stepLocation.stageId;

    // ✅ 用 mainStagesTranslated 计算索引，确保 turboMode 下索引一致
    const currentMainIndex = mainStagesTranslated.findIndex(s => s.id === anchorId);

    // 如果当前在分支上
    if (stepLocation.isOnBranch) {
      const triggerIndex = mainStagesTranslated.findIndex(
        s => s.id === (stepLocation.branchType === 'validation' ? 'validate' : 'review')
      );
      if (nodeIndex < triggerIndex) return 'completed';
      if (nodeIndex === triggerIndex) return 'current'; // 分支的触发节点显示为 current
      return 'pending';
    }

    // 正常主路逻辑
    if (nodeIndex < currentMainIndex) return 'completed';
    if (nodeIndex === currentMainIndex) return 'current';
    return 'pending';
  };

  /**
   * 获取分支节点状态
   */
  const getBranchNodeStatus = (
    branchType: 'validation' | 'review',
    nodeIndex: number,
    nodeId: string
  ): NodeStatus => {
    // 检查分支是否被触发过
    const wasBranchTriggered = 
      branchType === 'validation' ? validationBranchTriggered : reviewBranchTriggered;
    
    // 如果任务已完成
    if (isCompleted) {
      // 如果分支被触发过，显示为已完成（实心颜色）
      if (wasBranchTriggered) {
        return 'completed';
      }
      // 否则显示为跳过（空心颜色）
      return 'skipped';
    }
    
    // 关键修复：如果当前不在此分支上，但分支已被触发过，节点应显示为 completed
    if (!stepLocation.isOnBranch || stepLocation.branchType !== branchType) {
      // 如果分支被触发过，说明已经执行完成并返回主路
      if (wasBranchTriggered) {
        return 'completed';
      }
      // 否则显示为等待状态
      return 'pending';
    }

    // 当前在此分支上
    if (stepLocation.branchNodeIndex === undefined) return 'pending';
    
    if (isFailed && stepLocation.stageId === nodeId) return 'failed';
    if (nodeIndex < stepLocation.branchNodeIndex) return 'completed';
    if (nodeIndex === stepLocation.branchNodeIndex) return 'current';
    return 'pending';
  };

  /**
   * 获取节点图标
   */
  const getNodeIcon = (nodeStatus: NodeStatus, nodeId: string) => {
    // 分支节点的特殊图标
    if (nodeId.startsWith('plan')) {
      switch (nodeStatus) {
        case 'completed':
          return <CheckCircle2 className="w-4 h-4" />;
        case 'current':
          return <FileSearch className="w-4 h-4 animate-pulse" />;
        default:
          return <FileSearch className="w-4 h-4 opacity-50" />;
      }
    }
    
    if (nodeId.startsWith('edit')) {
      switch (nodeStatus) {
        case 'completed':
          return <CheckCircle2 className="w-4 h-4" />;
        case 'current':
          return <Edit3 className="w-4 h-4 animate-pulse" />;
        default:
          return <Edit3 className="w-4 h-4 opacity-50" />;
      }
    }

    // 主路节点图标
    switch (nodeStatus) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5" />;
      case 'current':
        return <Loader2 className="w-5 h-5 animate-spin" />;
      case 'failed':
        return <XCircle className="w-5 h-5" />;
      case 'skipped':
        return <CheckCircle2 className="w-5 h-5 opacity-50" />;
      default:
        return <Clock className="w-5 h-5 opacity-40" />;
    }
  };

  /**
   * 获取节点耗时统计
   */
  const getNodeDurationStat = (nodeId: string): WorkflowNodeDurationStat | null => {
    return nodeDurationStats[nodeId as keyof typeof nodeDurationStats] ?? null;
  };

  /**
   * 渲染节点耗时标签
   */
  const renderNodeDuration = (nodeId: string, nodeStatus: NodeStatus) => {
    const durationStat = getNodeDurationStat(nodeId);

    if (!durationStat) {
      return null;
    }

    return (
      <span
        className={cn(
          'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium tabular-nums',
          nodeStatus === 'completed' && 'bg-sage-100 text-sage-700',
          nodeStatus === 'current' && 'bg-sage-50 text-sage-700',
          nodeStatus === 'failed' && 'bg-red-50 text-red-600',
          (nodeStatus === 'pending' || nodeStatus === 'skipped') && 'bg-muted text-muted-foreground'
        )}
        title={
          durationStat.count > 1
            ? `${t('durationLabel')} ${formatWorkflowDuration(durationStat.latestMs)}`
            : `${t('durationLabel')} ${formatWorkflowDuration(durationStat.latestMs)}`
        }
      >
        {t('durationLabel')} {formatWorkflowDuration(durationStat.latestMs)}
      </span>
    );
  };

  /**
   * Human Review 操作处理
   */
  const handleApprove = async () => {
    if (!taskId) return;
    try {
      setReviewStatus('submitting');
      setReviewError(null);
      await tasksApi.approve(taskId, { approved: true });
      setReviewStatus('approved');
      onHumanReviewComplete?.();
    } catch (err: any) {
      console.error('Failed to approve roadmap:', err);
      setReviewError(err.message || 'Failed to approve roadmap');
      setReviewStatus('waiting');
    }
  };

  const handleReject = async () => {
    if (!taskId) return;
    if (!showFeedback) {
      setShowFeedback(true);
      return;
    }
    if (!feedback.trim()) {
      setReviewError('Please provide feedback for rejection');
      return;
    }
    try {
      setReviewStatus('submitting');
      setReviewError(null);
      await tasksApi.approve(taskId, { approved: false, feedback });
      // 反馈提交成功后，切换到 rejected 状态显示"已提交"提示
      // 面板会保持显示直到后端 WebSocket 推送新的 current_step（工作流重新激活）
      setReviewStatus('rejected');
      setShowFeedback(false);
      setFeedback('');
      onHumanReviewComplete?.();
    } catch (err: any) {
      console.error('Failed to reject roadmap:', err);
      setReviewError(err.message || 'Failed to submit feedback');
      setReviewStatus('waiting');
    }
  };

  const handleCancelFeedback = () => {
    setShowFeedback(false);
    setFeedback('');
    setReviewError(null);
  };

  return (
    <>
      <Card className="p-6">
        <div className="space-y-6">
        {/* 标题栏 */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-serif font-semibold">{t('workflowProgress')}</h2>
          {isCompleted && (
            <Badge className="bg-sage-600 hover:bg-sage-700 text-white">
              <CheckCircle2 className="w-3 h-3 mr-1" />
              {t('completed')}
            </Badge>
          )}
          {isFailed && (
            <Badge variant="destructive">
              <XCircle className="w-3 h-3 mr-1" />
              {t('failed')}
            </Badge>
          )}
          {!isCompleted && !isFailed && (
            <Badge variant="secondary" className="animate-pulse">
              <Clock className="w-3 h-3 mr-1" />
              {t('inProgress')}
            </Badge>
          )}
        </div>

        {/* 拓扑图 - 增加垂直空间以容纳上下分支 */}
        <div className="relative pt-24 pb-24">
          {/* 主路容器 */}
          <div className="relative">
            {/* 主路节点 */}
            <div className="relative flex justify-between items-start">
              {/* 主路连接线和动画 */}
              {mainStagesTranslated.map((stage, index) => {
                if (index >= mainStagesTranslated.length - 1) return null;
                const fromStatus = getMainNodeStatus(index, stage.id);
                const toStatus = getMainNodeStatus(index + 1, mainStagesTranslated[index + 1].id);
                
                const isCompleted = fromStatus === 'completed' && toStatus === 'completed';
                const isPendingConnector = fromStatus === 'pending' && toStatus === 'pending';
                
                // 计算连接线的位置（对齐节点圆心，节点高度48px，圆心在24px处）
                const leftPercent = ((index + 0.5) * 100) / mainStagesTranslated.length;
                const widthPercent = 100 / mainStagesTranslated.length;

                return (
                  <div
                    key={`main-connector-${index}`}
                    className="absolute z-10"
                    style={{
                      left: `${leftPercent}%`,
                      width: `${widthPercent}%`,
                      top: '22px', // 对齐节点圆心 (48px / 2 - 2px)
                      height: '4px',
                    }}
                  >
                    {isCompleted ? (
                      // 已完成的连接线：显示电流脉冲动画（使用 sage 色系）
                      <div className="w-full h-full">
                        <GradientTracing
                          width={200}
                          height={4}
                          baseColor="#4d6a5b"
                          gradientColors={["#5f8a70", "#7ba88d", "#98c4a9"]}
                          animationDuration={1.5}
                          strokeWidth={3}
                          path={`M0,2 L200,2`}
                          animate={true}
                        />
                      </div>
                    ) : isPendingConnector ? (
                      // 待处理的连接线：虚线
                      <div className="w-full h-0 border-t-2 border-dashed border-gray-300" />
                    ) : (
                      // 其他状态的连接线
                      <div
                        className={cn(
                          'w-full h-1 rounded-full transition-all duration-500',
                          fromStatus === 'completed' && 'bg-sage-600',
                          fromStatus === 'current' && 'bg-gradient-to-r from-sage-500 to-sage-300',
                          fromStatus === 'failed' && 'bg-red-500',
                          fromStatus === 'pending' && 'bg-gray-300'
                        )}
                      />
                    )}
                  </div>
                );
              })}

              {/* 主路节点按钮 */}
              {mainStagesTranslated.map((stage, index) => {
                const nodeStatus = getMainNodeStatus(index, stage.id);
                const isActive = nodeStatus === 'current';
                const isCompleteNode = nodeStatus === 'completed';
                const isFailedNode = nodeStatus === 'failed';
                const isPending = nodeStatus === 'pending';
                // ✅ 同样用 mainStagesTranslated 计算，避免 turboMode 索引偏移
                const isNextUp = isPending && index === mainStagesTranslated.findIndex(s => s.id === stepLocation.stageId) + 1;

                // Human Review 特殊处理
                // 当 reviewStatus 为 'rejected' 时隐藏面板，改为显示审核分支节点（计划/编辑）
                // 这样用户提交反馈后，能立即看到分支节点以 pending 状态等待后端执行
                const isReviewStage = stage.id === 'review';
                const showHumanReviewPanel =
                  isReviewStage &&
                  isHumanReviewActive &&
                  Boolean(taskId) &&
                  reviewStatus !== 'rejected';

                // 是否有激活的分支
                const hasBranch = stage.id === 'validate' || stage.id === 'review';
                const isValidationBranchActive = stepLocation.isOnBranch && stepLocation.branchType === 'validation' && stage.id === 'validate';
                const isReviewBranchActive = stepLocation.isOnBranch && stepLocation.branchType === 'review' && stage.id === 'review';

                return (
                  <div
                    key={stage.id}
                    className="relative flex flex-col items-center"
                    style={{ width: `${100 / mainStagesTranslated.length}%` }}
                  >
                    {/* 上方分支（Review 分支） - 位于节点上方，需要足够空间 */}
                    {stage.id === 'review' && !showHumanReviewPanel && (
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 w-full mb-2">
                        <BranchNodes
                          branch={reviewBranchTranslated}
                          branchType="review"
                          isActive={isReviewBranchActive}
                          getNodeStatus={(idx, id) => getBranchNodeStatus('review', idx, id)}
                          getNodeIcon={getNodeIcon}
                          renderNodeDuration={renderNodeDuration}
                          renderLoadingHint={renderNodeLoadingHint}
                          selectedNodeId={selectedNodeId}
                          onNodeSelect={onNodeSelect}
                        />
                      </div>
                    )}

                    {/* 主路节点 */}
                    <div className="flex flex-col items-center relative z-20">
                      <button
                        onClick={() => onNodeSelect?.(stage.id)}
                        className={cn(
                          'relative flex items-center justify-center w-12 h-12 rounded-full border-4 transition-all duration-300 cursor-pointer hover:scale-105',
                          isCompleteNode && 'bg-sage-600 border-sage-600 text-white shadow-md shadow-sage-600/30',
                          isActive && 'bg-sage-500 border-sage-500 text-white shadow-lg shadow-sage-500/50 scale-110',
                          isFailedNode && 'bg-red-500 border-red-500 text-white shadow-md shadow-red-500/30',
                          isPending && !isNextUp && 'bg-white border-gray-300 text-gray-400',
                          isNextUp && 'bg-sage-50 border-sage-400 text-sage-600 animate-pulse',
                          selectedNodeId === stage.id && 'ring-4 ring-sage-400/50 border-sage-500 shadow-xl shadow-sage-500/40'
                        )}
                      >
                        {getNodeIcon(nodeStatus, stage.id)}
                      </button>

                      <div className="mt-3 text-center space-y-1 max-w-[128px]">
                        <p
                          className={cn(
                            'text-xs font-medium transition-colors',
                            isActive && 'text-foreground font-semibold',
                            isCompleteNode && 'text-sage-700 font-medium',
                            isFailedNode && 'text-red-700 font-medium',
                            isNextUp && 'text-sage-700 font-medium',
                            isPending && !isNextUp && 'text-gray-500 font-normal'
                          )}
                        >
                          {stage.shortLabel}
                        </p>
                        <div className="flex justify-center">
                          {renderNodeDuration(stage.id, nodeStatus)}
                        </div>
                        <div className="flex justify-center">
                          {renderNodeLoadingHint(stage.id, nodeStatus, showHumanReviewPanel)}
                        </div>
                        <p 
                          className={cn(
                            'text-[10px] hidden sm:block transition-colors',
                            isActive && 'text-muted-foreground',
                            isCompleteNode && 'text-sage-600/80',
                            isFailedNode && 'text-red-600/70',
                            isNextUp && 'text-sage-600/80',
                            isPending && !isNextUp && 'text-gray-500'
                          )}
                        >
                          {stage.description}
                        </p>
                        {/* 内容生成阶段：节点数和预估时长提示 */}
                        {stage.id === 'content' && isActive && totalConcepts > 0 && (
                          <p className="text-[10px] hidden sm:block text-amber-600 font-medium leading-tight mt-0.5">
                            {totalConcepts} nodes · ~{Math.ceil(totalConcepts / 5) * 2} min
                          </p>
                        )}
                      </div>
                    </div>

                    {/* 下方分支（Validation 分支） - 位于节点及标题下方 */}
                    {stage.id === 'validate' && (
                      <div className="absolute top-full left-1/2 -translate-x-1/2 w-full mt-2">
                        <BranchNodes
                          branch={validationBranchTranslated}
                          branchType="validation"
                          isActive={isValidationBranchActive}
                          getNodeStatus={(idx, id) => getBranchNodeStatus('validation', idx, id)}
                          getNodeIcon={getNodeIcon}
                          renderNodeDuration={renderNodeDuration}
                          renderLoadingHint={renderNodeLoadingHint}
                          selectedNodeId={selectedNodeId}
                          onNodeSelect={onNodeSelect}
                        />
                      </div>
                    )}

                    {/* Human Review 内嵌面板（替代上方分支） */}
                    {showHumanReviewPanel && (
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 w-full max-w-[220px] mb-4 animate-in fade-in slide-in-from-top-2 duration-300">
                        <HumanReviewInlinePanel
                          roadmapTitle={roadmapTitle}
                          stagesCount={stagesCount}
                          reviewStatus={reviewStatus}
                          feedback={feedback}
                          showFeedback={showFeedback}
                          reviewError={reviewError}
                          onApprove={handleApprove}
                          onReject={handleReject}
                          onFeedbackChange={setFeedback}
                          onCancelFeedback={handleCancelFeedback}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* 当前步骤详细信息 */}
        {!isCompleted && !isFailed && currentStep && !isHumanReviewActive && (
          <div className="pt-4 border-t">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">{t('currentStep')}:</span>
              <Badge variant="outline" className="font-mono text-xs">
                {currentStep}
              </Badge>
              {editSource && (
                <Badge variant="secondary" className="text-xs">
                  {editSource === 'validation_failed' ? t('autoFix') : t('userFeedback')}
                </Badge>
              )}
            </div>
          </div>
        )}
        </div>
      </Card>
      
      {/* 节点详情侧边面板 */}
      {selectedNodeId && (
        <NodeDetailPanel
          selectedNodeId={selectedNodeId}
          executionLogs={executionLogs}
          onClose={() => onNodeSelect?.(null)}
        />
      )}
    </>
  );
}

// ============================================================================
// 分支节点组件
// ============================================================================

interface BranchNodesProps {
  branch: WorkflowBranch;
  branchType: 'validation' | 'review';
  isActive: boolean;
  getNodeStatus: (index: number, nodeId: string) => NodeStatus;
  getNodeIcon: (status: NodeStatus, nodeId: string) => React.ReactNode;
  renderNodeDuration: (nodeId: string, nodeStatus: NodeStatus) => React.ReactNode;
  renderLoadingHint: (nodeId: string, nodeStatus: NodeStatus) => React.ReactNode;
  selectedNodeId?: string | null;
  onNodeSelect?: (nodeId: string | null) => void;
}

function BranchNodes({
  branch,
  branchType,
  isActive,
  getNodeStatus,
  getNodeIcon,
  renderNodeDuration,
  renderLoadingHint,
  selectedNodeId,
  onNodeSelect,
}: BranchNodesProps) {
  const isTopBranch = branch.position === 'top';
  
  return (
    <div className="relative w-full flex flex-col items-center">
      {/* 虚线连接到主路节点（底部分支：虚线在上方） */}
      {!isTopBranch && (
        <div 
          className={cn(
            'w-0.5 border-l-2 border-dashed transition-colors duration-300 h-4 mb-1',
            isActive ? 'border-sage-400' : 'border-gray-300'
          )}
        />
      )}

      {/* 分支节点容器 */}
      <div 
        className={cn(
          'flex items-center justify-center gap-3 py-2 px-3 rounded-xl border-2 transition-all duration-300 bg-white shadow-sm',
          isActive ? 'border-sage-400 shadow-sage-200/50' : 'border-gray-200'
        )}
      >
        {/* 分支节点 */}
        {branch.nodes.map((node, index) => {
          const nodeStatus = getNodeStatus(index, node.id);
          const isCurrentNode = nodeStatus === 'current';
          const isCompleteNode = nodeStatus === 'completed';
          const isFailedNode = nodeStatus === 'failed';

          return (
            <div key={node.id} className="flex items-start gap-2">
              {/* 连接箭头 */}
              {index > 0 && (
                <div className="relative w-6 h-1 mt-[19px]">
                  {isCompleteNode ? (
                    // 已完成的连接线：显示电流脉冲动画（sage 色系）
                    <GradientTracing
                      width={24}
                      height={4}
                      baseColor="#4d6a5b"
                      gradientColors={["#5f8a70", "#7ba88d", "#98c4a9"]}
                      animationDuration={1}
                      strokeWidth={2}
                      path={`M0,2 L24,2`}
                      animate={true}
                    />
                  ) : (
                    <div className={cn(
                      'w-full h-0.5 rounded-full transition-colors duration-300',
                      isCurrentNode ? 'bg-sage-400' : 'bg-gray-300'
                    )} />
                  )}
                </div>
              )}
              
              {/* 节点 */}
              <div className="flex flex-col items-center gap-1">
                <button
                  onClick={() => onNodeSelect?.(node.id)}
                  className={cn(
                    'flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all duration-300 cursor-pointer hover:scale-105',
                    isCompleteNode && 'bg-sage-600 border-sage-600 text-white shadow-md shadow-sage-600/30',
                    isCurrentNode && 'bg-sage-500 border-sage-500 text-white shadow-lg shadow-sage-500/50 scale-110',
                    isFailedNode && 'bg-red-500 border-red-500 text-white shadow-md shadow-red-500/30',
                    !isCompleteNode && !isCurrentNode && !isFailedNode && 'bg-white border-gray-300 text-gray-400',
                    selectedNodeId === node.id && 'ring-3 ring-sage-400/50 border-sage-500 shadow-lg shadow-sage-500/40'
                  )}
                >
                  {getNodeIcon(nodeStatus, node.id)}
                </button>
                <span className={cn(
                  'text-[10px] font-medium transition-colors duration-300',
                  isCurrentNode && 'text-sage-700',
                  isCompleteNode && 'text-sage-600',
                  isFailedNode && 'text-red-600',
                  !isCompleteNode && !isCurrentNode && !isFailedNode && 'text-gray-500'
                )}>
                  {node.shortLabel}
                </span>
                {renderNodeDuration(node.id, nodeStatus)}
                {renderLoadingHint(node.id, nodeStatus)}
              </div>
            </div>
          );
        })}
      </div>

      {/* 虚线连接到主路节点（顶部分支：虚线在下方） */}
      {isTopBranch && (
        <div 
          className={cn(
            'w-0.5 border-l-2 border-dashed transition-colors duration-300 h-4 mt-1',
            isActive ? 'border-sage-400' : 'border-gray-300'
          )}
        />
      )}
    </div>
  );
}

interface NodeLoadingHintProps {
  messages: string[];
}

function NodeLoadingHint({ messages }: NodeLoadingHintProps) {
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    setMessageIndex(0);

    if (messages.length <= 1) {
      return;
    }

    const timer = window.setInterval(() => {
      setMessageIndex((prevIndex) => (prevIndex + 1) % messages.length);
    }, 2200);

    return () => {
      window.clearInterval(timer);
    };
  }, [messages]);

  if (messages.length === 0) {
    return null;
  }

  const activeMessage = messages[messageIndex];

  return (
    <div className="flex min-h-5 items-center justify-center" aria-live="polite" aria-atomic="true">
      <div className="relative h-4 w-[136px] overflow-hidden text-[10px] leading-4 text-sage-700/80">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={`${messageIndex}-${activeMessage}`}
            initial={{ opacity: 0, y: 10, filter: 'blur(6px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            exit={{ opacity: 0, y: -10, filter: 'blur(6px)' }}
            transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
            className="absolute inset-0 flex items-center justify-center px-1"
          >
            <span className="block w-full text-center truncate">
              {activeMessage}
            </span>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

// ============================================================================
// Human Review 内嵌面板组件
// ============================================================================

interface HumanReviewInlinePanelProps {
  roadmapTitle?: string;
  stagesCount: number;
  reviewStatus: 'waiting' | 'submitting' | 'approved' | 'rejected';
  feedback: string;
  showFeedback: boolean;
  reviewError: string | null;
  onApprove: () => void;
  onReject: () => void;
  onFeedbackChange: (value: string) => void;
  onCancelFeedback: () => void;
}

function HumanReviewInlinePanel({
  roadmapTitle,
  stagesCount,
  reviewStatus,
  feedback,
  showFeedback,
  reviewError,
  onApprove,
  onReject,
  onFeedbackChange,
  onCancelFeedback,
}: HumanReviewInlinePanelProps) {
  const t = useTranslations('taskDetail');

  if (reviewStatus === 'approved') {
    return (
      <div className="p-4 bg-accent/5 border-2 border-accent/30 rounded-xl shadow-md">
        <div className="flex items-center gap-2 text-accent">
          <CheckCircle2 className="w-4 h-4" />
          <span className="text-sm font-medium">{t('approvedStatus')}</span>
        </div>
        <p className="text-xs text-accent/80 mt-1">
          {t('contentGenerationSoon')}
        </p>
      </div>
    );
  }

  if (reviewStatus === 'rejected') {
    return (
      <div className="p-4 bg-muted/40 border-2 border-muted rounded-xl shadow-md">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm font-medium">{t('feedbackSubmitted')}</span>
        </div>
        <p className="text-xs text-muted-foreground/80 mt-1">
          {t('processingFeedback')}
        </p>
      </div>
    );
  }

  return (
    <div className="p-3 bg-accent/5 border-2 border-accent rounded-xl shadow-md space-y-2.5">
      <div className="text-center">
        <p className="text-xs text-accent/80 font-medium">{t('reviewRequired')}</p>
        {roadmapTitle && (
          <p className="text-sm font-semibold text-foreground truncate" title={roadmapTitle}>
            {roadmapTitle}
          </p>
        )}
        <p className="text-[10px] text-accent/70">{t('stagesCount', { count: stagesCount })}</p>
      </div>

      {reviewError && (
        <div className="p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">
          {reviewError}
        </div>
      )}

      {showFeedback && (
        <div className="space-y-2">
          <Textarea
            placeholder={t('describeFeedback')}
            value={feedback}
            onChange={(e) => onFeedbackChange(e.target.value)}
            rows={2}
            className="resize-none text-xs"
            disabled={reviewStatus === 'submitting'}
          />
        </div>
      )}

      <div className="flex items-center justify-center gap-1.5 w-full">
        {showFeedback ? (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={onCancelFeedback}
              disabled={reviewStatus === 'submitting'}
              className="h-7 text-xs px-2 flex-1 min-w-0"
            >
              {t('cancel')}
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={onReject}
              disabled={reviewStatus === 'submitting' || !feedback.trim()}
              className="h-7 text-xs px-2 flex-1 min-w-0"
            >
              {reviewStatus === 'submitting' ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <X className="w-3 h-3 mr-1" />
              )}
              {t('submit')}
            </Button>
          </>
        ) : (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={onReject}
              disabled={reviewStatus === 'submitting'}
              className="h-7 text-xs px-2.5 flex-1 min-w-0"
            >
              <X className="w-3 h-3 mr-1" />
              {t('change')}
            </Button>
            <Button
              size="sm"
              onClick={onApprove}
              disabled={reviewStatus === 'submitting'}
              className="h-7 text-xs px-2.5 flex-1 min-w-0 bg-accent hover:bg-accent/90 text-accent-foreground"
            >
              {reviewStatus === 'submitting' ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <Check className="w-3 h-3 mr-1" />
              )}
              {t('approve')}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

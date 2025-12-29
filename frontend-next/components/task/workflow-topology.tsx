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
 */

import { useState, useEffect, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { GradientTracing } from '@/components/ui/gradient-tracing';
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
import { approveRoadmap } from '@/lib/api/endpoints';
import { NodeDetailPanel } from './node-detail-panel';
import type { ExecutionLog } from '@/types/content-generation';

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
 * 主路节点
 * Analysis → Design → Validate → Review → Content
 */
const MAIN_STAGES: WorkflowNode[] = [
  {
    id: 'analysis',
    label: 'Intent Analysis',
    shortLabel: 'Analysis',
    description: 'Analyzing learning goals',
    steps: ['init', 'queued', 'starting', 'intent_analysis'],
  },
  {
    id: 'design',
    label: 'Curriculum Design',
    shortLabel: 'Design',
    description: 'Designing course structure',
    steps: ['curriculum_design', 'framework_generation'],
  },
  {
    id: 'validate',
    label: 'Structure Validation',
    shortLabel: 'Validate',
    description: 'Validating roadmap logic',
    steps: ['structure_validation'],
  },
  {
    id: 'review',
    label: 'Human Review',
    shortLabel: 'Review',
    description: 'Awaiting confirmation',
    steps: ['human_review', 'human_review_pending'],
  },
  {
    id: 'content',
    label: 'Content Generation',
    shortLabel: 'Content',
    description: 'Generating materials',
    steps: ['content_generation', 'tutorial_generation', 'resource_recommendation', 'quiz_generation'],
  },
];

/**
 * 验证分支：验证失败触发（显示在下方）
 * Validate → Plan1 → Edit1 → 回到 Validate
 */
const VALIDATION_BRANCH: WorkflowBranch = {
  id: 'validation_branch',
  triggerNode: 'validate',
  returnNode: 'validate',
  editSource: 'validation_failed',
  position: 'bottom',
  nodes: [
    {
      id: 'plan1',
      label: 'Edit Plan Analysis',
      shortLabel: 'Plan',
      description: 'Analyzing issues',
      steps: ['validation_edit_plan_analysis'],
    },
    {
      id: 'edit1',
      label: 'Roadmap Edit',
      shortLabel: 'Edit',
      description: 'Fixing issues',
      steps: ['roadmap_edit'],
    },
  ],
};

/**
 * 审核分支：人工审核拒绝触发（显示在上方）
 * Review → Plan2 → Edit2 → 回到 Review
 */
const REVIEW_BRANCH: WorkflowBranch = {
  id: 'review_branch',
  triggerNode: 'review',
  returnNode: 'review',
  editSource: 'human_review',
  position: 'top',
  nodes: [
    {
      id: 'plan2',
      label: 'Edit Plan Analysis',
      shortLabel: 'Plan',
      description: 'Analyzing feedback',
      steps: ['edit_plan_analysis'],
    },
    {
      id: 'edit2',
      label: 'Roadmap Edit',
      shortLabel: 'Edit',
      description: 'Applying changes',
      steps: ['roadmap_edit'],
    },
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
  
  // 检查主路节点
  for (const stage of MAIN_STAGES) {
    if (stage.steps.includes(currentStep)) {
      return { stageId: stage.id, isOnBranch: false };
    }
  }

  // 检查验证分支
  for (let i = 0; i < VALIDATION_BRANCH.nodes.length; i++) {
    const node = VALIDATION_BRANCH.nodes[i];
    if (node.steps.includes(currentStep)) {
      // 特殊处理 roadmap_edit：需要根据 editSource 判断
      if (currentStep === 'roadmap_edit') {
        if (editSource === 'validation_failed') {
          return { stageId: node.id, isOnBranch: true, branchType: 'validation', branchNodeIndex: i };
        }
        // 如果是 human_review，继续检查审核分支
        continue;
      }
      return { stageId: node.id, isOnBranch: true, branchType: 'validation', branchNodeIndex: i };
    }
  }

  // 检查审核分支
  for (let i = 0; i < REVIEW_BRANCH.nodes.length; i++) {
    const node = REVIEW_BRANCH.nodes[i];
    if (node.steps.includes(currentStep)) {
      // 特殊处理 roadmap_edit：需要根据 editSource 判断
      if (currentStep === 'roadmap_edit') {
        if (editSource === 'human_review') {
          return { stageId: node.id, isOnBranch: true, branchType: 'review', branchNodeIndex: i };
        }
        continue;
      }
      return { stageId: node.id, isOnBranch: true, branchType: 'review', branchNodeIndex: i };
    }
  }

  // 默认返回第一个主路节点
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
  /** 执行日志（用于判断分支是否被触发过） */
  executionLogs?: ExecutionLog[];
  /** Human Review 完成回调 */
  onHumanReviewComplete?: () => void;
  /** 当前选中的节点ID */
  selectedNodeId?: string | null;
  /** 节点选择回调 */
  onNodeSelect?: (nodeId: string | null) => void;
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
  onHumanReviewComplete,
  selectedNodeId = null,
  onNodeSelect,
}: WorkflowTopologyProps) {
  // Human Review 状态
  const [reviewStatus, setReviewStatus] = useState<'waiting' | 'submitting' | 'approved' | 'rejected'>('waiting');
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

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

  // 检查分支是否被触发过（通过执行日志的 details.edit_source 判断）
  // edit_source === 'validation_failed': 验证分支
  // edit_source === 'human_review': 审核分支
  const validationBranchTriggered = executionLogs.some(
    log => 
      (log.step === 'validation_edit_plan_analysis' || log.step === 'roadmap_edit') &&
      log.details?.edit_source === 'validation_failed'
  );
  const reviewBranchTriggered = executionLogs.some(
    log => 
      (log.step === 'edit_plan_analysis' || log.step === 'roadmap_edit') &&
      log.details?.edit_source === 'human_review'
  );

  /**
   * 获取主路节点状态
   */
  const getMainNodeStatus = (nodeIndex: number, nodeId: string): NodeStatus => {
    if (isCompleted) return 'completed';
    if (isFailed && stepLocation.stageId === nodeId && !stepLocation.isOnBranch) return 'failed';
    
    const currentMainIndex = getMainStageIndex(
      stepLocation.isOnBranch 
        ? (stepLocation.branchType === 'validation' ? 'validate' : 'review')
        : stepLocation.stageId
    );

    // 如果当前在分支上
    if (stepLocation.isOnBranch) {
      const triggerIndex = getMainStageIndex(
        stepLocation.branchType === 'validation' ? 'validate' : 'review'
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
   * Human Review 操作处理
   */
  const handleApprove = async () => {
    if (!taskId) return;
    try {
      setReviewStatus('submitting');
      setReviewError(null);
      await approveRoadmap(taskId, true);
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
      await approveRoadmap(taskId, false, feedback);
      // 反馈提交成功后，重置为 waiting 状态，让工作流自然过渡
      // 不显示 'rejected' 状态的确认面板
      setReviewStatus('waiting');
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
          <h2 className="text-lg font-serif font-semibold">Workflow Progress</h2>
          {isCompleted && (
            <Badge className="bg-sage-600 hover:bg-sage-700 text-white">
              <CheckCircle2 className="w-3 h-3 mr-1" />
              Completed
            </Badge>
          )}
          {isFailed && (
            <Badge variant="destructive">
              <XCircle className="w-3 h-3 mr-1" />
              Failed
            </Badge>
          )}
          {!isCompleted && !isFailed && (
            <Badge variant="secondary" className="animate-pulse">
              <Clock className="w-3 h-3 mr-1" />
              In Progress
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
              {MAIN_STAGES.map((stage, index) => {
                if (index >= MAIN_STAGES.length - 1) return null;
                const fromStatus = getMainNodeStatus(index, stage.id);
                const toStatus = getMainNodeStatus(index + 1, MAIN_STAGES[index + 1].id);
                
                const isCompleted = fromStatus === 'completed' && toStatus === 'completed';
                const isPendingConnector = fromStatus === 'pending' && toStatus === 'pending';
                
                // 计算连接线的位置（对齐节点圆心，节点高度48px，圆心在24px处）
                const leftPercent = ((index + 0.5) * 100) / MAIN_STAGES.length;
                const widthPercent = 100 / MAIN_STAGES.length;

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
              {MAIN_STAGES.map((stage, index) => {
                const nodeStatus = getMainNodeStatus(index, stage.id);
                const isActive = nodeStatus === 'current';
                const isCompleteNode = nodeStatus === 'completed';
                const isFailedNode = nodeStatus === 'failed';
                const isPending = nodeStatus === 'pending';
                const isNextUp = isPending && index === getMainStageIndex(stepLocation.stageId) + 1;

                // Human Review 特殊处理
                const isReviewStage = stage.id === 'review';
                const showHumanReviewPanel = isReviewStage && isHumanReviewActive && taskId;

                // 是否有激活的分支
                const hasBranch = stage.id === 'validate' || stage.id === 'review';
                const isValidationBranchActive = stepLocation.isOnBranch && stepLocation.branchType === 'validation' && stage.id === 'validate';
                const isReviewBranchActive = stepLocation.isOnBranch && stepLocation.branchType === 'review' && stage.id === 'review';

                return (
                  <div
                    key={stage.id}
                    className="relative flex flex-col items-center"
                    style={{ width: `${100 / MAIN_STAGES.length}%` }}
                  >
                    {/* 上方分支（Review 分支） - 位于节点上方，需要足够空间 */}
                    {stage.id === 'review' && !showHumanReviewPanel && (
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 w-full mb-2">
                        <BranchNodes
                          branch={REVIEW_BRANCH}
                          branchType="review"
                          isActive={isReviewBranchActive}
                          getNodeStatus={(idx, id) => getBranchNodeStatus('review', idx, id)}
                          getNodeIcon={getNodeIcon}
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

                      <div className="mt-3 text-center space-y-1 max-w-[90px]">
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
                      </div>
                    </div>

                    {/* 下方分支（Validation 分支） - 位于节点及标题下方 */}
                    {stage.id === 'validate' && (
                      <div className="absolute top-full left-1/2 -translate-x-1/2 w-full mt-2">
                        <BranchNodes
                          branch={VALIDATION_BRANCH}
                          branchType="validation"
                          isActive={isValidationBranchActive}
                          getNodeStatus={(idx, id) => getBranchNodeStatus('validation', idx, id)}
                          getNodeIcon={getNodeIcon}
                          selectedNodeId={selectedNodeId}
                          onNodeSelect={onNodeSelect}
                        />
                      </div>
                    )}

                    {/* Human Review 内嵌面板（替代上方分支） */}
                    {showHumanReviewPanel && (
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 w-full max-w-[280px] mb-4 animate-in fade-in slide-in-from-top-2 duration-300">
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
              <span className="text-muted-foreground">Current Step:</span>
              <Badge variant="outline" className="font-mono text-xs">
                {currentStep}
              </Badge>
              {editSource && (
                <Badge variant="secondary" className="text-xs">
                  {editSource === 'validation_failed' ? 'Auto-fix' : 'User feedback'}
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
  selectedNodeId?: string | null;
  onNodeSelect?: (nodeId: string | null) => void;
}

function BranchNodes({ branch, branchType, isActive, getNodeStatus, getNodeIcon, selectedNodeId, onNodeSelect }: BranchNodesProps) {
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
  if (reviewStatus === 'approved') {
    return (
      <div className="p-4 bg-accent/5 border-2 border-accent/30 rounded-xl shadow-md">
        <div className="flex items-center gap-2 text-accent">
          <CheckCircle2 className="w-4 h-4" />
          <span className="text-sm font-medium">Approved</span>
        </div>
        <p className="text-xs text-accent/80 mt-1">
          Content generation will begin shortly.
        </p>
      </div>
    );
  }

  // 移除 rejected 状态的显示
  // 用户提交反馈后，直接让工作流过渡到下一步，不显示中间确认面板

  return (
    <div className="p-4 bg-accent/5 border-2 border-accent rounded-xl shadow-md space-y-3">
      <div className="text-center">
        <p className="text-xs text-accent/80 font-medium">Review Required</p>
        {roadmapTitle && (
          <p className="text-sm font-semibold text-foreground truncate" title={roadmapTitle}>
            {roadmapTitle}
          </p>
        )}
        <p className="text-[10px] text-accent/70">{stagesCount} stages</p>
      </div>

      {reviewError && (
        <div className="p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">
          {reviewError}
        </div>
      )}

      {showFeedback && (
        <div className="space-y-2">
          <Textarea
            placeholder="Describe what needs to be changed..."
            value={feedback}
            onChange={(e) => onFeedbackChange(e.target.value)}
            rows={2}
            className="resize-none text-xs"
            disabled={reviewStatus === 'submitting'}
          />
        </div>
      )}

      <div className="flex items-center justify-center gap-2">
        {showFeedback ? (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={onCancelFeedback}
              disabled={reviewStatus === 'submitting'}
              className="h-7 text-xs"
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={onReject}
              disabled={reviewStatus === 'submitting' || !feedback.trim()}
              className="h-7 text-xs"
            >
              {reviewStatus === 'submitting' ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <X className="w-3 h-3 mr-1" />
              )}
              Submit
            </Button>
          </>
        ) : (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={onReject}
              disabled={reviewStatus === 'submitting'}
              className="h-7 text-xs"
            >
              <X className="w-3 h-3 mr-1" />
              Change
            </Button>
            <Button
              size="sm"
              onClick={onApprove}
              disabled={reviewStatus === 'submitting'}
              className="h-7 text-xs bg-accent hover:bg-accent/90 text-accent-foreground"
            >
              {reviewStatus === 'submitting' ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <Check className="w-3 h-3 mr-1" />
              )}
              Approve
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

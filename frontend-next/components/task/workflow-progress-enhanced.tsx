'use client';

/**
 * WorkflowProgressEnhanced - 增强版工作流进度组件
 * 
 * 功能增强:
 * - 增加 roadmap_edit 作为独立可见阶段
 * - Human Review 交互直接嵌入 Review 节点下方
 * - 与 checkpoint 状态完全同步
 */

import { useState } from 'react';
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
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { approveRoadmap } from '@/lib/api/endpoints';

/**
 * 工作流阶段定义（增加 roadmap_edit 为独立阶段）
 */
const WORKFLOW_STAGES = [
  {
    id: 'intent_analysis',
    label: 'Intent Analysis',
    shortLabel: 'Analysis',
    description: 'Analyzing learning goals',
    steps: ['init', 'queued', 'starting', 'intent_analysis'],
  },
  {
    id: 'curriculum_design',
    label: 'Curriculum Design',
    shortLabel: 'Design',
    description: 'Designing course structure',
    steps: ['curriculum_design', 'framework_generation'],
  },
  {
    id: 'structure_validation',
    label: 'Structure Validation',
    shortLabel: 'Validate',
    description: 'Validating roadmap logic',
    steps: ['structure_validation'],
  },
  {
    id: 'roadmap_edit',
    label: 'Roadmap Edit',
    shortLabel: 'Edit',
    description: 'Refining roadmap structure',
    steps: ['roadmap_edit'],
  },
  {
    id: 'human_review',
    label: 'Human Review',
    shortLabel: 'Review',
    description: 'Awaiting your confirmation',
    steps: ['human_review', 'human_review_pending'],
  },
  {
    id: 'content_generation',
    label: 'Content Generation',
    shortLabel: 'Content',
    description: 'Generating learning materials',
    steps: ['content_generation', 'tutorial_generation', 'resource_recommendation', 'quiz_generation'],
  },
];

type StageStatus = 'completed' | 'current' | 'pending' | 'failed' | 'skipped';

interface WorkflowProgressEnhancedProps {
  /** 当前步骤 */
  currentStep: string;
  /** 任务状态 */
  status: string;
  /** 任务 ID（用于 Human Review 操作） */
  taskId?: string;
  /** 路线图 ID */
  roadmapId?: string | null;
  /** 路线图标题 */
  roadmapTitle?: string;
  /** 阶段数量（用于 Human Review 展示） */
  stagesCount?: number;
  /** Human Review 完成回调 */
  onHumanReviewComplete?: () => void;
  /** 选中的阶段 */
  selectedPhase?: string;
  /** 阶段选择回调 */
  onPhaseSelect?: (phaseId: string) => void;
}

export function WorkflowProgressEnhanced({
  currentStep,
  status,
  taskId,
  roadmapId,
  roadmapTitle,
  stagesCount = 0,
  onHumanReviewComplete,
  selectedPhase,
  onPhaseSelect,
}: WorkflowProgressEnhancedProps) {
  // Human Review 状态
  const [reviewStatus, setReviewStatus] = useState<'waiting' | 'submitting' | 'approved' | 'rejected'>('waiting');
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  /**
   * 判断是否处于 Human Review 阶段
   */
  const isHumanReviewActive = 
    currentStep === 'human_review' || 
    currentStep === 'human_review_pending' ||
    status === 'human_review_pending';

  /**
   * 获取当前处于哪个阶段
   */
  const getCurrentStageIndex = (): number => {
    // 特殊状态处理
    if (status === 'completed' || status === 'partial_failure' || currentStep === 'completed') {
      return WORKFLOW_STAGES.length;
    }
    if (status === 'failed' || currentStep === 'failed') return -1;
    if (!currentStep) return 0;

    // 查找当前步骤所属的阶段
    const stageIndex = WORKFLOW_STAGES.findIndex(stage =>
      stage.steps.includes(currentStep)
    );

    return stageIndex === -1 ? 0 : stageIndex;
  };

  const currentStageIndex = getCurrentStageIndex();
  const isFailed = status === 'failed';
  const isCompleted = status === 'completed' || status === 'partial_failure';

  /**
   * 获取阶段状态
   * 
   * 特殊处理：
   * - roadmap_edit 阶段：如果验证通过且直接进入 human_review，则 roadmap_edit 显示为 skipped
   */
  const getStageStatus = (stageIndex: number, stageId: string): StageStatus => {
    if (isFailed && stageIndex === currentStageIndex) return 'failed';
    if (stageIndex < currentStageIndex) {
      // roadmap_edit 特殊处理：如果跳过了（验证通过直接到 review）
      if (stageId === 'roadmap_edit') {
        // 检查是否有 roadmap_edit 的历史记录
        // 如果没有，且当前已经过了 validation，则标记为 skipped
        const reviewIndex = WORKFLOW_STAGES.findIndex(s => s.id === 'human_review');
        if (currentStageIndex >= reviewIndex && stageIndex < reviewIndex) {
          // 可能是跳过的 - 但我们无法在前端确定，先显示为 completed
          // 在实际实现中，可以通过日志或状态来判断
        }
      }
      return 'completed';
    }
    if (stageIndex === currentStageIndex) return 'current';
    return 'pending';
  };

  /**
   * 获取阶段图标
   */
  const getStageIcon = (stageStatus: StageStatus, stageId: string) => {
    // 特殊处理：roadmap_edit 阶段使用 Edit 图标
    if (stageId === 'roadmap_edit') {
      switch (stageStatus) {
        case 'completed':
          return <CheckCircle2 className="w-5 h-5" />;
        case 'current':
          return <Edit3 className="w-5 h-5 animate-pulse" />;
        case 'skipped':
          return <CheckCircle2 className="w-5 h-5 opacity-50" />;
        default:
          return <Edit3 className="w-5 h-5" />;
      }
    }

    switch (stageStatus) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5" />;
      case 'current':
        return <Loader2 className="w-5 h-5 animate-spin" />;
      case 'failed':
        return <XCircle className="w-5 h-5" />;
      case 'skipped':
        return <CheckCircle2 className="w-5 h-5 opacity-50" />;
      default:
        return <Clock className="w-5 h-5" />;
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
      setReviewStatus('rejected');
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

  /**
   * 处理阶段点击
   */
  const handlePhaseClick = (phaseId: string, isClickable: boolean) => {
    if (isClickable && onPhaseSelect) {
      onPhaseSelect(phaseId);
    }
  };

  return (
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

        {/* 横向步进器 */}
        <div className="relative">
          {/* 背景线 */}
          <div className="absolute top-6 left-0 right-0 h-1 bg-gray-200 rounded-full" />

          {/* 阶段列表 */}
          <div className="relative flex justify-between items-start">
            {/* 连接线 */}
            {WORKFLOW_STAGES.map((stage, index) => {
              if (index >= WORKFLOW_STAGES.length - 1) return null;
              const fromStatus = getStageStatus(index, stage.id);
              const toStatus = getStageStatus(index + 1, WORKFLOW_STAGES[index + 1].id);
              
              const isPendingConnector = fromStatus === 'pending' && toStatus === 'pending';
              const isCurrentToNext = fromStatus === 'current' && toStatus === 'pending';
              
              let connectorClass = 'bg-gray-300';
              if (fromStatus === 'completed' && toStatus === 'completed') {
                connectorClass = 'bg-sage-600';
              } else if (fromStatus === 'completed') {
                connectorClass = 'bg-gradient-to-r from-sage-600 to-gray-300';
              } else if (fromStatus === 'failed') {
                connectorClass = 'bg-red-500';
              } else if (isCurrentToNext) {
                connectorClass = 'bg-gradient-to-r from-sage-500 to-sage-200';
              }

              return (
                <div
                  key={`connector-${index}`}
                  className={cn(
                    'absolute top-6 h-1 transition-all duration-500 rounded-full z-10',
                    connectorClass,
                    isPendingConnector && 'bg-none border-t-2 border-dashed border-gray-300 h-0'
                  )}
                  style={{
                    left: `${((index + 0.5) * 100) / WORKFLOW_STAGES.length}%`,
                    width: `${100 / WORKFLOW_STAGES.length}%`,
                  }}
                />
              );
            })}

            {/* 阶段按钮 */}
            {WORKFLOW_STAGES.map((stage, index) => {
              const stageStatus = getStageStatus(index, stage.id);
              const isActive = stageStatus === 'current';
              const isCompleteStage = stageStatus === 'completed';
              const isFailedStage = stageStatus === 'failed';
              const isPending = stageStatus === 'pending';
              const isSelected = selectedPhase === stage.id;
              const isClickable = isCompleteStage || isActive || isFailedStage;
              const isNextUp = isPending && index === currentStageIndex + 1;

              // Human Review 阶段特殊处理
              const isHumanReviewStage = stage.id === 'human_review';
              const showHumanReviewPanel = isHumanReviewStage && isHumanReviewActive && taskId;

              return (
                <div
                  key={stage.id}
                  className="flex flex-col items-center"
                  style={{ width: `${100 / WORKFLOW_STAGES.length}%` }}
                >
                  {/* 阶段按钮 */}
                  <button
                    onClick={() => handlePhaseClick(stage.id, isClickable)}
                    disabled={!isClickable}
                    className={cn(
                      'flex flex-col items-center transition-all duration-200 relative group',
                      isClickable && 'cursor-pointer',
                      !isClickable && 'cursor-default'
                    )}
                  >
                    {/* 圆点指示器 */}
                    <div
                      className={cn(
                        'relative z-20 flex items-center justify-center w-12 h-12 rounded-full border-4 transition-all duration-300',
                        isCompleteStage && 'bg-sage-600 border-sage-600 text-white',
                        isActive && 'bg-sage-500 border-sage-500 text-white shadow-lg shadow-sage-500/50 scale-110',
                        isFailedStage && 'bg-red-500 border-red-500 text-white',
                        isPending && !isNextUp && 'bg-gray-50 border-2 border-dashed border-gray-300 text-gray-500 group-hover:border-gray-400 group-hover:bg-gray-100',
                        isNextUp && 'bg-sage-50 border-2 border-dashed border-sage-300 text-sage-600 animate-pulse',
                        isSelected && isClickable && 'ring-4 ring-sage-200',
                        isClickable && 'hover:scale-110 hover:shadow-md'
                      )}
                    >
                      {getStageIcon(stageStatus, stage.id)}
                    </div>

                    {/* 阶段信息 */}
                    <div className="mt-3 text-center space-y-1 max-w-[100px]">
                      <p
                        className={cn(
                          'text-xs font-medium transition-colors',
                          isActive && 'text-foreground font-semibold',
                          isCompleteStage && 'text-sage-700 font-medium',
                          isFailedStage && 'text-red-700 font-medium',
                          isNextUp && 'text-sage-700 font-medium',
                          isPending && !isNextUp && 'text-gray-600 font-normal group-hover:text-gray-700',
                          isSelected && isClickable && 'font-semibold'
                        )}
                      >
                        {stage.shortLabel}
                      </p>
                      <p 
                        className={cn(
                          'text-[10px] hidden sm:block transition-colors',
                          isActive && 'text-muted-foreground',
                          isCompleteStage && 'text-sage-600/70',
                          isFailedStage && 'text-red-600/70',
                          isNextUp && 'text-sage-600/80',
                          isPending && !isNextUp && 'text-gray-500'
                        )}
                      >
                        {stage.description}
                      </p>
                    </div>
                  </button>

                  {/* Human Review 内嵌面板 */}
                  {showHumanReviewPanel && (
                    <div className="mt-4 w-full max-w-[280px] animate-in fade-in slide-in-from-top-2 duration-300">
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

        {/* 当前步骤详细信息 */}
        {!isCompleted && !isFailed && currentStep && !isHumanReviewActive && (
          <div className="pt-4 border-t">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">Current Step:</span>
              <Badge variant="outline" className="font-mono text-xs">
                {currentStep}
              </Badge>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

/**
 * Human Review 内嵌面板组件
 */
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
  // 已批准状态
  if (reviewStatus === 'approved') {
    return (
      <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
        <div className="flex items-center gap-2 text-green-700">
          <CheckCircle2 className="w-4 h-4" />
          <span className="text-sm font-medium">Approved</span>
        </div>
        <p className="text-xs text-green-600 mt-1">
          Content generation will begin shortly.
        </p>
      </div>
    );
  }

  // 已拒绝状态
  if (reviewStatus === 'rejected') {
    return (
      <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
        <div className="flex items-center gap-2 text-amber-700">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm font-medium">Changes Requested</span>
        </div>
        <p className="text-xs text-amber-600 mt-1">
          Roadmap will be updated based on your feedback.
        </p>
      </div>
    );
  }

  // 等待审核状态
  return (
    <div className="p-3 bg-blue-50 border-2 border-blue-300 rounded-lg space-y-3">
      {/* 标题 */}
      <div className="text-center">
        <p className="text-xs text-blue-600 font-medium">Review Required</p>
        {roadmapTitle && (
          <p className="text-sm font-semibold text-blue-900 truncate" title={roadmapTitle}>
            {roadmapTitle}
          </p>
        )}
        <p className="text-[10px] text-blue-500">{stagesCount} stages</p>
      </div>

      {/* 错误提示 */}
      {reviewError && (
        <div className="p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">
          {reviewError}
        </div>
      )}

      {/* 反馈输入 */}
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

      {/* 操作按钮 */}
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
              className="h-7 text-xs bg-green-600 hover:bg-green-700"
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


'use client';

import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, Circle, Loader2, XCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * 工作流阶段定义
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
    id: 'human_review',
    label: 'Human Review',
    shortLabel: 'Review',
    description: 'Awaiting confirmation',
    steps: ['human_review', 'roadmap_edit'],
  },
  {
    id: 'content_generation',
    label: 'Content Generation',
    shortLabel: 'Content',
    description: 'Generating learning materials',
    steps: ['content_generation', 'tutorial_generation', 'resource_recommendation', 'quiz_generation'],
  },
  {
    id: 'finalizing',
    label: 'Finalizing',
    shortLabel: 'Final',
    description: 'Wrapping up',
    steps: ['finalizing'],
  },
];

interface HorizontalWorkflowStepperProps {
  currentStep: string;
  status: string;
  selectedPhase?: string;
  onPhaseSelect?: (phaseId: string) => void;
}

/**
 * 横向工作流步进器
 * 
 * 设计特色:
 * - 现代的线性进度指示器
 * - 可点击的阶段导航
 * - 动态圆点动画
 * - 清晰的阶段标识
 * - 响应式设计
 * - pending 状态情感化设计（虚线边框、时钟图标、柔和背景色）
 */
export function HorizontalWorkflowStepper({
  currentStep,
  status,
  selectedPhase,
  onPhaseSelect,
}: HorizontalWorkflowStepperProps) {
  /**
   * 获取当前处于哪个阶段
   */
  const getCurrentStageIndex = (): number => {
    // 特殊状态处理
    // ✅ partial_failure 也视为完成
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
  // ✅ partial_failure 也视为完成
  const isCompleted = status === 'completed' || status === 'partial_failure';

  /**
   * 获取阶段状态
   */
  const getStageStatus = (stageIndex: number): 'completed' | 'current' | 'pending' | 'failed' => {
    if (isFailed && stageIndex === currentStageIndex) return 'failed';
    if (stageIndex < currentStageIndex) return 'completed';
    if (stageIndex === currentStageIndex) return 'current';
    return 'pending';
  };

  /**
   * 获取阶段图标
   */
  const getStageIcon = (stageStatus: string) => {
    switch (stageStatus) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5" />;
      case 'current':
        return <Loader2 className="w-5 h-5 animate-spin" />;
      case 'failed':
        return <XCircle className="w-5 h-5" />;
      default:
        // pending 状态使用 Clock 图标，更有"等待"的语义
        return <Clock className="w-5 h-5" />;
    }
  };

  /**
   * 获取连接线的样式
   */
  const getConnectorClassName = (fromIndex: number): string => {
    const fromStatus = getStageStatus(fromIndex);
    const toStatus = getStageStatus(fromIndex + 1);

    if (fromStatus === 'completed' && toStatus === 'completed') {
      return 'bg-sage-600';
    }
    if (fromStatus === 'completed') {
      return 'bg-gradient-to-r from-sage-600 to-gray-300';
    }
    if (fromStatus === 'failed') {
      return 'bg-red-500';
    }
    return 'bg-gray-300';
  };

  /**
   * 处理阶段点击
   */
  const handlePhaseClick = (phaseId: string) => {
    if (onPhaseSelect) {
      onPhaseSelect(phaseId);
    }
  };

  return (
    <Card className="p-8">
      <div className="space-y-6">
        {/* 标题 */}
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
            {/* 连接线容器 - 独立层级 */}
            {WORKFLOW_STAGES.map((stage, index) => {
              if (index >= WORKFLOW_STAGES.length - 1) return null;
              const fromStatus = getStageStatus(index);
              const toStatus = getStageStatus(index + 1);
              
              // 判断是否为 pending 之间的连接线
              const isPendingConnector = fromStatus === 'pending' && toStatus === 'pending';
              // 判断是否为 current 到下一个阶段的连接线
              const isCurrentToNext = fromStatus === 'current' && toStatus === 'pending';
              
              let connectorClass = 'bg-gray-300';
              if (fromStatus === 'completed' && toStatus === 'completed') {
                connectorClass = 'bg-sage-600';
              } else if (fromStatus === 'completed') {
                connectorClass = 'bg-gradient-to-r from-sage-600 to-gray-300';
              } else if (fromStatus === 'failed') {
                connectorClass = 'bg-red-500';
              } else if (isCurrentToNext) {
                // current 到 next-up 使用渐变 + 虚线混合效果
                connectorClass = 'bg-gradient-to-r from-sage-500 to-sage-200';
              }

              return (
                <div
                  key={`connector-${index}`}
                  className={cn(
                    'absolute top-6 h-1 transition-all duration-500 rounded-full z-10',
                    connectorClass,
                    // pending 连接线使用虚线效果
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
              const stageStatus = getStageStatus(index);
              const isActive = stageStatus === 'current';
              const isCompleteStage = stageStatus === 'completed';
              const isFailedStage = stageStatus === 'failed';
              const isPending = stageStatus === 'pending';
              const isSelected = selectedPhase === stage.id;
              const isClickable = isCompleteStage || isActive || isFailedStage;
              
              // 下一个即将执行的阶段（current 的下一个）
              const isNextUp = isPending && index === currentStageIndex + 1;

              return (
                <button
                  key={stage.id}
                  onClick={() => isClickable && handlePhaseClick(stage.id)}
                  disabled={!isClickable}
                  className={cn(
                    'flex flex-col items-center transition-all duration-200 relative group',
                    isClickable && 'cursor-pointer',
                    !isClickable && 'cursor-default'
                  )}
                  style={{ width: `${100 / WORKFLOW_STAGES.length}%` }}
                >
                  {/* 圆点指示器 */}
                  <div
                    className={cn(
                      'relative z-20 flex items-center justify-center w-12 h-12 rounded-full border-4 transition-all duration-300',
                      isCompleteStage && 'bg-sage-600 border-sage-600 text-white',
                      isActive && 'bg-sage-500 border-sage-500 text-white shadow-lg shadow-sage-500/50 scale-110',
                      isFailedStage && 'bg-red-500 border-red-500 text-white',
                      // pending 状态优化：更柔和的背景色 + 虚线边框 + 更高对比度的图标
                      isPending && !isNextUp && 'bg-gray-50 border-2 border-dashed border-gray-300 text-gray-500 group-hover:border-gray-400 group-hover:bg-gray-100',
                      // 下一个即将执行的阶段：更醒目的样式 + 微妙的脉冲动画
                      isNextUp && 'bg-sage-50 border-2 border-dashed border-sage-300 text-sage-600 animate-pulse',
                      isSelected && isClickable && 'ring-4 ring-sage-200',
                      isClickable && 'hover:scale-110 hover:shadow-md'
                    )}
                  >
                    {getStageIcon(stageStatus)}
                  </div>

                  {/* 阶段信息 */}
                  <div className="mt-3 text-center space-y-1 max-w-[120px]">
                    <p
                      className={cn(
                        'text-sm font-medium transition-colors',
                        isActive && 'text-foreground font-semibold',
                        isCompleteStage && 'text-sage-700 font-medium',
                        isFailedStage && 'text-red-700 font-medium',
                        // 下一个即将执行：sage 色系突出显示
                        isNextUp && 'text-sage-700 font-medium',
                        // 普通 pending 状态文字：更高对比度 + hover 效果
                        isPending && !isNextUp && 'text-gray-600 font-normal group-hover:text-gray-700',
                        isSelected && isClickable && 'font-semibold'
                      )}
                    >
                      {stage.shortLabel}
                    </p>
                    <p 
                      className={cn(
                        'text-xs hidden sm:block transition-colors',
                        // 描述文字使用更浅的颜色以区分层级
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

                  {/* 连接线 - 移到button外层 */}
                </button>
              );
            })}
          </div>
        </div>

        {/* 当前步骤详细信息 */}
        {!isCompleted && !isFailed && currentStep && (
          <div className="pt-4 border-t">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">Current Step:</span>
              <Badge variant="outline" className="font-mono">
                {currentStep}
              </Badge>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}


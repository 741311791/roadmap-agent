'use client';

/**
 * CoreDisplayArea - 核心展示区域组件
 * 
 * 页面中间部分，包含：
 * - 左侧：需求分析卡片
 * - 右侧：动态路线图
 * 
 * 状态流转：
 * 1. 初始/加载中：显示骨架动画
 * 2. intent_analysis 完成：显示需求分析卡片
 * 3. curriculum_design 完成：显示路线图
 * 4. roadmap_edit 时：路线图显示蒙版加载动画
 */

import { useMemo, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Target, Clock, TrendingUp, Lightbulb, Loader2, ChevronLeft, ChevronRight, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { RoadmapTree } from './roadmap-tree';
import type { Stage, RoadmapFramework } from '@/types/generated/models';
import Link from 'next/link';

/**
 * 需求分析输出数据类型
 */
interface IntentAnalysisOutput {
  learning_goal: string;
  key_technologies: string[];
  difficulty_level: string;
  estimated_duration_weeks: number;
  estimated_hours_per_week?: number;
  skill_gaps?: Array<{
    skill_name: string;
    current_level: string;
    required_level: string;
  }>;
  learning_strategies?: string[];
}

interface CoreDisplayAreaProps {
  /** 当前工作流步骤 */
  currentStep: string;
  /** 任务状态 */
  status: string;
  /** 任务 ID（用于获取验证结果） */
  taskId?: string;
  /** 路线图 ID（用于跳转详情页） */
  roadmapId?: string | null;
  /** 需求分析输出 */
  intentAnalysis?: IntentAnalysisOutput | null;
  /** 路线图框架 */
  roadmapFramework?: RoadmapFramework | null;
  /** 是否正在编辑路线图 */
  isEditingRoadmap?: boolean;
  /** 修改过的节点 ID 列表 */
  modifiedNodeIds?: string[];
  /** 加载中的 Concept ID 列表 */
  loadingConceptIds?: string[];
  /** 失败的 Concept ID 列表 */
  failedConceptIds?: string[];
  /** 部分失败的 Concept ID 列表 */
  partialFailedConceptIds?: string[];
  /** 最大高度 */
  maxHeight?: number;
  /** 自定义类名 */
  className?: string;
}

/**
 * 判断是否应该显示需求分析卡片
 */
function shouldShowIntentCard(currentStep: string, intentAnalysis?: IntentAnalysisOutput | null): boolean {
  if (!intentAnalysis) return false;
  
  // intent_analysis 完成后的任何阶段都显示
  const stepsAfterIntent = [
    'curriculum_design',
    'framework_generation',
    'structure_validation',
    'roadmap_edit',
    'human_review',
    'human_review_pending',
    'content_generation',
    'tutorial_generation',
    'resource_recommendation',
    'quiz_generation',
    'finalizing',
    'completed',
  ];
  
  return stepsAfterIntent.includes(currentStep) || currentStep === 'intent_analysis';
}

/**
 * 判断是否应该显示路线图
 */
function shouldShowRoadmap(currentStep: string, roadmapFramework?: RoadmapFramework | null): boolean {
  if (!roadmapFramework || !roadmapFramework.stages || roadmapFramework.stages.length === 0) {
    return false;
  }
  
  // curriculum_design 完成后的任何阶段都显示
  const stepsAfterDesign = [
    'structure_validation',
    'roadmap_edit',
    'human_review',
    'human_review_pending',
    'content_generation',
    'tutorial_generation',
    'resource_recommendation',
    'quiz_generation',
    'finalizing',
    'completed',
  ];
  
  return stepsAfterDesign.includes(currentStep);
}

/**
 * 判断是否正在编辑路线图
 */
function isRoadmapEditing(currentStep: string, isEditingRoadmap?: boolean): boolean {
  return isEditingRoadmap === true || currentStep === 'roadmap_edit';
}

/**
 * 获取难度等级的显示配置
 */
function getDifficultyConfig(level: string): { label: string; className: string } {
  const configs: Record<string, { label: string; className: string }> = {
    beginner: { label: 'Beginner', className: 'bg-sage-100 text-sage-700 border-sage-300' },
    intermediate: { label: 'Intermediate', className: 'bg-sage-200 text-sage-800 border-sage-400' },
    advanced: { label: 'Advanced', className: 'bg-sage-300 text-sage-900 border-sage-500' },
    expert: { label: 'Expert', className: 'bg-amber-100 text-amber-700 border-amber-300' },
  };
  return configs[level] || configs.intermediate;
}

/**
 * 骨架加载组件
 */
function CoreDisplaySkeleton() {
  return (
    <Card>
      {/* 标题部分 */}
      <div className="px-6 py-4 border-b">
        <h2 className="text-lg font-serif font-semibold">Learning Path Overview</h2>
      </div>
      
      {/* 内容区域 */}
      <div className="p-6">
        <div className="flex gap-6">
          {/* 左侧需求分析骨架 */}
          <div className="w-[320px] flex-shrink-0 space-y-4">
            <div className="flex items-center gap-2">
              <Skeleton className="w-5 h-5 rounded" />
              <Skeleton className="h-5 w-32" />
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <div className="flex gap-2">
              <Skeleton className="h-6 w-16 rounded-full" />
              <Skeleton className="h-6 w-16 rounded-full" />
              <Skeleton className="h-6 w-16 rounded-full" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Skeleton className="h-12 rounded" />
              <Skeleton className="h-12 rounded" />
            </div>
          </div>
          
          {/* 右侧路线图骨架 */}
          <div className="flex-1 space-y-4">
            <div className="flex items-center gap-2">
              <Skeleton className="w-5 h-5 rounded" />
              <Skeleton className="h-5 w-40" />
            </div>
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-8 w-24 rounded-full" />
                  <div className="flex gap-2">
                    <Skeleton className="h-7 w-20 rounded-full" />
                    <Skeleton className="h-7 w-20 rounded-full" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

/**
 * 需求分析卡片组件（内联版）
 */
function IntentAnalysisCardInline({ data }: { data: IntentAnalysisOutput }) {
  const difficultyConfig = getDifficultyConfig(data.difficulty_level);
  
  return (
    <div className="space-y-5">
      {/* 标题 */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-sage-600" />
          <h3 className="text-base font-semibold">Intent Analysis</h3>
        </div>
        <p className="text-xs text-muted-foreground">AI's understanding of your learning goal</p>
      </div>
      
      {/* 学习目标 */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs font-medium text-sage-700">
          <Target className="w-3.5 h-3.5" />
          <span>Learning Goal</span>
        </div>
        <p className="text-sm text-foreground leading-relaxed pl-5">{data.learning_goal}</p>
      </div>

      {/* 关键技术栈 */}
      <div className="space-y-2">
        <div className="text-xs font-medium text-sage-700">Key Technologies</div>
        <div className="flex flex-wrap gap-1.5">
          {data.key_technologies.slice(0, 6).map((tech, index) => (
            <Badge key={index} variant="secondary" className="text-xs">
              {tech}
            </Badge>
          ))}
          {data.key_technologies.length > 6 && (
            <Badge variant="outline" className="text-xs text-muted-foreground border-dashed">
              +{data.key_technologies.length - 6} more
            </Badge>
          )}
        </div>
      </div>

      {/* 预计时长和难度 */}
      <div className="grid grid-cols-2 gap-4 pt-3 border-t">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <Clock className="w-3.5 h-3.5" />
            <span>Duration</span>
          </div>
          <div>
            <p className="text-base font-semibold text-foreground">
              {data.estimated_duration_weeks} weeks
            </p>
            
          </div>
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Difficulty</span>
          </div>
          <Badge variant="outline" className={cn('text-xs w-fit', difficultyConfig.className)}>
            {difficultyConfig.label}
          </Badge>
        </div>
      </div>

      {/* 学习策略（如果有） */}
      {data.learning_strategies && data.learning_strategies.length > 0 && (
        <div className="space-y-2 pt-3 border-t">
          <div className="text-xs font-medium text-sage-700">Recommended Strategies</div>
          <ul className="space-y-1.5 text-xs text-muted-foreground">
            {data.learning_strategies.slice(0, 3).map((strategy, index) => (
              <li key={index} className="flex gap-2">
                <span className="text-sage-500 mt-0.5">•</span>
                <span>{strategy}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 技能差距（折叠，带可视化进度条） */}
      {data.skill_gaps && data.skill_gaps.length > 0 && (
        <details className="pt-3 border-t">
          <summary className="cursor-pointer text-xs font-medium text-sage-600 hover:text-sage-700 flex items-center gap-1.5 select-none">
            <TrendingUp className="w-3 h-3" />
            <span>Skill Gap Analysis</span>
            <Badge variant="outline" className="text-[10px] h-4 px-1 ml-auto">
              {data.skill_gaps.length}
            </Badge>
          </summary>
          <div className="mt-3 space-y-3 pl-1">
            {data.skill_gaps.map((gap, index) => {
              // 计算技能等级进度（简化映射）
              const levelMap: Record<string, number> = {
                'beginner': 25,
                'intermediate': 50,
                'advanced': 75,
                'expert': 100,
              };
              const currentLevel = levelMap[gap.current_level.toLowerCase()] || 0;
              const requiredLevel = levelMap[gap.required_level.toLowerCase()] || 100;
              const gapPercentage = requiredLevel - currentLevel;
              
              return (
                <div key={index} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-foreground">{gap.skill_name}</span>
                    <span className="text-[10px] text-muted-foreground">
                      {gap.current_level} → {gap.required_level}
                    </span>
                  </div>
                  <div className="relative h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    {/* 当前水平 */}
                    <div 
                      className="absolute left-0 h-full bg-sage-300 rounded-full" 
                      style={{ width: `${currentLevel}%` }}
                    />
                    {/* 需要达到的水平 */}
                    <div 
                      className="absolute left-0 h-full bg-amber-200 rounded-full opacity-50" 
                      style={{ width: `${requiredLevel}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-end text-[10px] text-amber-600">
                    <span>+{gapPercentage}% to learn</span>
                  </div>
                </div>
              );
            })}
          </div>
        </details>
      )}
    </div>
  );
}

/**
 * 获取当前步骤的等待状态文本
 * 
 * @param currentStep 当前工作流步骤
 * @returns 等待状态的描述文本
 */
function getWaitingStatusText(currentStep: string): string {
  const statusMap: Record<string, string> = {
    'intent_analysis': 'Analyzing your learning goals...',
    'curriculum_design': 'Designing roadmap structure...',
    'framework_generation': 'Generating curriculum framework...',
    'structure_validation': 'Validating roadmap structure...',
    'roadmap_edit': 'Applying modifications...',
    'human_review': 'Awaiting your review...',
    'human_review_pending': 'Awaiting your review...',
    'content_generation': 'Generating learning content...',
    'tutorial_generation': 'Generating tutorials...',
    'resource_recommendation': 'Finding learning resources...',
    'quiz_generation': 'Creating quiz questions...',
    'finalizing': 'Finalizing your roadmap...',
  };
  
  return statusMap[currentStep] || 'Preparing your roadmap...';
}

/**
 * 路线图加载等待组件
 * 
 * @param currentStep 当前工作流步骤，用于显示对应的状态文本
 */
function RoadmapWaitingSkeleton({ currentStep = 'curriculum_design' }: { currentStep?: string }) {
  return (
    <div className="flex-1 flex items-center justify-center py-12">
      <div className="text-center space-y-3">
        <Loader2 className="w-8 h-8 text-sage-500 animate-spin mx-auto" />
        <p className="text-sm text-muted-foreground">{getWaitingStatusText(currentStep)}</p>
      </div>
    </div>
  );
}

export function CoreDisplayArea({
  currentStep,
  status,
  taskId,
  roadmapId,
  intentAnalysis,
  roadmapFramework,
  isEditingRoadmap = false,
  modifiedNodeIds = [],
  loadingConceptIds = [],
  failedConceptIds = [],
  partialFailedConceptIds = [],
  maxHeight = 500,
  className,
}: CoreDisplayAreaProps) {
  // Intent Analysis 折叠状态
  const [isIntentCollapsed, setIsIntentCollapsed] = useState(false);
  
  // 计算显示状态
  const showIntentCard = shouldShowIntentCard(currentStep, intentAnalysis);
  const showRoadmap = shouldShowRoadmap(currentStep, roadmapFramework);
  const isEditing = isRoadmapEditing(currentStep, isEditingRoadmap);
  
  // 加载状态：还没有任何数据
  const isLoading = !showIntentCard && !showRoadmap && 
    !['completed', 'failed'].includes(status) &&
    !['completed', 'failed'].includes(currentStep);
  
  // 骨架状态
  if (isLoading) {
    return <CoreDisplaySkeleton />;
  }
  
  // 判断是否显示"View Roadmap"按钮
  const isTaskCompleted = status === 'completed' || status === 'partial_failure';
  const showViewRoadmapButton = isTaskCompleted && roadmapId;

  return (
    <Card className={cn('', className)}>
      {/* 标题部分 */}
      <div className="px-6 py-4 border-b flex items-center justify-between">
        <h2 className="text-lg font-serif font-semibold">Learning Path Overview</h2>
        
        {/* View Roadmap 按钮 - 任务完成时显示 */}
        {showViewRoadmapButton && (
          <Link href={`/roadmap/${roadmapId}`}>
            <Button
              size="sm"
              className="h-8 gap-1.5 bg-gradient-to-r from-sage-600 to-emerald-600 hover:from-sage-700 hover:to-emerald-700 text-white shadow-sm hover:shadow-md transition-all duration-200"
            >
              <span className="text-xs font-medium">View Roadmap</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </Link>
        )}
      </div>
      
      {/* 内容区域 */}
      <div className="p-6">
        <div className="flex gap-6 relative">
          {/* 左侧：需求分析卡片 - 可折叠 */}
          {showIntentCard && intentAnalysis && !isIntentCollapsed && (
            <div className="w-[280px] flex-shrink-0 border-r pr-6 relative">
              <IntentAnalysisCardInline data={intentAnalysis} />
              {/* 折叠按钮 */}
              <Button
                variant="ghost"
                size="sm"
                className="absolute -right-3 top-0 h-6 w-6 p-0 rounded-full bg-background border shadow-sm hover:bg-sage-50"
                onClick={() => setIsIntentCollapsed(true)}
                title="Collapse Analysis"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </Button>
            </div>
          )}
          
          {/* 展开Intent Analysis按钮（折叠时显示） */}
          {showIntentCard && intentAnalysis && isIntentCollapsed && (
            <Button
              variant="outline"
              size="sm"
              className="absolute left-0 top-0 h-8 gap-1.5 shadow-sm hover:bg-sage-50 z-10"
              onClick={() => setIsIntentCollapsed(false)}
            >
              <ChevronRight className="w-3.5 h-3.5" />
              <Lightbulb className="w-3.5 h-3.5 text-sage-600" />
              <span className="text-xs font-medium">Intent Analysis</span>
            </Button>
          )}
          
           {/* 右侧：路线图 - 占据剩余空间 */}
           <div className={cn(
             "flex-1 min-w-0 transition-all duration-200",
             !showIntentCard && "w-full",
             isIntentCollapsed && showIntentCard && "w-full"
           )}>
             {showRoadmap && roadmapFramework ? (
               <RoadmapTree
                 stages={roadmapFramework.stages}
                 showStartNode={showIntentCard && !isIntentCollapsed} // 只在显示需求分析卡片时显示起始节点
                 isEditing={isEditing}
                 taskId={taskId}
                 roadmapId={roadmapId}  // 传递 roadmapId
                 showHistoryButton={true}  // 启用历史版本按钮
                 modifiedNodeIds={modifiedNodeIds}
                 loadingConceptIds={loadingConceptIds}
                 failedConceptIds={failedConceptIds}
                 partialFailedConceptIds={partialFailedConceptIds}
               />
             ) : showIntentCard ? (
               // 需求分析已完成但路线图还在生成，传入当前步骤以显示正确的状态文本
               <RoadmapWaitingSkeleton currentStep={currentStep} />
             ) : null}
           </div>
        </div>
      </div>
    </Card>
  );
}


/**
 * MyLearningCard - 我的学习旅程卡片组件
 * 
 * 使用 FlippingCard 实现的 3D 翻转设计
 * - 正面：显示封面图片、标题和进度信息
 * - 背面：显示详细状态和操作按钮
 */
'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { FlippingCard } from '@/components/ui/flipping-card';
import { CoverImage } from './cover-image';
import { cn } from '@/lib/utils';
import { 
  Clock, 
  BookOpen, 
  ChevronRight, 
  AlertCircle, 
  Loader2,
  CheckCircle,
  MoreVertical,
  Trash2,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

export interface MyLearningCardProps {
  id: string;
  title: string;
  topic: string;
  status: string;
  totalConcepts: number;
  completedConcepts: number;
  lastAccessedAt: string;
  taskId?: string | null;
  taskStatus?: string | null;
  currentStep?: string | null;
  onDelete?: (id: string) => void;
  showActions?: boolean;
  className?: string;
  coverImageUrl?: string | null;  // 可选的封面图 URL（用于批量获取）
  enableFlip?: boolean;
  stages?: Array<{
    name: string;
    description?: string;
    order: number;
  }>;
}

/**
 * 获取生成步骤的国际化标签
 */
function getStepLabel(step: string | null, t: any): string {
  const stepMap: Record<string, string> = {
    'queued': t('myLearningCard.stepQueued'),
    'intent_analysis': t('myLearningCard.stepAnalyzing'),
    'curriculum_design': t('myLearningCard.stepDesigning'),
    'structure_validation': t('myLearningCard.stepValidating'),
    'human_review': t('myLearningCard.stepPendingReview'),
    'content_generation': t('myLearningCard.stepGenerating'),
    'completed': t('myLearningCard.stepCompleted'),
    'failed': t('myLearningCard.stepFailed'),
  };
  
  return stepMap[step || 'queued'] || t('myLearningCard.processingRoadmap');
}

/**
 * 格式化相对时间（国际化）
 */
function formatRelativeTime(dateString: string, t: any): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return t('myLearningCard.timeToday');
  if (diffDays === 1) return t('myLearningCard.timeYesterday');
  if (diffDays < 7) return t('myLearningCard.timeDaysAgo', { days: diffDays });
  if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return t('myLearningCard.timeWeeksAgo', { weeks });
  }
  const months = Math.floor(diffDays / 30);
  return t('myLearningCard.timeMonthsAgo', { months });
}

/**
 * 卡片正面内容
 */
function CardFront({ 
  id, 
  title, 
  topic, 
  status, 
  totalConcepts, 
  completedConcepts,
  coverImageUrl
}: Pick<MyLearningCardProps, 'id' | 'title' | 'topic' | 'status' | 'totalConcepts' | 'completedConcepts' | 'coverImageUrl'>) {
  const t = useTranslations();
  const progress = totalConcepts > 0 ? (completedConcepts / totalConcepts) * 100 : 0;
  const isCompleted = status === 'completed';
  const isGenerating = status === 'generating';
  const isFailed = status === 'failed';

  return (
    <div className="flex flex-col h-full w-full">
      {/* 封面图片 */}
      <div className="relative w-full aspect-[7/4] overflow-hidden rounded-t-xl bg-sage-100">
        <CoverImage
          roadmapId={id}
          topic={topic}
          title={title}
          className="w-full h-full"
          coverImageUrl={coverImageUrl}
        />
        
        {/* 渐变遮罩 */}
        {/* <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent" /> */}
        
        {/* Status Badge */}
        <div className="absolute top-3 left-3 z-10">
          {isCompleted && (
            <Badge className="bg-gradient-to-r from-green-500 to-green-600 text-white border-0 shadow-lg text-[10px] px-2 py-1 font-bold flex items-center gap-1">
              <CheckCircle className="w-3 h-3" />
              {t('myLearningCard.completed')}
            </Badge>
          )}
          {isGenerating && (
            <Badge className="bg-gradient-to-r from-blue-500 to-blue-600 text-white border-0 shadow-lg text-[10px] px-2 py-1 font-bold flex items-center gap-1">
              <Loader2 className="w-3 h-3 animate-spin" />
              {t('myLearningCard.generating')}
            </Badge>
          )}
          {isFailed && (
            <Badge className="bg-gradient-to-r from-red-500 to-red-600 text-white border-0 shadow-lg text-[10px] px-2 py-1 font-bold flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              {t('myLearningCard.failed')}
            </Badge>
          )}
          {!isCompleted && !isGenerating && !isFailed && (
            <Badge className="bg-gradient-to-r from-sage-500 to-sage-600 text-white border-0 shadow-lg text-[10px] px-2 py-1 font-bold">
              {t('myLearningCard.inProgress')}
            </Badge>
          )}
        </div>
      </div>

      {/* 内容区域 */}
      <div className="flex flex-col flex-1 p-4">
        {/* 标题 */}
        <h3 className="font-serif font-semibold text-base text-foreground line-clamp-2 mb-3 min-h-[48px]">
          {title}
        </h3>

        {/* 进度信息 */}
        {!isGenerating && !isFailed && (
          <div className="space-y-2 mb-3">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="font-medium">
                {completedConcepts}/{totalConcepts} {t('myLearningCard.concepts')}
              </span>
              <span className="font-bold text-sage-600">
                {progress.toFixed(0)}%
              </span>
            </div>
            <div className="h-2 bg-sage-100 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-sage-400 via-sage-500 to-sage-600 transition-all duration-500 rounded-full"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* 元信息 */}
        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-auto">
          {totalConcepts > 0 && (
            <div className="flex items-center gap-1">
              <BookOpen className="w-3.5 h-3.5" />
              <span>{totalConcepts} {t('myLearningCard.concepts')}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * 卡片背面内容 - 显示 Stages 信息
 */
function CardBack({ 
  id,
  title, 
  status, 
  totalConcepts, 
  totalHours,
  lastAccessedAt,
  currentStep,
  onDelete,
  showActions = true,
  stages = [],
}: Pick<MyLearningCardProps, 'id' | 'title' | 'status' | 'totalConcepts' | 'lastAccessedAt' | 'currentStep' | 'onDelete' | 'showActions' | 'stages'> & { totalHours?: number }) {
  const t = useTranslations();
  const isGenerating = status === 'generating';
  const isFailed = status === 'failed';
  const hasStages = stages && stages.length > 0;

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onDelete) {
      onDelete(id);
    }
  };

  return (
    <TooltipProvider>
      <div className="flex flex-col h-full w-full p-4 relative">
        {/* Actions Menu */}
        {showActions && onDelete && (
          <div className="absolute top-3 right-3 z-20">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 bg-white hover:bg-gray-100 shadow border border-sage-100"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                  }}
                >
                  <MoreVertical className="h-3.5 w-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  className="text-red-600 focus:text-red-600 focus:bg-red-50 cursor-pointer"
                  onClick={handleDeleteClick}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  <span>{t('myLearningCard.delete')}</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}

        {/* 标题 */}
        <h3 className="font-serif font-semibold text-base text-foreground mb-3 line-clamp-2 pr-8">
          {title}
        </h3>

        {/* 状态详情或 Stages 列表 */}
        {isFailed ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 w-full">
              <div className="flex items-center gap-2 text-red-600 mb-2">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm font-semibold">{t('myLearningCard.generationFailed')}</span>
              </div>
              <p className="text-xs text-red-600">
                {getStepLabel(currentStep || 'failed', t)}
              </p>
            </div>
          </div>
        ) : isGenerating ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="p-3 rounded-lg bg-blue-50 border border-blue-200 w-full">
              <div className="flex items-center gap-2 text-blue-600 mb-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm font-semibold">{t('myLearningCard.generatingText')}</span>
              </div>
              <p className="text-xs text-blue-600">
                {getStepLabel(currentStep || 'queued', t)}
              </p>
            </div>
          </div>
        ) : hasStages ? (
          <div className="flex-1 overflow-y-auto space-y-2 mb-3">
            {stages.slice(0, 5).map((stage, index) => (
              <Tooltip key={index} delayDuration={300}>
                <TooltipTrigger asChild>
                  <div
                    className="flex items-start gap-2 p-2 rounded-lg bg-sage-50/50 hover:bg-sage-100/50 transition-colors cursor-pointer"
                  >
                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-sage-200 flex items-center justify-center text-[10px] font-bold text-sage-700 mt-0.5">
                      {stage.order}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-foreground line-clamp-1">
                        {stage.name}
                      </div>
                      {stage.description && (
                        <div className="text-xs text-muted-foreground line-clamp-2 mt-0.5">
                          {stage.description}
                        </div>
                      )}
                    </div>
                  </div>
                </TooltipTrigger>
                <TooltipContent 
                  side="top" 
                  className="max-w-xs z-[100]"
                  sideOffset={5}
                >
                  <div className="space-y-1">
                    <p className="font-semibold text-sm">{stage.name}</p>
                    {stage.description && (
                      <p className="text-xs text-muted-foreground">{stage.description}</p>
                    )}
                  </div>
                </TooltipContent>
              </Tooltip>
            ))}
            {stages.length > 5 && (
              <div className="text-xs text-muted-foreground text-center py-1">
                {t('myLearningCard.moreStages', { count: stages.length - 5 })}
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-sm text-muted-foreground text-center">
              {t('myLearningCard.comprehensivePath')}
            </p>
          </div>
        )}

        {/* 底部操作区域 */}
        <div className="flex items-center justify-between pt-3 border-t border-sage-100">
          {/* 统计信息 */}
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            {totalConcepts > 0 && (
              <div className="flex items-center gap-1">
                <BookOpen className="w-3.5 h-3.5" />
                <span>{totalConcepts}</span>
              </div>
            )}
            {totalHours && totalHours > 0 && (
              <div className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                <span>{totalHours}{t('myLearningCard.hours')}</span>
              </div>
            )}
          </div>

          {/* 继续学习按钮 - 阻止事件冒泡 */}
          <div onClick={(e) => e.stopPropagation()}>
            <span className="flex items-center gap-1 text-xs font-medium text-sage-600 hover:text-sage-700 transition-colors cursor-pointer">
              {isGenerating || isFailed ? t('myLearningCard.viewStatus') : t('myLearningCard.continue')}
              <ChevronRight className="w-3 h-3" />
            </span>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}

export function MyLearningCard(props: MyLearningCardProps) {
  const {
    id,
    title,
    topic,
    status,
    totalConcepts,
    completedConcepts,
    lastAccessedAt,
    taskId,
    currentStep,
    onDelete,
    showActions = true,
    className,
    coverImageUrl,
    enableFlip = true,
    stages,
  } = props;

  const isGenerating = status === 'generating';
  const isFailed = status === 'failed';
  
  // 估算学习时长：每个概念约 0.5 小时
  const totalHours = totalConcepts > 0 ? Math.ceil(totalConcepts * 0.5) : 0;

  const href = (isGenerating || isFailed) && taskId
    ? `/new?task_id=${taskId}`
    : `/roadmap/${id}`;

  return (
    <Link href={href} className={cn('block', className)}>
      {enableFlip ? (
        <FlippingCard
          width={280}
          height={350}
          frontContent={
            <CardFront
              id={id}
              title={title}
              topic={topic}
              status={status}
              totalConcepts={totalConcepts}
              completedConcepts={completedConcepts}
              coverImageUrl={coverImageUrl}
            />
          }
          backContent={
            <CardBack
              id={id}
              title={title}
              status={status}
              totalConcepts={totalConcepts}
              totalHours={totalHours}
              lastAccessedAt={lastAccessedAt}
              currentStep={currentStep}
              onDelete={onDelete}
              showActions={showActions}
              stages={stages}
            />
          }
          className="w-full"
        />
      ) : (
        <div className="w-[280px] h-[350px] rounded-xl border border-neutral-200 bg-white shadow-lg overflow-hidden">
          <CardFront
            id={id}
            title={title}
            topic={topic}
            status={status}
            totalConcepts={totalConcepts}
            completedConcepts={completedConcepts}
            coverImageUrl={coverImageUrl}
          />
        </div>
      )}
    </Link>
  );
}


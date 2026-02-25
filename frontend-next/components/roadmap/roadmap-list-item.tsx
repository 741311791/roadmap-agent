/**
 * RoadmapListItem 组件
 * 
 * 列表视图的路线图展示，更紧凑的布局
 */
'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useTranslations } from 'next-intl';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { 
  Clock, 
  MoreVertical,
  Trash2,
  AlertCircle,
  Loader2,
  ImagePlus,
} from 'lucide-react';
import { MyRoadmap } from './roadmap-card';
import { getCoverImage, getGradientFallback, getTopicInitial, fetchCoverImageFromAPI } from '@/lib/cover-image';

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
  
  if (diffDays === 0) return t('roadmapCard.timeToday');
  if (diffDays === 1) return t('roadmapCard.timeYesterday');
  if (diffDays < 7) return t('roadmapCard.timeDaysAgo', { days: diffDays });
  if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return t('roadmapCard.timeWeeksAgo', { weeks });
  }
  const months = Math.floor(diffDays / 30);
  return t('roadmapCard.timeMonthsAgo', { months });
}

interface RoadmapListItemProps {
  roadmap: MyRoadmap;
  onDelete?: (roadmapId: string) => void;
  onGenerateCover?: (roadmapId: string) => void;
  coverImageUrl?: string;  // 可选的封面图 URL（用于批量获取）
}

export function RoadmapListItem({ roadmap, onDelete, onGenerateCover, coverImageUrl }: RoadmapListItemProps) {
  const t = useTranslations();
  const [imageError, setImageError] = useState(false);
  const [imageUrl, setImageUrl] = useState(getCoverImage(roadmap.topic));
  const gradient = getGradientFallback(roadmap.title);
  const initial = getTopicInitial(roadmap.title);
  
  // 检查是否为 R2.dev 的图片（不使用 Next.js 图片优化）
  const isR2Image = imageUrl.includes('r2.dev');
  
  // 如果提供了 coverImageUrl，直接使用；否则尝试从 API 获取封面图
  useEffect(() => {
    // 如果明确提供了封面图 URL（包括空字符串），直接使用
    if (coverImageUrl !== undefined) {
      // coverImageUrl 可能是 null（表示无封面图）或有效的 URL
      if (coverImageUrl) {
        setImageUrl(coverImageUrl);
      }
      // 如果是 null，保持默认的 Unsplash 图片
    } else {
      // 未提供时才从 API 获取
      fetchCoverImageFromAPI(roadmap.id).then((apiUrl) => {
        if (apiUrl) {
          setImageUrl(apiUrl);
        }
      });
    }
  }, [roadmap.id, coverImageUrl]);
  
  const progress = roadmap.totalConcepts > 0 
    ? (roadmap.completedConcepts / roadmap.totalConcepts) * 100 
    : 0;
  const isCompleted = roadmap.status === 'completed';
  const isGenerating = roadmap.status === 'generating';
  const isFailed = roadmap.status === 'failed';

  // 如果正在生成中或失败，点击跳转到生成页面查看进度或错误信息
  const href = (isGenerating || isFailed) && roadmap.taskId
    ? `/new?task_id=${roadmap.taskId}`
    : `/roadmap/${roadmap.id}`;

  // 处理删除点击事件（阻止导航）
  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onDelete) {
      onDelete(roadmap.id);
    }
  };

  // 处理生成封面图点击事件
  // DropdownMenuContent 由 Radix 渲染在 Portal 中，不在 Link DOM 树内，
  // 无需阻止事件冒泡；保留原生行为使菜单在点击后自动关闭
  const handleGenerateCoverClick = () => {
    if (onGenerateCover) {
      onGenerateCover(roadmap.id);
    }
  };

  return (
    <Link href={href}>
      <div className="group flex items-center gap-4 p-4 rounded-lg border border-border/30 hover:border-sage-200 hover:shadow-sm transition-all duration-200 bg-background">
        {/* 封面缩略图 */}
        <div className="flex-shrink-0 w-24 h-16 rounded-lg overflow-hidden">
          {!imageError ? (
            isR2Image ? (
              <img
                src={imageUrl}
                alt={roadmap.title}
                className="w-full h-full object-cover"
                onError={() => setImageError(true)}
                loading="lazy"
              />
            ) : (
              <Image
                src={imageUrl}
                alt={roadmap.title}
                width={96}
                height={64}
                className="w-full h-full object-cover"
                onError={() => setImageError(true)}
              />
            )
          ) : (
            <div className={`w-full h-full ${gradient.className} flex items-center justify-center`}>
              <span className={`text-lg font-serif font-bold ${gradient.text} opacity-80`}>
                {initial}
              </span>
            </div>
          )}
        </div>

        {/* 内容区域 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              {/* 标题 */}
              <h3 className="font-serif font-medium text-base text-foreground group-hover:text-sage-600 transition-colors truncate mb-1">
                {roadmap.title}
              </h3>

              {/* 状态信息 */}
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                {isFailed ? (
                  <span className="flex items-center gap-1.5 text-red-600">
                    <AlertCircle size={14} />
                    <span className="text-xs">
                      {getStepLabel(roadmap.currentStep || 'failed', t)}
                    </span>
                  </span>
                ) : isGenerating ? (
                  <span className="flex items-center gap-1.5 text-sage-600">
                    <Loader2 size={14} className="animate-spin" />
                    <span className="text-xs">
                      {getStepLabel(roadmap.currentStep || 'queued', t)}
                    </span>
                  </span>
                ) : (
                  <>
                    <span className="text-xs">
                      {roadmap.completedConcepts}/{roadmap.totalConcepts} {t('myLearningCard.concepts')}
                    </span>
                    <span className="text-xs text-muted-foreground/50">•</span>
                    <span className="flex items-center gap-1 text-xs">
                      <Clock size={12} />
                      {formatRelativeTime(roadmap.lastAccessedAt, t)}
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* 右侧：进度和操作 */}
            <div className="flex items-center gap-4">
              {/* 进度条 */}
              {!isGenerating && !isFailed && (
                <div className="flex items-center gap-3">
                  <div className="w-32">
                    <Progress value={progress} className="h-2" />
                  </div>
                  <span className="text-sm font-medium text-foreground whitespace-nowrap">
                    {progress.toFixed(0)}%
                  </span>
                </div>
              )}

              {/* 状态徽章 */}
              <Badge
                variant={isFailed ? 'outline' : isGenerating ? 'outline' : isCompleted ? 'success' : 'sage'}
                className={`text-xs whitespace-nowrap ${
                  isFailed 
                    ? 'border-red-300 text-red-600 bg-red-50' 
                    : isGenerating 
                    ? 'border-sage-300 text-sage-600 bg-sage-50' 
                    : ''
                }`}
              >
                {isFailed ? t('myLearningCard.failed') : isGenerating ? t('myLearningCard.generating') : isCompleted ? t('myLearningCard.completed') : t('myLearningCard.inProgress')}
              </Badge>

              {/* 操作菜单 */}
              {(onDelete || onGenerateCover) && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                      }}
                    >
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {/* 仅在路线图已完成（非生成中/失败状态）时显示封面图生成选项 */}
                    {onGenerateCover && !isGenerating && !isFailed && (
                      <>
                        <DropdownMenuItem
                          className="cursor-pointer"
                          onClick={handleGenerateCoverClick}
                        >
                          <ImagePlus className="mr-2 h-4 w-4" />
                          <span>{t('roadmapCard.generateCover')}</span>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                      </>
                    )}
                    {onDelete && (
                      <DropdownMenuItem
                        className="text-red-600 focus:text-red-600 focus:bg-red-50 cursor-pointer"
                        onClick={handleDeleteClick}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        <span>{t('myLearningCard.delete')}</span>
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}

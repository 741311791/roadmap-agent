/**
 * RoadmapCard 组件
 * 
 * 统一的路线图卡片组件，支持"我的路线图"和"社区路线图"两种类型
 */
'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useTranslations } from 'next-intl';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { MagicCard } from '@/components/ui/magic-card';
import { ShineBorder } from '@/components/ui/shine-border';
import { 
  Clock, 
  Heart, 
  Eye, 
  AlertCircle,
  Loader2,
  MoreVertical,
  Trash2,
  Sparkles,
  ImagePlus,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { CoverImage } from './cover-image';

// 我的路线图类型
export interface MyRoadmap {
  id: string;
  title: string;
  status: string;
  totalConcepts: number;
  completedConcepts: number;
  totalHours: number;
  lastAccessedAt: string;
  topic: string;
  taskId?: string | null;
  taskStatus?: string | null;
  currentStep?: string | null;
}

// 社区路线图类型
export interface CommunityRoadmap {
  id: string;
  title: string;
  author: {
    name: string;
    avatar: string;
  };
  likes: number;
  views: number;
  tags: string[];
  topic: string;
}

// 格式化相对时间（使用国际化）
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

// 获取生成步骤的国际化标签
function getStepLabel(step: string | null, t: any): string {
  const stepMap: Record<string, string> = {
    'queued': t('roadmapCard.stepQueued'),
    'intent_analysis': t('roadmapCard.stepIntentAnalysis'),
    'curriculum_design': t('roadmapCard.stepCurriculumDesign'),
    'structure_validation': t('roadmapCard.stepStructureValidation'),
    'human_review': t('roadmapCard.stepHumanReview'),
    'content_generation': t('roadmapCard.stepContentGeneration'),
    'completed': t('roadmapCard.stepCompleted'),
    'failed': t('roadmapCard.stepFailed'),
  };
  
  return stepMap[step || 'queued'] || t('roadmapCard.statusGenerating');
}

interface RoadmapCardProps {
  roadmap: MyRoadmap | CommunityRoadmap;
  type: 'my' | 'community';
  onDelete?: (roadmapId: string) => void;
  onGenerateCover?: (roadmapId: string) => void;
  showActions?: boolean;
  coverImageUrl?: string;  // 可选的封面图 URL（用于批量获取）
}

export function RoadmapCard({
  roadmap,
  type,
  onDelete,
  onGenerateCover,
  showActions = true,
  coverImageUrl,
}: RoadmapCardProps) {
  const t = useTranslations();
  const [avatarError, setAvatarError] = useState(false);
  
  const isMyRoadmap = type === 'my';
  const myRoadmap = isMyRoadmap ? roadmap as MyRoadmap : null;
  const communityRoadmap = !isMyRoadmap ? roadmap as CommunityRoadmap : null;
  
  const progress = myRoadmap && myRoadmap.totalConcepts > 0 
    ? (myRoadmap.completedConcepts / myRoadmap.totalConcepts) * 100 
    : 0;
  const isCompleted = myRoadmap?.status === 'completed';
  const isGenerating = myRoadmap?.status === 'generating';
  const isFailed = myRoadmap?.status === 'failed';

  // 如果正在生成中或失败，点击跳转到生成页面查看进度或错误信息
  const href = (isGenerating || isFailed) && myRoadmap?.taskId
    ? `/new?task_id=${myRoadmap.taskId}`
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
    <div className="group relative flex-shrink-0 w-full">
      {/* 操作菜单 - 只在 my 类型且显示 actions 时显示 */}
      {isMyRoadmap && showActions && onDelete && (
        <div className="absolute top-3 right-3 z-20 opacity-0 group-hover:opacity-100 transition-opacity">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 bg-white/95 hover:bg-white shadow-lg backdrop-blur-sm border border-sage-100"
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
              <DropdownMenuItem
                className="text-red-600 focus:text-red-600 focus:bg-red-50 cursor-pointer"
                onClick={handleDeleteClick}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                <span>{t('roadmapCard.delete')}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
      
      <Link href={href} className="block">
        <MagicCard
          className="overflow-hidden h-full rounded-xl"
          gradientSize={300}
          gradientColor="rgba(96, 117, 96, 0.1)"
          gradientFrom="#a3b1a3"
          gradientTo="#607560"
        >
          <Card className="overflow-hidden border-0 shadow-none bg-transparent h-full">
            {/* Shine Border 效果 */}
            <ShineBorder
              borderWidth={2}
              duration={12}
              shineColor={["#a3b1a3", "#607560", "#7d8f7d"]}
              className="opacity-0 group-hover:opacity-100 transition-opacity duration-500"
            />
            
            <CoverImage
              roadmapId={roadmap.id}
              topic={roadmap.topic}
              title={roadmap.title}
              className="rounded-t-xl"
              coverImageUrl={coverImageUrl}
            />
            <CardContent className="p-4 bg-white/95 backdrop-blur-sm">
            <div className="flex items-start gap-2 mb-2">
              <Sparkles className="w-3.5 h-3.5 text-sage-500 mt-0.5 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
              <h3 className="font-serif font-medium text-sm text-foreground line-clamp-2 group-hover:text-sage-700 transition-colors min-h-[40px] flex-1">
                {roadmap.title}
              </h3>
            </div>

            {isMyRoadmap && myRoadmap ? (
              isFailed ? (
                /* 生成失败的路线图 */
                <>
                  {/* 失败指示 */}
                  <div className="space-y-2 mb-3">
                    <div className="flex items-center gap-2 text-[10px] text-red-600 font-medium bg-red-50 px-2 py-1.5 rounded-lg">
                      <AlertCircle size={12} className="flex-shrink-0" />
                      <span className="truncate">
                        {getStepLabel(myRoadmap.currentStep || 'failed', t)}
                      </span>
                    </div>
                    {/* 失败进度条 */}
                    <div className="h-1.5 bg-red-100 rounded-full overflow-hidden shadow-inner">
                      <div className="h-full w-full bg-gradient-to-r from-red-400 to-red-600 rounded-full" />
                    </div>
                  </div>

                  {/* 状态 */}
                  <div className="flex items-center justify-between">
                    <Badge
                      variant="outline"
                      className="text-[10px] px-2 py-0.5 border-red-300 text-red-600 bg-red-50 font-medium"
                    >
                      {t('roadmapCard.statusFailed')}
                    </Badge>
                    <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                      <Clock size={10} />
                      {formatRelativeTime(myRoadmap.lastAccessedAt, t)}
                    </span>
                  </div>
                </>
              ) : isGenerating ? (
                /* 正在生成中的路线图 */
                <>
                  {/* 生成进度指示 */}
                  <div className="space-y-2 mb-3">
                    <div className="flex items-center gap-2 text-[10px] text-sage-700 font-medium bg-sage-50 px-2 py-1.5 rounded-lg">
                      <Loader2 size={12} className="animate-spin flex-shrink-0" />
                      <span className="truncate">
                        {getStepLabel(myRoadmap.currentStep || 'queued', t)}
                      </span>
                    </div>
                    {/* 无限进度条动画 */}
                    <div className="h-1.5 bg-sage-100 rounded-full overflow-hidden shadow-inner relative">
                      <div className="absolute inset-0 bg-gradient-to-r from-sage-400 via-sage-500 to-sage-400 animate-pulse" 
                           style={{ animation: 'pulse 1.5s ease-in-out infinite' }} />
                    </div>
                  </div>

                  {/* 状态 */}
                  <div className="flex items-center justify-between">
                    <Badge
                      variant="outline"
                      className="text-[10px] px-2 py-0.5 border-sage-300 text-sage-700 bg-sage-50 font-medium"
                    >
                      {t('roadmapCard.statusGenerating')}
                    </Badge>
                    <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                      <Clock size={10} />
                      {formatRelativeTime(myRoadmap.lastAccessedAt, t)}
                    </span>
                  </div>
                </>
              ) : (
                /* 已完成或学习中的路线图 */
                <>
                  {/* Progress Bar */}
                  <div className="space-y-2 mb-3">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-muted-foreground font-medium">
                        {myRoadmap.completedConcepts}/{myRoadmap.totalConcepts} {t('roadmapCard.concepts')}
                      </span>
                      <span className="font-bold text-sage-700 bg-sage-50 px-2 py-0.5 rounded-full">
                        {progress.toFixed(0)}%
                      </span>
                    </div>
                    <div className="relative">
                      <Progress value={progress} className="h-2 bg-sage-100" />
                      {progress > 0 && (
                        <div className="absolute inset-0 h-2 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-sage-400 via-sage-500 to-sage-600 transition-all duration-500"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Status & Time */}
                  <div className="flex items-center justify-between">
                    <Badge
                      variant={isCompleted ? 'success' : 'sage'}
                      className="text-[10px] px-2 py-0.5 font-medium"
                    >
                      {isCompleted ? `✓ ${t('roadmapCard.done')}` : `→ ${t('roadmapCard.learning')}`}
                    </Badge>
                    <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                      <Clock size={10} />
                      {formatRelativeTime(myRoadmap.lastAccessedAt, t)}
                    </span>
                  </div>
                </>
              )
            ) : communityRoadmap ? (
              <>
                {/* Author */}
                <div className="flex items-center gap-2 mb-3 bg-sage-50/50 px-2 py-1.5 rounded-lg">
                  <div className="w-6 h-6 rounded-full overflow-hidden bg-sage-100 flex-shrink-0 ring-2 ring-white shadow-sm">
                    {!avatarError ? (
                      <Image
                        src={communityRoadmap.author.avatar}
                        alt={communityRoadmap.author.name}
                        width={24}
                        height={24}
                        className="object-cover"
                        onError={() => setAvatarError(true)}
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[11px] font-bold text-sage-600">
                        {communityRoadmap.author.name.charAt(0)}
                      </div>
                    )}
                  </div>
                  <span className="text-[11px] text-foreground font-medium truncate">
                    {communityRoadmap.author.name}
                  </span>
                </div>

                {/* Tags */}
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {communityRoadmap.tags.slice(0, 2).map((tag) => (
                    <Badge
                      key={tag}
                      variant="secondary"
                      className="text-[9px] px-2 py-0.5 font-medium bg-sage-100 text-sage-700 border-0"
                    >
                      {tag}
                    </Badge>
                  ))}
                </div>

                {/* Social Stats */}
                <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
                  <span className="flex items-center gap-1.5 hover:text-rose-500 transition-colors">
                    <Heart size={11} className="text-rose-400 fill-rose-100" />
                    <span className="font-medium">{communityRoadmap.likes.toLocaleString()}</span>
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Eye size={11} className="text-sage-500" />
                    <span className="font-medium">{communityRoadmap.views.toLocaleString()}</span>
                  </span>
                </div>
              </>
            ) : null}
          </CardContent>
          </Card>
        </MagicCard>
      </Link>
    </div>
  );
}

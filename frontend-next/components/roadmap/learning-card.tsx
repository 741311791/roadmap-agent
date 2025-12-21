/**
 * LearningCard 组件
 * 
 * 统一的学习卡片组件，灵感来自 TravelCard 设计
 * 支持三种类型：create（创建新路线图）、my（我的路线图）、community（社区路线图）
 */
'use client';

import * as React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { CoverImage } from './cover-image';
import {
  Plus,
  ArrowRight,
  Clock,
  Heart,
  Eye,
  AlertCircle,
  Loader2,
  MoreVertical,
  Trash2,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

// 类型定义
export interface CreateCardProps {
  type: 'create';
}

export interface MyRoadmapCardProps {
  type: 'my';
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
}

export interface CommunityRoadmapCardProps {
  type: 'community';
  id: string;
  title: string;
  topic: string;
  author: {
    name: string;
    avatar: string;
  };
  likes: number;
  views: number;
  tags: string[];
}

type LearningCardProps = CreateCardProps | MyRoadmapCardProps | CommunityRoadmapCardProps;

// 生成步骤映射
const STEP_LABELS: Record<string, string> = {
  'queued': 'Queued',
  'intent_analysis': 'Analyzing',
  'curriculum_design': 'Designing',
  'structure_validation': 'Validating',
  'human_review': 'Pending Review',
  'content_generation': 'Generating',
  'tutorial_generation': 'Creating Tutorials',
  'resource_recommendation': 'Finding Resources',
  'quiz_generation': 'Creating Quizzes',
  'completed': 'Completed',
  'failed': 'Failed',
};

// 格式化相对时间
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return `${Math.floor(diffDays / 30)} months ago`;
}

// Create Card Component
function CreateCard() {
  return (
    <Link href="/new" className="group flex-shrink-0 w-full sm:w-[260px] lg:w-[280px]">
      <div
        className={cn(
          'relative w-full h-[340px] sm:h-[360px] overflow-hidden rounded-xl border border-dashed border-sage-300 bg-card shadow-lg',
          'transition-all duration-300 ease-in-out hover:shadow-2xl hover:-translate-y-2 hover:border-sage-500'
        )}
      >
        {/* 背景渐变 */}
        <div className="absolute inset-0 bg-gradient-to-br from-sage-50 via-white to-sage-100" />
        
        {/* 背景装饰 */}
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-0 left-0 w-32 h-32 bg-sage-300 rounded-full blur-3xl transform -translate-x-1/2 -translate-y-1/2 group-hover:scale-150 transition-transform duration-700" />
          <div className="absolute bottom-0 right-0 w-32 h-32 bg-sage-400 rounded-full blur-3xl transform translate-x-1/2 translate-y-1/2 group-hover:scale-150 transition-transform duration-700" />
        </div>

        {/* Content */}
        <div className="relative flex h-full flex-col items-center justify-center p-6 text-card-foreground">
          {/* Icon */}
          <div className="mb-6 w-20 h-20 rounded-2xl bg-gradient-to-br from-sage-100 to-sage-200 flex items-center justify-center group-hover:from-sage-200 group-hover:to-sage-300 transition-all duration-300 shadow-lg group-hover:shadow-xl group-hover:scale-110">
            <Plus size={36} className="text-sage-600 group-hover:text-sage-700 transition-colors" />
          </div>

          {/* Text */}
          <h3 className="font-serif font-bold text-lg sm:text-xl text-foreground mb-2 group-hover:text-sage-700 transition-colors">
            Create New
          </h3>
          <p className="text-xs sm:text-sm text-muted-foreground text-center">
            Start your learning journey
          </p>

          {/* Bottom CTA - revealed on hover */}
          <div className="absolute bottom-0 left-0 w-full p-6 opacity-0 transition-all duration-500 ease-in-out group-hover:opacity-100 group-hover:translate-y-0 translate-y-4">
            <Button 
              size="lg" 
              variant="sage"
              className="w-full"
            >
              Get Started <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </Link>
  );
}

// My Roadmap Card Component
function MyRoadmapCard(props: Omit<MyRoadmapCardProps, 'type'>) {
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
  } = props;

  const progress = totalConcepts > 0 ? (completedConcepts / totalConcepts) * 100 : 0;
  const isCompleted = status === 'completed';
  const isGenerating = status === 'generating';
  const isFailed = status === 'failed';

  const href = (isGenerating || isFailed) && taskId
    ? `/new?task_id=${taskId}`
    : `/roadmap/${id}`;

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onDelete) {
      onDelete(id);
    }
  };

  return (
    <div className="group relative flex-shrink-0 w-full sm:w-[260px] lg:w-[280px]">
      {/* Actions Menu */}
      {showActions && onDelete && (
        <div className="absolute top-3 right-3 z-20 opacity-0 group-hover:opacity-100 transition-opacity">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 sm:h-8 sm:w-8 bg-white/95 hover:bg-white shadow-lg backdrop-blur-sm border border-sage-100"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                }}
              >
                <MoreVertical className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                className="text-red-600 focus:text-red-600 focus:bg-red-50 cursor-pointer"
                onClick={handleDeleteClick}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                <span>Delete</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}

      <Link href={href}>
        <div
          className={cn(
            'relative w-full h-[340px] sm:h-[360px] overflow-hidden rounded-xl border border-border bg-card shadow-lg',
            'transition-all duration-300 ease-in-out hover:shadow-2xl hover:-translate-y-2'
          )}
        >
          {/* 背景图片 */}
          <div className="absolute inset-0 h-full w-full">
            <CoverImage
              topic={topic}
              title={title}
              className="w-full h-full object-cover transition-transform duration-500 ease-in-out group-hover:scale-110"
            />
          </div>

          {/* 渐变叠加层 */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-black/20" />

          {/* Content */}
          <div className="relative flex h-full flex-col justify-end p-4 sm:p-5 text-white">
            {/* Main Section - slides up on hover */}
            <div className="space-y-2 sm:space-y-3 transition-transform duration-500 ease-in-out group-hover:-translate-y-10 sm:group-hover:-translate-y-12">
              {/* Title */}
              <h3 className="text-base sm:text-lg lg:text-xl font-serif font-bold text-white line-clamp-2 leading-tight">
                {title}
              </h3>

              {/* Status Details */}
              <div className="space-y-2">
                {isFailed ? (
                  <>
                    <div className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs text-red-300 font-medium bg-red-500/20 px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg backdrop-blur-sm">
                      <AlertCircle size={12} className="sm:size-[14px] flex-shrink-0" />
                      <span className="truncate">
                        {STEP_LABELS[currentStep || 'failed'] || 'Generation Failed'}
                      </span>
                    </div>
                    <div className="h-1.5 bg-red-900/30 rounded-full overflow-hidden">
                      <div className="h-full w-full bg-gradient-to-r from-red-400 to-red-600 rounded-full" />
                    </div>
                  </>
                ) : isGenerating ? (
                  <>
                    <div className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs text-sage-200 font-medium bg-sage-500/20 px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg backdrop-blur-sm">
                      <Loader2 size={12} className="sm:size-[14px] animate-spin flex-shrink-0" />
                      <span className="truncate">
                        {STEP_LABELS[currentStep || 'queued'] || 'Generating...'}
                      </span>
                    </div>
                    <div className="h-1.5 bg-sage-900/30 rounded-full overflow-hidden relative">
                      <div className="absolute inset-0 bg-gradient-to-r from-sage-400 via-sage-500 to-sage-400 animate-pulse" />
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-center justify-between text-[10px] sm:text-xs text-white/80">
                      <span className="font-medium truncate">
                        {completedConcepts}/{totalConcepts} concepts
                      </span>
                      <span className="font-bold bg-white/10 px-1.5 sm:px-2 py-0.5 rounded-full backdrop-blur-sm ml-2">
                        {progress.toFixed(0)}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-white/20 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-sage-400 via-sage-500 to-sage-600 transition-all duration-500 rounded-full"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Bottom Section - revealed on hover */}
            <div className="absolute -bottom-20 left-0 w-full p-4 sm:p-5 opacity-0 transition-all duration-500 ease-in-out group-hover:opacity-100 group-hover:bottom-0">
              <div className="flex items-center gap-2">
                <Badge
                  variant={isCompleted ? 'success' : isFailed ? 'destructive' : 'secondary'}
                  className="text-[10px] sm:text-xs font-medium whitespace-nowrap"
                >
                  {isCompleted ? '✓ Done' : isFailed ? 'Failed' : isGenerating ? 'Generating' : '→ Learning'}
                </Badge>
                <span className="flex items-center gap-1 text-[10px] sm:text-xs text-white/70 truncate">
                  <Clock size={10} className="sm:size-3 flex-shrink-0" />
                  <span className="truncate">{formatRelativeTime(lastAccessedAt)}</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </Link>
    </div>
  );
}

// Community Roadmap Card Component
function CommunityRoadmapCard(props: Omit<CommunityRoadmapCardProps, 'type'>) {
  const { id, title, topic, author, likes, views, tags } = props;
  const [avatarError, setAvatarError] = React.useState(false);

  return (
    <div className="group relative flex-shrink-0 w-full sm:w-[260px] lg:w-[280px]">
      <Link href={`/roadmap/${id}`}>
        <div
          className={cn(
            'relative w-full h-[340px] sm:h-[360px] overflow-hidden rounded-xl border border-border bg-card shadow-lg',
            'transition-all duration-300 ease-in-out hover:shadow-2xl hover:-translate-y-2'
          )}
        >
          {/* 背景图片 */}
          <div className="absolute inset-0 h-full w-full">
            <CoverImage
              topic={topic}
              title={title}
              className="w-full h-full object-cover transition-transform duration-500 ease-in-out group-hover:scale-110"
            />
          </div>

          {/* 渐变叠加层 */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-black/20" />

          {/* Content */}
          <div className="relative flex h-full flex-col justify-between p-4 sm:p-5 text-white">
            {/* Top Section - Author */}
            <div className="flex h-24 sm:h-32 items-start">
              <div className="flex items-center gap-1.5 sm:gap-2 bg-black/20 backdrop-blur-sm px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg border border-white/10">
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full overflow-hidden bg-sage-100 flex-shrink-0 ring-2 ring-white/50">
                  {!avatarError ? (
                    <Image
                      src={author.avatar}
                      alt={author.name}
                      width={32}
                      height={32}
                      className="object-cover"
                      onError={() => setAvatarError(true)}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-xs sm:text-sm font-bold text-sage-600">
                      {author.name.charAt(0)}
                    </div>
                  )}
                </div>
                <span className="text-[10px] sm:text-xs text-white font-medium truncate max-w-[120px] sm:max-w-none">
                  {author.name}
                </span>
              </div>
            </div>

            {/* Middle Section - slides up on hover */}
            <div className="space-y-2 sm:space-y-3 transition-transform duration-500 ease-in-out group-hover:-translate-y-10 sm:group-hover:-translate-y-12">
              {/* Title */}
              <h3 className="text-base sm:text-lg lg:text-xl font-serif font-bold text-white line-clamp-2 leading-tight">
                {title}
              </h3>

              {/* Tags */}
              <div className="flex flex-wrap gap-1 sm:gap-1.5">
                {tags.slice(0, 3).map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="text-[10px] sm:text-xs px-1.5 sm:px-2 py-0.5 font-medium bg-white/10 text-white border-0 backdrop-blur-sm"
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Bottom Section - revealed on hover */}
            <div className="absolute -bottom-20 left-0 w-full p-4 sm:p-5 opacity-0 transition-all duration-500 ease-in-out group-hover:opacity-100 group-hover:bottom-0">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-3 sm:gap-4">
                  <span className="flex items-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs text-white/90">
                    <Heart size={12} className="sm:size-[14px] text-rose-400 fill-rose-400 flex-shrink-0" />
                    <span className="font-medium">{likes.toLocaleString()}</span>
                  </span>
                  <span className="flex items-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs text-white/90">
                    <Eye size={12} className="sm:size-[14px] flex-shrink-0" />
                    <span className="font-medium">{views.toLocaleString()}</span>
                  </span>
                </div>
                <Button 
                  size="sm" 
                  className="bg-white text-black hover:bg-white/90 text-xs px-2 sm:px-3 h-7 sm:h-8 flex-shrink-0"
                  onClick={(e) => e.preventDefault()}
                >
                  View <ArrowRight className="ml-1 h-3 w-3" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </Link>
    </div>
  );
}

// Main LearningCard Component
export const LearningCard = React.forwardRef<HTMLDivElement, LearningCardProps>(
  (props, ref) => {
    if (props.type === 'create') {
      return <CreateCard />;
    } else if (props.type === 'my') {
      return <MyRoadmapCard {...props} />;
    } else {
      return <CommunityRoadmapCard {...props} />;
    }
  }
);

LearningCard.displayName = 'LearningCard';

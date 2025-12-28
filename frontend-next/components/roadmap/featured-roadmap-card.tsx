/**
 * FeaturedRoadmapCard - 精选路线图卡片组件
 * 
 * 使用 FlippingCard 实现的简洁设计
 * - 正面：显示封面图片、标题和基本信息
 * - 背面：显示详细描述和操作按钮
 */
'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useState, useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { FlippingCard } from '@/components/ui/flipping-card';
import { getCoverImage, fetchCoverImageFromAPI } from '@/lib/cover-image';
import { cn } from '@/lib/utils';
import { Star, Clock, BookOpen, ChevronRight } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

export interface FeaturedRoadmap {
  id: string;
  title: string;
  topic: string;
  author?: {
    name: string;
    avatar?: string;
  };
  stats?: {
    likes?: number;
    views?: number;
    bookmarks?: number;
    learners?: number;
  };
  tags?: string[];
  totalConcepts?: number;
  totalHours?: number;
  difficulty?: 'beginner' | 'intermediate' | 'advanced';
  isTrending?: boolean;
  createdAt?: string;
  stages?: Array<{
    name: string;
    description?: string;
    order: number;
  }>;
}

interface FeaturedRoadmapCardProps {
  roadmap: FeaturedRoadmap;
  className?: string;
  coverImageUrl?: string;  // 可选的封面图 URL（用于批量获取）
}

// 难度级别配置
const DIFFICULTY_CONFIG = {
  beginner: {
    label: 'Beginner',
    color: 'text-green-600 bg-green-50 border-green-200',
  },
  intermediate: {
    label: 'Intermediate',
    color: 'text-amber-600 bg-amber-50 border-amber-200',
  },
  advanced: {
    label: 'Advanced',
    color: 'text-red-600 bg-red-50 border-red-200',
  },
};

/**
 * 格式化相对时间
 */
function formatRelativeTime(dateString?: string): string {
  if (!dateString) return 'Recently';
  
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

/**
 * 卡片正面内容
 */
function CardFront({ roadmap, coverImageUrl }: { roadmap: FeaturedRoadmap; coverImageUrl?: string }) {
  const [imageUrl, setImageUrl] = useState(getCoverImage(roadmap.topic, 400, 300));
  const [imageLoading, setImageLoading] = useState(true);
  const difficulty = roadmap.difficulty || 'intermediate';
  const difficultyConfig = DIFFICULTY_CONFIG[difficulty];
  
  // 检测是否为 R2.dev 图片
  const isR2Image = imageUrl.includes('r2.dev');
  
  // 如果提供了 coverImageUrl，直接使用；否则尝试从 API 获取封面图
  useEffect(() => {
    if (coverImageUrl) {
      setImageUrl(coverImageUrl);
      setImageLoading(false);
    } else if (roadmap.id) {
      fetchCoverImageFromAPI(roadmap.id).then((apiUrl) => {
        if (apiUrl) {
          setImageUrl(apiUrl);
        }
        setImageLoading(false);
      }).catch(() => {
        setImageLoading(false);
      });
    } else {
      setImageLoading(false);
    }
  }, [roadmap.id, coverImageUrl]);

  return (
    <div className="flex flex-col h-full w-full">
      {/* 封面图片 */}
      <div className="relative w-full h-40 overflow-hidden rounded-t-xl bg-sage-100">
        {/* 加载骨架屏 */}
        {imageLoading && (
          <div className="absolute inset-0 bg-gradient-to-br from-sage-200 to-sage-100 animate-pulse" />
        )}
        
        {/* R2.dev 图片使用普通 img 标签 */}
        {isR2Image ? (
          <img
            src={imageUrl}
            alt={roadmap.title}
            className={cn(
              "absolute inset-0 w-full h-full object-cover transition-opacity duration-300",
              imageLoading ? "opacity-0" : "opacity-100"
            )}
            onLoad={() => setImageLoading(false)}
            loading="lazy"
          />
        ) : (
          <Image
            src={imageUrl}
            alt={roadmap.title}
            fill
            className={cn(
              "object-cover transition-opacity duration-300",
              imageLoading ? "opacity-0" : "opacity-100"
            )}
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
            onLoad={() => setImageLoading(false)}
            priority={false}
          />
        )}
        
        {/* 渐变遮罩 */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent" />
        
        {/* Featured Badge */}
        <div className="absolute top-3 left-3 z-10">
          <Badge 
            className="bg-gradient-to-r from-amber-400 to-amber-500 text-white border-0 shadow-lg text-[10px] px-2 py-1 font-bold flex items-center gap-1"
          >
            <Star className="w-3 h-3 fill-white" />
            FEATURED
          </Badge>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="flex flex-col flex-1 p-4">
        {/* 标题 */}
        <h3 className="font-serif font-semibold text-base text-foreground line-clamp-2 mb-3 min-h-[48px]">
          {roadmap.title}
        </h3>

        {/* 标签和难度 */}
        <div className="flex items-center gap-1.5 mb-3 flex-wrap">
          <Badge
            variant="outline"
            className={cn('text-[9px] px-2 py-0.5 font-bold', difficultyConfig.color)}
          >
            {difficultyConfig.label}
          </Badge>
          
          {roadmap.tags && roadmap.tags.slice(0, 2).map((tag) => (
            <Badge
              key={tag}
              variant="secondary"
              className="text-[9px] px-2 py-0.5 font-medium bg-sage-100 text-sage-700 border-0"
            >
              {tag}
            </Badge>
          ))}
        </div>

        {/* 元信息 */}
        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-auto">
          {roadmap.totalConcepts && roadmap.totalConcepts > 0 && (
            <div className="flex items-center gap-1">
              <BookOpen className="w-3.5 h-3.5" />
              <span>{roadmap.totalConcepts} concepts</span>
            </div>
          )}
          {roadmap.totalHours && roadmap.totalHours > 0 && (
            <div className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              <span>{roadmap.totalHours}h</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * 卡片背面内容 - 显示路线图的各个 Stage 信息
 */
function CardBack({ roadmap }: { roadmap: FeaturedRoadmap }) {
  const stages = roadmap.stages || [];
  const hasStages = stages.length > 0;

  return (
    <TooltipProvider>
      <div className="flex flex-col h-full w-full p-4">
        {/* 标题 */}
        <h3 className="font-serif font-semibold text-base text-foreground mb-3 line-clamp-2">
          {roadmap.title}
        </h3>

        {/* Stages 列表 */}
        {hasStages ? (
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
                +{stages.length - 5} more stages
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-sm text-muted-foreground text-center">
              {roadmap.tags && roadmap.tags.length > 0 
                ? `Explore ${roadmap.tags.join(', ')} concepts and build your skills step by step.`
                : `A comprehensive learning path to master ${roadmap.topic}.`
              }
            </p>
          </div>
        )}

        {/* 底部操作区域 */}
        <div className="flex items-center justify-between pt-3 border-t border-sage-100">
          {/* 统计信息 */}
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            {roadmap.totalConcepts && roadmap.totalConcepts > 0 && (
              <div className="flex items-center gap-1">
                <BookOpen className="w-3.5 h-3.5" />
                <span>{roadmap.totalConcepts}</span>
              </div>
            )}
            {roadmap.totalHours && roadmap.totalHours > 0 && (
              <div className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                <span>{roadmap.totalHours}h</span>
              </div>
            )}
          </div>

          {/* 查看按钮 */}
          <Link
            href={`/roadmap/${roadmap.id}`}
            className="flex items-center gap-1 text-xs font-medium text-sage-600 hover:text-sage-700 transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            View
            <ChevronRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </TooltipProvider>
  );
}

export function FeaturedRoadmapCard({ roadmap, className, coverImageUrl }: FeaturedRoadmapCardProps) {
  return (
    <Link href={`/roadmap/${roadmap.id}`} className={cn('block', className)}>
      <FlippingCard
        width={280}
        height={350}
        frontContent={<CardFront roadmap={roadmap} coverImageUrl={coverImageUrl} />}
        backContent={<CardBack roadmap={roadmap} />}
        className="w-full"
      />
    </Link>
  );
}

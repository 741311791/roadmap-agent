/**
 * FeaturedRoadmapCard - 精选路线图卡片组件
 * 
 * 专为 Featured Roadmaps 模块设计，突出社区传播属性
 * 
 * 特点：
 * - 强调创作者信息和社区互动
 * - 显示 likes、views、bookmarks 等社交指标
 * - Featured 徽章标识
 * - 更具视觉冲击力的设计
 */
'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MagicCard } from '@/components/ui/magic-card';
import { ShineBorder } from '@/components/ui/shine-border';
import { 
  Heart, 
  Eye, 
  BookmarkPlus,
  Star,
  TrendingUp,
  Clock,
  Users,
  Sparkles,
} from 'lucide-react';
import { CoverImage } from './cover-image';
import { cn } from '@/lib/utils';

export interface FeaturedRoadmap {
  id: string;
  title: string;
  topic: string;
  author?: {
    name: string;
    avatar?: string;
  };
  stats: {
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
}

interface FeaturedRoadmapCardProps {
  roadmap: FeaturedRoadmap;
  className?: string;
}

// 难度级别配置
const DIFFICULTY_CONFIG = {
  beginner: {
    label: 'Beginner',
    color: 'text-green-600 bg-green-50 border-green-200',
    icon: '●',
  },
  intermediate: {
    label: 'Intermediate',
    color: 'text-amber-600 bg-amber-50 border-amber-200',
    icon: '●●',
  },
  advanced: {
    label: 'Advanced',
    color: 'text-red-600 bg-red-50 border-red-200',
    icon: '●●●',
  },
};

// 格式化数字（1.2k, 10k 等）
function formatNumber(num: number): string {
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}k`;
  }
  return num.toString();
}

// 格式化相对时间
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

export function FeaturedRoadmapCard({ roadmap, className }: FeaturedRoadmapCardProps) {
  const [avatarError, setAvatarError] = useState(false);
  
  const difficulty = roadmap.difficulty || 'intermediate';
  const difficultyConfig = DIFFICULTY_CONFIG[difficulty];
  
  const {
    likes = 0,
    views = 0,
    bookmarks = 0,
    learners = 0,
  } = roadmap.stats;

  return (
    <div className={cn('group relative flex-shrink-0 w-full', className)}>
      <Link href={`/roadmap/${roadmap.id}`} className="block">
        <MagicCard
          className="overflow-hidden h-full rounded-xl"
          gradientSize={350}
          gradientColor="rgba(96, 117, 96, 0.15)"
          gradientFrom="#607560"
          gradientTo="#a3b1a3"
        >
          <Card className="overflow-hidden border-0 shadow-none bg-transparent h-full hover:shadow-2xl transition-shadow duration-300">
            {/* Shine Border 效果 */}
            <ShineBorder
              borderWidth={2}
              duration={10}
              shineColor={["#607560", "#7d8f7d", "#a3b1a3"]}
              className="opacity-0 group-hover:opacity-100 transition-opacity duration-500"
            />
            
            {/* Featured Badge - 左上角 */}
            <div className="absolute top-3 left-3 z-10">
              <Badge 
                className="bg-gradient-to-r from-amber-400 to-amber-500 text-white border-0 shadow-lg text-[10px] px-2 py-1 font-bold flex items-center gap-1"
              >
                <Star className="w-3 h-3 fill-white" />
                FEATURED
              </Badge>
            </div>
            
            {/* Trending Badge - 右上角（如果是趋势路线图） */}
            {roadmap.isTrending && (
              <div className="absolute top-3 right-3 z-10">
                <Badge 
                  className="bg-gradient-to-r from-rose-400 to-pink-500 text-white border-0 shadow-lg text-[10px] px-2 py-1 font-bold flex items-center gap-1 animate-pulse"
                >
                  <TrendingUp className="w-3 h-3" />
                  HOT
                </Badge>
              </div>
            )}
            
            {/* Cover Image */}
            <CoverImage
              topic={roadmap.topic}
              title={roadmap.title}
              className="rounded-t-xl aspect-[16/9]"
            />
            
            <CardContent className="p-4 bg-white/98 backdrop-blur-sm">
              {/* Title */}
              <div className="flex items-start gap-2 mb-3">
                <Sparkles className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0 group-hover:animate-pulse" />
                <h3 className="font-serif font-semibold text-sm text-foreground line-clamp-2 group-hover:text-sage-700 transition-colors min-h-[40px] flex-1">
                  {roadmap.title}
                </h3>
              </div>

              {/* Author Info */}
              {roadmap.author && (
                <div className="flex items-center gap-2 mb-3 px-2 py-1.5 bg-gradient-to-r from-sage-50 to-transparent rounded-lg">
                  <div className="w-6 h-6 rounded-full overflow-hidden bg-sage-100 flex-shrink-0 ring-2 ring-white shadow-sm">
                    {roadmap.author.avatar && !avatarError ? (
                      <Image
                        src={roadmap.author.avatar}
                        alt={roadmap.author.name}
                        width={24}
                        height={24}
                        className="object-cover"
                        onError={() => setAvatarError(true)}
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[10px] font-bold text-sage-600 bg-gradient-to-br from-sage-100 to-sage-200">
                        {roadmap.author.name.charAt(0).toUpperCase()}
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-[10px] text-muted-foreground">Created by</span>
                    <p className="text-[11px] text-foreground font-semibold truncate">
                      {roadmap.author.name}
                    </p>
                  </div>
                </div>
              )}

              {/* Tags & Difficulty */}
              <div className="flex items-center gap-1.5 mb-3 flex-wrap">
                {/* Difficulty Badge */}
                <Badge
                  variant="outline"
                  className={cn('text-[9px] px-2 py-0.5 font-bold', difficultyConfig.color)}
                >
                  {difficultyConfig.icon} {difficultyConfig.label}
                </Badge>
                
                {/* Tags */}
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

              {/* Meta Info */}
              <div className="grid grid-cols-2 gap-2 mb-3 text-[10px]">
                {roadmap.totalConcepts && roadmap.totalConcepts > 0 && (
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <div className="w-1.5 h-1.5 rounded-full bg-sage-400" />
                    <span className="font-medium">{roadmap.totalConcepts} concepts</span>
                  </div>
                )}
                {roadmap.totalHours && roadmap.totalHours > 0 && (
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <Clock className="w-3 h-3 text-sage-500" />
                    <span className="font-medium">{roadmap.totalHours}h</span>
                  </div>
                )}
              </div>

              {/* Social Stats */}
              <div className="flex items-center justify-between pt-3 border-t border-sage-100">
                <div className="flex items-center gap-3 text-[10px]">
                  {/* Likes */}
                  {likes > 0 && (
                    <div className="flex items-center gap-1 text-rose-500 hover:text-rose-600 transition-colors cursor-pointer">
                      <Heart className="w-3.5 h-3.5 fill-rose-100" />
                      <span className="font-bold">{formatNumber(likes)}</span>
                    </div>
                  )}
                  
                  {/* Views */}
                  {views > 0 && (
                    <div className="flex items-center gap-1 text-sage-600">
                      <Eye className="w-3.5 h-3.5" />
                      <span className="font-semibold">{formatNumber(views)}</span>
                    </div>
                  )}
                  
                  {/* Learners */}
                  {learners > 0 && (
                    <div className="flex items-center gap-1 text-blue-600">
                      <Users className="w-3.5 h-3.5" />
                      <span className="font-semibold">{formatNumber(learners)}</span>
                    </div>
                  )}
                </div>

                {/* Time */}
                <div className="text-[9px] text-muted-foreground font-medium">
                  {formatRelativeTime(roadmap.createdAt)}
                </div>
              </div>

              {/* Bookmark Hover Effect */}
              <div className="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <button 
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    // TODO: Implement bookmark functionality
                  }}
                  className="w-8 h-8 rounded-full bg-white shadow-lg border border-sage-200 flex items-center justify-center hover:bg-sage-50 hover:border-sage-300 transition-all"
                >
                  <BookmarkPlus className="w-4 h-4 text-sage-600" />
                </button>
              </div>
            </CardContent>
          </Card>
        </MagicCard>
      </Link>
    </div>
  );
}






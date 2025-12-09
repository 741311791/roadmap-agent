/**
 * RoadmapCard 组件
 * 
 * 统一的路线图卡片组件，支持"我的路线图"和"社区路线图"两种类型
 */
'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
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
  // 用于未完成路线图
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

// 生成步骤中文映射
const STEP_LABELS: Record<string, string> = {
  'queued': '排队中',
  'intent_analysis': '分析学习目标',
  'curriculum_design': '设计课程架构',
  'structure_validation': '验证结构',
  'human_review': '等待审核',
  'content_generation': '生成内容',
  'tutorial_generation': '生成教程',
  'resource_recommendation': '推荐资源',
  'quiz_generation': '生成测验',
  'completed': '已完成',
  'failed': '生成失败',
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

interface RoadmapCardProps {
  roadmap: MyRoadmap | CommunityRoadmap;
  type: 'my' | 'community';
  onDelete?: (roadmapId: string) => void;
  showActions?: boolean;
}

export function RoadmapCard({
  roadmap,
  type,
  onDelete,
  showActions = true,
}: RoadmapCardProps) {
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

  return (
    <div className="group relative flex-shrink-0 w-[220px]">
      {/* 操作菜单 - 只在 my 类型且显示 actions 时显示 */}
      {isMyRoadmap && showActions && onDelete && (
        <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 bg-white/90 hover:bg-white shadow-sm"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                }}
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                className="text-red-600 focus:text-red-600 focus:bg-red-50 cursor-pointer"
                onClick={handleDeleteClick}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                <span>删除</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
      
      <Link href={href} className="block">
        <Card className="overflow-hidden hover:shadow-md transition-all duration-300 border-border/30 hover:border-sage-200 h-full">
          <CoverImage
            topic={roadmap.topic}
            title={roadmap.title}
            className="rounded-t-lg"
          />
          <CardContent className="p-4">
            <h3 className="font-serif font-medium text-sm text-foreground line-clamp-2 mb-2 group-hover:text-sage-600 transition-colors min-h-[40px]">
              {roadmap.title}
            </h3>

            {isMyRoadmap && myRoadmap ? (
              isFailed ? (
                /* 生成失败的路线图 */
                <>
                  {/* 失败指示 */}
                  <div className="space-y-1.5 mb-2">
                    <div className="flex items-center gap-2 text-[10px] text-red-600">
                      <AlertCircle size={12} />
                      <span className="font-medium">
                        {STEP_LABELS[myRoadmap.currentStep || 'failed'] || '生成失败'}
                      </span>
                    </div>
                    {/* 失败进度条 */}
                    <div className="h-1.5 bg-red-100 rounded-full overflow-hidden">
                      <div className="h-full w-full bg-red-500 rounded-full" />
                    </div>
                  </div>

                  {/* 状态 */}
                  <div className="flex items-center justify-between">
                    <Badge
                      variant="outline"
                      className="text-[10px] px-1.5 py-0 border-red-300 text-red-600 bg-red-50"
                    >
                      生成失败
                    </Badge>
                    <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                      <Clock size={10} />
                      {formatRelativeTime(myRoadmap.lastAccessedAt)}
                    </span>
                  </div>
                </>
              ) : isGenerating ? (
                /* 正在生成中的路线图 */
                <>
                  {/* 生成进度指示 */}
                  <div className="space-y-1.5 mb-2">
                    <div className="flex items-center gap-2 text-[10px] text-sage-600">
                      <Loader2 size={12} className="animate-spin" />
                      <span className="font-medium">
                        {STEP_LABELS[myRoadmap.currentStep || 'queued'] || '生成中...'}
                      </span>
                    </div>
                    {/* 无限进度条动画 */}
                    <div className="h-1.5 bg-sage-100 rounded-full overflow-hidden">
                      <div className="h-full w-1/3 bg-sage-500 rounded-full animate-pulse" 
                           style={{ animation: 'pulse 1.5s ease-in-out infinite' }} />
                    </div>
                  </div>

                  {/* 状态 */}
                  <div className="flex items-center justify-between">
                    <Badge
                      variant="outline"
                      className="text-[10px] px-1.5 py-0 border-sage-300 text-sage-600 bg-sage-50"
                    >
                      生成中
                    </Badge>
                    <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                      <Clock size={10} />
                      {formatRelativeTime(myRoadmap.lastAccessedAt)}
                    </span>
                  </div>
                </>
              ) : (
                /* 已完成或学习中的路线图 */
                <>
                  {/* Progress Bar */}
                  <div className="space-y-1.5 mb-2">
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                      <span>{myRoadmap.completedConcepts}/{myRoadmap.totalConcepts}</span>
                      <span className="font-medium text-foreground">{progress.toFixed(0)}%</span>
                    </div>
                    <Progress value={progress} className="h-1.5" />
                  </div>

                  {/* Status & Time */}
                  <div className="flex items-center justify-between">
                    <Badge
                      variant={isCompleted ? 'success' : 'sage'}
                      className="text-[10px] px-1.5 py-0"
                    >
                      {isCompleted ? 'Done' : 'Learning'}
                    </Badge>
                    <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                      <Clock size={10} />
                      {formatRelativeTime(myRoadmap.lastAccessedAt)}
                    </span>
                  </div>
                </>
              )
            ) : communityRoadmap ? (
              <>
                {/* Author */}
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-5 h-5 rounded-full overflow-hidden bg-sage-100 flex-shrink-0">
                    {!avatarError ? (
                      <Image
                        src={communityRoadmap.author.avatar}
                        alt={communityRoadmap.author.name}
                        width={20}
                        height={20}
                        className="object-cover"
                        onError={() => setAvatarError(true)}
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[10px] font-medium text-sage-600">
                        {communityRoadmap.author.name.charAt(0)}
                      </div>
                    )}
                  </div>
                  <span className="text-[11px] text-muted-foreground truncate">
                    {communityRoadmap.author.name}
                  </span>
                </div>

                {/* Tags */}
                <div className="flex flex-wrap gap-1 mb-2">
                  {communityRoadmap.tags.slice(0, 2).map((tag) => (
                    <Badge
                      key={tag}
                      variant="secondary"
                      className="text-[9px] px-1.5 py-0 font-normal"
                    >
                      {tag}
                    </Badge>
                  ))}
                </div>

                {/* Social Stats */}
                <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Heart size={10} className="text-rose-400" />
                    {communityRoadmap.likes.toLocaleString()}
                  </span>
                  <span className="flex items-center gap-1">
                    <Eye size={10} />
                    {communityRoadmap.views.toLocaleString()}
                  </span>
                </div>
              </>
            ) : null}
          </CardContent>
        </Card>
      </Link>
    </div>
  );
}

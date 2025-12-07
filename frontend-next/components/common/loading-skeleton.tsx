/**
 * Loading Skeleton Components
 * Reusable loading states for different UI sections
 */

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

/**
 * RoadmapListSkeleton - 路线图列表加载骨架
 */
export function RoadmapListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }, (_, i) => (
        <Card key={i}>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Skeleton className="h-5 w-5 rounded-full" />
              <Skeleton className="h-6 w-48" />
            </div>
            <Skeleton className="h-4 w-32 mt-2" />
          </CardHeader>
          <CardContent className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <div className="flex gap-2 mt-4">
              <Skeleton className="h-6 w-20" />
              <Skeleton className="h-6 w-20" />
              <Skeleton className="h-6 w-20" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

/**
 * TutorialContentSkeleton - 教程内容加载骨架
 */
export function TutorialContentSkeleton({ lines = 8 }: { lines?: number }) {
  return (
    <div className="space-y-3">
      <Skeleton className="h-8 w-3/4 mb-4" />
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton 
          key={i} 
          className={cn(
            'h-4',
            i % 4 === 3 ? 'w-1/2' : 'w-full'
          )} 
        />
      ))}
      <Skeleton className="h-32 w-full mt-6" />
      {Array.from({ length: 4 }, (_, i) => (
        <Skeleton key={i + lines} className="h-4 w-full" />
      ))}
    </div>
  );
}

/**
 * RoadmapDetailSkeleton - 路线图详情加载骨架
 */
export function RoadmapDetailSkeleton() {
  return (
    <div className="space-y-6">
      {/* 标题区域 */}
      <div className="space-y-3">
        <Skeleton className="h-10 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <div className="flex gap-4 mt-4">
          <Skeleton className="h-8 w-24" />
          <Skeleton className="h-8 w-24" />
          <Skeleton className="h-8 w-24" />
        </div>
      </div>

      {/* 进度条 */}
      <Skeleton className="h-2 w-full" />

      {/* Stage 列表 */}
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-6 w-20" />
                    <Skeleton className="h-6 w-48" />
                  </div>
                  <Skeleton className="h-4 w-full" />
                </div>
                <Skeleton className="h-8 w-8" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/**
 * CardGridSkeleton - 卡片网格加载骨架
 */
export function CardGridSkeleton({ count = 6, columns = 3 }: { count?: number; columns?: 2 | 3 | 4 }) {
  const gridCols = {
    2: 'md:grid-cols-2',
    3: 'md:grid-cols-2 lg:grid-cols-3',
    4: 'md:grid-cols-2 lg:grid-cols-4'
  };

  return (
    <div className={cn('grid gap-4', gridCols[columns])}>
      {Array.from({ length: count }, (_, i) => (
        <Card key={i}>
          <CardHeader>
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-4 w-1/2 mt-2" />
          </CardHeader>
          <CardContent className="space-y-2">
            <Skeleton className="h-20 w-full" />
            <div className="flex gap-2">
              <Skeleton className="h-6 w-16" />
              <Skeleton className="h-6 w-16" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

/**
 * ConceptListSkeleton - 概念列表加载骨架
 */
export function ConceptListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="flex items-center gap-3 p-3 border rounded-lg">
          <Skeleton className="h-4 w-4 rounded-full" />
          <div className="flex-1 space-y-1">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          <Skeleton className="h-6 w-16" />
        </div>
      ))}
    </div>
  );
}

/**
 * TableSkeleton - 表格加载骨架
 */
export function TableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="space-y-3">
      {/* 表头 */}
      <div className="flex gap-4 pb-2 border-b">
        {Array.from({ length: columns }, (_, i) => (
          <Skeleton key={`header-${i}`} className="h-4 flex-1" />
        ))}
      </div>
      {/* 表格行 */}
      {Array.from({ length: rows }, (_, rowIndex) => (
        <div key={`row-${rowIndex}`} className="flex gap-4 py-2">
          {Array.from({ length: columns }, (_, colIndex) => (
            <Skeleton key={`cell-${rowIndex}-${colIndex}`} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

/**
 * ProfileSkeleton - 用户画像加载骨架
 */
export function ProfileSkeleton() {
  return (
    <div className="space-y-6">
      {/* 头像和基本信息 */}
      <div className="flex items-center gap-4">
        <Skeleton className="h-20 w-20 rounded-full" />
        <div className="space-y-2 flex-1">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
      </div>

      {/* 表单区域 */}
      <div className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-10 w-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * FullPageSkeleton - 全页加载骨架
 */
export function FullPageSkeleton() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-4 w-96" />
      <div className="grid gap-6 mt-8">
        <RoadmapDetailSkeleton />
      </div>
    </div>
  );
}

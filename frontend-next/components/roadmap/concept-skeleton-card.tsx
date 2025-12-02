'use client';

import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

interface ConceptSkeletonCardProps {
  className?: string;
}

/**
 * ConceptSkeletonCard - Placeholder card during structure loading
 * 
 * Displays a realistic skeleton that mimics the ConceptCard layout
 * with shimmer animation
 */
export function ConceptSkeletonCard({ className }: ConceptSkeletonCardProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-3 p-3 border rounded-lg',
        'bg-muted/30 border-border/50',
        className
      )}
    >
      {/* Status icon placeholder */}
      <Skeleton className="w-5 h-5 rounded-full flex-shrink-0" />
      
      {/* Content area */}
      <div className="flex-1 min-w-0 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-full" />
      </div>
      
      {/* Right side metadata */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <Skeleton className="h-5 w-14 rounded-full" />
        <Skeleton className="h-4 w-8" />
      </div>
    </div>
  );
}

/**
 * ConceptSkeletonList - Group of skeleton cards for loading state
 */
export function ConceptSkeletonList({ 
  count = 3,
  className 
}: { 
  count?: number;
  className?: string;
}) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: count }).map((_, i) => (
        <ConceptSkeletonCard key={i} />
      ))}
    </div>
  );
}

/**
 * ModuleSkeletonCard - Skeleton for entire module section
 */
export function ModuleSkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn('border rounded-lg', className)}>
      {/* Module header */}
      <div className="p-4">
        <div className="flex items-center gap-2">
          <Skeleton className="w-4 h-4 rounded" />
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-5 w-16 rounded-full ml-auto" />
        </div>
        <Skeleton className="h-3 w-full mt-2 ml-6" />
      </div>
      
      {/* Concept skeletons */}
      <div className="p-4 pt-0">
        <ConceptSkeletonList count={3} />
      </div>
    </div>
  );
}

/**
 * StageSkeletonCard - Full stage section skeleton
 */
export function StageSkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn('border rounded-lg bg-card', className)}>
      {/* Stage header */}
      <div className="p-6 cursor-pointer">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Skeleton className="w-5 h-5 rounded" />
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
        </div>
        <Skeleton className="h-4 w-3/4 mt-2 ml-7" />
      </div>
      
      {/* Modules */}
      <div className="px-6 pb-6 space-y-4">
        <ModuleSkeletonCard />
        <ModuleSkeletonCard />
      </div>
    </div>
  );
}

/**
 * RoadmapSkeletonView - Complete roadmap skeleton for initial loading
 */
export function RoadmapSkeletonView({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-6', className)}>
      {Array.from({ length: 3 }).map((_, i) => (
        <StageSkeletonCard key={i} />
      ))}
    </div>
  );
}


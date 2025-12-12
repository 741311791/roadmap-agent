'use client';

import { Loader2, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

type ContentType = 'tutorial' | 'resources' | 'quiz';

interface GeneratingContentLoaderProps {
  /** 内容类型 */
  contentType: ContentType;
  /** 自定义样式 */
  className?: string;
}

const CONTENT_TYPE_LABELS: Record<ContentType, { name: string; verb: string }> = {
  tutorial: { name: 'Tutorial', verb: 'Generating' },
  resources: { name: 'Learning Resources', verb: 'Fetching' },
  quiz: { name: 'Quiz Questions', verb: 'Generating' },
};

/**
 * GeneratingContentLoader - 内容生成中加载指示器
 * 
 * 简单的加载状态显示组件，配合 WebSocket 实时状态同步使用。
 * 不包含超时检测逻辑，完全依赖后端 WebSocket 推送状态更新。
 * 
 * 使用示例：
 * ```tsx
 * {resourcesGenerating ? (
 *   <GeneratingContentLoader contentType="resources" />
 * ) : (
 *   // 正常内容显示
 * )}
 * ```
 */
export function GeneratingContentLoader({
  contentType,
  className,
}: GeneratingContentLoaderProps) {
  const label = CONTENT_TYPE_LABELS[contentType];

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-4 py-16 px-6 text-center',
        'bg-sage-50 dark:bg-sage-950/20 rounded-xl border border-sage-200 dark:border-sage-900',
        className
      )}
    >
      {/* Loading Icon */}
      <div className="w-16 h-16 rounded-full bg-sage-100 dark:bg-sage-900/50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-sage-600 dark:text-sage-400 animate-spin" />
      </div>

      {/* Message */}
      <div className="space-y-2">
        <h3 className="text-lg font-medium text-sage-800 dark:text-sage-200">
          {label.verb} {label.name}
        </h3>
        <p className="text-sm text-sage-600 dark:text-sage-400">
          This may take a few moments. Please wait...
        </p>
      </div>

      {/* Progress Animation */}
      <div className="w-48 h-1 bg-sage-200 dark:bg-sage-800 rounded-full overflow-hidden">
        <div 
          className="h-full bg-sage-500 dark:bg-sage-400 rounded-full animate-pulse"
          style={{ 
            width: '60%',
            animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
          }}
        />
      </div>

      {/* Hint Text */}
      <p className="text-xs text-sage-500 dark:text-sage-500 max-w-md mt-2">
        💡 Status updates are delivered in real-time via WebSocket
      </p>
    </div>
  );
}


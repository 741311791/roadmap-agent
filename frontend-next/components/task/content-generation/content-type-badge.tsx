'use client';

import { Badge } from '@/components/ui/badge';
import { CheckCircle2, Clock, Loader2, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ContentGenerationStatus } from '@/types/content-generation';

interface ContentTypeBadgeProps {
  label: string;
  status: ContentGenerationStatus;
  className?: string;
}

/**
 * 内容类型状态标记
 * 
 * 显示单个内容类型（Tutorial/Resources/Quiz）的生成状态
 */
export function ContentTypeBadge({ label, status, className }: ContentTypeBadgeProps) {
  const config = {
    pending: {
      icon: Clock,
      className: 'bg-gray-100 text-gray-600 border-gray-200',
    },
    generating: {
      icon: Loader2,
      className: 'bg-blue-100 text-blue-600 border-blue-200',
    },
    completed: {
      icon: CheckCircle2,
      className: 'bg-green-100 text-green-600 border-green-200',
    },
    failed: {
      icon: XCircle,
      className: 'bg-red-100 text-red-600 border-red-200',
    },
  }[status];

  const Icon = config.icon;

  return (
    <Badge
      variant="outline"
      className={cn('text-xs gap-1 px-2 py-0.5', config.className, className)}
    >
      <Icon
        className={cn('w-3 h-3', status === 'generating' && 'animate-spin')}
      />
      <span>{label}</span>
    </Badge>
  );
}

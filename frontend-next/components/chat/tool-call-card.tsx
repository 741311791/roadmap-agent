'use client';

import { Loader2, Wrench } from 'lucide-react';

import { cn } from '@/lib/utils';
import type { MentorToolCallState } from '@/lib/runtime/mentor-runtime-provider';

interface ToolCallCardProps {
  toolCall: MentorToolCallState;
}

/**
 * 工具调用展示卡片。
 */
export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const hasResult = toolCall.result !== undefined;

  return (
    <div
      className={cn(
        'rounded-md border px-3 py-2 text-xs space-y-1',
        toolCall.loading
          ? 'border-blue-200 bg-blue-50/70'
          : toolCall.success
            ? 'border-green-200 bg-green-50/70'
            : 'border-red-200 bg-red-50/70'
      )}
    >
      <div className="flex items-center gap-2 font-medium text-foreground">
        {toolCall.loading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-600" />
        ) : (
          <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
        )}
        <span>{toolCall.toolName}</span>
      </div>

      {toolCall.args && (
        <p className="text-muted-foreground break-all">
          参数：{JSON.stringify(toolCall.args)}
        </p>
      )}

      {hasResult && (
        <p className="text-muted-foreground break-all">
          结果：{JSON.stringify(toolCall.result)}
        </p>
      )}
    </div>
  );
}


'use client';

import { useMemo, useState } from 'react';
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Loader2,
  TriangleAlert,
  Wrench,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { MentorToolResultRenderer } from '@/lib/tools/mentor-toolkit';
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
  const [argsOpen, setArgsOpen] = useState(false);
  const [resultOpen, setResultOpen] = useState(true);

  const statusNode = useMemo(() => {
    if (toolCall.loading) {
      return (
        <Badge variant="secondary" className="gap-1 rounded-md px-2 py-0 text-[11px]">
          <Loader2 className="h-3 w-3 animate-spin" />
          执行中
        </Badge>
      );
    }

    if (toolCall.success) {
      return (
        <Badge variant="success" className="gap-1 rounded-md px-2 py-0 text-[11px]">
          <CheckCircle2 className="h-3 w-3" />
          已完成
        </Badge>
      );
    }

    return (
      <Badge variant="destructive" className="gap-1 rounded-md px-2 py-0 text-[11px]">
        <TriangleAlert className="h-3 w-3" />
        失败
      </Badge>
    );
  }, [toolCall.loading, toolCall.success]);

  return (
    <div
      className={cn(
        'rounded-xl border px-3 py-2 text-xs shadow-sm space-y-2',
        toolCall.loading
          ? 'border-primary/25 bg-primary/5'
          : toolCall.success
            ? 'border-green-200/90 bg-green-50/70'
            : 'border-red-200/90 bg-red-50/70'
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-medium text-foreground">
          {toolCall.loading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
          ) : (
            <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
          )}
          <span className="truncate max-w-[180px]">{toolCall.toolName}</span>
        </div>
        {statusNode}
      </div>

      {toolCall.args && (
        <Collapsible open={argsOpen} onOpenChange={setArgsOpen}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-1 text-[11px] text-muted-foreground hover:text-foreground"
            >
              {argsOpen ? (
                <ChevronDown className="mr-1 h-3 w-3" />
              ) : (
                <ChevronRight className="mr-1 h-3 w-3" />
              )}
              查看参数
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <pre className="overflow-x-auto rounded-md bg-background/80 p-2 text-[11px] leading-relaxed text-muted-foreground">
              {JSON.stringify(toolCall.args, null, 2)}
            </pre>
          </CollapsibleContent>
        </Collapsible>
      )}

      {hasResult && (
        <Collapsible open={resultOpen} onOpenChange={setResultOpen}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-1 text-[11px] text-muted-foreground hover:text-foreground"
            >
              {resultOpen ? (
                <ChevronDown className="mr-1 h-3 w-3" />
              ) : (
                <ChevronRight className="mr-1 h-3 w-3" />
              )}
              查看结果
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="rounded-md bg-background/80 p-2">
              <MentorToolResultRenderer
                toolName={toolCall.toolName}
                result={toolCall.result}
              />
            </div>
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  );
}


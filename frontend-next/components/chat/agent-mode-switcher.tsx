'use client';

import { GraduationCap, Sparkles } from 'lucide-react';

import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { MentorAgentMode } from '@/lib/runtime/mentor-runtime-provider';

interface AgentModeSwitcherProps {
  mode: MentorAgentMode;
  onModeChange: (mode: MentorAgentMode) => void;
  disabled?: boolean;
}

/**
 * Agent 模式切换组件（伴学 / 导学）。
 */
export function AgentModeSwitcher({
  mode,
  onModeChange,
  disabled = false,
}: AgentModeSwitcherProps) {
  return (
    <Tabs
      value={mode}
      onValueChange={(value) => onModeChange(value as MentorAgentMode)}
      className="w-full"
    >
      <TabsList className="grid w-full grid-cols-2 h-10 rounded-lg bg-muted/70 p-1">
        <TabsTrigger
          value="companion"
          disabled={disabled}
          className="text-xs data-[state=active]:shadow-sm"
        >
          <Sparkles className="mr-1 h-3.5 w-3.5" />
          伴学
        </TabsTrigger>
        <TabsTrigger
          value="tutoring"
          disabled={disabled}
          className="text-xs data-[state=active]:shadow-sm"
        >
          <GraduationCap className="mr-1 h-3.5 w-3.5" />
          导学
        </TabsTrigger>
      </TabsList>
    </Tabs>
  );
}


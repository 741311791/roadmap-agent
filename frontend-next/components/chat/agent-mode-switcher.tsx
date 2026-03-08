'use client';

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
      <TabsList className="grid w-full grid-cols-2 h-8">
        <TabsTrigger value="companion" disabled={disabled} className="text-xs">
          伴学
        </TabsTrigger>
        <TabsTrigger value="tutoring" disabled={disabled} className="text-xs">
          导学
        </TabsTrigger>
      </TabsList>
    </Tabs>
  );
}


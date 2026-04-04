"use client";

import type { ReactNode } from "react";

import { PromptInputProvider } from "@/components/deerflow-native/ai-elements/prompt-input";
import { DeerFlowArtifactsProvider } from "@/components/deerflow-chat-test/deerflow-artifacts-context";
import { DeerFlowSubtasksProvider } from "@/components/deerflow-chat-test/deerflow-subtasks-context";

/**
 * Deer-Flow 聊天工作台 provider 组合。
 */
export function DeerFlowChatProviders({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <DeerFlowSubtasksProvider>
      <DeerFlowArtifactsProvider>
        <PromptInputProvider>{children}</PromptInputProvider>
      </DeerFlowArtifactsProvider>
    </DeerFlowSubtasksProvider>
  );
}

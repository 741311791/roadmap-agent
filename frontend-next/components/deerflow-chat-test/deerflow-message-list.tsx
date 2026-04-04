"use client";

import type { ChatStatus } from "ai";
import { Sparkles } from "lucide-react";
import { useMemo } from "react";

import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/deerflow-native/ai-elements/conversation";
import {
  coalesceConsecutiveAssistantMessages,
  type DeerFlowChatMessage,
} from "@/components/deerflow-chat-test/deerflow-chat-state";

import { DeerFlowMessageListItem } from "./deerflow-message-list-item";

/**
 * Deer-Flow 消息列表。
 */
export function DeerFlowMessageList({
  messages,
  isLoading,
  status,
  threadId,
}: {
  messages: DeerFlowChatMessage[];
  isLoading: boolean;
  status: ChatStatus;
  /** 当前线程 ID，用于 present_files 产物预览 */
  threadId?: string;
}) {
  const isStreaming = status === "submitted" || status === "streaming";
  const timelineMessages = useMemo(
    () => coalesceConsecutiveAssistantMessages(messages),
    [messages]
  );

  if (isLoading && messages.length === 0) {
    return <DeerFlowMessageListSkeleton />;
  }

  return (
    <Conversation className="flex-1 px-6 py-8">
      <ConversationContent className="mx-auto w-full max-w-3xl gap-8 pt-6">
        {messages.length === 0 && !isLoading ? (
          <ConversationEmptyState
            icon={<Sparkles className="h-8 w-8 text-slate-900" />}
            title=""
            description=""
            className="min-h-[26vh] opacity-0"
          />
        ) : null}

        {timelineMessages.map((message) => (
          <DeerFlowMessageListItem
            key={message.id}
            isLoading={isStreaming && Boolean(message.isStreaming)}
            message={message}
            threadId={threadId}
          />
        ))}
      </ConversationContent>
      <ConversationScrollButton />
    </Conversation>
  );
}

/**
 * DeerFlowMessageListSkeleton - 历史加载骨架
 */
function DeerFlowMessageListSkeleton() {
  return (
    <Conversation className="flex-1 px-6 py-8">
      <ConversationContent className="mx-auto w-full max-w-4xl gap-8 pt-4">
        <div className="space-y-6">
          <div className="h-5 w-36 animate-pulse rounded-full bg-slate-200" />
          <div className="ml-auto h-28 w-[72%] animate-pulse rounded-[28px] bg-slate-100" />
          <div className="h-40 w-[82%] animate-pulse rounded-[28px] bg-slate-100" />
          <div className="ml-auto h-24 w-[58%] animate-pulse rounded-[28px] bg-slate-100" />
        </div>
      </ConversationContent>
    </Conversation>
  );
}

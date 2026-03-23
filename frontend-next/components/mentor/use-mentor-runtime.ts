"use client";

import { useMemo } from "react";
import {
  useLocalRuntime,
  type ChatModelAdapter,
  type ChatModelRunResult,
  type ThreadMessage,
  type ThreadMessageLike,
} from "@assistant-ui/react";

import {
  buildMentorAssistantMessage,
  buildMentorChatRequest,
  buildMentorStreamMetadata,
} from "@/components/mentor/mentor-adapter";
import {
  streamMentorChat,
  type MentorChatMetaEvent,
} from "@/components/mentor/mentor-api";
import type {
  MentorAgentType,
  MentorChapterContext,
} from "@/components/mentor/types";

interface MentorRuntimeStateChange {
  status: "idle" | "streaming" | "error";
  errorMessage?: string;
  traceId?: string;
}

interface UseMentorRuntimeOptions {
  agentType: MentorAgentType;
  modelId: string;
  threadId: string;
  remoteSessionId?: string;
  chapterContext: MentorChapterContext;
  initialMessages: ThreadMessageLike[];
  onSessionBound?: (params: { sessionId: string; traceId?: string }) => void;
  onRuntimeStateChange?: (params: MentorRuntimeStateChange) => void;
}

/**
 * extractLatestUserMessage - 获取最后一条用户消息文本
 */
function extractLatestUserMessage(messages: readonly ThreadMessage[]): string {
  const latestUserMessage = [...messages].reverse().find((message) => message.role === "user");

  if (!latestUserMessage) {
    return "Help me understand this chapter.";
  }

  return latestUserMessage.content
    .map((part) => ("text" in part ? part.text : ""))
    .join("")
    .trim();
}

/**
 * useMentorRuntime - 使用 assistant-ui LocalRuntime 接入真实导师后端
 */
export function useMentorRuntime({
  agentType,
  modelId,
  threadId,
  remoteSessionId,
  chapterContext,
  initialMessages,
  onSessionBound,
  onRuntimeStateChange,
}: UseMentorRuntimeOptions) {
  const chatModel = useMemo<ChatModelAdapter>(() => {
    return {
      async *run(options): AsyncGenerator<ChatModelRunResult, void, void> {
        const latestUserMessage = extractLatestUserMessage(options.messages);
        let accumulatedText = "";
        let metaEvent: MentorChatMetaEvent | undefined;
        const responseStartedAt = performance.now();

        onRuntimeStateChange?.({
          status: "streaming",
        });

        try {
          const requestPayload = buildMentorChatRequest({
            message: latestUserMessage,
            remoteSessionId,
            agentType,
            modelId,
            chapterContext,
          });

          for await (const event of streamMentorChat(requestPayload, options.abortSignal)) {
            if (options.abortSignal.aborted) {
              onRuntimeStateChange?.({
                status: "idle",
              });
              return;
            }

            if (event.type === "meta") {
              metaEvent = event;
              onSessionBound?.({
                sessionId: event.session_id,
                traceId: event.trace_id,
              });
              continue;
            }

            if (event.type === "error") {
              throw new Error(event.message);
            }

            accumulatedText += event.delta;

            yield buildMentorAssistantMessage({
              content: accumulatedText,
              metadata: buildMentorStreamMetadata({
                threadId,
                modelId,
                agentType,
                metaEvent,
              }),
            });
          }

          if (accumulatedText) {
            yield buildMentorAssistantMessage({
              content: accumulatedText,
              metadata: buildMentorStreamMetadata({
                threadId,
                modelId,
                agentType,
                metaEvent,
                responseDurationMs: Math.round(performance.now() - responseStartedAt),
              }),
            });
          }

          onRuntimeStateChange?.({
            status: "idle",
            traceId: metaEvent?.trace_id,
          });
        } catch (error) {
          if (options.abortSignal.aborted) {
            onRuntimeStateChange?.({
              status: "idle",
              traceId: metaEvent?.trace_id,
            });
            return;
          }

          const errorMessage =
            error instanceof Error
              ? error.message
              : "Mentor runtime request failed unexpectedly.";
          onRuntimeStateChange?.({
            status: "error",
            errorMessage,
            traceId: metaEvent?.trace_id,
          });
          throw error;
        }
      },
    };
  }, [
    agentType,
    chapterContext,
    modelId,
    onRuntimeStateChange,
    onSessionBound,
    remoteSessionId,
    threadId,
  ]);

  return useLocalRuntime(chatModel, {
    initialMessages,
  });
}

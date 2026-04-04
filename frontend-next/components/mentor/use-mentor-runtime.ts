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
  MentorAgentKind,
  MentorChapterContext,
  MentorContentPart,
  MentorQaStyle,
} from "@/components/mentor/types";

interface MentorRuntimeStateChange {
  status: "idle" | "streaming" | "error";
  errorMessage?: string;
  traceId?: string;
}

interface UseMentorRuntimeOptions {
  agentKind: MentorAgentKind;
  qaStyle: MentorQaStyle;
  modelId: string;
  threadId: string;
  remoteSessionId?: string;
  chapterContext: MentorChapterContext;
  initialMessages: ThreadMessageLike[];
  onSessionBound?: (params: { sessionId: string; traceId?: string }) => void;
  onMetaEvent?: (event: MentorChatMetaEvent) => void;
  onRuntimeStateChange?: (params: MentorRuntimeStateChange) => void;
}

const STREAM_DELTA_SOFT_CHUNK_SIZE = 28;

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
 * appendTextContentPart - 追加文本片段并合并相邻文本块
 */
function appendTextContentPart(contentParts: MentorContentPart[], text: string): void {
  if (!text) {
    return;
  }

  const lastPart = contentParts.at(-1);
  if (lastPart?.type === "text") {
    lastPart.text = `${lastPart.text}${text}`;
    return;
  }

  contentParts.push({
    type: "text",
    text,
  });
}

/**
 * appendThinkingContentPart - 追加思考片段并合并相邻思考块
 */
function appendThinkingContentPart(contentParts: MentorContentPart[], text: string): void {
  if (!text) {
    return;
  }

  const lastPart = contentParts.at(-1);
  if (lastPart?.type === "thinking") {
    lastPart.text = `${lastPart.text}${text}`;
    return;
  }

  contentParts.push({
    type: "thinking",
    text,
  });
}

/**
 * upsertToolContentPart - 更新或创建工具片段
 */
function upsertToolContentPart(params: {
  contentParts: MentorContentPart[];
  toolCallId: string;
  toolName: string;
  arguments: Record<string, unknown>;
  state: "running" | "completed";
  result?: string;
  isError?: boolean;
}): void {
  const matchedPart = params.contentParts.find(
    (part) => part.type === "tool-call" && part.toolCallId === params.toolCallId
  );

  if (matchedPart?.type === "tool-call") {
    matchedPart.toolName = params.toolName;
    matchedPart.arguments = params.arguments;
    matchedPart.state = params.state;
    matchedPart.result = params.result;
    matchedPart.isError = params.isError;
    return;
  }

  params.contentParts.push({
    type: "tool-call",
    toolCallId: params.toolCallId,
    toolName: params.toolName,
    arguments: params.arguments,
    state: params.state,
    result: params.result,
    isError: params.isError,
  });
}

/**
 * splitMentorDeltaForDisplay - 将较大的后端增量切成更细的显示片段
 *
 * 为什么这样做：
 * - 部分模型网关会把较长文本合并成大块 delta 返回
 * - 如果前端一次性塞入整段内容，用户会感觉“不是流式输出”
 * - 这里做轻量切片，只影响显示节奏，不改变最终文本内容
 */
export function splitMentorDeltaForDisplay(delta: string): string[] {
  if (!delta) {
    return [];
  }

  if (delta.length <= STREAM_DELTA_SOFT_CHUNK_SIZE) {
    return [delta];
  }

  const segments: string[] = [];
  let remainingText = delta;

  while (remainingText.length > STREAM_DELTA_SOFT_CHUNK_SIZE) {
    const candidate = remainingText.slice(0, STREAM_DELTA_SOFT_CHUNK_SIZE);
    const breakChars = ["\n", "。", "！", "？", "；", "，", " ", ")", "]"];
    let splitIndex = -1;

    for (const breakChar of breakChars) {
      const nextIndex = candidate.lastIndexOf(breakChar);
      if (nextIndex > splitIndex) {
        splitIndex = nextIndex;
      }
    }

    if (splitIndex < Math.floor(STREAM_DELTA_SOFT_CHUNK_SIZE / 3)) {
      splitIndex = STREAM_DELTA_SOFT_CHUNK_SIZE - 1;
    }

    const nextSegment = remainingText.slice(0, splitIndex + 1);
    segments.push(nextSegment);
    remainingText = remainingText.slice(splitIndex + 1);
  }

  if (remainingText) {
    segments.push(remainingText);
  }

  return segments;
}

/**
 * waitForNextStreamPaint - 让大块 delta 在多个渲染帧中逐步进入 UI
 */
async function waitForNextStreamPaint(): Promise<void> {
  await new Promise<void>((resolve) => {
    if (typeof window === "undefined" || typeof window.requestAnimationFrame !== "function") {
      setTimeout(resolve, 0);
      return;
    }

    window.requestAnimationFrame(() => resolve());
  });
}

/**
 * useMentorRuntime - 使用 assistant-ui LocalRuntime 接入真实导师后端
 */
export function useMentorRuntime({
  agentKind,
  qaStyle,
  modelId,
  threadId,
  remoteSessionId,
  chapterContext,
  initialMessages,
  onSessionBound,
  onMetaEvent,
  onRuntimeStateChange,
}: UseMentorRuntimeOptions) {
  const chatModel = useMemo<ChatModelAdapter>(() => {
    return {
      async *run(options): AsyncGenerator<ChatModelRunResult, void, void> {
        const latestUserMessage = extractLatestUserMessage(options.messages);
        const contentParts: MentorContentPart[] = [];
        let metaEvent: MentorChatMetaEvent | undefined;
        const responseStartedAt = performance.now();

        onRuntimeStateChange?.({
          status: "streaming",
        });

        try {
          const requestPayload = buildMentorChatRequest({
            message: latestUserMessage,
            remoteSessionId,
            agentKind,
            qaStyle,
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
              onMetaEvent?.(event);
              onSessionBound?.({
                sessionId: event.session_id,
                traceId: event.trace_id,
              });
              continue;
            }

            if (event.type === "error") {
              throw new Error(event.message);
            }

            if (event.type === "delta") {
              for (const deltaChunk of splitMentorDeltaForDisplay(event.delta)) {
                appendTextContentPart(contentParts, deltaChunk);
                yield buildMentorAssistantMessage({
                  contentParts,
                  metadata: buildMentorStreamMetadata({
                    threadId,
                    modelId,
                    agentKind,
                    qaStyle,
                    metaEvent,
                  }),
                });
                await waitForNextStreamPaint();
              }
              continue;
            }

            if (event.type === "thinking") {
              for (const deltaChunk of splitMentorDeltaForDisplay(event.delta)) {
                appendThinkingContentPart(contentParts, deltaChunk);
                yield buildMentorAssistantMessage({
                  contentParts,
                  metadata: buildMentorStreamMetadata({
                    threadId,
                    modelId,
                    agentKind,
                    qaStyle,
                    metaEvent,
                  }),
                });
                await waitForNextStreamPaint();
              }
              continue;
            }

            if (event.type === "tool_start") {
              upsertToolContentPart({
                contentParts,
                toolCallId: event.tool_call_id,
                toolName: event.tool_name,
                arguments: event.arguments,
                state: "running",
              });
              yield buildMentorAssistantMessage({
                contentParts,
                metadata: buildMentorStreamMetadata({
                  threadId,
                  modelId,
                  agentKind,
                  qaStyle,
                  metaEvent,
                }),
              });
              continue;
            }

            if (event.type === "tool_result") {
              upsertToolContentPart({
                contentParts,
                toolCallId: event.tool_call_id,
                toolName: event.tool_name,
                arguments: event.arguments,
                state: "completed",
                result: event.result,
                isError: event.is_error,
              });
              yield buildMentorAssistantMessage({
                contentParts,
                metadata: buildMentorStreamMetadata({
                  threadId,
                  modelId,
                  agentKind,
                  qaStyle,
                  metaEvent,
                }),
              });
              continue;
            }
          }

          if (contentParts.length > 0) {
            yield buildMentorAssistantMessage({
              contentParts,
              metadata: buildMentorStreamMetadata({
                threadId,
                modelId,
                agentKind,
                qaStyle,
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
    agentKind,
    chapterContext,
    modelId,
    onMetaEvent,
    onRuntimeStateChange,
    onSessionBound,
    qaStyle,
    remoteSessionId,
    threadId,
  ]);

  return useLocalRuntime(chatModel, {
    initialMessages,
  });
}

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
  coerceDeerFlowToolArgumentsToRecord,
  extractDeerFlowToolCallArguments,
  parseTodosPayload,
} from "@/components/deerflow-chat-test/deerflow-chat-state";
import type { DeerFlowTodo } from "@/components/deerflow-chat-test/deerflow-thread-context";
import {
  buildMentorAssistantMessage,
} from "@/components/mentor/mentor-adapter";
import { extractTodosFromMentorContentParts } from "@/components/mentor/mentor-deerflow-adapter";
import {
  streamMentorDeerFlowChat,
  type DeerFlowMetadataEvent,
  type DeerFlowMentorChatRequestPayload,
  type DeerFlowSseEvent,
} from "@/components/mentor/mentor-deerflow-api";
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

interface UseMentorDeerFlowRuntimeOptions {
  agentKind: MentorAgentKind;
  qaStyle: MentorQaStyle;
  modelId: string;
  threadId: string;
  remoteSessionId?: string;
  chapterContext: MentorChapterContext;
  initialMessages: ThreadMessageLike[];
  onSessionBound?: (params: { sessionId: string; traceId?: string }) => void;
  onRuntimeStateChange?: (params: MentorRuntimeStateChange) => void;
  /** 与官方一致：每次 values 快照中的 thread.values.todos */
  onTodosSnapshot?: (todos: DeerFlowTodo[]) => void;
}

interface DeerFlowSerializedToolCall {
  id?: string;
  name?: string;
  args?: Record<string, unknown> | string;
  arguments?: unknown;
  function?: { arguments?: unknown };
}

interface DeerFlowSerializedMessage {
  id?: string;
  type?: string;
  content?: unknown;
  additional_kwargs?: {
    reasoning_content?: string;
  };
  tool_calls?: DeerFlowSerializedToolCall[];
  tool_call_id?: string;
  name?: string;
  status?: string;
}

interface DeerFlowValuesPayload {
  messages?: DeerFlowSerializedMessage[];
  title?: string;
  todos?: unknown;
  [key: string]: unknown;
}

/**
 * 将 LangGraph / 网关下发的 values 数据规范为扁平快照（兼容外层再包一层 `values`）。
 */
function normalizeDeerFlowValuesPayload(data: unknown): DeerFlowValuesPayload | null {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return null;
  }

  const obj = data as Record<string, unknown>;
  if ("messages" in obj || "todos" in obj || "title" in obj) {
    return obj as DeerFlowValuesPayload;
  }

  const inner = obj.values;
  if (inner && typeof inner === "object" && !Array.isArray(inner)) {
    return inner as DeerFlowValuesPayload;
  }

  return null;
}

/**
 * extractLatestUserMessage - 获取最后一条用户消息文本
 */
function extractLatestUserMessage(messages: readonly ThreadMessage[]): string {
  const latestUserMessage = [...messages].reverse().find((message) => message.role === "user");

  if (!latestUserMessage) {
    return "Help me understand the current roadmap step.";
  }

  return latestUserMessage.content
    .map((part) => ("text" in part ? part.text : ""))
    .join("")
    .trim();
}

/**
 * extractSerializedMessageText - 提取 Deer-Flow 序列化消息文本
 */
function extractSerializedMessageText(content: unknown): string {
  if (typeof content === "string") {
    return content.trim();
  }

  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (typeof part === "string") {
          return part;
        }

        if (
          typeof part === "object" &&
          part !== null &&
          "text" in part &&
          typeof part.text === "string"
        ) {
          return part.text;
        }

        return "";
      })
      .join("\n")
      .trim();
  }

  return "";
}

/**
 * appendTextContentPart - 合并文本片段
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
 * appendThinkingContentPart - 合并思考片段
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
 * upsertToolContentPart - 创建或更新工具片段
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
    matchedPart.arguments =
      Object.keys(params.arguments).length > 0
        ? params.arguments
        : matchedPart.arguments;
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
 * 路线图伴学默认 Deer-Flow 模式：与官方 Pro 一致（启用 is_plan_mode → To-do 列表）。
 */
const DEFAULT_DEERFLOW_MENTOR_MODE = "pro" as const;

/**
 * buildDeerFlowChatRequest - 构建 Deer-Flow 聊天请求体
 */
function buildDeerFlowChatRequest(params: {
  message: string;
  remoteSessionId?: string;
  chapterContext: MentorChapterContext;
}): DeerFlowMentorChatRequestPayload {
  const mode = DEFAULT_DEERFLOW_MENTOR_MODE;
  const reasoning_effort = "medium" as const;

  return {
    message: params.message,
    thread_id: params.remoteSessionId,
    context: {
      roadmap_id: params.chapterContext.roadmapId,
      concept_id: params.chapterContext.conceptId,
      concept_title: params.chapterContext.conceptName,
      tutorial_excerpt: params.chapterContext.conceptSummary,
      roadmap_context: params.chapterContext.conceptSummary,
      mode,
      reasoning_effort,
    },
  };
}

/**
 * buildDeerFlowContentParts - 基于 Deer-Flow values 快照重建当前轮次的可视内容
 */
export function buildDeerFlowContentParts(
  messages: DeerFlowSerializedMessage[]
): MentorContentPart[] {
  const contentParts: MentorContentPart[] = [];
  const lastHumanIndex = messages.map((message) => message.type).lastIndexOf("human");
  const visibleMessages =
    lastHumanIndex >= 0 ? messages.slice(lastHumanIndex + 1) : messages;

  for (const message of visibleMessages) {
    if (message.type === "system") {
      continue;
    }

    if (message.type === "ai") {
      const reasoningContent = message.additional_kwargs?.reasoning_content?.trim();
      if (reasoningContent) {
        appendThinkingContentPart(contentParts, reasoningContent);
      }

      for (const toolCall of message.tool_calls ?? []) {
        if (!toolCall.id || !toolCall.name) {
          continue;
        }

        upsertToolContentPart({
          contentParts,
          toolCallId: toolCall.id,
          toolName: toolCall.name,
          arguments: coerceDeerFlowToolArgumentsToRecord(
            extractDeerFlowToolCallArguments(toolCall)
          ),
          state: "running",
        });
      }

      const text = extractSerializedMessageText(message.content);
      if (text) {
        appendTextContentPart(contentParts, text);
      }
      continue;
    }

    if (message.type === "tool" && message.tool_call_id) {
      upsertToolContentPart({
        contentParts,
        toolCallId: message.tool_call_id,
        toolName: message.name ?? "tool",
        arguments: {},
        state: "completed",
        result: extractSerializedMessageText(message.content),
        isError: message.status === "error",
      });
    }
  }

  return contentParts;
}

/**
 * useMentorDeerFlowRuntime - 使用 assistant-ui LocalRuntime 接入 Deer-Flow 代理后端
 */
export function useMentorDeerFlowRuntime({
  agentKind,
  qaStyle,
  modelId,
  threadId,
  remoteSessionId,
  chapterContext,
  initialMessages,
  onSessionBound,
  onRuntimeStateChange,
  onTodosSnapshot,
}: UseMentorDeerFlowRuntimeOptions) {
  const chatModel = useMemo<ChatModelAdapter>(() => {
    return {
      async *run(options): AsyncGenerator<ChatModelRunResult, void, void> {
        const latestUserMessage = extractLatestUserMessage(options.messages);
        let metadataEvent: DeerFlowMetadataEvent | undefined;

        onRuntimeStateChange?.({
          status: "streaming",
        });

        try {
          const requestPayload = buildDeerFlowChatRequest({
            message: latestUserMessage,
            remoteSessionId,
            chapterContext,
          });

          for await (const event of streamMentorDeerFlowChat(
            requestPayload,
            options.abortSignal
          )) {
            if (options.abortSignal.aborted) {
              onRuntimeStateChange?.({
                status: "idle",
              });
              return;
            }

            if (event.event === "metadata") {
              metadataEvent = event as DeerFlowMetadataEvent;
              onSessionBound?.({
                sessionId: metadataEvent.data.thread_id,
                traceId: metadataEvent.data.run_id,
              });
              continue;
            }

            if (event.event === "error") {
              const errorMessage =
                typeof event.data === "object" &&
                event.data !== null &&
                "message" in event.data &&
                typeof event.data.message === "string"
                  ? event.data.message
                  : "Deer-Flow stream failed.";
              throw new Error(errorMessage);
            }

            if (event.event === "values") {
              const payload =
                normalizeDeerFlowValuesPayload(event.data) ?? (event.data as DeerFlowValuesPayload);

              const serializedMessages = Array.isArray(payload.messages) ? payload.messages : [];
              const contentParts = buildDeerFlowContentParts(serializedMessages);

              const hasTodosField = Object.prototype.hasOwnProperty.call(payload, "todos");
              let nextTodos: DeerFlowTodo[] | undefined;
              if (hasTodosField) {
                nextTodos = parseTodosPayload(payload.todos);
              } else {
                const fromWriteTodos = extractTodosFromMentorContentParts(contentParts);
                if (fromWriteTodos.length > 0) {
                  nextTodos = fromWriteTodos;
                }
              }

              if (nextTodos !== undefined) {
                onTodosSnapshot?.(nextTodos);
              }

              if (contentParts.length === 0) {
                continue;
              }

              yield buildMentorAssistantMessage({
                contentParts,
                metadata: {
                  threadId,
                  sessionId: metadataEvent?.data.thread_id,
                  traceId: metadataEvent?.data.run_id,
                  modelId,
                  agentKind,
                  qaStyle,
                },
              });
              continue;
            }

            if (event.event === "end") {
              break;
            }
          }

          onRuntimeStateChange?.({
            status: "idle",
            traceId: metadataEvent?.data.run_id,
          });
        } catch (error) {
          const errorMessage =
            error instanceof Error
              ? error.message
              : "Failed to stream Deer-Flow response.";
          onRuntimeStateChange?.({
            status: "error",
            errorMessage,
            traceId: metadataEvent?.data.run_id,
          });
          throw error;
        }
      },
    };
  }, [
    agentKind,
    chapterContext,
    modelId,
    onRuntimeStateChange,
    onSessionBound,
    onTodosSnapshot,
    qaStyle,
    remoteSessionId,
    threadId,
  ]);

  return useLocalRuntime(chatModel, {
    initialMessages,
  });
}

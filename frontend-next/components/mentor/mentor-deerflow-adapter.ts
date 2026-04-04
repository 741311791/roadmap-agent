"use client";

import type { ThreadMessageLike } from "@assistant-ui/react";

import { parseTodosPayload } from "@/components/deerflow-chat-test/deerflow-chat-state";
import type { DeerFlowTodo } from "@/components/deerflow-chat-test/deerflow-thread-context";
import { normalizeMentorContentParts } from "@/components/mentor/mentor-adapter";
import type {
  DeerFlowMentorMessageDto,
  DeerFlowMentorThreadDto,
} from "@/components/mentor/mentor-deerflow-api";
import type {
  MentorContentPart,
  MentorMessageMetadata,
  MentorThreadRecord,
} from "@/components/mentor/types";

/**
 * 从单条 ThreadMessageLike 中取出导师内容片段（优先 metadata，其次 content 数组）。
 *
 * Args:
 *   message: assistant-ui 线程消息
 *
 * Returns:
 *   MentorContentPart 列表
 */
function getMentorContentPartsFromThreadMessage(message: ThreadMessageLike): MentorContentPart[] {
  const meta = message.metadata as { custom?: MentorMessageMetadata } | undefined;
  const fromMeta = meta?.custom?.contentParts;
  if (Array.isArray(fromMeta) && fromMeta.length > 0) {
    return fromMeta;
  }

  const raw = message.content;
  if (!Array.isArray(raw)) {
    return [];
  }

  return raw.filter((part): part is MentorContentPart => {
    if (typeof part !== "object" || part === null || !("type" in part)) {
      return false;
    }
    const type = (part as { type: string }).type;
    return type === "text" || type === "thinking" || type === "tool-call";
  });
}

/**
 * 从已持久化或运行时的 Deer-Flow 线程消息中提取最新 write_todos 列表（与官方 values.todos 展示对齐）。
 *
 * Args:
 *   messages: 按时间顺序排列的线程消息
 *
 * Returns:
 *   解析后的 To-do 项；若无则空数组
 */
export function extractTodosFromDeerFlowThreadMessages(
  messages: readonly ThreadMessageLike[]
): DeerFlowTodo[] {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.role !== "assistant") {
      continue;
    }

    const parts = getMentorContentPartsFromThreadMessage(message);
    for (const part of parts) {
      if (part.type !== "tool-call" || part.toolName !== "write_todos") {
        continue;
      }

      const fromArgs = parseTodosPayload(part.arguments);
      if (fromArgs.length > 0) {
        return fromArgs;
      }

      const fromResult = parseTodosPayload(part.result);
      if (fromResult.length > 0) {
        return fromResult;
      }
    }
  }

  return [];
}

/**
 * 从单轮助手 contentParts 中提取最新 write_todos 列表（用于 SSE values 未带 todos 字段时的回退，与官方 thread.values.todos 对齐）。
 *
 * Args:
 *   parts: buildDeerFlowContentParts 产出的片段列表
 *
 * Returns:
 *   解析后的 To-do；若无 write_todos 或解析为空则返回空数组
 */
export function extractTodosFromMentorContentParts(parts: readonly MentorContentPart[]): DeerFlowTodo[] {
  for (let index = parts.length - 1; index >= 0; index -= 1) {
    const part = parts[index];
    if (part.type !== "tool-call" || part.toolName !== "write_todos") {
      continue;
    }

    const fromArgs = parseTodosPayload(part.arguments);
    if (fromArgs.length > 0) {
      return fromArgs;
    }

    const fromResult = parseTodosPayload(part.result);
    if (fromResult.length > 0) {
      return fromResult;
    }
  }

  return [];
}

/**
 * mapDeerFlowMessageToThreadMessage - 将 Deer-Flow 消息映射为 assistant-ui 消息
 */
export function mapDeerFlowMessageToThreadMessage(
  message: DeerFlowMentorMessageDto
): ThreadMessageLike {
  const rawMetadata = (message.message_metadata ?? {}) as Record<string, unknown>;
  const contentParts = normalizeMentorContentParts({
    contentParts:
      (rawMetadata.contentParts as MentorContentPart[] | undefined) ??
      (rawMetadata.content_parts as MentorContentPart[] | undefined),
    fallbackText: message.content,
  });
  const metadata: MentorMessageMetadata = {
    threadId: message.thread_id,
    messageId: message.message_id,
    contentParts,
  };

  return {
    id: message.message_id,
    role: message.role,
    content: contentParts as ThreadMessageLike["content"],
    createdAt: new Date(message.created_at),
    metadata: {
      custom: metadata,
    },
  };
}

/**
 * mapDeerFlowMessagesToThreadMessages - 批量映射 Deer-Flow 消息
 */
export function mapDeerFlowMessagesToThreadMessages(
  messages: DeerFlowMentorMessageDto[]
): ThreadMessageLike[] {
  return messages.map(mapDeerFlowMessageToThreadMessage);
}

/**
 * mapDeerFlowThreadStatus - 映射 Deer-Flow 线程状态
 */
function mapDeerFlowThreadStatus(
  status: string
): MentorThreadRecord["status"] {
  if (status === "running" || status === "pending") {
    return "streaming";
  }

  if (status === "error") {
    return "error";
  }

  return "idle";
}

/**
 * mapDeerFlowThreadToThreadRecord - 将 Deer-Flow 线程映射为本地线程
 */
export function mapDeerFlowThreadToThreadRecord(
  thread: DeerFlowMentorThreadDto
): MentorThreadRecord {
  const updatedTimestamp = new Date(thread.updated_at).getTime();
  const createdTimestamp = new Date(thread.created_at).getTime();
  const fallbackTitle = thread.last_message_preview?.trim() || "New thread";

  return {
    id: `deerflow-thread-${thread.thread_id}`,
    title: thread.title?.trim() || fallbackTitle,
    agentKind: "qa",
    qaStyle: "casual",
    modelId: thread.model_id ?? "",
    chapterContext: {
      roadmapId: thread.roadmap_id ?? "",
      conceptId: thread.concept_id ?? undefined,
    },
    messages: [],
    messageCount: thread.message_count,
    remoteSessionId: thread.thread_id,
    status: mapDeerFlowThreadStatus(thread.status),
    isHydrated: false,
    createdAt: Number.isNaN(createdTimestamp) ? Date.now() : createdTimestamp,
    updatedAt: Number.isNaN(updatedTimestamp) ? Date.now() : updatedTimestamp,
  };
}

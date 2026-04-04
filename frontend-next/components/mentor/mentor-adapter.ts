import type {
  ChatModelRunResult,
  ThreadMessageLike,
} from "@assistant-ui/react";

import type {
  MentorChatRequestPayload,
  MentorChatMetaEvent,
  MentorMessageDto,
  MentorSessionDto,
} from "@/components/mentor/mentor-api";
import type {
  MentorAgentKind,
  MentorChapterContext,
  MentorContentPart,
  MentorMessageMetadata,
  MentorQaStyle,
  MentorThreadRecord,
} from "@/components/mentor/types";

/**
 * MentorStreamMetadata - 导师流式元数据
 */
export interface MentorStreamMetadata {
  threadId: string;
  sessionId?: string;
  traceId?: string;
  langfuseTraceId?: string;
  assistantMessageId?: string;
  modelId: string;
  agentKind: MentorAgentKind;
  qaStyle: MentorQaStyle;
  emotionLabel?: string;
  emotionSummary?: string;
  responseDurationMs?: number;
}

/**
 * normalizeMentorContentParts - 规范化 Mentor 内容片段
 */
export function normalizeMentorContentParts(params: {
  contentParts?: MentorContentPart[];
  fallbackText?: string;
}): MentorContentPart[] {
  const normalizedParts: MentorContentPart[] = [];
  for (const part of params.contentParts ?? []) {
    if (part.type === "text" || part.type === "thinking") {
      if (!part.text.length) {
        continue;
      }
      normalizedParts.push({
        type: part.type,
        text: part.text,
      });
      continue;
    }

    if (!part.toolCallId || !part.toolName) {
      continue;
    }

    normalizedParts.push({
      type: "tool-call",
      toolCallId: part.toolCallId,
      toolName: part.toolName,
      arguments: part.arguments,
      state: part.state,
      result: part.result,
      isError: part.isError,
    });
  }

  if (normalizedParts.length > 0) {
    return normalizedParts;
  }

  const fallbackText = params.fallbackText?.trim();
  if (!fallbackText) {
    return [];
  }

  return [
    {
      type: "text",
      text: fallbackText,
    },
  ];
}

/**
 * toAssistantUiContent - 转换为 assistant-ui 可消费的 content 数组
 */
function toAssistantUiContent(contentParts: MentorContentPart[]) {
  return contentParts.map((part) => {
    if (part.type === "thinking") {
      return {
        type: "reasoning",
        text: part.text,
      };
    }

    return part;
  }) as unknown as ChatModelRunResult["content"];
}

/**
 * mapMentorMessageToThreadMessage - 将后端消息映射为 assistant-ui 消息
 */
export function mapMentorMessageToThreadMessage(message: MentorMessageDto): ThreadMessageLike {
  const rawMetadata = (message.message_metadata ?? {}) as Record<string, unknown>;
  const metadata: MentorMessageMetadata = {
    sessionId: message.session_id,
    messageId: message.message_id,
    traceId: message.trace_id ?? undefined,
    agentKind: message.agent_kind ?? undefined,
    agentType: message.agent_kind ?? undefined,
    qaStyle: message.qa_style ?? undefined,
    modelId: message.model_id ?? undefined,
    emotionLabel:
      (rawMetadata.emotionLabel as string | undefined) ??
      (rawMetadata.emotion_label as string | undefined),
    emotionSummary:
      (rawMetadata.emotionSummary as string | undefined) ??
      (rawMetadata.emotion_summary as string | undefined),
    contentParts:
      (rawMetadata.contentParts as MentorContentPart[] | undefined) ??
      (rawMetadata.content_parts as MentorContentPart[] | undefined),
  };
  const contentParts = normalizeMentorContentParts({
    contentParts: metadata.contentParts,
    fallbackText: message.content,
  });
  metadata.contentParts = contentParts;

  return {
    id: message.message_id,
    role: message.role,
    content: toAssistantUiContent(contentParts) ?? "",
    createdAt: new Date(message.created_at),
    metadata: {
      custom: metadata,
    },
  };
}

/**
 * mapMentorMessagesToThreadMessages - 批量转换后端消息
 */
export function mapMentorMessagesToThreadMessages(
  messages: MentorMessageDto[]
): ThreadMessageLike[] {
  return messages.map(mapMentorMessageToThreadMessage);
}

/**
 * mapMentorSessionToThreadRecord - 将后端会话映射为本地线程
 */
export function mapMentorSessionToThreadRecord(session: MentorSessionDto): MentorThreadRecord {
  const timestamp = new Date(session.updated_at).getTime();
  const fallbackTitle = session.last_message_preview?.trim() || "New thread";

  return {
    id: `mentor-session-${session.session_id}`,
    title: session.title?.trim() || fallbackTitle,
    agentKind: session.agent_kind,
    qaStyle: session.qa_style ?? "casual",
    modelId: session.model_id ?? "",
    chapterContext: {
      roadmapId: session.roadmap_id,
      conceptId: session.concept_id ?? undefined,
    },
    messages: [],
    messageCount: session.message_count,
    remoteSessionId: session.session_id,
    status: "idle",
    isHydrated: false,
    createdAt: new Date(session.created_at).getTime(),
    updatedAt: Number.isNaN(timestamp) ? Date.now() : timestamp,
  };
}

/**
 * buildMentorChatRequest - 构建后端聊天请求体
 */
export function buildMentorChatRequest(params: {
  message: string;
  remoteSessionId?: string;
  agentKind: MentorAgentKind;
  qaStyle: MentorQaStyle;
  modelId: string;
  chapterContext: MentorChapterContext;
}): MentorChatRequestPayload {
  return {
    message: params.message,
    session_id: params.remoteSessionId,
    agent_kind: params.agentKind,
    qa_style: params.qaStyle,
    model_id: params.modelId,
    context: {
      roadmap_id: params.chapterContext.roadmapId,
      concept_id: params.chapterContext.conceptId,
      concept_title: params.chapterContext.conceptName,
      roadmap_context: params.chapterContext.conceptSummary,
      tutorial_excerpt: params.chapterContext.conceptSummary,
    },
  };
}

/**
 * buildMentorAssistantMessage - 构建 assistant-ui 可消费的流式消息快照
 */
export function buildMentorAssistantMessage(params: {
  contentParts: MentorContentPart[];
  metadata: MentorStreamMetadata;
}): ChatModelRunResult {
  const contentParts = normalizeMentorContentParts({
    contentParts: params.contentParts,
  });
  const metadata: MentorMessageMetadata = {
    threadId: params.metadata.threadId,
    sessionId: params.metadata.sessionId,
    traceId: params.metadata.traceId,
    langfuseTraceId: params.metadata.langfuseTraceId,
    assistantMessageId: params.metadata.assistantMessageId,
    modelId: params.metadata.modelId,
    agentKind: params.metadata.agentKind,
    agentType: params.metadata.agentKind,
    qaStyle: params.metadata.qaStyle,
    emotionLabel: params.metadata.emotionLabel,
    emotionSummary: params.metadata.emotionSummary,
    responseDurationMs: params.metadata.responseDurationMs,
    contentParts,
  };

  return {
    content: toAssistantUiContent(contentParts),
    metadata: {
      custom: metadata,
    },
  };
}

/**
 * buildMentorStreamMetadata - 用 meta 事件补全流式元数据
 */
export function buildMentorStreamMetadata(params: {
  threadId: string;
  modelId: string;
  agentKind: MentorAgentKind;
  qaStyle: MentorQaStyle;
  metaEvent?: MentorChatMetaEvent;
  responseDurationMs?: number;
}): MentorStreamMetadata {
  return {
    threadId: params.threadId,
    sessionId: params.metaEvent?.session_id,
    traceId: params.metaEvent?.trace_id,
    langfuseTraceId: params.metaEvent?.langfuse_trace_id,
    assistantMessageId: params.metaEvent?.assistant_message_id,
    modelId: params.modelId,
    agentKind: params.metaEvent?.agent_kind ?? params.agentKind,
    qaStyle: params.metaEvent?.qa_style ?? params.qaStyle,
    emotionLabel: params.metaEvent?.emotion_label,
    emotionSummary: params.metaEvent?.emotion_summary,
    responseDurationMs: params.responseDurationMs,
  };
}

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
  MentorAgentType,
  MentorChapterContext,
  MentorMessageMetadata,
  MentorThreadRecord,
} from "@/components/mentor/types";
import { normalizeMentorModelId } from "@/components/mentor/types";

/**
 * MentorStreamMetadata - 导师流式元数据
 */
export interface MentorStreamMetadata {
  threadId: string;
  sessionId?: string;
  traceId?: string;
  assistantMessageId?: string;
  modelId: string;
  agentType: MentorAgentType;
  responseDurationMs?: number;
}

/**
 * mapMentorMessageToThreadMessage - 将后端消息映射为 assistant-ui 消息
 */
export function mapMentorMessageToThreadMessage(message: MentorMessageDto): ThreadMessageLike {
  const metadata: MentorMessageMetadata = {
    sessionId: message.session_id,
    messageId: message.message_id,
    traceId: message.trace_id ?? undefined,
    agentType: message.agent_type ?? undefined,
    modelId: message.model_id ?? undefined,
  };

  return {
    id: message.message_id,
    role: message.role,
    content: message.content,
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
    agentType: session.agent_type,
    modelId: normalizeMentorModelId(session.model_id),
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
  agentType: MentorAgentType;
  modelId: string;
  chapterContext: MentorChapterContext;
}): MentorChatRequestPayload {
  return {
    message: params.message,
    session_id: params.remoteSessionId,
    agent_type: params.agentType,
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
  content: string;
  metadata: MentorStreamMetadata;
}): ChatModelRunResult {
  const metadata: MentorMessageMetadata = {
    threadId: params.metadata.threadId,
    sessionId: params.metadata.sessionId,
    traceId: params.metadata.traceId,
    assistantMessageId: params.metadata.assistantMessageId,
    modelId: params.metadata.modelId,
    agentType: params.metadata.agentType,
    responseDurationMs: params.metadata.responseDurationMs,
  };

  return {
    content: [
      {
        type: "text",
        text: params.content,
      },
    ],
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
  agentType: MentorAgentType;
  metaEvent?: MentorChatMetaEvent;
  responseDurationMs?: number;
}): MentorStreamMetadata {
  return {
    threadId: params.threadId,
    sessionId: params.metaEvent?.session_id,
    traceId: params.metaEvent?.trace_id,
    assistantMessageId: params.metaEvent?.assistant_message_id,
    modelId: params.modelId,
    agentType: params.agentType,
    responseDurationMs: params.responseDurationMs,
  };
}

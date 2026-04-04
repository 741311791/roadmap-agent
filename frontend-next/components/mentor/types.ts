import type { ThreadMessageLike } from "@assistant-ui/react";

/**
 * MentorAgentKind - 聊天页固定 Agent 类型
 */
export type MentorAgentKind = "qa" | "guide" | "quiz";

/**
 * MentorAgentType - 兼容旧命名
 */
export type MentorAgentType = MentorAgentKind;

/**
 * MentorQaStyle - 答疑风格
 */
export type MentorQaStyle = "casual" | "serious";

/**
 * MentorChapterContext - 当前章节上下文
 */
export interface MentorChapterContext {
  roadmapId: string;
  conceptId?: string;
  conceptName?: string;
  conceptSummary?: string;
}

/**
 * MentorToolState - 工具调用状态
 */
export type MentorToolState = "running" | "completed";

/**
 * MentorTextContentPart - 文本内容片段
 */
export interface MentorTextContentPart {
  type: "text";
  text: string;
}

/**
 * MentorThinkingContentPart - 思考内容片段
 */
export interface MentorThinkingContentPart {
  type: "thinking";
  text: string;
}

/**
 * MentorToolCallContentPart - 工具调用内容片段
 */
export interface MentorToolCallContentPart {
  type: "tool-call";
  toolCallId: string;
  toolName: string;
  arguments?: Record<string, unknown>;
  state: MentorToolState;
  result?: string | null;
  isError?: boolean;
}

/**
 * MentorContentPart - Mentor 消息内容片段
 */
export type MentorContentPart =
  | MentorTextContentPart
  | MentorThinkingContentPart
  | MentorToolCallContentPart;

/**
 * MentorMessageMetadata - 导师消息扩展元数据
 */
export interface MentorMessageMetadata {
  threadId?: string;
  sessionId?: string;
  messageId?: string;
  traceId?: string;
  langfuseTraceId?: string;
  assistantMessageId?: string;
  agentKind?: MentorAgentKind;
  agentType?: MentorAgentKind;
  qaStyle?: MentorQaStyle;
  modelId?: string;
  emotionLabel?: string;
  emotionSummary?: string;
  responseDurationMs?: number;
  contentParts?: MentorContentPart[];
  [key: string]: unknown;
}

/**
 * MentorQuickAction - 快捷动作配置
 */
export interface MentorQuickAction {
  id: string;
  label: string;
  prompt: string;
  autoSend?: boolean;
}

/**
 * MentorModelOption - 可选模型配置
 */
export interface MentorModelOption {
  id: string;
  label: string;
  description?: string;
  provider?: string;
  isDefault?: boolean;
  isUnavailable?: boolean;
}

/**
 * MentorThreadStatus - 线程同步状态
 */
export type MentorThreadStatus = "idle" | "streaming" | "error";

/**
 * MentorAgentOption - 可选 Agent 配置
 */
export interface MentorAgentOption {
  id: MentorAgentKind;
  label: string;
  description: string;
}

/**
 * MentorThreadRecord - 历史线程记录
 */
export interface MentorThreadRecord {
  id: string;
  title: string;
  agentKind: MentorAgentKind;
  qaStyle: MentorQaStyle;
  modelId: string;
  chapterContext: MentorChapterContext;
  messages: ThreadMessageLike[];
  messageCount?: number;
  remoteSessionId?: string;
  lastTraceId?: string;
  emotionLabel?: string;
  emotionSummary?: string;
  status: MentorThreadStatus;
  lastError?: string;
  isHydrated: boolean;
  createdAt: number;
  updatedAt: number;
}

/**
 * MAX_MENTOR_THREAD_HISTORY - 历史线程上限
 */
export const MAX_MENTOR_THREAD_HISTORY = 10;

/**
 * MENTOR_AGENT_OPTIONS - Agent 下拉选项
 */
export const MENTOR_AGENT_OPTIONS: MentorAgentOption[] = [
  {
    id: "qa",
    label: "Answer",
    description: "Direct Q&A with tool support and memory.",
  },
  {
    id: "guide",
    label: "Guide",
    description: "Coming soon: guided learning flow.",
  },
  {
    id: "quiz",
    label: "Quiz",
    description: "Coming soon: adaptive chapter quizzes.",
  },
];

/**
 * QA_STYLE_OPTIONS - 答疑风格选项
 */
export const QA_STYLE_OPTIONS: Array<{ id: MentorQaStyle; label: string }> = [
  { id: "casual", label: "Casual" },
  { id: "serious", label: "Serious" },
];

/**
 * ensureMentorModelOption - 确保当前模型在下拉列表中可见
 *
 * 为什么这样做：
 * - 历史线程可能引用了已下线或当前用户无权限访问的模型
 * - 不能静默回退到默认模型，否则用户会误以为历史消息来自另一模型
 */
export function ensureMentorModelOption(
  options: MentorModelOption[],
  modelId?: string | null
): MentorModelOption[] {
  const normalizedModelId = modelId?.trim();
  if (!normalizedModelId) {
    return options;
  }

  const hasCurrentModel = options.some((option) => option.id === normalizedModelId);
  if (hasCurrentModel) {
    return options;
  }

  return [
    {
      id: normalizedModelId,
      label: normalizedModelId,
      description: "Unavailable model",
      isUnavailable: true,
    },
    ...options,
  ];
}

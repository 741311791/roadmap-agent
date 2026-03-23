import type { ThreadMessageLike } from "@assistant-ui/react";

/**
 * MentorAgentType - 侧栏 Agent 类型
 */
export type MentorAgentType = "company" | "tutoring";

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
 * MentorMessageMetadata - 导师消息扩展元数据
 */
export interface MentorMessageMetadata {
  threadId?: string;
  sessionId?: string;
  messageId?: string;
  traceId?: string;
  assistantMessageId?: string;
  agentType?: MentorAgentType;
  modelId?: string;
  responseDurationMs?: number;
  [key: string]: unknown;
}

/**
 * MentorModelOption - 可选模型配置
 */
export interface MentorModelOption {
  id: string;
  label: string;
  isLimitedFree?: boolean;
}

/**
 * MentorThreadStatus - 线程同步状态
 */
export type MentorThreadStatus = "idle" | "streaming" | "error";

/**
 * MentorAgentOption - 可选 Agent 配置
 */
export interface MentorAgentOption {
  id: MentorAgentType;
  label: string;
  promptTemplate: string;
  description: string;
}

/**
 * MentorThreadRecord - 历史线程记录
 */
export interface MentorThreadRecord {
  id: string;
  title: string;
  agentType: MentorAgentType;
  modelId: string;
  chapterContext: MentorChapterContext;
  messages: ThreadMessageLike[];
  messageCount?: number;
  remoteSessionId?: string;
  lastTraceId?: string;
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
 * DEFAULT_MENTOR_MODEL_ID - 默认导师模型
 */
export const DEFAULT_MENTOR_MODEL_ID = "google/gemini-3-flash-preview";

/**
 * SUPPORTED_MENTOR_MODEL_IDS - 当前后端已验证可用的导师模型
 */
export const SUPPORTED_MENTOR_MODEL_IDS = [
  "google/gemini-3.1-pro-preview",
  "google/gemini-3-flash-preview",
] as const;

/**
 * normalizeMentorModelId - 将不可用模型回退到默认模型
 */
export function normalizeMentorModelId(modelId?: string | null): string {
  if (!modelId) {
    return DEFAULT_MENTOR_MODEL_ID;
  }

  return SUPPORTED_MENTOR_MODEL_IDS.includes(
    modelId as (typeof SUPPORTED_MENTOR_MODEL_IDS)[number]
  )
    ? modelId
    : DEFAULT_MENTOR_MODEL_ID;
}

/**
 * MENTOR_AGENT_OPTIONS - Agent 下拉选项
 */
export const MENTOR_AGENT_OPTIONS: MentorAgentOption[] = [
  {
    id: "company",
    label: "Companion Agent",
    promptTemplate: "backend/prompts/company_agent.j2",
    description: "Patient explanations with examples and analogies.",
  },
  {
    id: "tutoring",
    label: "Tutoring Agent",
    promptTemplate: "backend/prompts/tutorin_agent.j2",
    description: "Guided questions with a Socratic teaching style.",
  },
];

/**
 * MENTOR_MODEL_OPTIONS - 模型下拉选项
 */
export const MENTOR_MODEL_OPTIONS: MentorModelOption[] = [
  {
    id: "google/gemini-3.1-pro-preview",
    label: "Gemini 3.1 Pro Preview",
    isLimitedFree: true,
  },
  {
    id: "google/gemini-3-flash-preview",
    label: "Gemini 3 Flash Preview",
  },
];

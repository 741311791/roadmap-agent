import { API_PREFIX } from "@/lib/constants";
import { apiClient } from "@/lib/api/client";
import { authService } from "@/lib/services/auth-service";

/**
 * MentorMessageRole - 后端导师消息角色
 */
export type MentorMessageRole = "system" | "user" | "assistant";

/**
 * MentorChatContextPayload - 导师聊天上下文请求体
 */
export interface MentorChatContextPayload {
  roadmap_id: string;
  concept_id?: string;
  concept_title?: string;
  tutorial_excerpt?: string;
  roadmap_context?: string;
}

/**
 * MentorChatRequestPayload - 导师聊天请求体
 */
export interface MentorChatRequestPayload {
  message: string;
  session_id?: string;
  agent_type: "company" | "tutoring";
  model_id: string;
  context: MentorChatContextPayload;
}

/**
 * MentorSessionDto - 导师会话 DTO
 */
export interface MentorSessionDto {
  session_id: string;
  user_id: string;
  roadmap_id: string;
  concept_id?: string | null;
  title?: string | null;
  agent_type: "company" | "tutoring";
  model_id?: string | null;
  message_count: number;
  last_message_preview?: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * MentorMessageDto - 导师消息 DTO
 */
export interface MentorMessageDto {
  message_id: string;
  session_id: string;
  role: MentorMessageRole;
  content: string;
  agent_type?: "company" | "tutoring" | null;
  model_id?: string | null;
  trace_id?: string | null;
  created_at: string;
}

/**
 * MentorSessionListDto - 会话列表 DTO
 */
export interface MentorSessionListDto {
  items: MentorSessionDto[];
  total: number;
}

/**
 * MentorSessionScope - 会话历史作用域
 */
export type MentorSessionScope = "roadmap" | "concept";

/**
 * MentorMessageListDto - 消息列表 DTO
 */
export interface MentorMessageListDto {
  items: MentorMessageDto[];
  total: number;
}

/**
 * MentorChatMetaEvent - 流式 meta 事件
 */
export interface MentorChatMetaEvent {
  type: "meta";
  session_id: string;
  trace_id: string;
  user_message_id: string;
  assistant_message_id: string;
}

/**
 * MentorChatDeltaEvent - 流式增量事件
 */
export interface MentorChatDeltaEvent {
  type: "delta";
  delta: string;
}

/**
 * MentorChatErrorEvent - 流式错误事件
 */
export interface MentorChatErrorEvent {
  type: "error";
  message: string;
}

/**
 * MentorChatStreamEvent - 导师聊天流事件
 */
export type MentorChatStreamEvent =
  | MentorChatMetaEvent
  | MentorChatDeltaEvent
  | MentorChatErrorEvent;

/**
 * buildMentorStreamHeaders - 构建 SSE 请求头
 */
function buildMentorStreamHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Trace-ID": crypto.randomUUID(),
  };
  const token = authService.getToken();
  const userId = authService.getCurrentUserId();

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  if (userId) {
    headers["X-User-ID"] = userId;
  }

  return headers;
}

/**
 * parseMentorSseFrame - 解析单个 SSE 数据帧
 */
function parseMentorSseFrame(frame: string): MentorChatStreamEvent | null {
  const payload = frame
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim())
    .join("\n")
    .trim();

  if (!payload || payload === "[DONE]") {
    return null;
  }

  return JSON.parse(payload) as MentorChatStreamEvent;
}

/**
 * readMentorSseFrames - 逐帧解析 SSE 文本流
 */
async function* readMentorSseFrames(
  stream: ReadableStream<Uint8Array>
): AsyncGenerator<MentorChatStreamEvent, void, void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        const event = parseMentorSseFrame(frame);
        if (event) {
          yield event;
        }
      }

      if (done) {
        break;
      }
    }

    if (buffer.trim()) {
      const event = parseMentorSseFrame(buffer);
      if (event) {
        yield event;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * listMentorSessions - 获取导师会话列表
 */
export async function listMentorSessions(params: {
  roadmapId: string;
  conceptId?: string;
}): Promise<MentorSessionDto[]> {
  const scope: MentorSessionScope = params.conceptId ? "concept" : "roadmap";
  const { data } = await apiClient.get<MentorSessionListDto>("/learning/mentor/sessions", {
    params: {
      roadmap_id: params.roadmapId,
      scope,
      concept_id: params.conceptId,
      limit: 20,
      offset: 0,
    },
  });

  return data.items;
}

/**
 * listMentorMessages - 获取指定会话消息列表
 */
export async function listMentorMessages(sessionId: string): Promise<MentorMessageDto[]> {
  const { data } = await apiClient.get<MentorMessageListDto>(
    `/learning/mentor/sessions/${sessionId}/messages`,
    {
      params: {
        limit: 100,
        offset: 0,
      },
    }
  );

  return data.items;
}

/**
 * deleteMentorSession - 删除指定导师会话
 */
export async function deleteMentorSession(
  sessionId: string
): Promise<{ session_id: string }> {
  const { data } = await apiClient.delete<{ session_id: string }>(
    `/learning/mentor/sessions/${sessionId}`
  );

  return data;
}

/**
 * WarmupRequest - 缓存预热请求参数
 */
export interface WarmupRequest {
  roadmap_id: string;
  concept_id?: string;
  concept_title?: string;
}

/**
 * warmupMentorContext - 触发伴学助手上下文缓存预热
 *
 * 在用户进入路线图详情页或切换章节时调用（fire-and-forget 模式），
 * 后端会异步将 LTM 向量检索结果和学习上下文写入 Redis，
 * 供后续对话直接读取，消除每次发消息时的 Mem0 延迟。
 *
 * 此函数不抛出异常，失败静默处理，不影响主流程。
 */
export async function warmupMentorContext(params: WarmupRequest): Promise<void> {
  try {
    await apiClient.post("/learning/mentor/warmup", {
      roadmap_id: params.roadmap_id,
      concept_id: params.concept_id ?? null,
      concept_title: params.concept_title ?? null,
    });
  } catch {
    // warmup 是非关键路径，失败静默处理
  }
}

/**
 * streamMentorChat - 发起导师聊天 SSE 请求
 */
export async function* streamMentorChat(
  payload: MentorChatRequestPayload,
  abortSignal: AbortSignal
): AsyncGenerator<MentorChatStreamEvent, void, void> {
  const response = await fetch(`${API_PREFIX}/learning/mentor/chat`, {
    method: "POST",
    headers: buildMentorStreamHeaders(),
    body: JSON.stringify(payload),
    signal: abortSignal,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Mentor chat request failed with status ${response.status}.`);
  }

  if (!response.body) {
    throw new Error("Mentor chat response body is empty.");
  }

  for await (const event of readMentorSseFrames(response.body)) {
    yield event;
  }
}

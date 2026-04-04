"use client";

import { API_PREFIX } from "@/lib/constants";
import { apiClient } from "@/lib/api/client";
import { authService } from "@/lib/services/auth-service";

import type {
  MentorMessageRole,
  MentorModelDto,
  MentorModelListDto,
} from "@/components/mentor/mentor-api";

/**
 * DeerFlowMentorChatContextPayload - Deer-Flow 聊天上下文
 */
export interface DeerFlowMentorChatContextPayload {
  roadmap_id: string;
  stage_id?: string;
  task_id?: string;
  concept_id?: string;
  concept_title?: string;
  tutorial_excerpt?: string;
  roadmap_context?: string;
  mode?: "flash" | "thinking" | "pro" | "ultra";
  reasoning_effort?: "minimal" | "low" | "medium" | "high";
}

/**
 * DeerFlowMentorChatRequestPayload - Deer-Flow 聊天请求
 */
export interface DeerFlowMentorChatRequestPayload {
  message: string;
  thread_id?: string;
  assistant_id?: string;
  model_id?: string;
  context: DeerFlowMentorChatContextPayload;
}

/**
 * DeerFlowMentorThreadDto - Deer-Flow 线程 DTO
 */
export interface DeerFlowMentorThreadDto {
  thread_id: string;
  user_id: string;
  roadmap_id: string | null;
  stage_id?: string | null;
  task_id?: string | null;
  concept_id?: string | null;
  title?: string | null;
  source: "deer_flow";
  assistant_id?: string | null;
  model_id?: string | null;
  status: string;
  message_count: number;
  last_message_preview?: string | null;
  last_message_at?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

/**
 * DeerFlowMentorMessageDto - Deer-Flow 消息 DTO
 */
export interface DeerFlowMentorMessageDto {
  message_id: string;
  thread_id: string;
  role: MentorMessageRole;
  content: string;
  message_metadata?: Record<string, unknown> | null;
  created_at: string;
}

/**
 * DeerFlowMentorThreadListDto - 线程列表 DTO
 */
export interface DeerFlowMentorThreadListDto {
  items: DeerFlowMentorThreadDto[];
  total: number;
}

/**
 * DeerFlowMentorThreadCreatePayload - 创建线程请求
 */
export interface DeerFlowMentorThreadCreatePayload {
  roadmap_id: string;
  stage_id?: string;
  task_id?: string;
  concept_id?: string;
  title?: string;
  assistant_id?: string;
  model_id?: string;
}

/**
 * DeerFlowMentorMessageListDto - 消息列表 DTO
 */
export interface DeerFlowMentorMessageListDto {
  items: DeerFlowMentorMessageDto[];
  total: number;
}

/**
 * DeerFlowMentorWarmupRequest - 缓存预热参数
 */
export interface DeerFlowMentorWarmupRequest {
  roadmap_id: string;
  concept_id?: string;
  concept_title?: string;
}

/**
 * DeerFlowSseEvent - Deer-Flow SSE 通用事件
 */
export interface DeerFlowSseEvent<T = unknown> {
  event: string;
  data: T;
  id?: string;
}

/**
 * DeerFlowMetadataEvent - Deer-Flow metadata 事件
 */
export type DeerFlowMetadataEvent = DeerFlowSseEvent<{
  run_id: string;
  thread_id: string;
}>;

/**
 * buildDeerFlowStreamHeaders - 构建流式请求头
 */
export function buildDeerFlowStreamHeaders(): HeadersInit {
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
 * parseDeerFlowSseFrame - 解析 Deer-Flow 单帧 SSE
 */
export function parseDeerFlowSseFrame(frame: string): DeerFlowSseEvent | null {
  const lines = frame
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length === 0 || lines.every((line) => line.startsWith(":"))) {
    return null;
  }

  const eventLine = lines.find((line) => line.startsWith("event:"));
  const dataLines = lines.filter((line) => line.startsWith("data:"));
  const idLine = lines.find((line) => line.startsWith("id:"));

  const event = eventLine?.slice(6).trim() || "message";
  const payload = dataLines
    .map((line) => line.slice(5).trim())
    .join("\n")
    .trim();

  let data: unknown = null;
  if (payload) {
    data = JSON.parse(payload) as unknown;
  }

  return {
    event,
    data,
    id: idLine?.slice(3).trim(),
  };
}

/**
 * readDeerFlowSseFrames - 逐帧读取 Deer-Flow SSE
 */
export async function* readDeerFlowSseFrames(
  stream: ReadableStream<Uint8Array>
): AsyncGenerator<DeerFlowSseEvent, void, void> {
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
        const event = parseDeerFlowSseFrame(frame);
        if (event) {
          yield event;
        }
      }

      if (done) {
        break;
      }
    }

    if (buffer.trim()) {
      const event = parseDeerFlowSseFrame(buffer);
      if (event) {
        yield event;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * listMentorDeerFlowThreads - 获取 Deer-Flow 线程列表
 */
export async function listMentorDeerFlowThreads(params: {
  roadmapId: string;
  conceptId?: string;
}): Promise<DeerFlowMentorThreadDto[]> {
  const scope = params.conceptId ? "concept" : "roadmap";
  const { data } = await apiClient.get<DeerFlowMentorThreadListDto>("/learning/mentor-deerflow/threads", {
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
 * createMentorDeerFlowThread - 创建 Deer-Flow 线程
 */
export async function createMentorDeerFlowThread(
  payload: DeerFlowMentorThreadCreatePayload
): Promise<DeerFlowMentorThreadDto> {
  const { data } = await apiClient.post<DeerFlowMentorThreadDto>(
    "/learning/mentor-deerflow/threads",
    payload
  );

  return data;
}

/**
 * listMentorDeerFlowMessages - 获取指定 Deer-Flow 线程消息
 */
export async function listMentorDeerFlowMessages(
  threadId: string
): Promise<DeerFlowMentorMessageDto[]> {
  const { data } = await apiClient.get<DeerFlowMentorMessageListDto>(
    `/learning/mentor-deerflow/threads/${threadId}/messages`
  );
  return data.items;
}

/**
 * fetchMentorDeerFlowArtifact - 拉取 Deer-Flow 线程产物
 */
export async function fetchMentorDeerFlowArtifact(params: {
  threadId: string;
  artifactPath: string;
  download?: boolean;
}): Promise<Response> {
  const normalizedPath = params.artifactPath.startsWith("/")
    ? params.artifactPath.slice(1)
    : params.artifactPath;
  const query = params.download ? "?download=true" : "";
  const response = await fetch(
    `${API_PREFIX}/learning/mentor-deerflow/threads/${params.threadId}/artifacts/${normalizedPath}${query}`,
    {
      method: "GET",
      headers: buildDeerFlowStreamHeaders(),
      cache: "no-store",
    }
  );

  if (!response.ok) {
    throw new Error(`Deer-Flow artifact request failed with status ${response.status}.`);
  }

  return response;
}

/**
 * listMentorDeerFlowModels - 获取 Deer-Flow 模式可用模型列表
 */
export async function listMentorDeerFlowModels(): Promise<MentorModelListDto> {
  const { data } = await apiClient.get<MentorModelListDto>("/learning/mentor-deerflow/models");
  return data;
}

/**
 * deleteMentorDeerFlowThread - 删除 Deer-Flow 线程
 */
export async function deleteMentorDeerFlowThread(
  threadId: string
): Promise<{ thread_id: string }> {
  const { data } = await apiClient.delete<{ thread_id: string }>(
    `/learning/mentor-deerflow/threads/${threadId}`
  );
  return data;
}

/**
 * warmupMentorDeerFlowContext - 触发 Deer-Flow 上下文预热
 */
export async function warmupMentorDeerFlowContext(
  params: DeerFlowMentorWarmupRequest
): Promise<void> {
  try {
    await apiClient.post("/learning/mentor-deerflow/warmup", {
      roadmap_id: params.roadmap_id,
      concept_id: params.concept_id ?? null,
      concept_title: params.concept_title ?? null,
    });
  } catch {
    // warmup 是非关键路径，失败静默处理
  }
}

/**
 * streamMentorDeerFlowChat - 发起 Deer-Flow 流式聊天
 */
export async function* streamMentorDeerFlowChat(
  payload: DeerFlowMentorChatRequestPayload,
  abortSignal: AbortSignal
): AsyncGenerator<DeerFlowSseEvent, void, void> {
  const response = await fetch(`${API_PREFIX}/learning/mentor-deerflow/chat`, {
    method: "POST",
    headers: buildDeerFlowStreamHeaders(),
    body: JSON.stringify(payload),
    signal: abortSignal,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Deer-Flow chat request failed with status ${response.status}.`);
  }

  if (!response.body) {
    throw new Error("Deer-Flow chat response body is empty.");
  }

  for await (const event of readDeerFlowSseFrames(response.body)) {
    yield event;
  }
}

export type { MentorModelDto, MentorModelListDto };

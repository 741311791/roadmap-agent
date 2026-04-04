"use client";

import { API_PREFIX } from "@/lib/constants";
import { apiClient } from "@/lib/api/client";

import {
  buildDeerFlowStreamHeaders,
  readDeerFlowSseFrames,
  type DeerFlowMentorMessageDto,
  type DeerFlowMentorThreadDto,
  type DeerFlowSseEvent,
  type MentorModelDto,
  type MentorModelListDto,
} from "@/components/mentor/mentor-deerflow-api";

/**
 * 独立 Deer-Flow 实验室运行时上下文（无路线图字段）。
 */
export interface DeerFlowStandaloneChatContextPayload {
  mode?: "flash" | "thinking" | "pro" | "ultra";
  reasoning_effort?: "minimal" | "low" | "medium" | "high";
}

/**
 * 独立 Deer-Flow 聊天请求体。
 */
export interface DeerFlowStandaloneChatRequestPayload {
  message: string;
  thread_id?: string;
  assistant_id?: string;
  model_id?: string;
  context: DeerFlowStandaloneChatContextPayload;
}

const STANDALONE_BASE = "/deerflow";

/**
 * 列出独立 Deer-Flow 线程。
 */
export async function listDeerFlowStandaloneThreads(): Promise<DeerFlowMentorThreadDto[]> {
  const { data } = await apiClient.get<{ items: DeerFlowMentorThreadDto[]; total: number }>(
    `${STANDALONE_BASE}/threads`,
    { params: { limit: 20, offset: 0 } }
  );
  return data.items;
}

/**
 * 创建独立 Deer-Flow 线程。
 */
export async function createDeerFlowStandaloneThread(payload: {
  title?: string;
  assistant_id?: string;
  model_id?: string;
}): Promise<DeerFlowMentorThreadDto> {
  const { data } = await apiClient.post<DeerFlowMentorThreadDto>(`${STANDALONE_BASE}/threads`, payload);
  return data;
}

/**
 * 拉取独立模式线程消息。
 */
export async function listDeerFlowStandaloneMessages(threadId: string): Promise<DeerFlowMentorMessageDto[]> {
  const { data } = await apiClient.get<{ items: DeerFlowMentorMessageDto[]; total: number }>(
    `${STANDALONE_BASE}/threads/${threadId}/messages`
  );
  return data.items;
}

/**
 * 拉取独立模式线程产物。
 */
export async function fetchDeerFlowStandaloneArtifact(params: {
  threadId: string;
  artifactPath: string;
  download?: boolean;
}): Promise<Response> {
  const normalizedPath = params.artifactPath.startsWith("/")
    ? params.artifactPath.slice(1)
    : params.artifactPath;
  const query = params.download ? "?download=true" : "";
  const response = await fetch(
    `${API_PREFIX}${STANDALONE_BASE}/threads/${params.threadId}/artifacts/${normalizedPath}${query}`,
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
 * 独立模式可用模型列表。
 */
export async function listDeerFlowStandaloneModels(): Promise<MentorModelListDto> {
  const { data } = await apiClient.get<MentorModelListDto>(`${STANDALONE_BASE}/models`);
  return data;
}

/**
 * 删除独立 Deer-Flow 线程。
 */
export async function deleteDeerFlowStandaloneThread(threadId: string): Promise<{ thread_id: string }> {
  const { data } = await apiClient.delete<{ thread_id: string }>(`${STANDALONE_BASE}/threads/${threadId}`);
  return data;
}

/**
 * 独立 Deer-Flow 流式聊天。
 */
export async function* streamDeerFlowStandaloneChat(
  payload: DeerFlowStandaloneChatRequestPayload,
  abortSignal: AbortSignal
): AsyncGenerator<DeerFlowSseEvent, void, void> {
  const response = await fetch(`${API_PREFIX}${STANDALONE_BASE}/chat`, {
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

export type { DeerFlowMentorMessageDto, DeerFlowMentorThreadDto, MentorModelDto };

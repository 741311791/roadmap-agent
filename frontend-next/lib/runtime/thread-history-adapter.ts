'use client';

import { API_PREFIX } from '@/lib/constants';
import { authService } from '@/lib/services/auth-service';
import type {
  MentorAgentMode,
  MentorModelName,
} from '@/lib/api/sse/mentor-sse-adapter';

const MENTOR_SESSION_STORAGE_KEY = 'mentor_active_session';
const MENTOR_THREAD_CACHE_KEY = 'mentor_thread_cache';

export interface MentorSessionSummary {
  session_id: string;
  roadmap_id: string;
  concept_id: string | null;
  agent_mode: MentorAgentMode;
  model_name: MentorModelName;
  title: string | null;
  message_count: number;
  last_message_preview: string | null;
  updated_at: string;
}

export interface MentorHistoryMessage {
  message_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  message_metadata?: Record<string, unknown> | null;
  created_at: string;
}

interface MentorSessionStorage {
  [key: string]: string;
}

interface MentorThreadCacheStorage {
  [key: string]: MentorThreadCachePayload;
}

export interface MentorThreadCachePayload {
  sessionId: string | null;
  messages: Array<{
    id: string;
    role: 'user' | 'assistant';
    text: string;
    toolCalls: Array<{
      toolCallId: string;
      toolName: string;
      args?: Record<string, unknown>;
      loading: boolean;
      success?: boolean;
      result?: unknown;
    }>;
  }>;
}

interface WrappedApiResponse<T> {
  code: number;
  msg: string;
  data: T;
}

function buildStorageKey(
  roadmapId: string,
  agentMode: MentorAgentMode,
  modelName: MentorModelName
): string {
  return `${roadmapId}:${agentMode}:${modelName}`;
}

function readStorage(): MentorSessionStorage {
  if (typeof window === 'undefined') return {};
  const raw = window.localStorage.getItem(MENTOR_SESSION_STORAGE_KEY);
  if (!raw) return {};
  try {
    return JSON.parse(raw) as MentorSessionStorage;
  } catch {
    return {};
  }
}

function writeStorage(data: MentorSessionStorage): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(MENTOR_SESSION_STORAGE_KEY, JSON.stringify(data));
}

function readThreadCacheStorage(): MentorThreadCacheStorage {
  if (typeof window === 'undefined') return {};
  const raw = window.localStorage.getItem(MENTOR_THREAD_CACHE_KEY);
  if (!raw) return {};
  try {
    return JSON.parse(raw) as MentorThreadCacheStorage;
  } catch {
    return {};
  }
}

function writeThreadCacheStorage(data: MentorThreadCacheStorage): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(MENTOR_THREAD_CACHE_KEY, JSON.stringify(data));
}

export class ThreadHistoryAdapter {
  /**
   * 兼容历史版本缓存结构并规范化。
   */
  private normalizeCachedPayload(raw: unknown): MentorThreadCachePayload | null {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
      return null;
    }

    const direct = raw as Partial<MentorThreadCachePayload>;
    if (Array.isArray(direct.messages)) {
      return {
        sessionId:
          typeof direct.sessionId === 'string' ? direct.sessionId : null,
        messages: direct.messages as MentorThreadCachePayload['messages'],
      };
    }

    // 兼容旧格式：{ "<session_id>": { messages: [...] } }
    const entries = Object.entries(raw as Record<string, unknown>);
    if (entries.length === 0) return null;

    const [legacySessionId, legacyPayload] = entries[0];
    if (
      legacyPayload &&
      typeof legacyPayload === 'object' &&
      !Array.isArray(legacyPayload)
    ) {
      const legacyMessages = (legacyPayload as { messages?: unknown }).messages;
      if (Array.isArray(legacyMessages)) {
        return {
          sessionId: legacySessionId,
          messages: legacyMessages as MentorThreadCachePayload['messages'],
        };
      }
    }

    return null;
  }

  /**
   * 发送带认证的 JSON 请求。
   */
  private async requestJson<T>(path: string): Promise<T> {
    const token = authService.getToken();
    if (!token) {
      throw new Error('未登录，无法加载 Mentor 历史会话');
    }

    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 6000);

    let response: Response;
    try {
      response = await fetch(`${API_PREFIX}${path}`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
        cache: 'no-store',
        signal: controller.signal,
      });
    } finally {
      window.clearTimeout(timeoutId);
    }

    if (!response.ok) {
      throw new Error(`Mentor 历史请求失败: ${response.status}`);
    }

    const payload = (await response.json()) as WrappedApiResponse<T> | T;
    if (
      payload &&
      typeof payload === 'object' &&
      'code' in payload &&
      'data' in payload
    ) {
      const wrapped = payload as WrappedApiResponse<T>;
      if (wrapped.code !== 200) {
        throw new Error(wrapped.msg || 'Mentor 历史请求失败');
      }
      return wrapped.data;
    }

    return payload as T;
  }

  /**
   * 读取当前路线图+模式对应的活跃会话 ID。
   */
  getStoredSessionId(
    roadmapId: string,
    agentMode: MentorAgentMode,
    modelName: MentorModelName
  ): string | null {
    const storage = readStorage();
    return storage[buildStorageKey(roadmapId, agentMode, modelName)] ?? null;
  }

  /**
   * 保存当前路线图+模式的活跃会话 ID。
   */
  setStoredSessionId(
    roadmapId: string,
    agentMode: MentorAgentMode,
    modelName: MentorModelName,
    sessionId: string
  ): void {
    const storage = readStorage();
    storage[buildStorageKey(roadmapId, agentMode, modelName)] = sessionId;
    writeStorage(storage);
  }

  /**
   * 清除当前路线图+模式的活跃会话 ID。
   */
  clearStoredSessionId(
    roadmapId: string,
    agentMode: MentorAgentMode,
    modelName: MentorModelName
  ): void {
    const storage = readStorage();
    delete storage[buildStorageKey(roadmapId, agentMode, modelName)];
    writeStorage(storage);
  }

  /**
   * 读取本地缓存的线程消息。
   */
  getCachedThread(
    roadmapId: string,
    agentMode: MentorAgentMode,
    modelName: MentorModelName
  ): MentorThreadCachePayload | null {
    const storage = readThreadCacheStorage();
    return this.normalizeCachedPayload(
      storage[buildStorageKey(roadmapId, agentMode, modelName)]
    );
  }

  /**
   * 保存本地线程缓存。
   */
  setCachedThread(
    roadmapId: string,
    agentMode: MentorAgentMode,
    modelName: MentorModelName,
    payload: MentorThreadCachePayload
  ): void {
    const storage = readThreadCacheStorage();
    storage[buildStorageKey(roadmapId, agentMode, modelName)] = payload;
    writeThreadCacheStorage(storage);
  }

  /**
   * 清除本地线程缓存。
   */
  clearCachedThread(
    roadmapId: string,
    agentMode: MentorAgentMode,
    modelName: MentorModelName
  ): void {
    const storage = readThreadCacheStorage();
    delete storage[buildStorageKey(roadmapId, agentMode, modelName)];
    writeThreadCacheStorage(storage);
  }

  /**
   * 获取会话列表。
   */
  async listSessions(
    roadmapId: string,
    agentMode: MentorAgentMode,
    modelName: MentorModelName,
    limit = 20
  ): Promise<MentorSessionSummary[]> {
    const query = new URLSearchParams({
      agent_mode: agentMode,
      model_name: modelName,
      limit: String(limit),
    }).toString();
    return await this.requestJson<MentorSessionSummary[]>(
      `/learning/roadmaps/${roadmapId}/mentor/sessions?${query}`
    );
  }

  /**
   * 获取指定会话消息。
   */
  async getSessionMessages(
    roadmapId: string,
    sessionId: string,
    limit = 200
  ): Promise<MentorHistoryMessage[]> {
    const query = new URLSearchParams({
      limit: String(limit),
    }).toString();
    return await this.requestJson<MentorHistoryMessage[]>(
      `/learning/roadmaps/${roadmapId}/mentor/sessions/${sessionId}/messages?${query}`
    );
  }
}

export const threadHistoryAdapter = new ThreadHistoryAdapter();

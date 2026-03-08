/**
 * Mentor SSE 适配器。
 *
 * 负责将后端 SSE 事件转换为前端可消费的强类型事件流。
 */

import { fetchEventSource } from '@microsoft/fetch-event-source';
import { API_PREFIX } from '@/lib/constants';
import { authService } from '@/lib/services/auth-service';

export type MentorAgentMode = 'companion' | 'tutoring';

export interface MentorBackendMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface MentorTextDeltaEvent {
  type: 'text_delta';
  content: string;
  is_thinking?: boolean;
}

export interface MentorToolCallStartEvent {
  type: 'tool_call_start';
  tool_call_id: string;
  tool_name: string;
  args?: Record<string, unknown>;
}

export interface MentorToolCallEndEvent {
  type: 'tool_call_end';
  tool_call_id: string;
  tool_name: string;
  success: boolean;
  result?: unknown;
}

export interface MentorDoneEvent {
  type: 'done';
  message_id?: string;
}

export interface MentorErrorEvent {
  type: 'error';
  message: string;
}

export type MentorSSEEvent =
  | MentorTextDeltaEvent
  | MentorToolCallStartEvent
  | MentorToolCallEndEvent
  | MentorDoneEvent
  | MentorErrorEvent;

interface StreamMentorChatParams {
  roadmapId: string;
  messages: MentorBackendMessage[];
  agentMode: MentorAgentMode;
  conceptId?: string | null;
  abortSignal?: AbortSignal;
}

/**
 * 流式调用 Mentor 聊天接口并返回事件迭代器。
 *
 * Args:
 *   params: SSE 调用参数。
 *
 * Returns:
 *   AsyncGenerator<MentorSSEEvent>: 事件流。
 *
 * Raises:
 *   Error: 当 SSE 连接失败或后端返回错误时抛出。
 */
export async function* streamMentorChat(
  params: StreamMentorChatParams
): AsyncGenerator<MentorSSEEvent> {
  const { roadmapId, messages, agentMode, conceptId, abortSignal } = params;

  const token = authService.getToken();
  if (!token) {
    throw new Error('未登录，无法发起 Mentor 对话');
  }

  const endpoint = `${API_PREFIX}/learning/roadmaps/${roadmapId}/mentor/chat`;
  const eventQueue: MentorSSEEvent[] = [];
  let done = false;
  let streamError: Error | null = null;
  let wake: (() => void) | null = null;

  const resolveWake = () => {
    wake?.();
    wake = null;
  };

  void fetchEventSource(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({
      messages,
      agent_mode: agentMode,
      concept_id: conceptId ?? null,
    }),
    signal: abortSignal,
    async onopen(response) {
      if (!response.ok) {
        throw new Error(`Mentor SSE 连接失败: ${response.status}`);
      }
    },
    onmessage(event) {
      if (!event.data) return;
      try {
        const parsed = JSON.parse(event.data) as MentorSSEEvent;
        eventQueue.push(parsed);
        resolveWake();
      } catch (error) {
        streamError = error instanceof Error ? error : new Error(String(error));
        done = true;
        resolveWake();
      }
    },
    onclose() {
      done = true;
      resolveWake();
    },
    onerror(error) {
      streamError = error instanceof Error ? error : new Error(String(error));
      done = true;
      resolveWake();
      throw error;
    },
  }).catch((error) => {
    if (error instanceof Error && error.name === 'AbortError') {
      done = true;
      resolveWake();
      return;
    }
    streamError = error instanceof Error ? error : new Error(String(error));
    done = true;
    resolveWake();
  });

  while (!done || eventQueue.length > 0) {
    if (eventQueue.length === 0) {
      await new Promise<void>((resolve) => {
        wake = resolve;
      });
    }

    if (streamError) {
      throw streamError;
    }

    const nextEvent = eventQueue.shift();
    if (!nextEvent) {
      continue;
    }

    yield nextEvent;

    if (nextEvent.type === 'done' || nextEvent.type === 'error') {
      done = true;
    }
  }
}


'use client';

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import {
  streamMentorChat,
  type MentorAgentMode,
  type MentorSSEEvent,
} from '@/lib/api/sse/mentor-sse-adapter';

export interface MentorToolCallState {
  toolCallId: string;
  toolName: string;
  args?: Record<string, unknown>;
  loading: boolean;
  success?: boolean;
  result?: unknown;
}

export interface MentorMessageState {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  toolCalls: MentorToolCallState[];
}

interface MentorRuntimeContextValue {
  messages: MentorMessageState[];
  isStreaming: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  stopStreaming: () => void;
}

interface MentorRuntimeProviderProps {
  roadmapId: string;
  conceptId: string | null;
  agentMode: MentorAgentMode;
  children: React.ReactNode;
}

const MentorRuntimeContext = createContext<MentorRuntimeContextValue | null>(null);

/**
 * Mentor Runtime Provider。
 *
 * 负责管理对话状态、SSE 流以及工具调用展示状态。
 */
export function MentorRuntimeProvider({
  roadmapId,
  conceptId,
  agentMode,
  children,
}: MentorRuntimeProviderProps) {
  const [messages, setMessages] = useState<MentorMessageState[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesRef = useRef<MentorMessageState[]>([]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    // 为什么这样做：切换伴学/导学后需要隔离上下文，避免两种教学策略互相污染。
    setMessages([]);
    setError(null);
  }, [agentMode]);

  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsStreaming(false);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  const updateAssistantMessage = useCallback(
    (
      assistantId: string,
      updater: (message: MentorMessageState) => MentorMessageState
    ) => {
      setMessages((prev) =>
        prev.map((message) => (message.id === assistantId ? updater(message) : message))
      );
    },
    []
  );

  const applySseEvent = useCallback(
    (assistantId: string, event: MentorSSEEvent) => {
      switch (event.type) {
        case 'text_delta':
          updateAssistantMessage(assistantId, (message) => ({
            ...message,
            text: `${message.text}${event.content}`,
          }));
          break;

        case 'tool_call_start':
          updateAssistantMessage(assistantId, (message) => ({
            ...message,
            toolCalls: [
              ...message.toolCalls.filter((item) => item.toolCallId !== event.tool_call_id),
              {
                toolCallId: event.tool_call_id,
                toolName: event.tool_name,
                args: event.args,
                loading: true,
              },
            ],
          }));
          break;

        case 'tool_call_end':
          updateAssistantMessage(assistantId, (message) => ({
            ...message,
            toolCalls: message.toolCalls.map((toolCall) =>
              toolCall.toolCallId === event.tool_call_id
                ? {
                    ...toolCall,
                    loading: false,
                    success: event.success,
                    result: event.result,
                  }
                : toolCall
            ),
          }));
          break;

        default:
          break;
      }
    },
    [updateAssistantMessage]
  );

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isStreaming) return;

      setError(null);
      setIsStreaming(true);

      const userMessage: MentorMessageState = {
        id: `user_${crypto.randomUUID()}`,
        role: 'user',
        text: content.trim(),
        toolCalls: [],
      };
      const assistantMessage: MentorMessageState = {
        id: `assistant_${crypto.randomUUID()}`,
        role: 'assistant',
        text: '',
        toolCalls: [],
      };

      const historyMessages = [...messagesRef.current, userMessage]
        .filter((message) => message.role === 'user' || message.role === 'assistant')
        .map((message) => ({
          role: message.role,
          content: message.text,
        }))
        .filter((message) => message.content.trim().length > 0);

      setMessages((prev) => [...prev, userMessage, assistantMessage]);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        for await (const event of streamMentorChat({
          roadmapId,
          conceptId,
          agentMode,
          messages: historyMessages,
          abortSignal: controller.signal,
        })) {
          if (event.type === 'error') {
            throw new Error(event.message);
          }

          if (event.type === 'done') {
            break;
          }

          applySseEvent(assistantMessage.id, event);
        }
      } catch (streamError) {
        if (
          streamError instanceof Error &&
          streamError.name === 'AbortError'
        ) {
          return;
        }
        setError(streamError instanceof Error ? streamError.message : 'Mentor 对话失败');
      } finally {
        abortControllerRef.current = null;
        setIsStreaming(false);
      }
    },
    [agentMode, applySseEvent, conceptId, isStreaming, roadmapId]
  );

  const value = useMemo<MentorRuntimeContextValue>(
    () => ({
      messages,
      isStreaming,
      error,
      sendMessage,
      clearMessages,
      stopStreaming,
    }),
    [clearMessages, error, isStreaming, messages, sendMessage, stopStreaming]
  );

  return (
    <MentorRuntimeContext.Provider value={value}>
      {children}
    </MentorRuntimeContext.Provider>
  );
}

/**
 * 获取 Mentor Runtime 上下文。
 */
export function useMentorRuntime(): MentorRuntimeContextValue {
  const context = useContext(MentorRuntimeContext);
  if (!context) {
    throw new Error('useMentorRuntime 必须在 MentorRuntimeProvider 内部使用');
  }
  return context;
}

export type { MentorAgentMode } from '@/lib/api/sse/mentor-sse-adapter';


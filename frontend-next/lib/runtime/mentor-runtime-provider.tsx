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
  type MentorModelName,
  type MentorSSEEvent,
} from '@/lib/api/sse/mentor-sse-adapter';
import {
  threadHistoryAdapter,
  type MentorHistoryMessage,
  type MentorSessionSummary,
  type MentorThreadCachePayload,
} from '@/lib/runtime/thread-history-adapter';

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
  sessionSummaries: MentorSessionSummary[];
  isStreaming: boolean;
  isHistoryLoading: boolean;
  error: string | null;
  activeSessionId: string | null;
  sendMessage: (content: string) => Promise<void>;
  switchSession: (sessionId: string) => Promise<void>;
  clearMessages: () => void;
  stopStreaming: () => void;
}

interface MentorRuntimeProviderProps {
  roadmapId: string;
  conceptId: string | null;
  conceptName?: string | null;
  agentMode: MentorAgentMode;
  modelName: MentorModelName;
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
  conceptName = null,
  agentMode,
  modelName,
  children,
}: MentorRuntimeProviderProps) {
  const [messages, setMessages] = useState<MentorMessageState[]>([]);
  const [sessionSummaries, setSessionSummaries] = useState<MentorSessionSummary[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [isHistoryBootstrapped, setIsHistoryBootstrapped] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesRef = useRef<MentorMessageState[]>([]);
  const activeSessionIdRef = useRef<string | null>(null);
  const previousAgentModeRef = useRef<MentorAgentMode>(agentMode);
  const previousModelNameRef = useRef<MentorModelName>(modelName);
  const hasConceptInitializedRef = useRef(false);
  const roadmapIdRef = useRef(roadmapId);
  const previousConceptIdRef = useRef<string | null>(conceptId);
  const pendingConceptContextRef = useRef<string | null>(null);
  const skipHistoryBootstrapRef = useRef(false);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    activeSessionIdRef.current = activeSessionId;
  }, [activeSessionId]);

  useEffect(() => {
    roadmapIdRef.current = roadmapId;
  }, [roadmapId]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsStreaming(false);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
    setActiveSessionId(null);
    threadHistoryAdapter.clearStoredSessionId(roadmapId, agentMode, modelName);
    threadHistoryAdapter.clearCachedThread(roadmapId, agentMode, modelName);
  }, [agentMode, modelName, roadmapId]);

  const mapHistoryMessagesToRuntime = useCallback(
    (historyMessages: MentorHistoryMessage[]): MentorMessageState[] => {
      return historyMessages
        .filter(
          (historyMessage) =>
            historyMessage.role === 'user' || historyMessage.role === 'assistant'
        )
        .map((historyMessage) => {
          const metadata = historyMessage.message_metadata as
            | { tool_calls?: Array<Record<string, unknown>> }
            | null
            | undefined;
          const rawToolCalls = Array.isArray(metadata?.tool_calls)
            ? metadata.tool_calls
            : [];

          const toolCalls: MentorToolCallState[] = rawToolCalls.map((toolCall) => ({
            toolCallId: String(toolCall['tool_call_id'] ?? ''),
            toolName: String(toolCall['tool_name'] ?? 'unknown_tool'),
            args:
              toolCall['args'] && typeof toolCall['args'] === 'object'
                ? (toolCall['args'] as Record<string, unknown>)
                : undefined,
            loading: Boolean(toolCall['loading']),
            success:
              typeof toolCall['success'] === 'boolean'
                ? (toolCall['success'] as boolean)
                : undefined,
            result: toolCall['result'],
          }));

          return {
            id: historyMessage.message_id,
            role: historyMessage.role as 'user' | 'assistant',
            text: historyMessage.content,
            toolCalls,
          };
        });
    },
    []
  );

  const refreshSessionSummaries = useCallback(async () => {
    const sessions = await threadHistoryAdapter.listSessions(
      roadmapId,
      agentMode,
      modelName,
      20
    );
    setSessionSummaries(sessions);
    return sessions;
  }, [agentMode, modelName, roadmapId]);

  const switchSession = useCallback(
    async (sessionId: string) => {
      if (!sessionId || isStreaming) return;

      setIsHistoryLoading(true);
      setError(null);

      try {
        const historyMessages = await threadHistoryAdapter.getSessionMessages(
          roadmapId,
          sessionId,
          200
        );
        const restoredMessages = mapHistoryMessagesToRuntime(historyMessages);

        setMessages(restoredMessages);
        setActiveSessionId(sessionId);
        threadHistoryAdapter.setStoredSessionId(
          roadmapId,
          agentMode,
          modelName,
          sessionId
        );
        threadHistoryAdapter.setCachedThread(roadmapId, agentMode, modelName, {
          sessionId,
          messages: restoredMessages,
        });
      } catch (switchError) {
        setError(
          switchError instanceof Error ? switchError.message : '切换历史会话失败'
        );
      } finally {
        setIsHistoryLoading(false);
        setIsHistoryBootstrapped(true);
      }
    },
    [
      agentMode,
      isStreaming,
      mapHistoryMessagesToRuntime,
      modelName,
      roadmapId,
    ]
  );

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

  const sendMessageInternal = useCallback(
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

      setMessages((prev) => [...prev, userMessage, assistantMessage]);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        for await (const event of streamMentorChat({
          roadmapId,
          conceptId,
          agentMode,
          modelName,
          sessionId: activeSessionIdRef.current,
          messages: [
            {
              role: 'user',
              content: userMessage.text,
            },
          ],
          abortSignal: controller.signal,
        })) {
          if (event.type === 'error') {
            throw new Error(event.message);
          }

          if (event.type === 'done') {
            if (event.session_id) {
              setActiveSessionId(event.session_id);
              threadHistoryAdapter.setStoredSessionId(
                roadmapId,
                agentMode,
                modelName,
                event.session_id
              );
            }
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
        void refreshSessionSummaries().catch(() => undefined);
      }
    },
    [
      agentMode,
      applySseEvent,
      conceptId,
      isStreaming,
      modelName,
      refreshSessionSummaries,
      roadmapId,
    ]
  );

  const sendMessage = useCallback(
    async (content: string) => {
      await sendMessageInternal(content);
    },
    [sendMessageInternal]
  );

  useEffect(() => {
    if (previousAgentModeRef.current === agentMode) {
      return;
    }

    previousAgentModeRef.current = agentMode;
    // 为什么这样做：切换伴学/导学后必须从空白线程开始，避免策略上下文串话。
    skipHistoryBootstrapRef.current = true;
    stopStreaming();
    setMessages([]);
    setSessionSummaries([]);
    setError(null);
    setActiveSessionId(null);
    threadHistoryAdapter.clearStoredSessionId(
      roadmapIdRef.current,
      agentMode,
      modelName
    );
    threadHistoryAdapter.clearCachedThread(
      roadmapIdRef.current,
      agentMode,
      modelName
    );
  }, [agentMode, modelName, stopStreaming]);

  useEffect(() => {
    if (previousModelNameRef.current === modelName) {
      return;
    }

    previousModelNameRef.current = modelName;
    // 为什么这样做：切换模型后需要重新加载该模型对应的独立会话历史。
    skipHistoryBootstrapRef.current = false;
    stopStreaming();
    setMessages([]);
    setError(null);
    setActiveSessionId(null);
    setIsHistoryBootstrapped(false);
  }, [modelName, stopStreaming]);

  useEffect(() => {
    const cachedThread = threadHistoryAdapter.getCachedThread(
      roadmapId,
      agentMode,
      modelName
    );
    if (!cachedThread) return;
    if (cachedThread.sessionId) {
      setActiveSessionId(cachedThread.sessionId);
    }
    if (cachedThread.messages.length > 0) {
      setMessages(cachedThread.messages);
    }
  }, [roadmapId, agentMode, modelName]);

  useEffect(() => {
    let cancelled = false;

    async function loadHistory() {
      if (skipHistoryBootstrapRef.current) {
        skipHistoryBootstrapRef.current = false;
        return;
      }

      setIsHistoryBootstrapped(false);
      setIsHistoryLoading(true);
      setError(null);

      try {
        const sessions = await refreshSessionSummaries();
        if (cancelled) return;

        const storedSessionId = threadHistoryAdapter.getStoredSessionId(
          roadmapId,
          agentMode,
          modelName
        );
        const availableSessionIds = new Set(sessions.map((session) => session.session_id));
        const sessionId = storedSessionId && availableSessionIds.has(storedSessionId)
          ? storedSessionId
          : (sessions[0]?.session_id ?? null);

        if (!sessionId) {
          if (!cancelled) {
            setMessages([]);
            setActiveSessionId(null);
          }
          return;
        }

        const historyMessages = await threadHistoryAdapter.getSessionMessages(roadmapId, sessionId, 200);
        if (cancelled) return;

        setActiveSessionId(sessionId);
        threadHistoryAdapter.setStoredSessionId(
          roadmapId,
          agentMode,
          modelName,
          sessionId
        );

        const restoredMessages = mapHistoryMessagesToRuntime(historyMessages);

        setMessages(restoredMessages);
        threadHistoryAdapter.setCachedThread(roadmapId, agentMode, modelName, {
          sessionId,
          messages: restoredMessages,
        });
      } catch (historyError) {
        if (!cancelled) {
          setError(
            historyError instanceof Error ? historyError.message : '加载历史对话失败'
          );
          setMessages([]);
          setActiveSessionId(null);
        }
      } finally {
        if (!cancelled) {
          setIsHistoryLoading(false);
          setIsHistoryBootstrapped(true);
        }
      }
    }

    void loadHistory();

    return () => {
      cancelled = true;
    };
  }, [
    agentMode,
    mapHistoryMessagesToRuntime,
    modelName,
    refreshSessionSummaries,
    roadmapId,
  ]);

  useEffect(() => {
    if (!isHistoryBootstrapped) return;
    const payload: MentorThreadCachePayload = {
      sessionId: activeSessionId,
      messages,
    };
    threadHistoryAdapter.setCachedThread(roadmapId, agentMode, modelName, payload);
  }, [
    activeSessionId,
    agentMode,
    isHistoryBootstrapped,
    messages,
    modelName,
    roadmapId,
  ]);

  useEffect(() => {
    if (!hasConceptInitializedRef.current) {
      hasConceptInitializedRef.current = true;
      previousConceptIdRef.current = conceptId;
      return;
    }

    const previousConceptId = previousConceptIdRef.current;
    previousConceptIdRef.current = conceptId;

    if (conceptId === previousConceptId) return;
    if (!conceptId) return;
    if (messagesRef.current.length === 0) return;

    const displayConcept = (conceptName && conceptName.trim()) || conceptId;
    const autoContextMessage = `我现在在学「${displayConcept}」。请基于这个概念继续指导我。`;
    if (isStreaming) {
      pendingConceptContextRef.current = autoContextMessage;
      return;
    }
    void sendMessageInternal(autoContextMessage);
  }, [conceptId, conceptName, isStreaming, sendMessageInternal]);

  useEffect(() => {
    if (isStreaming) return;
    if (!pendingConceptContextRef.current) return;
    const message = pendingConceptContextRef.current;
    pendingConceptContextRef.current = null;
    void sendMessageInternal(message);
  }, [isStreaming, sendMessageInternal]);

  const value = useMemo<MentorRuntimeContextValue>(
    () => ({
      messages,
      sessionSummaries,
      isStreaming,
      isHistoryLoading,
      error,
      activeSessionId,
      sendMessage,
      switchSession,
      clearMessages,
      stopStreaming,
    }),
    [
      activeSessionId,
      clearMessages,
      error,
      isHistoryLoading,
      isStreaming,
      messages,
      sessionSummaries,
      sendMessage,
      stopStreaming,
      switchSession,
    ]
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

export type {
  MentorAgentMode,
  MentorModelName,
} from '@/lib/api/sse/mentor-sse-adapter';


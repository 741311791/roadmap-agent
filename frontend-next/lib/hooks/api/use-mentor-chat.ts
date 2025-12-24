/**
 * useMentorChat - 伴学Agent聊天 Hook
 * 
 * 功能:
 * - SSE 流式聊天
 * - 会话管理
 * - 消息历史
 * - 笔记管理
 */

import { useState, useCallback, useRef } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { API_CONFIG } from '@/lib/constants/api';

// ============================================================
// 类型定义
// ============================================================

export interface ChatMessage {
  message_id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  intent_type?: string;
  created_at: string;
}

export interface ChatSession {
  session_id: string;
  user_id: string;
  roadmap_id: string;
  concept_id?: string;
  title?: string;
  message_count: number;
  last_message_preview?: string;
  created_at: string;
  updated_at: string;
}

export interface LearningNote {
  note_id: string;
  user_id: string;
  roadmap_id: string;
  concept_id: string;
  title?: string;
  content: string;
  source: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

interface UseMentorChatOptions {
  userId: string;
  roadmapId: string;
  conceptId?: string;
  /** 完成回调 */
  onComplete?: (messageId: string) => void;
  /** 错误回调 */
  onError?: (error: string) => void;
}

// ============================================================
// Hook 实现
// ============================================================

export function useMentorChat(options: UseMentorChatOptions) {
  const { userId, roadmapId, conceptId, onComplete, onError } = options;

  // 状态
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);

  // Abort Controller
  const abortControllerRef = useRef<AbortController | null>(null);

  // 发送消息
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    // 添加用户消息到列表（临时ID）
    const tempUserMessageId = `temp-${Date.now()}`;
    const userMessage: ChatMessage = {
      message_id: tempUserMessageId,
      session_id: sessionId || '',
      role: 'user',
      content: content.trim(),
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    // 清空之前的错误和流缓冲
    setError(null);
    setStreamBuffer('');
    setIsStreaming(true);

    // 创建 Abort Controller
    abortControllerRef.current = new AbortController();

    try {
      const endpoint = `${API_CONFIG.BASE_URL}/api/v1/mentor/chat/stream`;
      const requestBody = {
        user_id: userId,
        roadmap_id: roadmapId,
        concept_id: conceptId || null,
        message: content.trim(),
        session_id: sessionId,
      };

      await fetchEventSource(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
        signal: abortControllerRef.current.signal,

        onopen: async (response) => {
          if (!response.ok) {
            throw new Error(`SSE connection failed: ${response.status}`);
          }
          console.log('[MentorChat] SSE connected');
        },

        onmessage: (event) => {
          try {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
              case 'session_id':
                // 更新会话ID
                setSessionId(data.session_id);
                break;

              case 'content':
                // 流式内容
                setStreamBuffer(prev => prev + data.chunk);
                break;

              case 'done':
                // 完成，将流缓冲转为消息
                setMessages(prev => {
                  // 获取最终内容
                  const finalContent = prev.find(m => m.message_id.startsWith('streaming-'))?.content || '';
                  // 移除streaming消息，添加最终消息
                  const filtered = prev.filter(m => !m.message_id.startsWith('streaming-'));
                  return [
                    ...filtered,
                    {
                      message_id: data.message_id,
                      session_id: sessionId || data.session_id,
                      role: 'assistant' as const,
                      content: finalContent || streamBuffer,
                      created_at: new Date().toISOString(),
                    },
                  ];
                });
                setStreamBuffer('');
                setIsStreaming(false);
                onComplete?.(data.message_id);
                break;

              case 'error':
                setError(data.message);
                setIsStreaming(false);
                onError?.(data.message);
                break;
            }
          } catch (e) {
            console.error('[MentorChat] Failed to parse SSE message:', e);
          }
        },

        onerror: (err) => {
          console.error('[MentorChat] SSE error:', err);
          setIsStreaming(false);
          throw err;
        },

        onclose: () => {
          console.log('[MentorChat] SSE closed');
          setIsStreaming(false);
        },
      });
    } catch (err: any) {
      // 忽略 abort 错误
      if (err.name === 'AbortError') {
        console.log('[MentorChat] Request aborted');
        return;
      }
      
      console.error('[MentorChat] Error:', err);
      const errorMessage = err.message || 'Failed to send message';
      setError(errorMessage);
      setLastFailedMessage(content.trim());
      setIsStreaming(false);
      onError?.(errorMessage);
    }
  }, [userId, roadmapId, conceptId, sessionId, streamBuffer, onComplete, onError]);

  // 停止流式输出
  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  // 重试失败的消息
  const retryLastMessage = useCallback(() => {
    if (lastFailedMessage) {
      setError(null);
      setLastFailedMessage(null);
      sendMessage(lastFailedMessage);
    }
  }, [lastFailedMessage, sendMessage]);

  // 清空消息
  const clearMessages = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setStreamBuffer('');
    setError(null);
  }, []);

  // 加载会话历史
  const loadSessionHistory = useCallback(async (targetSessionId: string) => {
    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}/api/v1/mentor/messages/${targetSessionId}?limit=50`
      );
      if (!response.ok) {
        throw new Error('Failed to load messages');
      }
      const data = await response.json();
      setMessages(data.messages);
      setSessionId(targetSessionId);
    } catch (err: any) {
      console.error('[MentorChat] Failed to load history:', err);
      setError(err.message);
    }
  }, []);

  // 获取会话列表
  const getSessions = useCallback(async (): Promise<ChatSession[]> => {
    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}/api/v1/mentor/sessions/${roadmapId}?user_id=${encodeURIComponent(userId)}`
      );
      if (!response.ok) {
        throw new Error('Failed to load sessions');
      }
      const data = await response.json();
      return data.sessions;
    } catch (err: any) {
      console.error('[MentorChat] Failed to load sessions:', err);
      return [];
    }
  }, [userId, roadmapId]);

  // 获取笔记列表
  const getNotes = useCallback(async (filterConceptId?: string): Promise<LearningNote[]> => {
    try {
      let url = `${API_CONFIG.BASE_URL}/api/v1/mentor/notes/${roadmapId}?user_id=${encodeURIComponent(userId)}`;
      if (filterConceptId) {
        url += `&concept_id=${encodeURIComponent(filterConceptId)}`;
      }
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Failed to load notes');
      }
      const data = await response.json();
      return data.notes;
    } catch (err: any) {
      console.error('[MentorChat] Failed to load notes:', err);
      return [];
    }
  }, [userId, roadmapId]);

  // 计算当前显示的消息（包括流式缓冲）
  const displayMessages = [...messages];
  if (isStreaming && streamBuffer) {
    // 添加或更新streaming消息
    const existingStreamingIndex = displayMessages.findIndex(m => m.message_id.startsWith('streaming-'));
    if (existingStreamingIndex >= 0) {
      displayMessages[existingStreamingIndex] = {
        ...displayMessages[existingStreamingIndex],
        content: streamBuffer,
      };
    } else {
      displayMessages.push({
        message_id: `streaming-${Date.now()}`,
        session_id: sessionId || '',
        role: 'assistant',
        content: streamBuffer,
        created_at: new Date().toISOString(),
      });
    }
  }

  return {
    // 状态
    messages: displayMessages,
    sessionId,
    isStreaming,
    error,
    lastFailedMessage,

    // 操作
    sendMessage,
    stopStreaming,
    retryLastMessage,
    clearMessages,
    loadSessionHistory,
    getSessions,
    getNotes,
  };
}

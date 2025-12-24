/**
 * 聊天状态管理 Store
 * 使用 Zustand 管理 AI 聊天状态
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

/**
 * 消息类型
 */
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

/**
 * 聊天 Store 状态
 */
export interface ChatState {
  // 消息列表
  messages: Message[];

  // 流式状态
  isStreaming: boolean;
  streamBuffer: string;

  // 上下文
  contextConceptId: string | null;
  contextRoadmapId: string | null;

  // 错误
  error: string | null;
}

/**
 * 聊天 Store Actions
 */
export interface ChatActions {
  // 消息管理
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateMessage: (id: string, content: string) => void;
  clearMessages: () => void;

  // 流式输出
  appendToStream: (chunk: string) => void;
  completeStream: () => void;
  clearStream: () => void;

  // 上下文管理
  setContext: (conceptId: string | null, roadmapId: string | null) => void;
  clearContext: () => void;

  // 错误处理
  setError: (error: string | null) => void;
}

/**
 * 聊天 Store 类型
 */
export type ChatStore = ChatState & ChatActions;

/**
 * 创建聊天 Store
 * 生产环境优化：移除 devtools 中间件
 */
const storeImplementation = (set: any, get: any): ChatStore => ({
      // 初始状态
      messages: [],
      isStreaming: false,
      streamBuffer: '',
      contextConceptId: null,
      contextRoadmapId: null,
      error: null,

      // 消息管理
      addMessage: (message: Omit<Message, 'id' | 'timestamp'>) =>
        set((state: ChatStore) => ({
          messages: [
            ...state.messages,
            {
              ...message,
              id: crypto.randomUUID(),
              timestamp: new Date().toISOString(),
            },
          ],
        })),

      updateMessage: (id: string, content: string) =>
        set((state: ChatStore) => ({
          messages: state.messages.map((msg) =>
            msg.id === id ? { ...msg, content } : msg
          ),
        })),

      clearMessages: () => set({ messages: [] }),

      // 流式输出
      appendToStream: (chunk: string) =>
        set((state: ChatStore) => ({
          streamBuffer: state.streamBuffer + chunk,
          isStreaming: true,
        })),

      completeStream: () =>
        set((state: ChatStore) => {
          // 将流式缓冲区的内容作为新消息添加
          if (state.streamBuffer) {
            return {
              messages: [
                ...state.messages,
                {
                  id: crypto.randomUUID(),
                  role: 'assistant',
                  content: state.streamBuffer,
                  timestamp: new Date().toISOString(),
                },
              ],
              isStreaming: false,
              streamBuffer: '',
            };
          }
          return { isStreaming: false };
        }),

      clearStream: () =>
        set({
          isStreaming: false,
          streamBuffer: '',
        }),

      // 上下文管理
      setContext: (conceptId: string | null, roadmapId: string | null) =>
        set({
          contextConceptId: conceptId,
          contextRoadmapId: roadmapId,
        }),

      clearContext: () =>
        set({
          contextConceptId: null,
          contextRoadmapId: null,
        }),

      // 错误处理
      setError: (error: string | null) => set({ error }),
});

// 根据环境选择是否使用 devtools
export const useChatStore =
  process.env.NODE_ENV === 'development'
    ? create<ChatStore>()(devtools(storeImplementation, { name: 'ChatStore' }))
    : create<ChatStore>()(storeImplementation);

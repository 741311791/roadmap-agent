import { describe, it, expect, beforeEach } from 'vitest';
import { useChatStore } from '@/lib/store/chat-store';
import { act, renderHook } from '@testing-library/react';

describe('ChatStore', () => {
  beforeEach(() => {
    // 在每个测试前重置store
    const { result } = renderHook(() => useChatStore());
    act(() => {
      result.current.clearMessages();
    });
  });

  describe('消息管理', () => {
    it('应该添加消息', () => {
      const { result } = renderHook(() => useChatStore());

      const mockMessage = {
        role: 'user' as const,
        content: 'Hello',
      };

      act(() => {
        result.current.addMessage(mockMessage);
      });

      expect(result.current.messages[0]).toMatchObject({
        role: 'user',
        content: 'Hello',
      });
      expect(result.current.messages).toHaveLength(1);
    });

    it('应该更新消息', () => {
      const { result } = renderHook(() => useChatStore());

      const mockMessage = {
        role: 'user' as const,
        content: 'Hello',
      };

      let messageId: string;

      act(() => {
        result.current.addMessage(mockMessage);
        messageId = result.current.messages[0].id;
        result.current.updateMessage(messageId, 'Updated content');
      });

      const updatedMessage = result.current.messages.find(m => m.id === messageId);
      expect(updatedMessage?.content).toBe('Updated content');
    });

    it('应该清除所有消息', () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.addMessage({
          role: 'user',
          content: 'Hello',
        });
        result.current.addMessage({
          role: 'assistant',
          content: 'Hi',
        });
      });

      expect(result.current.messages).toHaveLength(2);

      act(() => {
        result.current.clearMessages();
      });

      expect(result.current.messages).toHaveLength(0);
    });
  });

  describe('流式消息管理', () => {
    it('应该追加流式内容', () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.appendToStream('Hello ');
        result.current.appendToStream('World');
      });

      expect(result.current.streamBuffer).toBe('Hello World');
      expect(result.current.isStreaming).toBe(true);
    });

    it('应该完成流式输出', () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.appendToStream('Complete message');
        result.current.completeStream();
      });

      expect(result.current.isStreaming).toBe(false);
      expect(result.current.streamBuffer).toBe('');
      
      const message = result.current.messages.find(m => m.content === 'Complete message');
      expect(message).toBeDefined();
      expect(message?.content).toBe('Complete message');
    });
  });

  describe('上下文管理', () => {
    it('应该设置上下文', () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setContext('c1', 'r1');
      });

      expect(result.current.contextConceptId).toBe('c1');
      expect(result.current.contextRoadmapId).toBe('r1');
    });

    it('应该清除上下文', () => {
      const { result } = renderHook(() => useChatStore());

      act(() => {
        result.current.setContext('c1', 'r1');
        result.current.clearContext();
      });

      expect(result.current.contextConceptId).toBeNull();
      expect(result.current.contextRoadmapId).toBeNull();
    });
  });
});


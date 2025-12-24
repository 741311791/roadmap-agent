/**
 * useChatStream - AI 聊天流式输出 Hook (SSE)
 * 
 * 功能:
 * - SSE 连接管理
 * - 聊天修改流程事件监听
 * - 意图分析、修改进度、结果处理
 * - 流式输出到 Store
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { useChatStore } from '@/lib/store/chat-store';

interface UseChatStreamOptions {
  /** 完成回调 */
  onComplete?: () => void;
  /** 错误回调 */
  onError?: (error: string) => void;
}

/**
 * AI 聊天流式 Hook
 * @param endpoint - SSE 端点 URL
 * @param requestBody - 请求体
 * @param options - 配置选项
 * @returns 连接状态和控制函数
 */
export function useChatStream(
  endpoint: string | null,
  requestBody: any | null,
  options: UseChatStreamOptions = {}
) {
  const { onComplete, onError } = options;

  const abortControllerRef = useRef<AbortController | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const {
    appendToStream,
    completeStream,
    setError,
  } = useChatStore();

  // 处理 SSE 消息
  const handleMessage = useCallback(
    (data: any) => {
      console.log('[SSE] Message:', data.type);

      switch (data.type) {
        case 'analyzing':
          console.log('[SSE] Analyzing intent...');
          appendToStream('🔍 正在分析您的修改需求...\n\n');
          break;

        case 'intents':
          console.log('[SSE] Intents detected:', data.intents);
          appendToStream('📋 识别到以下修改意图:\n');
          data.intents?.forEach((intent: any, index: number) => {
            appendToStream(`${index + 1}. ${intent}\n`);
          });
          appendToStream('\n');
          break;

        case 'modifying':
          console.log('[SSE] Modifying:', data.target_name);
          appendToStream(`✏️ 正在修改: ${data.target_name}...\n`);
          break;

        case 'result':
          console.log('[SSE] Result:', data.success);
          if (data.success) {
            appendToStream(`✅ ${data.target_name} 修改成功\n`);
          } else {
            appendToStream(
              `❌ ${data.target_name} 修改失败: ${data.error_message}\n`
            );
          }
          break;

        case 'done':
          console.log('[SSE] Modification complete');
          appendToStream('\n🎉 所有修改已完成！\n');
          completeStream();
          setIsStreaming(false);
          onComplete?.();
          break;

        case 'modification_error':
          console.error('[SSE] Error:', data.message);
          appendToStream(`\n❌ 错误: ${data.message}\n`);
          setError(data.message);
          setIsStreaming(false);
          onError?.(data.message);
          break;

        default:
          console.warn('[SSE] Unknown message type:', data.type);
      }
    },
    [appendToStream, completeStream, setError, onComplete, onError]
  );

  // 启动 SSE 连接
  const connect = useCallback(async () => {
    if (!endpoint || !requestBody) return;

    abortControllerRef.current = new AbortController();
    setIsStreaming(true);

    try {
      await fetchEventSource(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
        signal: abortControllerRef.current.signal,

        onopen: async (response) => {
          if (response.ok) {
            console.log('[SSE] Connection opened');
          } else {
            throw new Error(`SSE connection failed: ${response.status}`);
          }
        },

        onmessage: (event) => {
          try {
            const data = JSON.parse(event.data);
            handleMessage(data);
          } catch (error) {
            console.error('[SSE] Failed to parse message:', error);
          }
        },

        onerror: (error) => {
          console.error('[SSE] Error:', error);
          setIsStreaming(false);
          throw error;
        },

        onclose: () => {
          console.log('[SSE] Connection closed');
          setIsStreaming(false);
        },
      });
    } catch (error: any) {
      console.error('[SSE] Connection error:', error);
      setError(error.message || 'SSE 连接失败');
      setIsStreaming(false);
      onError?.(error.message || 'SSE 连接失败');
    }
  }, [endpoint, requestBody, handleMessage, setError, onError]);

  // 断开连接
  const disconnect = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      console.log('[SSE] Connection aborted');
    }
    setIsStreaming(false);
  }, []);

  // 自动连接
  useEffect(() => {
    if (endpoint && requestBody) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [endpoint, requestBody, connect, disconnect]);

  return {
    isStreaming,
    disconnect,
  };
}

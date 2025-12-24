/**
 * AI 聊天 SSE 客户端
 * 用于 AI 聊天修改流式输出
 */

import { fetchEventSource } from '@microsoft/fetch-event-source';
import { API_PREFIX } from '@/lib/constants';
import { createLogger } from '@/lib/utils/logger';

const logger = createLogger('SSE');

/**
 * 聊天修改事件类型
 */
export interface ChatModificationEvent {
  type: string;
  timestamp: string;
}

export interface AnalyzingEvent extends ChatModificationEvent {
  type: 'analyzing';
  message: string;
}

export interface IntentsEvent extends ChatModificationEvent {
  type: 'intents';
  intents: Array<{
    type: string;
    target: string;
    description: string;
  }>;
}

export interface ModifyingEvent extends ChatModificationEvent {
  type: 'modifying';
  target_type: string;
  target_name: string;
  message: string;
}

export interface ResultEvent extends ChatModificationEvent {
  type: 'result';
  target_type: string;
  target_name: string;
  success: boolean;
  error_message?: string;
}

export interface ModificationDoneEvent extends ChatModificationEvent {
  type: 'done';
  success_count: number;
  failed_count: number;
  message: string;
}

export interface ModificationErrorEvent extends ChatModificationEvent {
  type: 'error';
  message: string;
}

/**
 * SSE 事件处理器
 */
export interface ChatSSEHandlers {
  onAnalyzing?: (event: AnalyzingEvent) => void;
  onIntents?: (event: IntentsEvent) => void;
  onModifying?: (event: ModifyingEvent) => void;
  onResult?: (event: ResultEvent) => void;
  onDone?: (event: ModificationDoneEvent) => void;
  onError?: (event: ModificationErrorEvent) => void;
}

/**
 * AI 聊天 SSE 客户端
 */
export class ChatSSE {
  private abortController: AbortController | null = null;
  private handlers: ChatSSEHandlers;

  constructor(handlers: ChatSSEHandlers) {
    this.handlers = handlers;
  }

  /**
   * 连接 SSE
   */
  async connect(endpoint: string, requestBody: any) {
    this.abortController = new AbortController();

    const fullUrl = endpoint.startsWith('http') ? endpoint : `${API_PREFIX}${endpoint}`;
    
    logger.info('Connecting to SSE:', fullUrl);

    try {
      await fetchEventSource(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
        signal: this.abortController.signal,
        
        onopen: async (response) => {
          if (response.ok) {
            logger.info('SSE connection opened');
          } else {
            throw new Error(`SSE connection failed: ${response.status}`);
          }
        },
        
        onmessage: (event) => {
          try {
            const data: ChatModificationEvent = JSON.parse(event.data);
            this.handleMessage(data);
          } catch (error) {
            logger.error('Failed to parse SSE message:', error);
          }
        },
        
        onerror: (error) => {
          logger.error('SSE error:', error);
          throw error;
        },
      });
    } catch (error) {
      logger.error('SSE connection error:', error);
      throw error;
    }
  }

  /**
   * 处理消息
   */
  private handleMessage(data: ChatModificationEvent) {
    switch (data.type) {
      case 'analyzing':
        this.handlers.onAnalyzing?.(data as AnalyzingEvent);
        break;
        
      case 'intents':
        this.handlers.onIntents?.(data as IntentsEvent);
        break;
        
      case 'modifying':
        this.handlers.onModifying?.(data as ModifyingEvent);
        break;
        
      case 'result':
        this.handlers.onResult?.(data as ResultEvent);
        break;
        
      case 'done':
        this.handlers.onDone?.(data as ModificationDoneEvent);
        this.disconnect();
        break;
        
      case 'error':
        this.handlers.onError?.(data as ModificationErrorEvent);
        this.disconnect();
        break;
        
      default:
        logger.warn('Unknown SSE event type:', data.type);
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
      logger.info('SSE connection closed');
    }
  }
}

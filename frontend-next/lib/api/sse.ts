/**
 * Server-Sent Events (SSE) Manager
 * 
 * Handles SSE connections for:
 * - Roadmap generation streaming
 * - Chat modification streaming
 */

import type { BaseSSEEvent, SSEHandlers } from '@/types/custom/sse';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface SSEConfig<T extends BaseSSEEvent> {
  url: string;
  handlers: SSEHandlers<T>;
  body?: unknown;
}

/**
 * SSE Manager class for managing Server-Sent Events connections
 */
export class SSEManager<T extends BaseSSEEvent> {
  private eventSource: EventSource | null = null;
  private abortController: AbortController | null = null;
  private config: SSEConfig<T>;
  private connected: boolean = false;

  constructor(config: SSEConfig<T>) {
    this.config = config;
  }

  /**
   * Connect to SSE endpoint using fetch API (for POST requests with body)
   */
  async connectWithPost(): Promise<void> {
    const { url, handlers, body } = this.config;
    const fullUrl = `${API_BASE_URL}${url}`;

    this.abortController = new AbortController();

    try {
      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: body ? JSON.stringify(body) : undefined,
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      this.connected = true;
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          handlers.onComplete?.();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6)) as T;
              handlers.onEvent(data);

              // Check for completion event
              if (data.type === 'complete' || data.type === 'done') {
                handlers.onComplete?.();
              }
            } catch (e) {
              // Not valid JSON, might be a heartbeat or other message
              console.debug('[SSE] Non-JSON data:', line);
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.debug('[SSE] Connection aborted');
        return;
      }

      handlers.onError?.(error instanceof Error ? error : new Error(String(error)));
    } finally {
      this.connected = false;
    }
  }

  /**
   * Connect to SSE endpoint using EventSource (for GET requests)
   */
  connectWithGet(): void {
    const { url, handlers } = this.config;
    const fullUrl = `${API_BASE_URL}${url}`;

    this.eventSource = new EventSource(fullUrl);
    this.connected = true;

    this.eventSource.onopen = () => {
      console.debug('[SSE] Connection opened');
    };

    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as T;
        handlers.onEvent(data);

        // Check for completion event
        if (data.type === 'complete' || data.type === 'done') {
          handlers.onComplete?.();
          this.disconnect();
        }
      } catch (e) {
        console.error('[SSE] Parse error:', e);
      }
    };

    this.eventSource.onerror = (error) => {
      console.error('[SSE] Connection error:', error);
      handlers.onError?.(new Error('SSE connection error'));
      this.disconnect();
    };
  }

  /**
   * Disconnect from SSE endpoint
   */
  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }

    this.connected = false;
    console.debug('[SSE] Connection closed');
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.connected;
  }
}

/**
 * Create SSE connection for roadmap generation
 */
export function createGenerationStream(
  body: {
    user_request: {
      user_id: string;
      session_id: string;
      preferences: {
        learning_goal: string;
        available_hours_per_week: number;
        motivation: string;
        current_level: string;
        career_background: string;
        content_preference: string[];
      };
    };
  },
  handlers: SSEHandlers<BaseSSEEvent>
): SSEManager<BaseSSEEvent> {
  const manager = new SSEManager({
    url: '/api/v1/roadmaps/generate-full-stream',
    handlers,
    body,
  });

  manager.connectWithPost();
  return manager;
}

/**
 * Create SSE connection for chat modification
 */
export function createChatModificationStream(
  roadmapId: string,
  body: {
    user_id: string;
    user_message: string;
    preferences: unknown;
    context?: {
      concept_id?: string;
    };
  },
  handlers: SSEHandlers<BaseSSEEvent>
): SSEManager<BaseSSEEvent> {
  const manager = new SSEManager({
    url: `/api/v1/roadmaps/${roadmapId}/chat-stream`,
    handlers,
    body,
  });

  manager.connectWithPost();
  return manager;
}

export default SSEManager;


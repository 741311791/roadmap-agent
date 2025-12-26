/**
 * WebSocket Manager
 * 
 * Handles WebSocket connections for real-time task status updates
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// WebSocket 事件类型（匹配后端 NotificationService 定义）
export interface WSEvent {
  type: string;
  task_id: string;
  timestamp?: string;
  message?: string;
  [key: string]: unknown;
}

// 连接成功事件（前端 WebSocket 端点）
export interface WSConnectedEvent extends WSEvent {
  type: 'connected';
  message: string;
}

// 当前状态事件（前端请求时返回）
export interface WSCurrentStatusEvent extends WSEvent {
  type: 'current_status';
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'human_review_pending';
  current_step: string | null;
  roadmap_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

// 进度更新事件（后端 TaskEvent.PROGRESS）
export interface WSProgressEvent extends WSEvent {
  type: 'progress';
  step: string;
  status: string;
  message?: string;
  timestamp: string;
  data?: {
    key_technologies?: string[];
    roadmap_id?: string;
    stages_count?: number;
    is_valid?: boolean;
    overall_score?: number;
    issues_count?: number;
    modification_count?: number;
    modified_concept_ids?: string[];  // 修改的概念节点 ID 列表
    total_concepts?: number;
    enabled_agents?: string[];
    approved?: boolean;
    feedback?: string | null;
    edit_source?: 'validation_failed' | 'human_review';  // 编辑来源（用于区分分支）
  };
}

// 任务完成事件（后端 TaskEvent.COMPLETED）
export interface WSCompletedEvent extends WSEvent {
  type: 'completed';
  roadmap_id: string;
  message?: string;
  timestamp: string;
  tutorials_count?: number;
  failed_count?: number;
}

// 任务失败事件（后端 TaskEvent.FAILED）
export interface WSFailedEvent extends WSEvent {
  type: 'failed';
  error: string;
  error_message?: string; // alias
  step?: string;
  timestamp: string;
}

// 人工审核请求事件（后端 TaskEvent.HUMAN_REVIEW_REQUIRED）
export interface WSHumanReviewEvent extends WSEvent {
  type: 'human_review_required';
  roadmap_id: string;
  roadmap_title: string;
  stages_count: number;
  message: string;
  timestamp: string;
}

// Concept 级别事件（后端 TaskEvent.CONCEPT_START/COMPLETE/FAILED）
export interface WSConceptStartEvent extends WSEvent {
  type: 'concept_start';
  concept_id: string;
  concept_name: string;
  content_type: 'tutorial' | 'resources' | 'quiz';
  progress: {
    current: number;
    total: number;
    percentage: number;
  };
  message: string;
  timestamp: string;
}

export interface WSConceptCompleteEvent extends WSEvent {
  type: 'concept_complete';
  concept_id: string;
  concept_name: string;
  content_type: 'tutorial' | 'resources' | 'quiz';
  message: string;
  timestamp: string;
  data?: {
    tutorial_id?: string;
    content_url?: string;
    resources_count?: number;
    quiz_id?: string;
    questions_count?: number;
  };
}

export interface WSConceptFailedEvent extends WSEvent {
  type: 'concept_failed';
  concept_id: string;
  concept_name: string;
  content_type: 'tutorial' | 'resources' | 'quiz';
  error: string;
  message: string;
  timestamp: string;
}

// 批次处理事件（后端 TaskEvent.BATCH_START/COMPLETE）
export interface WSBatchStartEvent extends WSEvent {
  type: 'batch_start';
  batch_index: number;
  batch_size: number;
  total_batches: number;
  concept_ids: string[];
  message: string;
  timestamp: string;
}

export interface WSBatchCompleteEvent extends WSEvent {
  type: 'batch_complete';
  batch_index: number;
  total_batches: number;
  progress: {
    completed: number;
    failed: number;
    total: number;
    percentage: number;
  };
  message: string;
  timestamp: string;
}

// 连接关闭事件
export interface WSClosingEvent extends WSEvent {
  type: 'closing';
  reason: string;
  message: string;
}

// 错误事件
export interface WSErrorEvent extends WSEvent {
  type: 'error';
  message: string;
}

// 心跳响应
export interface WSPongEvent extends WSEvent {
  type: 'pong';
}

// 超时事件
export interface WSTimeoutEvent extends WSEvent {
  type: 'timeout';
  message: string;
}

export type TaskWSEvent =
  | WSConnectedEvent
  | WSCurrentStatusEvent
  | WSProgressEvent
  | WSCompletedEvent
  | WSFailedEvent
  | WSHumanReviewEvent
  | WSConceptStartEvent
  | WSConceptCompleteEvent
  | WSConceptFailedEvent
  | WSBatchStartEvent
  | WSBatchCompleteEvent
  | WSClosingEvent
  | WSErrorEvent
  | WSPongEvent
  | WSTimeoutEvent;

export interface WSHandlers {
  // 连接事件
  onConnected?: (event: WSConnectedEvent) => void;
  onStatus?: (event: WSCurrentStatusEvent) => void;
  onClosing?: (event: WSClosingEvent) => void;
  onError?: (event: WSErrorEvent) => void;
  
  // 任务级别事件
  onProgress?: (event: WSProgressEvent) => void;
  onCompleted?: (event: WSCompletedEvent) => void;
  onFailed?: (event: WSFailedEvent) => void;
  onHumanReview?: (event: WSHumanReviewEvent) => void;
  
  // Concept 级别事件
  onConceptStart?: (event: WSConceptStartEvent) => void;
  onConceptComplete?: (event: WSConceptCompleteEvent) => void;
  onConceptFailed?: (event: WSConceptFailedEvent) => void;
  
  // 批次事件
  onBatchStart?: (event: WSBatchStartEvent) => void;
  onBatchComplete?: (event: WSBatchCompleteEvent) => void;
  
  // 通用处理器（接收所有事件）
  onAnyEvent?: (event: TaskWSEvent) => void;
}

/**
 * WebSocket Manager for task status subscriptions
 */
export class TaskWebSocket {
  private ws: WebSocket | null = null;
  private taskId: string;
  private handlers: WSHandlers;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 3;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private isIntentionallyClosed = false;

  constructor(taskId: string, handlers: WSHandlers) {
    this.taskId = taskId;
    this.handlers = handlers;
  }

  /**
   * Connect to WebSocket server
   */
  connect(includeHistory = true): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[WS] Already connected');
      return;
    }

    // Convert http(s) to ws(s)
    const wsBaseUrl = API_BASE_URL.replace(/^http/, 'ws');
    const wsUrl = `${wsBaseUrl}/api/v1/ws/${this.taskId}?include_history=${includeHistory}`;

    console.log('[WS] Connecting to:', wsUrl);

    this.isIntentionallyClosed = false;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('[WS] Connection opened');
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as TaskWSEvent;
        console.log('[WS] Message received:', data.type, data);

        // Call specific handler based on event type
        switch (data.type) {
          // Connection events
          case 'connected':
            this.handlers.onConnected?.(data as WSConnectedEvent);
            break;
          case 'current_status':
            this.handlers.onStatus?.(data as WSCurrentStatusEvent);
            break;
          case 'closing':
            this.handlers.onClosing?.(data as WSClosingEvent);
            break;
          case 'error':
            this.handlers.onError?.(data as WSErrorEvent);
            break;
          case 'pong':
            // Heartbeat response, no action needed
            break;
          
          // Task-level events (from NotificationService)
          case 'progress':
            this.handlers.onProgress?.(data as WSProgressEvent);
            break;
          case 'completed':
            this.handlers.onCompleted?.(data as WSCompletedEvent);
            break;
          case 'failed':
            this.handlers.onFailed?.(data as WSFailedEvent);
            break;
          case 'human_review_required':
            this.handlers.onHumanReview?.(data as WSHumanReviewEvent);
            break;
          
          // Concept-level events
          case 'concept_start':
            this.handlers.onConceptStart?.(data as WSConceptStartEvent);
            break;
          case 'concept_complete':
            this.handlers.onConceptComplete?.(data as WSConceptCompleteEvent);
            break;
          case 'concept_failed':
            this.handlers.onConceptFailed?.(data as WSConceptFailedEvent);
            break;
          
          // Batch events
          case 'batch_start':
            this.handlers.onBatchStart?.(data as WSBatchStartEvent);
            break;
          case 'batch_complete':
            this.handlers.onBatchComplete?.(data as WSBatchCompleteEvent);
            break;
          
          // Timeout event
          case 'timeout':
            this.handlers.onError?.({ type: 'error', task_id: data.task_id, message: data.message || '连接超时' });
            break;
        }

        // Always call onAnyEvent if defined
        this.handlers.onAnyEvent?.(data);

      } catch (e) {
        console.error('[WS] Failed to parse message:', event.data, e);
      }
    };

    this.ws.onerror = (error) => {
      console.error('[WS] Connection error:', error);
    };

    this.ws.onclose = (event) => {
      console.log('[WS] Connection closed:', event.code, event.reason);
      this.stopHeartbeat();

      // Attempt reconnect if not intentionally closed
      if (!this.isIntentionallyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        console.log(`[WS] Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`);
        setTimeout(() => this.connect(false), 2000 * this.reconnectAttempts);
      }
    };
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.isIntentionallyClosed = true;
    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
  }

  /**
   * Send a message to the server
   */
  send(message: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  /**
   * Request current status
   */
  requestStatus(): void {
    this.send({ type: 'get_status' });
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, 30000); // Every 30 seconds
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

/**
 * Create a WebSocket connection for a task
 */
export function createTaskWebSocket(
  taskId: string,
  handlers: WSHandlers
): TaskWebSocket {
  return new TaskWebSocket(taskId, handlers);
}




/**
 * 路线图生成 WebSocket 客户端
 * 用于实时监听路线图生成进度
 */

import { WS_CONFIG } from '@/lib/constants';
import { createLogger } from '@/lib/utils/logger';

const logger = createLogger('WebSocket');

/**
 * WebSocket 事件类型
 */
export interface WebSocketEvent {
  type: string;
  task_id: string;
  timestamp: string;
}

export interface ConnectedEvent extends WebSocketEvent {
  type: 'connected';
  message: string;
}

export interface CurrentStatusEvent extends WebSocketEvent {
  type: 'current_status';
  status: string;
  current_step: string;
  roadmap_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ProgressEvent extends WebSocketEvent {
  type: 'progress';
  step: string;
  status: string;
  message?: string;
  data?: {
    roadmap_id?: string;
    stages_count?: number;
    total_concepts?: number;
    [key: string]: any;
  };
  sub_status?: 'waiting' | 'editing';
}

export interface HumanReviewRequiredEvent extends WebSocketEvent {
  type: 'human_review_required';
  roadmap_id: string;
  roadmap_title: string;
  stages_count: number;
  message: string;
}

export interface ConceptStartEvent extends WebSocketEvent {
  type: 'concept_start';
  concept_id: string;
  concept_name: string;
  progress: {
    current: number;
    total: number;
    percentage: number;
  };
  message: string;
}

export interface ConceptCompleteEvent extends WebSocketEvent {
  type: 'concept_complete';
  concept_id: string;
  concept_name: string;
  data?: {
    tutorial_id?: string;
    content_url?: string;
    [key: string]: any;
  };
  message: string;
}

export interface ConceptFailedEvent extends WebSocketEvent {
  type: 'concept_failed';
  concept_id: string;
  concept_name: string;
  error: string;
  message: string;
}

export interface BatchStartEvent extends WebSocketEvent {
  type: 'batch_start';
  batch_index: number;
  batch_size: number;
  total_batches: number;
  concept_ids: string[];
  message: string;
}

export interface BatchCompleteEvent extends WebSocketEvent {
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
}

export interface CompletedEvent extends WebSocketEvent {
  type: 'completed';
  roadmap_id: string;
  tutorials_count?: number;
  failed_count?: number;
  message: string;
}

export interface FailedEvent extends WebSocketEvent {
  type: 'failed';
  error: string;
  step?: string;
  message: string;
}

export interface ClosingEvent extends WebSocketEvent {
  type: 'closing';
  reason: string;
  message: string;
}

export interface ErrorEvent extends WebSocketEvent {
  type: 'error';
  message: string;
}

/**
 * WebSocket 事件处理器
 */
export interface RoadmapWSHandlers {
  onConnected?: () => void;
  onCurrentStatus?: (event: CurrentStatusEvent) => void;
  onProgress?: (event: ProgressEvent) => void;
  onHumanReview?: (event: HumanReviewRequiredEvent) => void;
  onConceptStart?: (event: ConceptStartEvent) => void;
  onConceptComplete?: (event: ConceptCompleteEvent) => void;
  onConceptFailed?: (event: ConceptFailedEvent) => void;
  onBatchStart?: (event: BatchStartEvent) => void;
  onBatchComplete?: (event: BatchCompleteEvent) => void;
  onCompleted?: (event: CompletedEvent) => void;
  onFailed?: (event: FailedEvent) => void;
  onError?: (error: Error) => void;
  onClose?: (reason: string) => void;
}

/**
 * 路线图生成 WebSocket 客户端
 */
export class RoadmapWebSocket {
  private ws: WebSocket | null = null;
  private taskId: string;
  private handlers: RoadmapWSHandlers;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = WS_CONFIG.RECONNECT_MAX_ATTEMPTS;
  private heartbeatInterval: NodeJS.Timeout | null = null;

  constructor(taskId: string, handlers: RoadmapWSHandlers) {
    this.taskId = taskId;
    this.handlers = handlers;
  }

  /**
   * 连接 WebSocket
   */
  connect(includeHistory = true) {
    const wsUrl = WS_CONFIG.BASE_URL;
    const url = `${wsUrl}/ws/${this.taskId}?include_history=${includeHistory}`;
    
    try {
      logger.info(`Connecting to WebSocket: ${url}`);
      this.ws = new WebSocket(url);
      this.setupEventHandlers();
      this.startHeartbeat();
    } catch (error) {
      logger.error('Connection failed:', error);
      this.handlers.onError?.(error as Error);
    }
  }

  /**
   * 设置事件处理器
   */
  private setupEventHandlers() {
    if (!this.ws) return;

    this.ws.onopen = () => {
      logger.info('Connected to task:', this.taskId);
      this.reconnectAttempts = 0;
      this.handlers.onConnected?.();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        logger.error('Failed to parse message:', error);
      }
    };

    this.ws.onerror = (error) => {
      logger.error('WebSocket error:', error);
      this.handlers.onError?.(new Error('WebSocket connection error'));
    };

    this.ws.onclose = (event) => {
      logger.info('Connection closed:', event.code, event.reason);
      this.stopHeartbeat();
      
      const reason = event.reason || 'unknown';
      this.handlers.onClose?.(reason);
      
      // 仅在非正常关闭时重连
      if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnect();
      }
    };
  }

  /**
   * 处理消息
   */
  private handleMessage(data: any) {
    switch (data.type) {
      case 'connected':
        logger.debug('Connection confirmed');
        break;
        
      case 'current_status':
        this.handlers.onCurrentStatus?.(data as CurrentStatusEvent);
        break;
        
      case 'progress':
        this.handlers.onProgress?.(data as ProgressEvent);
        break;
        
      case 'human_review_required':
        this.handlers.onHumanReview?.(data as HumanReviewRequiredEvent);
        break;
        
      case 'concept_start':
        this.handlers.onConceptStart?.(data as ConceptStartEvent);
        break;
        
      case 'concept_complete':
        this.handlers.onConceptComplete?.(data as ConceptCompleteEvent);
        break;
        
      case 'concept_failed':
        this.handlers.onConceptFailed?.(data as ConceptFailedEvent);
        break;
        
      case 'batch_start':
        this.handlers.onBatchStart?.(data as BatchStartEvent);
        break;
        
      case 'batch_complete':
        this.handlers.onBatchComplete?.(data as BatchCompleteEvent);
        break;
        
      case 'completed':
        this.handlers.onCompleted?.(data as CompletedEvent);
        this.disconnect();
        break;
        
      case 'failed':
        this.handlers.onFailed?.(data as FailedEvent);
        this.disconnect();
        break;
        
      case 'closing':
        logger.info('Server closing connection:', data.reason);
        break;
        
      case 'pong':
        // 心跳响应
        break;
        
      default:
        logger.warn('Unknown message type:', data.type);
    }
  }

  /**
   * 开始心跳
   */
  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, WS_CONFIG.HEARTBEAT_INTERVAL);
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * 重连
   */
  private reconnect() {
    this.reconnectAttempts++;
    const delay = Math.min(
      WS_CONFIG.RECONNECT_DELAY_BASE * Math.pow(2, this.reconnectAttempts),
      WS_CONFIG.RECONNECT_DELAY_MAX
    );
    
    logger.info(
      `Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * 主动请求当前状态
   */
  requestStatus() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'get_status' }));
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
  }

  /**
   * 是否已连接
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

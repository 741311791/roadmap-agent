/**
 * 任务状态轮询客户端（WebSocket 降级方案）
 */

import { POLLING_CONFIG } from '@/lib/constants';
import { createLogger } from '@/lib/utils/logger';
import { roadmapsApi, type TaskStatusResponse } from '../endpoints/roadmaps';

const logger = createLogger('Polling');

/**
 * 轮询事件处理器
 */
export interface PollingHandlers {
  onStatusUpdate: (status: TaskStatusResponse) => void;
  onComplete: (status: TaskStatusResponse) => void;
  onError: (error: Error) => void;
}

/**
 * 任务轮询客户端
 */
export class TaskPolling {
  private taskId: string;
  private handlers: PollingHandlers;
  private intervalId: NodeJS.Timeout | null = null;
  private isRunning = false;

  constructor(taskId: string, handlers: PollingHandlers) {
    this.taskId = taskId;
    this.handlers = handlers;
  }

  /**
   * 开始轮询
   */
  start(intervalMs = POLLING_CONFIG.INTERVAL) {
    if (this.isRunning) {
      logger.warn('Already running');
      return;
    }

    logger.info('Started for task:', this.taskId);
    this.isRunning = true;

    this.intervalId = setInterval(async () => {
      try {
        const status = await roadmapsApi.getTaskStatus(this.taskId);
        this.handlers.onStatusUpdate(status);

        // 任务结束时自动停止
        if (status.status === 'completed' || status.status === 'failed') {
          this.handlers.onComplete(status);
          this.stop();
        }
      } catch (error) {
        logger.error('Error:', error);
        this.handlers.onError(error as Error);
      }
    }, intervalMs);
  }

  /**
   * 停止轮询
   */
  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
      this.isRunning = false;
      logger.info('Stopped');
    }
  }

  /**
   * 是否正在运行
   */
  running(): boolean {
    return this.isRunning;
  }
}

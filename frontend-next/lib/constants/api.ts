/**
 * API 相关常量
 */

/**
 * API 基础配置
 */
export const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  API_VERSION: 'v1',
  TIMEOUT: 180000, // 180秒 (3分钟) - 适应长时间内容生成任务（如教程、资源、测验生成）
} as const;

/**
 * API 端点前缀
 */
export const API_PREFIX = `${API_CONFIG.BASE_URL}/api/${API_CONFIG.API_VERSION}`;

/**
 * WebSocket 配置
 */
export const WS_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
  HEARTBEAT_INTERVAL: 30000, // 30秒
  RECONNECT_MAX_ATTEMPTS: 5,
  RECONNECT_DELAY_BASE: 1000, // 1秒
  RECONNECT_DELAY_MAX: 30000, // 30秒
} as const;

/**
 * 轮询配置
 */
export const POLLING_CONFIG = {
  INTERVAL: 2000, // 2秒
  MAX_RETRIES: 3,
} as const;

/**
 * 请求重试配置
 */
export const RETRY_CONFIG = {
  MAX_ATTEMPTS: 3,
  INITIAL_DELAY: 1000, // 1秒
  MAX_DELAY: 30000, // 30秒
  BACKOFF_MULTIPLIER: 2,
} as const;

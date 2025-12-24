/**
 * 重试拦截器
 * 自动重试失败的请求
 */

import type { AxiosInstance, AxiosError } from 'axios';
import { RETRY_CONFIG } from '@/lib/constants';
import { logger } from '@/lib/utils/logger';

/**
 * 延迟函数
 */
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * 计算退避延迟
 */
function calculateBackoff(attempt: number): number {
  const backoff = RETRY_CONFIG.INITIAL_DELAY * Math.pow(RETRY_CONFIG.BACKOFF_MULTIPLIER, attempt);
  return Math.min(backoff, RETRY_CONFIG.MAX_DELAY);
}

/**
 * 判断是否应该重试
 */
function shouldRetry(error: AxiosError): boolean {
  // 仅重试幂等请求 (GET, HEAD, OPTIONS, PUT, DELETE)
  const method = error.config?.method?.toUpperCase();
  if (!method || method === 'POST' || method === 'PATCH') {
    return false;
  }
  
  // 仅重试网络错误或 5xx 错误
  if (!error.response) {
    return true; // 网络错误
  }
  
  const status = error.response.status;
  return status >= 500 && status < 600;
}

/**
 * 添加重试拦截器
 */
export function retryInterceptor(axiosInstance: AxiosInstance): void {
  axiosInstance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const config = error.config as any;
      
      if (!config) {
        return Promise.reject(error);
      }
      
      // 初始化重试计数
      config._retryCount = config._retryCount || 0;
      
      // 检查是否应该重试
      if (!shouldRetry(error) || config._retryCount >= RETRY_CONFIG.MAX_ATTEMPTS) {
        return Promise.reject(error);
      }
      
      // 增加重试计数
      config._retryCount++;
      
      // 计算延迟
      const backoffDelay = calculateBackoff(config._retryCount - 1);
      
      logger.warn(
        `[API] 请求失败，${backoffDelay}ms 后重试 (${config._retryCount}/${RETRY_CONFIG.MAX_ATTEMPTS})`,
        error.config?.url
      );
      
      // 等待后重试
      await delay(backoffDelay);
      
      return axiosInstance.request(config);
    }
  );
}

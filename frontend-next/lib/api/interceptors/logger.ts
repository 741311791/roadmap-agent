/**
 * 日志拦截器（开发环境）
 * 记录请求和响应日志
 */

import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { logger } from '@/lib/utils/logger';

/**
 * 请求日志拦截器
 */
export function requestLoggerInterceptor(config: InternalAxiosRequestConfig) {
  if (process.env.NODE_ENV === 'development') {
    logger.debug('[API Request]', {
      method: config.method?.toUpperCase(),
      url: config.url,
      params: config.params,
      data: config.data,
    });
  }
  
  // 添加请求开始时间
  (config as any)._startTime = Date.now();
  
  return config;
}

/**
 * 响应日志拦截器
 */
export function responseLoggerInterceptor(response: AxiosResponse) {
  if (process.env.NODE_ENV === 'development') {
    const config = response.config as any;
    const duration = config._startTime ? Date.now() - config._startTime : 0;
    
    logger.debug('[API Response]', {
      method: config.method?.toUpperCase(),
      url: config.url,
      status: response.status,
      duration: `${duration}ms`,
      data: response.data,
    });
  }
  
  return response;
}

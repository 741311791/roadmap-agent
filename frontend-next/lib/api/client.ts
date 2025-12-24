/**
 * Axios API 客户端基础配置
 */

import axios, { type AxiosInstance } from 'axios';
import { API_CONFIG, API_PREFIX } from '@/lib/constants';
import {
  authInterceptor,
  errorInterceptor,
  retryInterceptor,
  requestLoggerInterceptor,
  responseLoggerInterceptor,
} from './interceptors';

/**
 * 创建 Axios 实例
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_PREFIX,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(authInterceptor);
apiClient.interceptors.request.use(requestLoggerInterceptor);

// 响应拦截器
apiClient.interceptors.response.use(
  responseLoggerInterceptor,
  errorInterceptor
);

// 重试拦截器
retryInterceptor(apiClient);

/**
 * 导出 API 配置
 */
export { API_PREFIX, API_CONFIG };

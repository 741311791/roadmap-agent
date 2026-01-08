/**
 * Axios API 客户端基础配置
 * 
 * 重构说明：
 * - ✅ 自动提取统一响应格式中的data字段
 * - ✅ 支持新的错误格式
 * - ✅ 兼容旧格式（过渡期）
 */

import axios, { type AxiosInstance, type AxiosResponse } from 'axios';
import { API_CONFIG, API_PREFIX } from '@/lib/constants';
import {
  authInterceptor,
  errorInterceptor,
  retryInterceptor,
  requestLoggerInterceptor,
  responseLoggerInterceptor,
} from './interceptors';
import type { APIResponse } from '@/types/custom/api-response';

/**
 * 响应数据提取拦截器
 * 
 * 自动从 {code, msg, data} 格式中提取 data 字段
 */
function extractDataInterceptor<T = any>(response: AxiosResponse<APIResponse<T> | T>): any {
  const { data } = response;
  
  // 新格式：{code, msg, data}
  if (data && typeof data === 'object' && 'code' in data && 'msg' in data && 'data' in data) {
    const apiResponse = data as APIResponse<T>;
    
    // 验证业务状态码
    if (apiResponse.code !== 200) {
      throw new Error(apiResponse.msg);
    }
    
    // 返回实际数据（自动提取data字段）
    response.data = apiResponse.data as any;
    return response;
  }
  
  // 旧格式：直接返回数据（兼容）
  return response;
}

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

// 响应拦截器（注意顺序：先提取data，再记录日志）
apiClient.interceptors.response.use(extractDataInterceptor);
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

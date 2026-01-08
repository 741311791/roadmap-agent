/**
 * 错误拦截器
 * 统一处理 API 错误
 * 
 * 重构说明：
 * - ✅ 支持新的错误格式 {error: {...}}
 * - ✅ 兼容旧格式 {detail: ...}（过渡期）
 * - ✅ 使用APIException统一错误类型
 */

import type { AxiosError } from 'axios';
import { logger } from '@/lib/utils/logger';
import { authService } from '@/lib/services/auth-service';
import { APIException, type APIError } from '@/types/custom/api-response';

/**
 * 错误响应接口（兼容旧格式）
 */
interface ErrorResponse {
  detail?: string;
  error_code?: string;
}

/**
 * 联合类型：新旧错误格式
 */
type ErrorResponseUnion = ErrorResponse | APIError;

/**
 * 错误拦截器
 * 
 * 处理 API 错误，特别是 401 未授权错误时自动登出并跳转到登录页。
 * 
 * 重构说明：
 * - ✅ 支持新的错误格式 {error: {...}}
 * - ✅ 自动转换为APIException
 * - ✅ 兼容旧格式（过渡期）
 */
export function errorInterceptor(error: AxiosError<ErrorResponseUnion>) {
  const { response, config } = error;
  
  // ========================================
  // 优化：检查是否为取消请求（AbortError）
  // ========================================
  if (error.name === 'AbortError' || error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
    // 请求被取消，不作为错误处理
    logger.debug('[API] Request cancelled');
    return Promise.reject(error);
  }
  
  if (!response) {
    // 网络错误
    logger.error('[API] Network connection failed', error);
    return Promise.reject(new Error('Network connection failed. Please check your internet connection.'));
  }
  
  const { status, data } = response;
  
  // ========================================
  // 新格式：{error: {...}}
  // ========================================
  if (data && 'error' in data) {
    const apiError = (data as APIError).error;
    
    logger.error('[API] Error', {
      code: apiError.code,
      message: apiError.message,
      request_id: apiError.request_id,
      status,
    });
    
    // 处理401未授权
    if (status === 401 || apiError.code === 'UNAUTHORIZED') {
      logger.error('[API] 未授权，请重新登录');
      authService.logout();
      
      if (typeof window !== 'undefined' && !config?.url?.includes('/auth/')) {
        const currentPath = window.location.pathname;
        if (currentPath !== '/login') {
          window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
        }
      }
    }
    
    // 转换为APIException并返回
    return Promise.reject(new APIException(apiError, status));
  }
  
  // ========================================
  // 旧格式兼容：{detail: ...}（过渡期）
  // ========================================
  const errorMessage = (data as ErrorResponse)?.detail || '未知错误';
  
  switch (status) {
    case 400:
      logger.error('[API] 请求参数错误:', errorMessage);
      break;
      
    case 401:
      logger.error('[API] 未授权，请重新登录');
      authService.logout();
      if (typeof window !== 'undefined' && !config?.url?.includes('/auth/')) {
        const currentPath = window.location.pathname;
        if (currentPath !== '/login') {
          window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
        }
      }
      break;
      
    case 403:
      logger.error('[API] 无权限访问');
      break;
      
    case 404:
      logger.error('[API] 资源不存在');
      break;
      
    case 422:
      logger.error('[API] 数据验证失败:', errorMessage);
      break;
      
    case 500:
      logger.error('[API] 服务器内部错误');
      break;
      
    case 503:
      logger.error('[API] 服务暂时不可用');
      break;
      
    default:
      logger.error('[API] 请求失败:', errorMessage);
  }
  
  return Promise.reject(error);
}

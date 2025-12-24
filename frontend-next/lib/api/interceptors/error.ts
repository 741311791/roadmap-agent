/**
 * 错误拦截器
 * 统一处理 API 错误
 */

import type { AxiosError } from 'axios';
import { logger } from '@/lib/utils/logger';
import { authService } from '@/lib/services/auth-service';

/**
 * 错误响应接口
 */
interface ErrorResponse {
  detail?: string;
  error_code?: string;
}

/**
 * 错误拦截器
 * 
 * 处理 API 错误，特别是 401 未授权错误时自动登出并跳转到登录页。
 */
export function errorInterceptor(error: AxiosError<ErrorResponse>) {
  const { response, config } = error;
  
  if (!response) {
    // 网络错误
    logger.error('[API] Network connection failed', error);
    return Promise.reject(new Error('Network connection failed. Please check your internet connection.'));
  }
  
  const { status, data } = response;
  const errorMessage = data?.detail || '未知错误';
  
  switch (status) {
    case 400:
      logger.error('[API] 请求参数错误:', errorMessage);
      break;
      
    case 401:
      logger.error('[API] 未授权，请重新登录');
      // 清除本地认证信息
      authService.logout();
      // 跳转到登录页（排除登录相关请求）
      if (typeof window !== 'undefined' && !config?.url?.includes('/auth/')) {
        const currentPath = window.location.pathname;
        // 避免在登录页重复跳转
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

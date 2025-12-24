/**
 * 认证拦截器
 * 自动添加 Bearer Token 和 User ID 到请求头
 */

import type { InternalAxiosRequestConfig } from 'axios';
import { authService } from '@/lib/services/auth-service';

/**
 * 认证拦截器
 * 
 * 自动从 authService 获取 JWT 令牌并添加到请求头。
 * 同时保持 x-user-id Header 以兼容旧版后端 API。
 */
export function authInterceptor(
  config: InternalAxiosRequestConfig
): InternalAxiosRequestConfig {
  // 添加追踪 ID
  const traceId = crypto.randomUUID();
  config.headers['X-Trace-ID'] = traceId;
  
  // 添加 JWT Bearer Token（优先）
  const token = authService.getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  // 同时添加 x-user-id Header（兼容旧版 API）
  const userId = authService.getCurrentUserId();
  if (userId) {
    config.headers['X-User-ID'] = userId;
  }
  
  return config;
}

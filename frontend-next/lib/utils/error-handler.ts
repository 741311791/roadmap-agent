/**
 * 统一错误处理工具
 * 
 * 提供一致的错误处理机制，利用APIException进行错误分类和用户友好提示
 */

import { toast } from 'sonner';
import { APIException } from '@/types/custom/api-response';

/**
 * API错误处理配置
 */
export interface ErrorHandlerOptions {
  /** 上下文描述（如"Roadmap"、"Tutorial"） */
  context?: string;
  /** 是否显示Toast提示 */
  showToast?: boolean;
  /** 自定义错误消息映射 */
  customMessages?: Partial<Record<string, string>>;
  /** 错误回调 */
  onError?: (error: unknown) => void;
}

/**
 * 统一错误处理函数
 * 
 * @param error - 错误对象
 * @param options - 处理选项
 * @returns 处理后的错误消息
 */
export function handleApiError(
  error: unknown,
  options: ErrorHandlerOptions = {}
): string {
  const {
    context,
    showToast = true,
    customMessages = {},
    onError,
  } = options;

  let errorMessage = 'An unknown error occurred';

  if (error instanceof APIException) {
    // 使用APIException的便捷方法
    if (error.isNotFound()) {
      errorMessage = customMessages.notFound || `${context || 'Resource'} not found`;
      if (showToast) toast.error(errorMessage);
    } else if (error.isUnauthorized()) {
      // 401已由拦截器处理（自动登出），此处仅记录
      errorMessage = customMessages.unauthorized || 'Please login to continue';
      if (showToast) toast.error(errorMessage);
    } else if (error.isForbidden()) {
      errorMessage = customMessages.forbidden || `You don't have permission to access ${context || 'this resource'}`;
      if (showToast) toast.error(errorMessage);
    } else if (error.isValidationError()) {
      errorMessage = customMessages.validation || `Validation failed: ${error.getUserMessage()}`;
      if (showToast) toast.error(errorMessage);
    } else if (error.isBadRequest()) {
      errorMessage = customMessages.badRequest || error.getUserMessage();
      if (showToast) toast.error(errorMessage);
    } else if (error.isServerError()) {
      errorMessage = customMessages.serverError || 'Server error occurred. Please try again later.';
      if (showToast) toast.error(errorMessage);
    } else {
      errorMessage = error.getUserMessage();
      if (showToast) toast.error(errorMessage);
    }
  } else if (error instanceof Error) {
    errorMessage = error.message;
    if (showToast) toast.error(errorMessage);
  } else if (typeof error === 'string') {
    errorMessage = error;
    if (showToast) toast.error(errorMessage);
  } else {
    if (showToast) toast.error(errorMessage);
  }

  // 执行自定义错误回调
  onError?.(error);

  // 记录错误日志（生产环境可发送到监控服务）
  console.error('[Error Handler]', {
    context,
    error,
    message: errorMessage,
  });

  return errorMessage;
}

/**
 * 异步操作错误处理装饰器
 * 
 * @param fn - 异步函数
 * @param options - 错误处理选项
 * @returns 包装后的函数
 */
export function withErrorHandler<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  options: ErrorHandlerOptions = {}
): T {
  return (async (...args: Parameters<T>): Promise<ReturnType<T>> => {
    try {
      return await fn(...args);
    } catch (error) {
      handleApiError(error, options);
      throw error;
    }
  }) as T;
}

/**
 * React组件错误处理Hook辅助函数
 * 
 * @param context - 错误上下文
 * @returns 错误处理函数
 */
export function useErrorHandler(context?: string) {
  return (error: unknown, showToast = true) => {
    return handleApiError(error, { context, showToast });
  };
}

/**
 * 错误消息国际化映射
 */
export const ERROR_MESSAGES = {
  // 网络错误
  NETWORK_ERROR: 'Network connection failed. Please check your internet connection.',
  TIMEOUT_ERROR: 'Request timeout. Please try again.',
  
  // 通用错误
  NOT_FOUND: 'The requested resource was not found.',
  UNAUTHORIZED: 'Please login to continue.',
  FORBIDDEN: 'You don\'t have permission to perform this action.',
  SERVER_ERROR: 'Server error occurred. Please try again later.',
  
  // 业务错误
  GENERATION_FAILED: 'Failed to generate roadmap. Please try again.',
  CONTENT_GENERATION_FAILED: 'Failed to generate content. Please try again.',
  MODIFICATION_FAILED: 'Failed to modify content. Please try again.',
  
  // 验证错误
  VALIDATION_ERROR: 'Validation failed. Please check your input.',
  INVALID_INPUT: 'Invalid input. Please check your data.',
} as const;

/**
 * 根据错误码获取友好消息
 * 
 * @param code - 错误码
 * @param fallback - 默认消息
 * @returns 友好的错误消息
 */
export function getErrorMessage(code: string, fallback?: string): string {
  return ERROR_MESSAGES[code as keyof typeof ERROR_MESSAGES] || fallback || code;
}

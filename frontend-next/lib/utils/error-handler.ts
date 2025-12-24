/**
 * Error Handling Utilities
 * Centralized error handling and user-friendly error messages
 */

export interface ApiError {
  status: number;
  message: string;
  url?: string;
  details?: unknown;
}

/**
 * Get user-friendly error message from error object
 */
export function getErrorMessage(error: unknown): string {
  if (typeof error === 'string') {
    return error;
  }

  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === 'object' && error !== null) {
    const apiError = error as ApiError;
    if (apiError.message) {
      return apiError.message;
    }
  }

  return '发生未知错误,请稍后重试';
}

/**
 * Check if error is a network error
 */
export function isNetworkError(error: unknown): boolean {
  if (typeof error === 'object' && error !== null) {
    const apiError = error as ApiError;
    return apiError.status === 0 || apiError.status >= 500;
  }
  return false;
}

/**
 * Check if error is a client error (4xx)
 */
export function isClientError(error: unknown): boolean {
  if (typeof error === 'object' && error !== null) {
    const apiError = error as ApiError;
    return apiError.status >= 400 && apiError.status < 500;
  }
  return false;
}

/**
 * Get error status code
 */
export function getErrorStatus(error: unknown): number {
  if (typeof error === 'object' && error !== null) {
    const apiError = error as ApiError;
    return apiError.status || 500;
  }
  return 500;
}

/**
 * Format error for logging
 */
export function formatErrorForLogging(error: unknown, context?: string): string {
  const message = getErrorMessage(error);
  const status = getErrorStatus(error);
  const contextStr = context ? `[${context}] ` : '';
  
  return `${contextStr}Error ${status}: ${message}`;
}

/**
 * Get user-friendly error title and description
 */
export function getErrorDisplay(error: unknown): {
  title: string;
  description: string;
  severity: 'error' | 'warning' | 'info';
} {
  const message = getErrorMessage(error);
  const status = getErrorStatus(error);

  if (isNetworkError(error)) {
    return {
      title: '网络错误',
      description: '无法连接到服务器,请检查网络连接或稍后重试',
      severity: 'error',
    };
  }

  if (status === 401 || status === 403) {
    return {
      title: '认证失败',
      description: '您没有权限访问此资源,请重新登录',
      severity: 'warning',
    };
  }

  if (status === 404) {
    return {
      title: '资源不存在',
      description: '请求的资源未找到',
      severity: 'warning',
    };
  }

  if (status === 429) {
    return {
      title: '请求过于频繁',
      description: '请稍候再试',
      severity: 'warning',
    };
  }

  if (status >= 500) {
    return {
      title: '服务器错误',
      description: '服务器处理请求时发生错误,请稍后重试',
      severity: 'error',
    };
  }

  return {
    title: '操作失败',
    description: message,
    severity: 'error',
  };
}

/**
 * Log error to console (can be extended to send to logging service)
 */
export function logError(error: unknown, context?: string): void {
  const logMessage = formatErrorForLogging(error, context);
  
  if (process.env.NEXT_PUBLIC_ENABLE_DEBUG === 'true') {
    console.error(logMessage, error);
  }
  
  // TODO: Send to logging service (e.g., Sentry, LogRocket)
  // if (typeof window !== 'undefined' && window.errorLogger) {
  //   window.errorLogger.log(error, context);
  // }
}

/**
 * Retry function with exponential backoff
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  initialDelay: number = 1000
): Promise<T> {
  let lastError: unknown;
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      
      // Don't retry on client errors
      if (isClientError(error)) {
        throw error;
      }
      
      if (attempt < maxRetries - 1) {
        const delay = initialDelay * Math.pow(2, attempt);
        console.log(`Retry attempt ${attempt + 1}/${maxRetries} after ${delay}ms`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  
  throw lastError;
}


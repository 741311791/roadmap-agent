/**
 * 统一API响应格式类型定义
 * 
 * 对应后端的ResponseSchemaModel[T]结构
 */

/**
 * 统一API响应格式
 * 
 * 所有后端API都返回此格式
 */
export interface APIResponse<T> {
  /** HTTP状态码 */
  code: number;
  /** 响应消息（用户友好） */
  msg: string;
  /** 响应数据（泛型） */
  data: T;
}

/**
 * 统一错误格式
 * 
 * 对应后端的ErrorResponse结构
 */
export interface APIError {
  error: {
    /** 错误码（枚举） */
    code: ErrorCode;
    /** 错误消息（用户友好） */
    message: string;
    /** 错误详情（可选） */
    details?: any;
    /** 请求ID（用于追踪） */
    request_id?: string;
    /** 错误发生时间（UTC） */
    timestamp: string;
    /** 调试信息（仅开发环境） */
    debug_info?: {
      exception_type: string;
      traceback: string;
    };
  };
}

/**
 * 后端错误码枚举
 */
export enum ErrorCode {
  // 客户端错误 (4xx)
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  NOT_FOUND = 'NOT_FOUND',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  BAD_REQUEST = 'BAD_REQUEST',
  CONFLICT = 'CONFLICT',
  
  // 服务器错误 (5xx)
  INTERNAL_SERVER_ERROR = 'INTERNAL_SERVER_ERROR',
  DATABASE_ERROR = 'DATABASE_ERROR',
  EXTERNAL_SERVICE_ERROR = 'EXTERNAL_SERVICE_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',
}

/**
 * API异常类
 * 
 * 封装后端返回的错误，提供便捷的错误类型判断方法
 */
export class APIException extends Error {
  /** 错误码 */
  code: ErrorCode;
  /** 错误详情 */
  details?: any;
  /** 请求ID */
  request_id?: string;
  /** HTTP状态码 */
  status: number;
  
  constructor(errorData: APIError['error'], status: number = 500) {
    super(errorData.message);
    this.name = 'APIException';
    this.code = errorData.code;
    this.details = errorData.details;
    this.request_id = errorData.request_id;
    this.status = status;
    
    // 保持正确的原型链
    Object.setPrototypeOf(this, APIException.prototype);
  }
  
  /**
   * 是否为资源不存在错误
   */
  isNotFound(): boolean {
    return this.code === ErrorCode.NOT_FOUND;
  }
  
  /**
   * 是否为未授权错误
   */
  isUnauthorized(): boolean {
    return this.code === ErrorCode.UNAUTHORIZED;
  }
  
  /**
   * 是否为权限不足错误
   */
  isForbidden(): boolean {
    return this.code === ErrorCode.FORBIDDEN;
  }
  
  /**
   * 是否为参数错误
   */
  isBadRequest(): boolean {
    return this.code === ErrorCode.BAD_REQUEST;
  }
  
  /**
   * 是否为验证错误
   */
  isValidationError(): boolean {
    return this.code === ErrorCode.VALIDATION_ERROR;
  }
  
  /**
   * 是否为服务器错误
   */
  isServerError(): boolean {
    return this.status >= 500;
  }
  
  /**
   * 获取用户友好的错误消息
   */
  getUserMessage(): string {
    // 根据错误码返回更友好的中文消息
    const messages: Record<ErrorCode, string> = {
      [ErrorCode.NOT_FOUND]: '请求的资源不存在',
      [ErrorCode.BAD_REQUEST]: '请求参数错误，请检查输入',
      [ErrorCode.UNAUTHORIZED]: '您尚未登录，请先登录',
      [ErrorCode.FORBIDDEN]: '您没有权限执行此操作',
      [ErrorCode.VALIDATION_ERROR]: '数据验证失败，请检查输入',
      [ErrorCode.CONFLICT]: '资源已存在或发生冲突',
      [ErrorCode.INTERNAL_SERVER_ERROR]: '服务器内部错误，请稍后重试',
      [ErrorCode.DATABASE_ERROR]: '数据库操作失败，请稍后重试',
      [ErrorCode.EXTERNAL_SERVICE_ERROR]: '外部服务调用失败，请稍后重试',
      [ErrorCode.TIMEOUT_ERROR]: '请求超时，请稍后重试',
    };
    
    return messages[this.code] || this.message;
  }
}


/**
 * 常量统一导出
 */

export * from './status';
export * from './api';
export * from './routes';

/**
 * 通用常量
 */
export const CONSTANTS = {
  // 应用信息
  APP_NAME: 'Learning Roadmap',
  APP_DESCRIPTION: 'AI-powered personalized learning roadmap generator',
  APP_VERSION: '2.0.0',
  
  // 默认值
  DEFAULT_TIMEOUT: 30000,
  DEFAULT_POLLING_INTERVAL: 2000,
  DEFAULT_PAGE_SIZE: 10,
  
  // 限制
  MAX_ROADMAP_TITLE_LENGTH: 100,
  MAX_CONCEPT_TITLE_LENGTH: 50,
  MAX_DESCRIPTION_LENGTH: 500,
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  
  // 缓存键
  CACHE_KEYS: {
    USER_PROFILE: 'user_profile',
    ROADMAP_LIST: 'roadmap_list',
    CURRENT_ROADMAP: 'current_roadmap',
    PREFERENCES: 'preferences',
  },
  
  // LocalStorage 键
  STORAGE_KEYS: {
    TOKEN: 'auth_token',
    USER_ID: 'user_id',
    LAST_VISITED: 'last_visited',
    THEME: 'theme',
  },
} as const;

/**
 * 错误码
 */
export const ERROR_CODES = {
  // 通用错误
  UNKNOWN_ERROR: 'UNKNOWN_ERROR',
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT_ERROR: 'TIMEOUT_ERROR',
  
  // 认证错误
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  TOKEN_EXPIRED: 'TOKEN_EXPIRED',
  
  // 资源错误
  NOT_FOUND: 'NOT_FOUND',
  TASK_NOT_FOUND: 'TASK_NOT_FOUND',
  ROADMAP_NOT_FOUND: 'ROADMAP_NOT_FOUND',
  
  // 验证错误
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  INVALID_TASK_STATUS: 'INVALID_TASK_STATUS',
  
  // 业务错误
  CONTENT_GENERATION_FAILED: 'CONTENT_GENERATION_FAILED',
  LLM_API_ERROR: 'LLM_API_ERROR',
  DATABASE_ERROR: 'DATABASE_ERROR',
} as const;

/**
 * HTTP 状态码
 */
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  UNPROCESSABLE_ENTITY: 422,
  INTERNAL_SERVER_ERROR: 500,
  SERVICE_UNAVAILABLE: 503,
} as const;

/**
 * 错误消息映射
 */
export const ERROR_MESSAGES: Record<string, string> = {
  [ERROR_CODES.UNKNOWN_ERROR]: '发生未知错误',
  [ERROR_CODES.NETWORK_ERROR]: '网络连接失败，请检查网络',
  [ERROR_CODES.TIMEOUT_ERROR]: '请求超时，请重试',
  [ERROR_CODES.UNAUTHORIZED]: '请先登录',
  [ERROR_CODES.FORBIDDEN]: '权限不足',
  [ERROR_CODES.TOKEN_EXPIRED]: '登录已过期，请重新登录',
  [ERROR_CODES.NOT_FOUND]: '资源不存在',
  [ERROR_CODES.TASK_NOT_FOUND]: '任务不存在，请重新生成',
  [ERROR_CODES.ROADMAP_NOT_FOUND]: '路线图不存在',
  [ERROR_CODES.VALIDATION_ERROR]: '输入数据有误',
  [ERROR_CODES.INVALID_TASK_STATUS]: '任务状态不允许此操作',
  [ERROR_CODES.CONTENT_GENERATION_FAILED]: '内容生成失败',
  [ERROR_CODES.LLM_API_ERROR]: '服务暂时繁忙，请稍后重试',
  [ERROR_CODES.DATABASE_ERROR]: '系统错误，请联系客服',
};

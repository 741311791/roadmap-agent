/**
 * 统一响应格式类型定义
 * 
 * 对应后端 backend/app/core/response_schema.py
 * 
 * ⚠️ WARNING: 请勿手动修改此文件
 * 
 * Generated at: 2026-01-16
 */

/**
 * 通用响应模型
 * 
 * 所有 API 响应都遵循此格式:
 * {
 *   "code": 200,
 *   "msg": "Success",
 *   "data": { ... }
 * }
 */
export interface ResponseModel<T = any> {
  /**
   * HTTP 状态码
   */
  code: number;
  
  /**
   * 响应消息 (用户友好)
   */
  msg: string;
  
  /**
   * 响应数据
   */
  data?: T | null;
}

/**
 * 响应码常量
 */
export const ResponseCode = {
  // 成功响应 (2xx)
  OK: 200,
  CREATED: 201,
  ACCEPTED: 202,
  NO_CONTENT: 204,
  
  // 客户端错误 (4xx)
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  
  // 服务器错误 (5xx)
  INTERNAL_SERVER_ERROR: 500,
  SERVICE_UNAVAILABLE: 503,
} as const;

/**
 * 响应码类型
 */
export type ResponseCodeType = typeof ResponseCode[keyof typeof ResponseCode];

/**
 * 响应消息映射
 */
export const ResponseMessages: Record<ResponseCodeType, string> = {
  200: "操作成功",
  201: "创建成功",
  202: "请求已接受",
  204: "无内容",
  400: "请求参数错误",
  401: "未授权",
  403: "权限不足",
  404: "资源不存在",
  409: "资源冲突",
  422: "数据验证失败",
  500: "服务器内部错误",
  503: "服务暂时不可用",
};

/**
 * 成功响应类型守卫
 */
export function isSuccessResponse<T>(response: ResponseModel<T>): response is ResponseModel<T> & { data: T } {
  return response.code >= 200 && response.code < 300 && response.data !== null && response.data !== undefined;
}

/**
 * 错误响应类型守卫
 */
export function isErrorResponse<T>(response: ResponseModel<T>): boolean {
  return response.code >= 400;
}

/**
 * 提取响应数据 (带类型安全)
 */
export function extractResponseData<T>(response: ResponseModel<T>): T {
  if (!isSuccessResponse(response)) {
    throw new Error(response.msg || '请求失败');
  }
  return response.data;
}

/**
 * 常用响应类型别名
 */

// 分页响应
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// 列表响应
export interface ListResponse<T> {
  items: T[];
  total: number;
}

// 详情响应
export type DetailResponse<T> = T;

// 创建响应
export interface CreateResponse {
  id: string;
  [key: string]: any;
}

// 更新响应
export interface UpdateResponse {
  success: boolean;
  message?: string;
}

// 删除响应
export interface DeleteResponse {
  success: boolean;
  message?: string;
}


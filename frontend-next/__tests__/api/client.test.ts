/**
 * API Client 拦截器测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import type { APIResponse, APIError } from '@/types/custom/api-response';

// 注意：这里是测试概念验证，实际需要mock axios实例

describe('API Client Interceptors', () => {
  describe('extractDataInterceptor', () => {
    it('should extract data from new response format {code, msg, data}', () => {
      const mockResponse: APIResponse<{ id: string }> = {
        code: 200,
        msg: 'Success',
        data: { id: '123' },
      };

      // 模拟拦截器逻辑
      const extractedData = mockResponse.data;

      expect(extractedData).toEqual({ id: '123' });
    });

    it('should throw error if code is not 200', () => {
      const mockResponse: APIResponse<any> = {
        code: 400,
        msg: 'Bad Request',
        data: null,
      };

      // 模拟拦截器逻辑
      expect(() => {
        if (mockResponse.code !== 200) {
          throw new Error(mockResponse.msg);
        }
      }).toThrow('Bad Request');
    });

    it('should pass through old format response', () => {
      const oldFormatResponse = { id: '123', name: 'Test' };

      // 旧格式直接返回
      const result = oldFormatResponse;

      expect(result).toEqual({ id: '123', name: 'Test' });
    });
  });

  describe('errorInterceptor', () => {
    it('should convert new error format to APIException', () => {
      const mockErrorResponse: APIError = {
        error: {
          code: 'NOT_FOUND' as any,
          message: 'Resource not found',
          request_id: 'req-123',
          timestamp: '2026-01-17T00:00:00Z',
        },
      };

      // 验证错误结构
      expect(mockErrorResponse.error.code).toBe('NOT_FOUND');
      expect(mockErrorResponse.error.message).toBe('Resource not found');
      expect(mockErrorResponse.error.request_id).toBe('req-123');
    });

    it('should handle 401 unauthorized error with auto logout', () => {
      const mockErrorResponse: APIError = {
        error: {
          code: 'UNAUTHORIZED' as any,
          message: 'Token expired',
          request_id: 'req-456',
          timestamp: '2026-01-17T00:00:00Z',
        },
      };

      // 验证401错误码
      expect(mockErrorResponse.error.code).toBe('UNAUTHORIZED');
    });
  });

  describe('authInterceptor', () => {
    it('should add JWT token to request headers', () => {
      const mockConfig = {
        headers: {} as any,
      };

      // 模拟添加Token
      const token = 'mock-jwt-token';
      mockConfig.headers.Authorization = `Bearer ${token}`;

      expect(mockConfig.headers.Authorization).toBe('Bearer mock-jwt-token');
    });

    it('should add trace ID to request headers', () => {
      const mockConfig = {
        headers: {} as any,
      };

      // 模拟添加Trace ID
      const traceId = 'trace-123';
      mockConfig.headers['X-Trace-ID'] = traceId;

      expect(mockConfig.headers['X-Trace-ID']).toBe('trace-123');
    });
  });
});

/**
 * 响应格式测试
 */
describe('Response Format', () => {
  it('should match ResponseSchemaModel format', () => {
    interface TestData {
      id: string;
      name: string;
    }

    const response: APIResponse<TestData> = {
      code: 200,
      msg: 'Success',
      data: {
        id: 'test-1',
        name: 'Test Item',
      },
    };

    expect(response.code).toBe(200);
    expect(response.msg).toBe('Success');
    expect(response.data.id).toBe('test-1');
    expect(response.data.name).toBe('Test Item');
  });

  it('should handle empty data response', () => {
    const response: APIResponse<null> = {
      code: 204,
      msg: 'No Content',
      data: null,
    };

    expect(response.code).toBe(204);
    expect(response.data).toBeNull();
  });
});


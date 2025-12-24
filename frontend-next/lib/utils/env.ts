/**
 * 类型化环境变量工具
 * 
 * 提供类型安全的环境变量访问
 * 在应用启动时验证环境变量
 */

import { z } from 'zod';

/**
 * 环境变量 Schema 定义
 */
const envSchema = z.object({
  // API 配置
  NEXT_PUBLIC_API_URL: z
    .string()
    .url('Invalid API URL')
    .default('http://localhost:8000'),
  
  NEXT_PUBLIC_WS_URL: z
    .string()
    .url('Invalid WebSocket URL')
    .optional()
    .transform(val => val || undefined),
  
  // 环境类型
  NEXT_PUBLIC_ENV: z
    .enum(['development', 'staging', 'production'])
    .default('development'),
  
  // 功能开关
  NEXT_PUBLIC_ENABLE_SSE: z
    .string()
    .default('true')
    .transform(val => val === 'true')
    .pipe(z.boolean()),
  
  NEXT_PUBLIC_ENABLE_WEBSOCKET: z
    .string()
    .default('true')
    .transform(val => val === 'true')
    .pipe(z.boolean()),
  
  NEXT_PUBLIC_ENABLE_POLLING_FALLBACK: z
    .string()
    .default('true')
    .transform(val => val === 'true')
    .pipe(z.boolean()),
  
  // 调试选项
  NEXT_PUBLIC_DEBUG: z
    .string()
    .default('false')
    .transform(val => val === 'true')
    .pipe(z.boolean()),
  
  NEXT_PUBLIC_LOG_LEVEL: z
    .enum(['debug', 'info', 'warn', 'error'])
    .default('info'),
});

/**
 * 环境变量类型
 */
export type Env = z.infer<typeof envSchema>;

/**
 * 解析环境变量
 */
function parseEnv(): Env {
  try {
    return envSchema.parse({
      NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
      NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL,
      NEXT_PUBLIC_ENV: process.env.NEXT_PUBLIC_ENV,
      NEXT_PUBLIC_ENABLE_SSE: process.env.NEXT_PUBLIC_ENABLE_SSE,
      NEXT_PUBLIC_ENABLE_WEBSOCKET: process.env.NEXT_PUBLIC_ENABLE_WEBSOCKET,
      NEXT_PUBLIC_ENABLE_POLLING_FALLBACK: process.env.NEXT_PUBLIC_ENABLE_POLLING_FALLBACK,
      NEXT_PUBLIC_DEBUG: process.env.NEXT_PUBLIC_DEBUG,
      NEXT_PUBLIC_LOG_LEVEL: process.env.NEXT_PUBLIC_LOG_LEVEL,
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error('❌ Environment variable validation failed:');
      error.issues.forEach(err => {
        console.error(`  • ${err.path.join('.')}: ${err.message}`);
      });
      throw new Error('Invalid environment variables');
    }
    throw error;
  }
}

/**
 * 导出类型化的环境变量
 * 
 * 使用示例:
 * ```ts
 * import { env } from '@/lib/utils/env';
 * 
 * const apiUrl = env.NEXT_PUBLIC_API_URL;
 * ```
 */
export const env = parseEnv();

/**
 * 检查是否为开发环境
 */
export const isDevelopment = env.NEXT_PUBLIC_ENV === 'development';

/**
 * 检查是否为生产环境
 */
export const isProduction = env.NEXT_PUBLIC_ENV === 'production';

/**
 * 检查是否为测试环境
 */
export const isStaging = env.NEXT_PUBLIC_ENV === 'staging';

/**
 * API 基础 URL
 */
export const API_BASE_URL = env.NEXT_PUBLIC_API_URL;

/**
 * WebSocket URL (自动从 API URL 推断)
 */
export const WS_URL = 
  env.NEXT_PUBLIC_WS_URL || 
  env.NEXT_PUBLIC_API_URL.replace(/^http/, 'ws');

/**
 * 功能开关
 */
export const features = {
  sse: env.NEXT_PUBLIC_ENABLE_SSE,
  websocket: env.NEXT_PUBLIC_ENABLE_WEBSOCKET,
  pollingFallback: env.NEXT_PUBLIC_ENABLE_POLLING_FALLBACK,
} as const;

/**
 * 调试配置
 */
export const debug = {
  enabled: env.NEXT_PUBLIC_DEBUG,
  logLevel: env.NEXT_PUBLIC_LOG_LEVEL,
} as const;

/**
 * 日志工具函数
 */
export const logger = {
  debug: (...args: any[]) => {
    if (debug.enabled && debug.logLevel === 'debug') {
      console.debug('[DEBUG]', ...args);
    }
  },
  info: (...args: any[]) => {
    if (debug.enabled && ['debug', 'info'].includes(debug.logLevel)) {
      console.info('[INFO]', ...args);
    }
  },
  warn: (...args: any[]) => {
    if (debug.enabled && ['debug', 'info', 'warn'].includes(debug.logLevel)) {
      console.warn('[WARN]', ...args);
    }
  },
  error: (...args: any[]) => {
    console.error('[ERROR]', ...args);
  },
};

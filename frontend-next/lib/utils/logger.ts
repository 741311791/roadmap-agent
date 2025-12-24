/**
 * 日志工具
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

class Logger {
  private prefix: string;

  constructor(prefix: string = '') {
    this.prefix = prefix;
  }

  private log(level: LogLevel, ...args: any[]) {
    const timestamp = new Date().toISOString();
    const fullPrefix = this.prefix ? `[${this.prefix}]` : '';
    
    // 仅在开发环境打印日志
    if (process.env.NODE_ENV === 'development') {
      console[level](`[${timestamp}]${fullPrefix}`, ...args);
    }
  }

  debug(...args: any[]) {
    this.log('debug', ...args);
  }

  info(...args: any[]) {
    this.log('info', ...args);
  }

  warn(...args: any[]) {
    this.log('warn', ...args);
  }

  error(...args: any[]) {
    this.log('error', ...args);
  }
}

/**
 * 创建 Logger 实例
 */
export function createLogger(prefix: string): Logger {
  return new Logger(prefix);
}

/**
 * 默认 Logger
 */
export const logger = new Logger();

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  formatDateTime,
  formatRelativeTime,
  formatDuration,
  truncate,
} from '@/lib/utils/format';

describe('格式化工具函数', () => {
  beforeEach(() => {
    // 设置固定时区为 Asia/Shanghai
    vi.setSystemTime(new Date('2024-01-15T10:00:00.000Z'));
  });

  describe('formatDateTime', () => {
    it('应该正确格式化日期字符串', () => {
      const date = '2024-01-15T08:30:00.000Z';
      const result = formatDateTime(date);
      expect(result).toMatch(/2024/);
      expect(result).toMatch(/01/);
      expect(result).toMatch(/15/);
    });

    it('应该正确格式化 Date 对象', () => {
      const date = new Date('2024-01-15T08:30:00.000Z');
      const result = formatDateTime(date);
      expect(result).toMatch(/2024/);
      expect(result).toMatch(/01/);
      expect(result).toMatch(/15/);
    });
  });

  describe('formatRelativeTime', () => {
    it('应该返回"刚刚"对于几秒前的时间', () => {
      const date = new Date(Date.now() - 5000); // 5秒前
      expect(formatRelativeTime(date)).toBe('刚刚');
    });

    it('应该返回分钟数对于几分钟前的时间', () => {
      const date = new Date(Date.now() - 5 * 60 * 1000); // 5分钟前
      expect(formatRelativeTime(date)).toBe('5分钟前');
    });

    it('应该返回小时数对于几小时前的时间', () => {
      const date = new Date(Date.now() - 3 * 60 * 60 * 1000); // 3小时前
      expect(formatRelativeTime(date)).toBe('3小时前');
    });

    it('应该返回天数对于几天前的时间', () => {
      const date = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000); // 2天前
      expect(formatRelativeTime(date)).toBe('2天前');
    });
  });

  describe('formatDuration', () => {
    it('应该正确格式化秒', () => {
      expect(formatDuration(30)).toBe('30秒');
    });

    it('应该正确格式化分钟', () => {
      expect(formatDuration(120)).toBe('2分钟');
      expect(formatDuration(300)).toBe('5分钟');
    });

    it('应该正确格式化小时', () => {
      expect(formatDuration(3600)).toBe('1小时');
      expect(formatDuration(7200)).toBe('2小时');
    });

    it('应该正确格式化小时和分钟组合', () => {
      expect(formatDuration(3660)).toBe('1小时1分钟');
      expect(formatDuration(5400)).toBe('1小时30分钟');
    });
  });

  describe('truncate', () => {
    it('应该不截断短于最大长度的文本', () => {
      const text = 'Hello World';
      expect(truncate(text, 20)).toBe('Hello World');
    });

    it('应该截断超过最大长度的文本并添加省略号', () => {
      const text = 'This is a very long text that needs to be truncated';
      const result = truncate(text, 20);
      expect(result).toBe('This is a very long ...');
      expect(result.length).toBe(23); // 20 + '...'
    });

    it('应该处理正好等于最大长度的文本', () => {
      const text = '12345678901234567890';
      expect(truncate(text, 20)).toBe('12345678901234567890');
    });
  });
});


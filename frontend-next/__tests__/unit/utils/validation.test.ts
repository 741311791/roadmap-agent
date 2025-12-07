import { describe, it, expect } from 'vitest';
import {
  isValidEmail,
  isValidUrl,
  isEmpty,
  isLengthValid,
} from '@/lib/utils/validation';

describe('验证工具函数', () => {
  describe('isValidEmail', () => {
    it('应该验证有效的邮箱地址', () => {
      expect(isValidEmail('test@example.com')).toBe(true);
      expect(isValidEmail('user.name@example.co.uk')).toBe(true);
      expect(isValidEmail('user+tag@example.com')).toBe(true);
    });

    it('应该拒绝无效的邮箱地址', () => {
      expect(isValidEmail('invalid')).toBe(false);
      expect(isValidEmail('invalid@')).toBe(false);
      expect(isValidEmail('@example.com')).toBe(false);
      expect(isValidEmail('user@')).toBe(false);
      expect(isValidEmail('')).toBe(false);
    });
  });

  describe('isValidUrl', () => {
    it('应该验证有效的 URL', () => {
      expect(isValidUrl('https://example.com')).toBe(true);
      expect(isValidUrl('http://example.com')).toBe(true);
      expect(isValidUrl('https://example.com/path?query=1')).toBe(true);
      expect(isValidUrl('ftp://example.com')).toBe(true);
    });

    it('应该拒绝无效的 URL', () => {
      expect(isValidUrl('not a url')).toBe(false);
      expect(isValidUrl('example.com')).toBe(false);
      expect(isValidUrl('')).toBe(false);
      expect(isValidUrl('//example.com')).toBe(false);
    });
  });

  describe('isEmpty', () => {
    it('应该检测空字符串', () => {
      expect(isEmpty('')).toBe(true);
      expect(isEmpty('   ')).toBe(true);
      expect(isEmpty(null)).toBe(true);
      expect(isEmpty(undefined)).toBe(true);
    });

    it('应该检测非空字符串', () => {
      expect(isEmpty('hello')).toBe(false);
      expect(isEmpty('  hello  ')).toBe(false);
      expect(isEmpty('0')).toBe(false);
    });
  });

  describe('isLengthValid', () => {
    it('应该验证字符串长度在范围内', () => {
      expect(isLengthValid('hello', 1, 10)).toBe(true);
      expect(isLengthValid('hello', 5, 5)).toBe(true);
      expect(isLengthValid('   hello   ', 5, 5)).toBe(true); // trim后为5
    });

    it('应该拒绝字符串长度超出范围', () => {
      expect(isLengthValid('hi', 5, 10)).toBe(false);
      expect(isLengthValid('this is a very long text', 1, 10)).toBe(false);
    });

    it('应该处理边界情况', () => {
      expect(isLengthValid('hello', 5, 10)).toBe(true); // min边界
      expect(isLengthValid('hello world', 5, 11)).toBe(true); // max边界
    });
  });
});


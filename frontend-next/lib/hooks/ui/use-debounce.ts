/**
 * useDebounce - 防抖 Hook
 * 
 * 延迟更新值,直到指定时间内没有新的值变化
 * 
 * @param value - 要防抖的值
 * @param delay - 延迟时间 (毫秒)
 * @returns 防抖后的值
 */

import { useEffect, useState } from 'react';

export function useDebounce<T>(value: T, delay: number = 500): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

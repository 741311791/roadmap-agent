/**
 * useThrottle - 节流 Hook
 * 
 * 限制函数调用频率,确保在指定时间内最多执行一次
 * 
 * @param value - 要节流的值
 * @param limit - 时间限制 (毫秒)
 * @returns 节流后的值
 */

import { useEffect, useRef, useState } from 'react';

export function useThrottle<T>(value: T, limit: number = 500): T {
  const [throttledValue, setThrottledValue] = useState<T>(value);
  const lastRan = useRef<number>(Date.now());

  useEffect(() => {
    const handler = setTimeout(() => {
      if (Date.now() - lastRan.current >= limit) {
        setThrottledValue(value);
        lastRan.current = Date.now();
      }
    }, limit - (Date.now() - lastRan.current));

    return () => {
      clearTimeout(handler);
    };
  }, [value, limit]);

  return throttledValue;
}

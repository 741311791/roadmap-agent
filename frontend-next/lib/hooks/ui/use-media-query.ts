/**
 * useMediaQuery - 响应式断点 Hook
 * 
 * 检测媒体查询是否匹配
 * 
 * @param query - 媒体查询字符串
 * @returns 是否匹配
 */

import { useEffect, useState } from 'react';

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    
    // 初始值
    setMatches(media.matches);

    // 监听变化
    const listener = (e: MediaQueryListEvent) => {
      setMatches(e.matches);
    };

    // 添加监听器
    media.addEventListener('change', listener);

    return () => {
      media.removeEventListener('change', listener);
    };
  }, [query]);

  return matches;
}

/**
 * 常用的响应式断点 Hooks
 */

export function useIsMobile() {
  return useMediaQuery('(max-width: 768px)');
}

export function useIsTablet() {
  return useMediaQuery('(min-width: 769px) and (max-width: 1024px)');
}

export function useIsDesktop() {
  return useMediaQuery('(min-width: 1025px)');
}

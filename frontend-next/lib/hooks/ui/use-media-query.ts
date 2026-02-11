/**
 * useMediaQuery - 响应式断点 Hook
 * 
 * 检测媒体查询是否匹配
 * 支持服务端渲染（SSR）和客户端渲染（CSR）
 * 
 * @param query - 媒体查询字符串
 * @returns 是否匹配
 * 
 * @example
 * const isMobile = useMediaQuery('(max-width: 767px)');
 * const isWideScreen = useMediaQuery('(min-width: 1920px)');
 */

import { useEffect, useState } from 'react';

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    // SSR 保护
    if (typeof window === 'undefined') return;

    const media = window.matchMedia(query);
    
    // 初始值
    setMatches(media.matches);

    // 监听变化
    const listener = (e: MediaQueryListEvent) => {
      setMatches(e.matches);
    };

    // 添加监听器（兼容旧版浏览器）
    if (media.addEventListener) {
      media.addEventListener('change', listener);
    } else {
      // @ts-ignore - 兼容 Safari < 14
      media.addListener(listener);
    }

    return () => {
      if (media.removeEventListener) {
        media.removeEventListener('change', listener);
      } else {
        // @ts-ignore - 兼容 Safari < 14
        media.removeListener(listener);
      }
    };
  }, [query]);

  return matches;
}

/**
 * 预定义的响应式断点 Hooks
 * 
 * 断点系统（与 Tailwind CSS 保持一致）：
 * - mobile: < 768px
 * - tablet: 768px - 1023px
 * - desktop: >= 1024px
 * - wide: >= 1920px
 */

export function useIsMobile(): boolean {
  return useMediaQuery('(max-width: 767px)');
}

export function useIsTablet(): boolean {
  return useMediaQuery('(min-width: 768px) and (max-width: 1023px)');
}

export function useIsDesktop(): boolean {
  return useMediaQuery('(min-width: 1024px)');
}

export function useIsWide(): boolean {
  return useMediaQuery('(min-width: 1920px)');
}

/**
 * 组合 Hook：获取当前设备类型
 */
export type DeviceType = 'mobile' | 'tablet' | 'desktop' | 'wide';

export function useDeviceType(): DeviceType {
  const isMobile = useIsMobile();
  const isTablet = useIsTablet();
  const isWide = useIsWide();

  if (isMobile) return 'mobile';
  if (isTablet) return 'tablet';
  if (isWide) return 'wide';
  return 'desktop';
}

/**
 * 检测是否为触摸设备
 */
export function useIsTouchDevice(): boolean {
  const [isTouch, setIsTouch] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const checkTouch = () => {
      setIsTouch(
        'ontouchstart' in window ||
        navigator.maxTouchPoints > 0 ||
        // @ts-ignore
        navigator.msMaxTouchPoints > 0
      );
    };

    checkTouch();
    window.addEventListener('resize', checkTouch);

    return () => window.removeEventListener('resize', checkTouch);
  }, []);

  return isTouch;
}

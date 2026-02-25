/**
 * useBreakpoint Hook
 * 
 * 基于 Tailwind CSS 断点系统的响应式 Hook
 * 提供更详细的断点信息和窗口尺寸
 * 
 * @example
 * const { isMobile, isTablet, isDesktop, width, currentBreakpoint } = useBreakpoint();
 * 
 * if (isMobile) {
 *   return <MobileView />;
 * } else if (isTablet) {
 *   return <TabletView />;
 * } else {
 *   return <DesktopView />;
 * }
 */

import { useState, useEffect } from 'react';

// Tailwind CSS 默认断点（与 tailwind.config.ts 保持一致）
export const breakpoints = {
  sm: 640,    // 手机横屏
  md: 768,    // 平板竖屏
  lg: 1024,   // 平板横屏 / 小桌面
  xl: 1280,   // 桌面
  '2xl': 1536, // 大桌面
} as const;

export type Breakpoint = keyof typeof breakpoints;

export interface BreakpointState {
  /** 当前窗口宽度 */
  width: number;
  /** 当前窗口高度 */
  height: number;
  /** >= 640px */
  isSm: boolean;
  /** >= 768px */
  isMd: boolean;
  /** >= 1024px */
  isLg: boolean;
  /** >= 1280px */
  isXl: boolean;
  /** >= 1536px */
  is2Xl: boolean;
  /** < 768px（手机）*/
  isMobile: boolean;
  /** >= 768px and < 1024px（平板）*/
  isTablet: boolean;
  /** >= 1024px（桌面）*/
  isDesktop: boolean;
  /** >= 1920px（宽屏）*/
  isWide: boolean;
  /** 当前断点 */
  currentBreakpoint: Breakpoint | 'xs';
}

function getBreakpointState(width: number, height: number): BreakpointState {
  return {
    width,
    height,
    isSm: width >= breakpoints.sm,
    isMd: width >= breakpoints.md,
    isLg: width >= breakpoints.lg,
    isXl: width >= breakpoints.xl,
    is2Xl: width >= breakpoints['2xl'],
    isMobile: width < breakpoints.md,
    isTablet: width >= breakpoints.md && width < breakpoints.lg,
    isDesktop: width >= breakpoints.lg,
    isWide: width >= 1920,
    currentBreakpoint: getCurrentBreakpoint(width),
  };
}

function getCurrentBreakpoint(width: number): Breakpoint | 'xs' {
  if (width >= breakpoints['2xl']) return '2xl';
  if (width >= breakpoints.xl) return 'xl';
  if (width >= breakpoints.lg) return 'lg';
  if (width >= breakpoints.md) return 'md';
  if (width >= breakpoints.sm) return 'sm';
  return 'xs';
}

export function useBreakpoint(): BreakpointState {
  const [state, setState] = useState<BreakpointState>(() => {
    if (typeof window === 'undefined') {
      // SSR 默认值（桌面端，避免闪烁）
      return getBreakpointState(1024, 768);
    }
    return getBreakpointState(window.innerWidth, window.innerHeight);
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleResize = () => {
      setState(getBreakpointState(window.innerWidth, window.innerHeight));
    };

    // 初始化
    handleResize();

    // 监听窗口变化
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return state;
}

/**
 * 简化版：根据断点返回不同的值
 * 
 * @example
 * const columns = useBreakpointValue({
 *   xs: 1,
 *   sm: 2,
 *   md: 3,
 *   lg: 4,
 *   default: 1,
 * });
 */
export function useBreakpointValue<T>(values: {
  xs?: T;
  sm?: T;
  md?: T;
  lg?: T;
  xl?: T;
  '2xl'?: T;
  default: T;
}): T {
  const { currentBreakpoint } = useBreakpoint();
  return values[currentBreakpoint] ?? values.default;
}

/**
 * 检测屏幕方向
 */
export type Orientation = 'portrait' | 'landscape';

export function useOrientation(): Orientation {
  const [orientation, setOrientation] = useState<Orientation>('portrait');

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleOrientationChange = () => {
      setOrientation(
        window.innerHeight > window.innerWidth ? 'portrait' : 'landscape'
      );
    };

    handleOrientationChange();
    window.addEventListener('resize', handleOrientationChange);

    return () => {
      window.removeEventListener('resize', handleOrientationChange);
    };
  }, []);

  return orientation;
}

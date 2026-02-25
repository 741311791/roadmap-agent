/**
 * 响应式工具函数
 * 
 * 提供响应式设计相关的工具函数和类名生成器
 */

import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * 响应式类名生成器
 * 
 * @example
 * responsiveClasses({
 *   base: 'p-4',
 *   sm: 'p-6',
 *   md: 'p-8',
 *   lg: 'p-10',
 * })
 * // 输出: 'p-4 sm:p-6 md:p-8 lg:p-10'
 */
export function responsiveClasses(classes: {
  base?: ClassValue;
  sm?: ClassValue;
  md?: ClassValue;
  lg?: ClassValue;
  xl?: ClassValue;
  '2xl'?: ClassValue;
}): string {
  const { base, sm, md, lg, xl, '2xl': xxl } = classes;

  return twMerge(
    clsx(
      base,
      sm && `sm:${sm}`,
      md && `md:${md}`,
      lg && `lg:${lg}`,
      xl && `xl:${xl}`,
      xxl && `2xl:${xxl}`
    )
  );
}

/**
 * 容器宽度类名
 * 根据设计系统生成统一的容器宽度
 */
export const containerClasses = {
  // 全宽容器（带padding）
  fullWidth: 'w-full px-4 sm:px-6 md:px-8 lg:px-12 xl:px-16',
  
  // 内容容器（居中，最大宽度）
  content: 'w-full max-w-7xl mx-auto px-4 sm:px-6 md:px-8 lg:px-12',
  
  // 窄容器（文章、表单）
  narrow: 'w-full max-w-3xl mx-auto px-4 sm:px-6 md:px-8',
  
  // 宽容器（仪表盘、列表）
  wide: 'w-full max-w-[1920px] mx-auto px-4 sm:px-6 md:px-8 lg:px-12 xl:px-16',
} as const;

/**
 * 网格布局类名
 */
export const gridClasses = {
  // 卡片网格（自适应列数）
  cards: 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-6 lg:gap-8',
  
  // 双列网格
  twoColumns: 'grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 lg:gap-8',
  
  // 侧边栏布局（主内容区 + 侧边栏）
  sidebar: 'grid grid-cols-1 lg:grid-cols-[1fr_300px] xl:grid-cols-[1fr_360px] gap-4 md:gap-6 lg:gap-8',
  
  // 反向侧边栏（侧边栏 + 主内容区）
  sidebarReverse: 'grid grid-cols-1 lg:grid-cols-[300px_1fr] xl:grid-cols-[360px_1fr] gap-4 md:gap-6 lg:gap-8',
} as const;

/**
 * 间距系统
 */
export const spacingClasses = {
  // 垂直间距
  sectionY: 'py-8 md:py-12 lg:py-16 xl:py-20',
  contentY: 'py-6 md:py-8 lg:py-10',
  
  // 水平间距
  sectionX: 'px-4 sm:px-6 md:px-8 lg:px-12 xl:px-16',
  contentX: 'px-4 md:px-6 lg:px-8',
  
  // 元素间距
  stack: 'space-y-4 md:space-y-6 lg:space-y-8',
  inline: 'space-x-2 md:space-x-3 lg:space-x-4',
} as const;

/**
 * 字体大小响应式类名
 */
export const typographyClasses = {
  // 标题
  h1: 'text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-serif font-semibold',
  h2: 'text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-serif font-semibold',
  h3: 'text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-serif font-medium',
  h4: 'text-xl sm:text-2xl md:text-3xl font-serif font-medium',
  h5: 'text-lg sm:text-xl md:text-2xl font-sans font-semibold',
  h6: 'text-base sm:text-lg md:text-xl font-sans font-semibold',
  
  // 正文
  body: 'text-sm sm:text-base md:text-lg',
  bodyLarge: 'text-base sm:text-lg md:text-xl',
  bodySmall: 'text-xs sm:text-sm md:text-base',
  
  // 引用
  quote: 'text-lg sm:text-xl md:text-2xl font-serif italic',
  
  // 代码
  code: 'text-xs sm:text-sm md:text-base font-mono',
} as const;

/**
 * 检测是否为移动设备（仅客户端）
 */
export function isMobileDevice(): boolean {
  if (typeof window === 'undefined') return false;
  
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  );
}

/**
 * 获取视口尺寸
 */
export function getViewportSize(): { width: number; height: number } {
  if (typeof window === 'undefined') {
    return { width: 1024, height: 768 };
  }
  
  return {
    width: window.innerWidth,
    height: window.innerHeight,
  };
}

/**
 * 生成响应式图片 srcSet
 */
export function generateSrcSet(
  baseUrl: string,
  widths: number[] = [640, 768, 1024, 1280, 1536]
): string {
  return widths
    .map((width) => `${baseUrl}?w=${width} ${width}w`)
    .join(', ');
}

/**
 * 响应式值选择器（基于断点）
 */
export function getResponsiveValue<T>(
  values: {
    xs?: T;
    sm?: T;
    md?: T;
    lg?: T;
    xl?: T;
    '2xl'?: T;
  },
  width: number,
  defaultValue: T
): T {
  if (width >= 1536 && values['2xl'] !== undefined) return values['2xl'];
  if (width >= 1280 && values.xl !== undefined) return values.xl;
  if (width >= 1024 && values.lg !== undefined) return values.lg;
  if (width >= 768 && values.md !== undefined) return values.md;
  if (width >= 640 && values.sm !== undefined) return values.sm;
  if (values.xs !== undefined) return values.xs;
  return defaultValue;
}

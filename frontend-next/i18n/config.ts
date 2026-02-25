/**
 * i18n 配置
 * 
 * 定义支持的语言和浏览器语言检测逻辑
 */

export const locales = ['en', 'zh'] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = 'en';

/**
 * 浏览器语言检测
 * 
 * @returns 检测到的语言（中文或英文）
 */
export function detectBrowserLocale(): Locale {
  if (typeof window === 'undefined') return defaultLocale;
  
  const browserLang = navigator.language.toLowerCase();
  if (browserLang.startsWith('zh')) return 'zh';
  return 'en';
}

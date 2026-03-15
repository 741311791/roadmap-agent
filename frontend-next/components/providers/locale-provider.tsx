'use client';

/**
 * Locale Provider
 * 
 * 纯客户端语言管理Provider
 * 支持浏览器语言自动检测和localStorage持久化
 */

import { createContext, useContext, useEffect, useMemo, useState, ReactNode } from 'react';
import { NextIntlClientProvider } from 'next-intl';
import { useUIStore } from '@/lib/store/ui-store';
import { defaultTimeZone, detectBrowserLocale } from '@/i18n/config';
import enMessages from '@/messages/en.json';
import zhMessages from '@/messages/zh.json';

type Locale = 'en' | 'zh';
type LocaleMessages = typeof enMessages;

const LOCALE_MESSAGES: Record<Locale, LocaleMessages> = {
  en: enMessages,
  zh: zhMessages,
};

type LocaleContextType = {
  locale: Locale;
  setLocale: (locale: Locale) => Promise<void>;
};

const LocaleContext = createContext<LocaleContextType | undefined>(undefined);

export function useLocaleContext() {
  const context = useContext(LocaleContext);
  if (!context) {
    throw new Error('useLocaleContext must be used within LocaleProvider');
  }
  return context;
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const { locale: storeLocale, setLocale: setStoreLocale } = useUIStore();
  const [locale, setLocaleState] = useState<Locale>(() => storeLocale || 'en');

  const messages = useMemo(() => LOCALE_MESSAGES[locale], [locale]);

  // 说明：
  // 为了避免根布局在 hydration 前被整页 loading 阻塞，这里默认同步渲染英文包，
  // 再在客户端挂载后根据 localStorage / 浏览器语言切换到目标语言。
  useEffect(() => {
    const savedLocale = localStorage.getItem('locale') as Locale | null;
    const initialLocale = savedLocale || detectBrowserLocale();
    setLocaleState(initialLocale);
    setStoreLocale(initialLocale);
    document.cookie = `NEXT_LOCALE=${initialLocale}; path=/; max-age=31536000`;
  }, [setStoreLocale]);

  const setLocale = async (newLocale: Locale) => {
    setLocaleState(newLocale);
    setStoreLocale(newLocale);
    localStorage.setItem('locale', newLocale);
    document.cookie = `NEXT_LOCALE=${newLocale}; path=/; max-age=31536000`;
  };

  return (
    <LocaleContext.Provider value={{ locale, setLocale }}>
      <NextIntlClientProvider
        locale={locale}
        messages={messages}
        timeZone={defaultTimeZone}
      >
        {children}
      </NextIntlClientProvider>
    </LocaleContext.Provider>
  );
}

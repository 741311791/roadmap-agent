'use client';

/**
 * Locale Provider
 * 
 * 纯客户端语言管理Provider
 * 支持浏览器语言自动检测和localStorage持久化
 */

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { NextIntlClientProvider } from 'next-intl';
import { useUIStore } from '@/lib/store/ui-store';
import { detectBrowserLocale } from '@/i18n/config';

type LocaleContextType = {
  locale: 'en' | 'zh';
  setLocale: (locale: 'en' | 'zh') => void;
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
  const [locale, setLocaleState] = useState<'en' | 'zh'>('en');
  const [messages, setMessages] = useState<any>(null);
  const [isReady, setIsReady] = useState(false);

  // 初始化locale
  useEffect(() => {
    const initializeLocale = async () => {
      // 优先级：localStorage > 浏览器语言 > 默认en
      const savedLocale = localStorage.getItem('locale') as 'en' | 'zh' | null;
      const initialLocale = savedLocale || detectBrowserLocale();
      
      // 加载对应语言的翻译文件
      const localeMessages = await import(`@/messages/${initialLocale}.json`);
      
      setLocaleState(initialLocale);
      setStoreLocale(initialLocale);
      setMessages(localeMessages.default);
      
      // 设置cookie供服务端使用
      document.cookie = `NEXT_LOCALE=${initialLocale}; path=/; max-age=31536000`;
      
      setIsReady(true);
    };

    initializeLocale();
  }, []);

  const setLocale = async (newLocale: 'en' | 'zh') => {
    // 加载新语言的翻译文件
    const localeMessages = await import(`@/messages/${newLocale}.json`);
    
    // 更新状态
    setLocaleState(newLocale);
    setStoreLocale(newLocale);
    setMessages(localeMessages.default);
    
    // 持久化到localStorage和cookie
    localStorage.setItem('locale', newLocale);
    document.cookie = `NEXT_LOCALE=${newLocale}; path=/; max-age=31536000`;
  };

  // 等待初始化完成
  if (!isReady || !messages) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-sage-200 border-t-sage-600 rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <LocaleContext.Provider value={{ locale, setLocale }}>
      <NextIntlClientProvider locale={locale} messages={messages}>
        {children}
      </NextIntlClientProvider>
    </LocaleContext.Provider>
  );
}

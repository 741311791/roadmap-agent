'use client';

/**
 * 语言切换组件
 * 
 * 提供两种样式：
 * - default: 下拉选择器（用于Settings页面）
 * - compact: 紧凑按钮（用于Header和Sidebar）
 */

import { useLocaleContext } from '@/components/providers/locale-provider';
import { Globe } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const languages = [
  { code: 'en', label: 'English', nativeLabel: 'English' },
  { code: 'zh', label: 'Chinese', nativeLabel: '简体中文' },
] as const;

export function LanguageSwitcher({ variant = 'default' }: { variant?: 'default' | 'compact' }) {
  const { locale, setLocale } = useLocaleContext();

  const handleChange = async (newLocale: 'en' | 'zh') => {
    await setLocale(newLocale);
  };

  if (variant === 'compact') {
    return (
      <button
        onClick={() => handleChange(locale === 'en' ? 'zh' : 'en')}
        className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-primary/5 transition-colors"
        title="Switch language"
      >
        <Globe size={16} className="text-foreground/60" />
        <span className="text-sm font-medium">
          {locale === 'en' ? 'EN' : '中'}
        </span>
      </button>
    );
  }

  return (
    <Select value={locale} onValueChange={handleChange}>
      <SelectTrigger className="w-[180px]">
        <div className="flex items-center gap-2">
          <Globe size={16} />
          <SelectValue />
        </div>
      </SelectTrigger>
      <SelectContent>
        {languages.map((lang) => (
          <SelectItem key={lang.code} value={lang.code}>
            {lang.nativeLabel}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

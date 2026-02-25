'use client';

/**
 * 应用设置页面
 * 
 * 提供应用级别的设置选项，包括语言、主题、显示偏好等
 */

import { useTranslations } from 'next-intl';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Languages, Sun, Moon, Monitor, Check } from 'lucide-react';
import { useLocaleContext } from '@/components/providers/locale-provider';
import { cn } from '@/lib/utils';

export default function AppSettingsPage() {
  const t = useTranslations('appSettings');
  const { locale, setLocale } = useLocaleContext();

  const handleLanguageChange = async (newLocale: 'en' | 'zh') => {
    await setLocale(newLocale);
  };

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-serif font-bold text-foreground">{t('title')}</h1>
        <p className="text-muted-foreground mt-2">
          {t('description')}
        </p>
      </div>

      <div className="space-y-6">
        {/* Language Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Languages className="w-5 h-5 text-sage-600" />
              {t('language')}
            </CardTitle>
            <CardDescription>
              {t('languageDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => handleLanguageChange('en')}
                className={cn(
                  "group relative p-4 rounded-lg border-2 text-left transition-all",
                  locale === 'en'
                    ? "border-sage-600 bg-sage-50"
                    : "border-border hover:border-sage-300 hover:bg-sage-50/50"
                )}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-sm">English</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {t('interfaceInEnglish')}
                    </div>
                  </div>
                  {locale === 'en' && (
                    <div className="w-5 h-5 rounded-full bg-sage-600 flex items-center justify-center">
                      <Check className="w-3 h-3 text-white" />
                    </div>
                  )}
                </div>
              </button>

              <button
                onClick={() => handleLanguageChange('zh')}
                className={cn(
                  "group relative p-4 rounded-lg border-2 text-left transition-all",
                  locale === 'zh'
                    ? "border-sage-600 bg-sage-50"
                    : "border-border hover:border-sage-300 hover:bg-sage-50/50"
                )}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-sm">简体中文</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {t('interfaceInChinese')}
                    </div>
                  </div>
                  {locale === 'zh' && (
                    <div className="w-5 h-5 rounded-full bg-sage-600 flex items-center justify-center">
                      <Check className="w-3 h-3 text-white" />
                    </div>
                  )}
                </div>
              </button>
            </div>
          </CardContent>
        </Card>

        {/* Appearance Section */}
        <Card className="opacity-60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sun className="w-5 h-5 text-muted-foreground" />
              {t('appearance')}
            </CardTitle>
            <CardDescription>
              {t('appearanceDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Theme */}
            <div>
              <label className="block text-sm font-medium mb-3 text-muted-foreground">
                {t('theme')}
              </label>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { value: 'light', label: t('theme'), icon: Sun, color: 'text-muted-foreground' },
                  { value: 'dark', label: t('theme'), icon: Moon, color: 'text-muted-foreground' },
                  { value: 'system', label: t('theme'), icon: Monitor, color: 'text-muted-foreground' }
                ].map((themeOption, index) => {
                  const Icon = themeOption.icon;
                  const labels = ['Light', 'Dark', 'System'];
                  return (
                    <button
                      key={themeOption.value}
                      disabled
                      className={cn(
                        "p-4 rounded-lg border-2 text-center cursor-not-allowed",
                        "border-border bg-muted/30"
                      )}
                    >
                      <Icon className={cn("w-6 h-6 mx-auto mb-2", themeOption.color)} />
                      <div className="text-sm font-medium text-muted-foreground">{labels[index]}</div>
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-muted-foreground mt-3 italic">
                ⚠️ {t('featureInDevelopment')}
              </p>
            </div>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}

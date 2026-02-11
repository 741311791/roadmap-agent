'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { User, Bell, Palette, Shield, LogOut } from 'lucide-react';
import { LanguageSwitcher } from '@/components/language-switcher';

export default function SettingsPage() {
  const t = useTranslations('settings');
  const [notifications, setNotifications] = useState({
    email: true,
    progress: true,
    recommendations: false,
  });

  return (
    <div className="max-w-3xl mx-auto py-12 px-6">
      <div className="mb-8">
        <h1 className="text-3xl font-serif font-bold text-foreground">{t('title')}</h1>
        <p className="text-muted-foreground mt-1">
          {t('description')}
        </p>
      </div>

      <div className="space-y-6">
        {/* Profile Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <User className="w-5 h-5 text-sage-600" />
              {t('profile')}
            </CardTitle>
            <CardDescription>{t('profileDesc')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-sage-200 flex items-center justify-center text-foreground font-bold text-xl">
                L
              </div>
              <div>
                <div className="font-medium text-lg">Learner</div>
                <div className="text-sm text-muted-foreground">learner@example.com</div>
                <Badge variant="sage" className="mt-1">{t('freePlan')}</Badge>
              </div>
            </div>
            <Separator />
            <div className="grid gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{t('displayName')}</label>
                <input
                  type="text"
                  defaultValue="Learner"
                  className="w-full p-3 rounded-lg border border-input bg-background"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t('email')}</label>
                <input
                  type="email"
                  defaultValue="learner@example.com"
                  className="w-full p-3 rounded-lg border border-input bg-background"
                />
              </div>
            </div>
            <Button variant="sage">{t('saveChanges')}</Button>
          </CardContent>
        </Card>

        {/* Notifications Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Bell className="w-5 h-5 text-sage-600" />
              {t('notifications')}
            </CardTitle>
            <CardDescription>{t('notificationsDesc')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">{t('emailNotifications')}</div>
                <div className="text-sm text-muted-foreground">
                  {t('emailNotificationsDesc')}
                </div>
              </div>
              <button
                onClick={() => setNotifications(prev => ({ ...prev, email: !prev.email }))}
                className={`w-12 h-6 rounded-full transition-colors ${
                  notifications.email ? 'bg-sage-600' : 'bg-muted'
                }`}
              >
                <div
                  className={`w-5 h-5 rounded-full bg-white shadow transition-transform ${
                    notifications.email ? 'translate-x-6' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">{t('progressReminders')}</div>
                <div className="text-sm text-muted-foreground">
                  {t('progressRemindersDesc')}
                </div>
              </div>
              <button
                onClick={() => setNotifications(prev => ({ ...prev, progress: !prev.progress }))}
                className={`w-12 h-6 rounded-full transition-colors ${
                  notifications.progress ? 'bg-sage-600' : 'bg-muted'
                }`}
              >
                <div
                  className={`w-5 h-5 rounded-full bg-white shadow transition-transform ${
                    notifications.progress ? 'translate-x-6' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">{t('contentRecommendations')}</div>
                <div className="text-sm text-muted-foreground">
                  {t('contentRecommendationsDesc')}
                </div>
              </div>
              <button
                onClick={() => setNotifications(prev => ({ ...prev, recommendations: !prev.recommendations }))}
                className={`w-12 h-6 rounded-full transition-colors ${
                  notifications.recommendations ? 'bg-sage-600' : 'bg-muted'
                }`}
              >
                <div
                  className={`w-5 h-5 rounded-full bg-white shadow transition-transform ${
                    notifications.recommendations ? 'translate-x-6' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>
          </CardContent>
        </Card>

        {/* Appearance Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Palette className="w-5 h-5 text-sage-600" />
              {t('appearance')}
            </CardTitle>
            <CardDescription>{t('appearanceDesc')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Theme */}
            <div>
              <label className="block text-sm font-medium mb-2">{t('theme')}</label>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { value: 'light', label: t('light') },
                  { value: 'dark', label: t('dark') },
                  { value: 'system', label: t('system') }
                ].map((theme) => (
                  <button
                    key={theme.value}
                    className={`p-4 rounded-lg border text-center capitalize ${
                      theme.value === 'light'
                        ? 'border-sage-600 bg-sage-50'
                        : 'border-border hover:border-sage-300'
                    }`}
                  >
                    {theme.label}
                  </button>
                ))}
              </div>
            </div>

            <Separator />

            {/* Language */}
            <div>
              <label className="block text-sm font-medium mb-2">
                {t('language')}
              </label>
              <p className="text-xs text-muted-foreground mb-3">
                {t('languageDesc')}
              </p>
              <LanguageSwitcher variant="default" />
            </div>
          </CardContent>
        </Card>

        {/* Account Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Shield className="w-5 h-5 text-sage-600" />
              {t('account')}
            </CardTitle>
            <CardDescription>{t('accountDesc')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button variant="outline" className="w-full justify-start gap-2">
              {t('changePassword')}
            </Button>
            <Button variant="outline" className="w-full justify-start gap-2 text-destructive hover:text-destructive">
              <LogOut className="w-4 h-4" />
              {t('signOut')}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}












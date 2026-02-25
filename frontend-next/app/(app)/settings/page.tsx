'use client';

import { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import Avatar, { genConfig, type AvatarFullConfig } from 'react-nice-avatar';
import { Shuffle, Save, Eye, EyeOff, User, KeyRound, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/lib/store/auth-store';
import { usersApi } from '@/lib/api/endpoints/users';

/** 保存状态类型 */
type SaveStatus = 'idle' | 'saving' | 'success' | 'error';

/**
 * 账户设置页面
 *
 * 提供三项核心功能：
 * 1. 头像编辑 —— 基于 react-nice-avatar 随机生成并持久化 JSON 配置
 * 2. 用户名编辑
 * 3. 密码修改
 */
export default function SettingsPage() {
  const t = useTranslations('accountSettings');
  const { user, updateUser } = useAuthStore();

  // ---------- 头像状态 ----------
  // 若数据库中已有配置则使用，否则根据 email 生成确定性初始头像
  const initialAvatarConfig = (user?.avatar_config as AvatarFullConfig | null | undefined)
    ?? genConfig(user?.email ?? '');
  const [avatarConfig, setAvatarConfig] = useState<AvatarFullConfig>(initialAvatarConfig);
  const [avatarStatus, setAvatarStatus] = useState<SaveStatus>('idle');

  // ---------- 用户名状态 ----------
  const [username, setUsername] = useState(user?.username ?? '');
  const [usernameStatus, setUsernameStatus] = useState<SaveStatus>('idle');

  // ---------- 密码状态 ----------
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordStatus, setPasswordStatus] = useState<SaveStatus>('idle');
  const [passwordError, setPasswordError] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  /** 随机生成新头像配置 */
  const handleRandomAvatar = useCallback(() => {
    setAvatarConfig(genConfig());
    // 重置保存状态，提示用户记得保存
    setAvatarStatus('idle');
  }, []);

  /** 保存头像配置到后端，并立即同步到 store（左下角头像实时更新） */
  const handleSaveAvatar = useCallback(async () => {
    setAvatarStatus('saving');
    try {
      const updated = await usersApi.updateCurrentUser({
        avatar_config: avatarConfig as Record<string, unknown>,
      });
      // 用 API 返回值直接更新 store + localStorage，无需再次 GET /users/me
      updateUser(updated);
      setAvatarStatus('success');
      setTimeout(() => setAvatarStatus('idle'), 2000);
    } catch {
      setAvatarStatus('error');
      setTimeout(() => setAvatarStatus('idle'), 3000);
    }
  }, [avatarConfig, updateUser]);

  /** 保存用户名到后端，并立即同步到 store（左下角用户名实时更新） */
  const handleSaveUsername = useCallback(async () => {
    if (!username.trim()) return;
    setUsernameStatus('saving');
    try {
      const updated = await usersApi.updateCurrentUser({ username: username.trim() });
      updateUser(updated);
      setUsernameStatus('success');
      setTimeout(() => setUsernameStatus('idle'), 2000);
    } catch {
      setUsernameStatus('error');
      setTimeout(() => setUsernameStatus('idle'), 3000);
    }
  }, [username, updateUser]);

  /** 修改密码 */
  const handleSavePassword = useCallback(async () => {
    setPasswordError('');

    if (!newPassword) {
      setPasswordError(t('passwordRequired'));
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError(t('passwordMinLength'));
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError(t('passwordMismatch'));
      return;
    }

    setPasswordStatus('saving');
    try {
      await usersApi.updateCurrentUser({ password: newPassword });
      setPasswordStatus('success');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setPasswordStatus('idle'), 2000);
    } catch {
      setPasswordStatus('error');
      setPasswordError(t('passwordUpdateFailed'));
      setTimeout(() => setPasswordStatus('idle'), 3000);
    }
  }, [newPassword, confirmPassword, t]);

  if (!user) return null;

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">{t('pageTitle')}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {t('pageDescription')}
        </p>
      </div>

      {/* ───── 头像编辑区 ───── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <User className="w-4 h-4" />
            {t('avatar')}
          </CardTitle>
          <CardDescription>
            {t('avatarDesc')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row items-center gap-6">
            {/* 头像预览 */}
            <div className="shrink-0">
              <Avatar
                className="w-28 h-28 rounded-full ring-2 ring-border"
                {...avatarConfig}
              />
            </div>

            <div className="flex flex-col gap-3 flex-1">
              <p className="text-sm text-muted-foreground">
                {t('avatarHint')}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRandomAvatar}
                  disabled={avatarStatus === 'saving'}
                >
                  <Shuffle className="w-4 h-4 mr-2" />
                  {t('random')}
                </Button>
                <SaveButton
                  status={avatarStatus}
                  onClick={handleSaveAvatar}
                  label={t('saveAvatar')}
                  savingLabel={t('saving')}
                  savedLabel={t('saved')}
                  failedLabel={t('failed')}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ───── 用户名编辑区 ───── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <User className="w-4 h-4" />
            {t('username')}
          </CardTitle>
          <CardDescription>{t('usernameDesc')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="username">{t('username')}</Label>
              <div className="flex gap-2">
                <Input
                  id="username"
                  value={username}
                  onChange={(e) => {
                    setUsername(e.target.value);
                    setUsernameStatus('idle');
                  }}
                  placeholder={t('usernamePlaceholder')}
                  className="max-w-sm"
                  disabled={usernameStatus === 'saving'}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSaveUsername();
                  }}
                />
                <SaveButton
                  status={usernameStatus}
                  onClick={handleSaveUsername}
                  label={t('save')}
                  savingLabel={t('saving')}
                  savedLabel={t('saved')}
                  failedLabel={t('failed')}
                  disabled={!username.trim() || username.trim() === user.username}
                />
              </div>
              {usernameStatus === 'error' && (
                <StatusMessage type="error" message={t('usernameUpdateFailed')} />
              )}
            </div>
            <div className="text-xs text-muted-foreground">
              {t('currentUsername')} <span className="font-medium text-foreground">{user.username}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ───── 密码修改区 ───── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <KeyRound className="w-4 h-4" />
            {t('changePassword')}
          </CardTitle>
          <CardDescription>
            {t('changePasswordDesc')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4 max-w-sm">
            {/* 当前密码（仅作 UX 提示，后端验证 JWT 身份） */}
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="current-password">{t('currentPassword')}</Label>
              <div className="relative">
                <Input
                  id="current-password"
                  type={showCurrentPassword ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder={t('currentPasswordPlaceholder')}
                  disabled={passwordStatus === 'saving'}
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  tabIndex={-1}
                >
                  {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* 新密码 */}
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="new-password">{t('newPassword')}</Label>
              <div className="relative">
                <Input
                  id="new-password"
                  type={showNewPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => {
                    setNewPassword(e.target.value);
                    setPasswordError('');
                  }}
                  placeholder={t('newPasswordPlaceholder')}
                  disabled={passwordStatus === 'saving'}
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  tabIndex={-1}
                >
                  {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* 确认新密码 */}
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="confirm-password">{t('confirmPassword')}</Label>
              <div className="relative">
                <Input
                  id="confirm-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    setPasswordError('');
                  }}
                  placeholder={t('confirmPasswordPlaceholder')}
                  disabled={passwordStatus === 'saving'}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSavePassword();
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  tabIndex={-1}
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* 错误提示 */}
            {passwordError && (
              <StatusMessage type="error" message={passwordError} />
            )}

            <SaveButton
              status={passwordStatus}
              onClick={handleSavePassword}
              label={t('updatePassword')}
              savingLabel={t('saving')}
              savedLabel={t('saved')}
              failedLabel={t('failed')}
              disabled={!newPassword || !confirmPassword}
              className="self-start"
            />
          </div>
        </CardContent>
      </Card>

      {/* 账户信息（只读） */}
      <Card className="bg-muted/30">
        <CardContent className="pt-6">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">{t('email')}</span>
              <p className="font-medium mt-0.5">{user.email}</p>
            </div>
            <div>
              <span className="text-muted-foreground">{t('accountCreated')}</span>
              <p className="font-medium mt-0.5">
                {user.created_at
                  ? new Date(user.created_at).toLocaleDateString()
                  : '—'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/* ─────────────────────────────────────────────────────── */
/*  小型辅助组件                                           */
/* ─────────────────────────────────────────────────────── */

interface SaveButtonProps {
  status: SaveStatus;
  onClick: () => void;
  label: string;
  savingLabel?: string;
  savedLabel?: string;
  failedLabel?: string;
  disabled?: boolean;
  className?: string;
}

/**
 * 带保存状态反馈的按钮
 *
 * idle → 默认样式；saving → 旋转加载；success → 绿色勾；error → 红色 X
 */
function SaveButton({
  status,
  onClick,
  label,
  savingLabel = 'Saving…',
  savedLabel = 'Saved!',
  failedLabel = 'Failed',
  disabled,
  className,
}: SaveButtonProps) {
  const isDisabled = disabled || status === 'saving';

  return (
    <Button
      size="sm"
      onClick={onClick}
      disabled={isDisabled}
      className={cn(
        'transition-colors',
        status === 'success' && 'bg-green-600 hover:bg-green-600 text-white',
        status === 'error' && 'bg-red-600 hover:bg-red-600 text-white',
        className
      )}
    >
      {status === 'saving' && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
      {status === 'success' && <CheckCircle2 className="w-4 h-4 mr-2" />}
      {status === 'error' && <AlertCircle className="w-4 h-4 mr-2" />}
      {status === 'idle' && <Save className="w-4 h-4 mr-2" />}
      {status === 'saving' ? savingLabel : status === 'success' ? savedLabel : status === 'error' ? failedLabel : label}
    </Button>
  );
}

interface StatusMessageProps {
  type: 'error' | 'success';
  message: string;
}

/**
 * 状态提示文字组件
 */
function StatusMessage({ type, message }: StatusMessageProps) {
  return (
    <p className={cn(
      'text-xs flex items-center gap-1',
      type === 'error' ? 'text-red-600' : 'text-green-600'
    )}>
      {type === 'error'
        ? <AlertCircle className="w-3 h-3" />
        : <CheckCircle2 className="w-3 h-3" />}
      {message}
    </p>
  );
}

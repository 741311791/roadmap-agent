/**
 * 用户菜单组件
 *
 * 显示当前登录用户信息，提供登出功能。
 * 支持标准模式和紧凑模式（用于侧边栏）。
 * 使用 react-nice-avatar 渲染卡通头像；若尚未设置则根据 email 生成确定性默认头像。
 */
'use client';

import dynamic from 'next/dynamic';
import { genConfig, type AvatarFullConfig } from 'react-nice-avatar';
import { useAuthStore } from '@/lib/store/auth-store';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { LogOut, User, Settings, Shield, ChevronUp } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';

/**
 * 动态导入 NiceAvatar 以避免 SSR hydration 错误（内部包含随机数逻辑）。
 * loading 时渲染占位圆圈，确保布局稳定。
 */
const NiceAvatar = dynamic(() => import('react-nice-avatar'), {
  ssr: false,
  loading: () => <div className="w-full h-full rounded-full bg-sage-100" />,
});

interface UserMenuProps {
  /** 紧凑模式 - 用于侧边栏等空间有限的场景 */
  compact?: boolean;
  /** 自定义样式类名 */
  className?: string;
}

/**
 * 根据用户数据构建头像 config：
 * - 若数据库中已有 avatar_config，直接使用；
 * - 否则根据 email 生成确定性初始头像（相同 email 永远相同）。
 */
function buildAvatarConfig(
  avatarConfig: Record<string, unknown> | null | undefined,
  email: string,
): AvatarFullConfig {
  if (avatarConfig && Object.keys(avatarConfig).length > 0) {
    return avatarConfig as AvatarFullConfig;
  }
  return genConfig(email);
}

export function UserMenu({ compact = false, className }: UserMenuProps) {
  const router = useRouter();
  const t = useTranslations();
  const { user, logout, isAdmin } = useAuthStore();

  if (!user) {
    return null;
  }

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const avatarConfig = buildAvatarConfig(user.avatar_config, user.email);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {compact ? (
          // 紧凑模式 - 用于侧边栏
          <button
            className={cn(
              'w-full flex items-center gap-3 p-2 rounded-lg',
              'hover:bg-sage-50 transition-colors group',
              className,
            )}
          >
            <UserAvatar config={avatarConfig} size="sm" />
            <div className="flex-1 min-w-0 text-left">
              <p className="text-xs font-medium text-foreground truncate">
                {user.username}
              </p>
              <p className="text-[10px] text-muted-foreground truncate">
                {user.email}
              </p>
            </div>
            <ChevronUp className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors shrink-0" />
          </button>
        ) : (
          // 标准模式 - 用于顶部导航栏
          <Button
            variant="ghost"
            className={cn('gap-2 hover:bg-sage-50', className)}
          >
            <UserAvatar config={avatarConfig} size="sm" />
            <span className="hidden md:inline font-medium text-sm">{user.username}</span>
          </Button>
        )}
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align={compact ? 'start' : 'end'}
        side={compact ? 'top' : 'bottom'}
        className="w-64"
      >
        {/* 用户信息展示 */}
        <DropdownMenuLabel>
          <div className="flex flex-col space-y-2">
            <div className="flex items-center gap-3">
              <UserAvatar config={avatarConfig} size="md" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold truncate">{user.username}</p>
                <p className="text-xs text-muted-foreground truncate">{user.email}</p>
              </div>
            </div>
            {isAdmin() && (
              <div className="flex items-center gap-1 text-xs text-sage-700 bg-sage-100 px-2 py-1 rounded-md">
                <Shield className="w-3 h-3" />
                <span>{t('userMenu.administrator')}</span>
              </div>
            )}
          </div>
        </DropdownMenuLabel>

        <DropdownMenuSeparator />

        {/* 菜单项 */}
        <DropdownMenuItem
          onClick={() => router.push('/settings')}
          className="cursor-pointer"
        >
          <User className="mr-2 h-4 w-4" />
          <span>{t('userMenu.profileSettings')}</span>
        </DropdownMenuItem>

        <DropdownMenuItem
          onClick={() => router.push('/app-settings')}
          className="cursor-pointer"
        >
          <Settings className="mr-2 h-4 w-4" />
          <span>{t('userMenu.appSettings')}</span>
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        {/* 登出 */}
        <DropdownMenuItem
          onClick={handleLogout}
          className="cursor-pointer text-red-600 focus:text-red-600 focus:bg-red-50"
        >
          <LogOut className="mr-2 h-4 w-4" />
          <span>{t('userMenu.logout')}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/* ─────────────────────────────────────────────────────── */
/*  内部头像渲染组件                                        */
/* ─────────────────────────────────────────────────────── */

interface UserAvatarProps {
  config: AvatarFullConfig;
  /** sm: 用于触发器和列表；md: 用于下拉菜单头部 */
  size: 'sm' | 'md';
}

/**
 * 统一的用户头像渲染组件
 *
 * 使用 NiceAvatar（动态加载），loading 时显示占位圆圈。
 */
function UserAvatar({ config, size }: UserAvatarProps) {
  const sizeClass = size === 'sm' ? 'w-8 h-8' : 'w-10 h-10';

  return (
    <div className={cn('shrink-0 rounded-full overflow-hidden', sizeClass)}>
      <NiceAvatar className="w-full h-full" {...config} />
    </div>
  );
}

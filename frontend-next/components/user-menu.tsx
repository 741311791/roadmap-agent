/**
 * 用户菜单组件
 * 
 * 显示当前登录用户信息，提供登出功能
 * 支持标准模式和紧凑模式（用于侧边栏）
 */
'use client';

import { useAuthStore } from '@/lib/store/auth-store';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
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
import { cn } from '@/lib/utils';

interface UserMenuProps {
  /** 紧凑模式 - 用于侧边栏等空间有限的场景 */
  compact?: boolean;
  /** 自定义样式类名 */
  className?: string;
}

export function UserMenu({ compact = false, className }: UserMenuProps) {
  const router = useRouter();
  const { user, logout, isAdmin } = useAuthStore();
  
  if (!user) {
    return null;
  }
  
  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  // 获取用户名首字母
  const initials = user.username.slice(0, 2).toUpperCase();
  
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {compact ? (
          // 紧凑模式 - 用于侧边栏
          <button 
            className={cn(
              "w-full flex items-center gap-3 p-2 rounded-lg",
              "hover:bg-sage-50 transition-colors group",
              className
            )}
          >
            <Avatar className="w-8 h-8 shrink-0">
              <AvatarFallback className="bg-sage-100 text-sage-700 text-xs font-medium">
                {initials}
              </AvatarFallback>
            </Avatar>
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
            className={cn("gap-2 hover:bg-sage-50", className)}
          >
            <Avatar className="w-7 h-7">
              <AvatarFallback className="bg-sage-100 text-sage-700 text-xs font-medium">
                {initials}
              </AvatarFallback>
            </Avatar>
            <span className="hidden md:inline font-medium text-sm">{user.username}</span>
          </Button>
        )}
      </DropdownMenuTrigger>
      
      <DropdownMenuContent 
        align={compact ? "start" : "end"} 
        side={compact ? "top" : "bottom"}
        className="w-64"
      >
        {/* User Info */}
        <DropdownMenuLabel>
          <div className="flex flex-col space-y-2">
            <div className="flex items-center gap-3">
              <Avatar className="w-10 h-10 shrink-0">
                <AvatarFallback className="bg-sage-100 text-sage-700 text-sm font-semibold">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold truncate">{user.username}</p>
                <p className="text-xs text-muted-foreground truncate">{user.email}</p>
              </div>
            </div>
            {isAdmin() && (
              <div className="flex items-center gap-1 text-xs text-sage-700 bg-sage-100 px-2 py-1 rounded-md">
                <Shield className="w-3 h-3" />
                <span>Administrator</span>
              </div>
            )}
          </div>
        </DropdownMenuLabel>
        
        <DropdownMenuSeparator />
        
        {/* Menu Items */}
        <DropdownMenuItem 
          onClick={() => router.push('/profile')}
          className="cursor-pointer"
        >
          <User className="mr-2 h-4 w-4" />
          <span>Profile Settings</span>
        </DropdownMenuItem>
        
        <DropdownMenuItem 
          onClick={() => router.push('/settings')}
          className="cursor-pointer"
          disabled
        >
          <Settings className="mr-2 h-4 w-4" />
          <span>App Settings</span>
          <span className="ml-auto text-xs text-muted-foreground">Soon</span>
        </DropdownMenuItem>
        
        <DropdownMenuSeparator />
        
        {/* Logout */}
        <DropdownMenuItem 
          onClick={handleLogout}
          className="cursor-pointer text-red-600 focus:text-red-600 focus:bg-red-50"
        >
          <LogOut className="mr-2 h-4 w-4" />
          <span>Logout</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

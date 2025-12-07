/**
 * 用户菜单组件
 * 
 * 显示当前登录用户信息，提供登出功能
 */
'use client';

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
import { LogOut, User, Settings, Shield } from 'lucide-react';
import { useRouter } from 'next/navigation';

export function UserMenu() {
  const router = useRouter();
  const { user, logout, isAdmin } = useAuthStore();
  
  if (!user) {
    return null;
  }
  
  const handleLogout = () => {
    logout();
    router.push('/login');
  };
  
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button 
          variant="ghost" 
          className="gap-2 hover:bg-sage-50"
        >
          <span className="text-2xl">{user.avatar}</span>
          <span className="hidden md:inline font-medium">{user.username}</span>
        </Button>
      </DropdownMenuTrigger>
      
      <DropdownMenuContent align="end" className="w-64">
        {/* User Info */}
        <DropdownMenuLabel>
          <div className="flex flex-col space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{user.avatar}</span>
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










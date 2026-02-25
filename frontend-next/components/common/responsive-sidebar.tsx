/**
 * ResponsiveSidebar - 响应式侧边栏组件
 * 
 * 移动端：Sheet（抽屉式）
 * 桌面端：固定侧边栏
 * 
 * @example
 * <ResponsiveSidebar>
 *   <nav>Navigation Links</nav>
 * </ResponsiveSidebar>
 */

'use client';

import * as React from 'react';
import { useIsMobile } from '@/lib/hooks';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Menu, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ResponsiveSidebarProps {
  /** 侧边栏内容 */
  children: React.ReactNode;
  /** 侧边栏位置（移动端 Sheet 方向）*/
  side?: 'left' | 'right';
  /** 桌面端侧边栏宽度 */
  width?: string;
  /** 容器类名 */
  className?: string;
  /** 自定义触发按钮（移动端）*/
  trigger?: React.ReactNode;
  /** 是否默认打开（仅桌面端）*/
  defaultOpen?: boolean;
}

export function ResponsiveSidebar({
  children,
  side = 'left',
  width = 'w-64',
  className,
  trigger,
  defaultOpen = true,
}: ResponsiveSidebarProps) {
  const isMobile = useIsMobile();
  const [open, setOpen] = React.useState(false);

  // 移动端：Sheet（抽屉）
  if (isMobile) {
    return (
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          {trigger || (
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              aria-label="Toggle menu"
            >
              <Menu className="h-5 w-5" />
            </Button>
          )}
        </SheetTrigger>
        <SheetContent side={side} className={cn('w-[280px] sm:w-[320px]', className)}>
          {children}
        </SheetContent>
      </Sheet>
    );
  }

  // 桌面端：固定侧边栏
  if (!defaultOpen) return null;

  return (
    <aside
      className={cn(
        'hidden md:flex flex-col border-r bg-card',
        width,
        className
      )}
    >
      {children}
    </aside>
  );
}

/**
 * 可折叠侧边栏（仅桌面端）
 */
interface CollapsibleSidebarProps extends ResponsiveSidebarProps {
  /** 折叠时的宽度 */
  collapsedWidth?: string;
  /** 是否默认折叠 */
  defaultCollapsed?: boolean;
}

export function CollapsibleSidebar({
  children,
  side = 'left',
  width = 'w-64',
  collapsedWidth = 'w-16',
  className,
  trigger,
  defaultCollapsed = false,
}: CollapsibleSidebarProps) {
  const isMobile = useIsMobile();
  const [collapsed, setCollapsed] = React.useState(defaultCollapsed);
  const [mobileOpen, setMobileOpen] = React.useState(false);

  // 移动端：Sheet（抽屉）
  if (isMobile) {
    return (
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetTrigger asChild>
          {trigger || (
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              aria-label="Toggle menu"
            >
              <Menu className="h-5 w-5" />
            </Button>
          )}
        </SheetTrigger>
        <SheetContent side={side} className="w-[280px] sm:w-[320px]">
          {children}
        </SheetContent>
      </Sheet>
    );
  }

  // 桌面端：可折叠侧边栏
  return (
    <aside
      className={cn(
        'hidden md:flex flex-col border-r bg-card transition-all duration-300 ease-in-out',
        collapsed ? collapsedWidth : width,
        className
      )}
    >
      <div className="flex items-center justify-between p-4 border-b">
        {!collapsed && <div className="font-semibold">Menu</div>}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setCollapsed(!collapsed)}
          className={cn('h-8 w-8', collapsed && 'mx-auto')}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <Menu className="h-4 w-4" /> : <X className="h-4 w-4" />}
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto">{children}</div>
    </aside>
  );
}

/**
 * 响应式侧边栏容器（自动添加触发按钮）
 */
interface ResponsiveSidebarContainerProps {
  /** 侧边栏内容 */
  sidebar: React.ReactNode;
  /** 主内容 */
  children: React.ReactNode;
  /** 侧边栏位置 */
  side?: 'left' | 'right';
  /** 桌面端侧边栏宽度 */
  sidebarWidth?: string;
}

export function ResponsiveSidebarContainer({
  sidebar,
  children,
  side = 'left',
  sidebarWidth = 'w-64',
}: ResponsiveSidebarContainerProps) {
  const isMobile = useIsMobile();
  const [mobileOpen, setMobileOpen] = React.useState(false);

  return (
    <div className="flex h-full">
      {/* 移动端触发按钮 */}
      {isMobile && (
        <div className="fixed top-4 left-4 z-50 md:hidden">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                className="bg-background shadow-md"
                aria-label="Toggle menu"
              >
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side={side} className="w-[280px] sm:w-[320px]">
              {sidebar}
            </SheetContent>
          </Sheet>
        </div>
      )}

      {/* 桌面端固定侧边栏 */}
      {!isMobile && side === 'left' && (
        <aside className={cn('hidden md:flex flex-col border-r bg-card', sidebarWidth)}>
          {sidebar}
        </aside>
      )}

      {/* 主内容区 */}
      <main className="flex-1 overflow-y-auto">{children}</main>

      {/* 右侧边栏 */}
      {!isMobile && side === 'right' && (
        <aside className={cn('hidden md:flex flex-col border-l bg-card', sidebarWidth)}>
          {sidebar}
        </aside>
      )}
    </div>
  );
}

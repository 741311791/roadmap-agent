/**
 * ResponsiveDialog - 响应式对话框组件
 * 
 * 移动端：全屏 Sheet（从底部弹出）
 * 桌面端：居中 Dialog
 * 
 * @example
 * <ResponsiveDialog open={open} onOpenChange={setOpen}>
 *   <ResponsiveDialogHeader>
 *     <ResponsiveDialogTitle>Title</ResponsiveDialogTitle>
 *   </ResponsiveDialogHeader>
 *   <ResponsiveDialogContent>
 *     Content here
 *   </ResponsiveDialogContent>
 * </ResponsiveDialog>
 */

'use client';

import * as React from 'react';
import { useIsMobile } from '@/lib/hooks';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { cn } from '@/lib/utils';

interface ResponsiveDialogProps {
  children: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  className?: string;
}

export function ResponsiveDialog({
  children,
  open,
  onOpenChange,
  className,
}: ResponsiveDialogProps) {
  const isMobile = useIsMobile();

  if (isMobile) {
    return (
      <Sheet open={open} onOpenChange={onOpenChange}>
        {children}
      </Sheet>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {children}
    </Dialog>
  );
}

interface ResponsiveDialogTriggerProps {
  children: React.ReactNode;
  asChild?: boolean;
  className?: string;
}

export function ResponsiveDialogTrigger({
  children,
  asChild,
  className,
}: ResponsiveDialogTriggerProps) {
  const isMobile = useIsMobile();

  if (isMobile) {
    return (
      <SheetTrigger asChild={asChild} className={className}>
        {children}
      </SheetTrigger>
    );
  }

  return (
    <DialogTrigger asChild={asChild} className={className}>
      {children}
    </DialogTrigger>
  );
}

interface ResponsiveDialogContentProps {
  children: React.ReactNode;
  className?: string;
  /** 桌面端对话框最大宽度 */
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
}

export function ResponsiveDialogContent({
  children,
  className,
  maxWidth = 'lg',
}: ResponsiveDialogContentProps) {
  const isMobile = useIsMobile();

  const maxWidthClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    full: 'max-w-full',
  };

  if (isMobile) {
    return (
      <SheetContent
        side="bottom"
        className={cn(
          'h-[90vh] rounded-t-2xl flex flex-col',
          className
        )}
      >
        <div className="flex-1 overflow-y-auto">{children}</div>
      </SheetContent>
    );
  }

  return (
    <DialogContent className={cn(maxWidthClasses[maxWidth], className)}>
      {children}
    </DialogContent>
  );
}

interface ResponsiveDialogHeaderProps {
  children: React.ReactNode;
  className?: string;
}

export function ResponsiveDialogHeader({
  children,
  className,
}: ResponsiveDialogHeaderProps) {
  const isMobile = useIsMobile();

  if (isMobile) {
    return <SheetHeader className={className}>{children}</SheetHeader>;
  }

  return <DialogHeader className={className}>{children}</DialogHeader>;
}

interface ResponsiveDialogTitleProps {
  children: React.ReactNode;
  className?: string;
}

export function ResponsiveDialogTitle({
  children,
  className,
}: ResponsiveDialogTitleProps) {
  const isMobile = useIsMobile();

  if (isMobile) {
    return <SheetTitle className={className}>{children}</SheetTitle>;
  }

  return <DialogTitle className={className}>{children}</DialogTitle>;
}

interface ResponsiveDialogDescriptionProps {
  children: React.ReactNode;
  className?: string;
}

export function ResponsiveDialogDescription({
  children,
  className,
}: ResponsiveDialogDescriptionProps) {
  const isMobile = useIsMobile();

  if (isMobile) {
    return <SheetDescription className={className}>{children}</SheetDescription>;
  }

  return <DialogDescription className={className}>{children}</DialogDescription>;
}

/**
 * 响应式对话框底部操作区
 * 移动端：垂直堆叠按钮，桌面端：水平排列
 */
interface ResponsiveDialogFooterProps {
  children: React.ReactNode;
  className?: string;
}

export function ResponsiveDialogFooter({
  children,
  className,
}: ResponsiveDialogFooterProps) {
  return (
    <div
      className={cn(
        'flex flex-col-reverse gap-2 mt-6',
        'sm:flex-row sm:justify-end sm:gap-3',
        className
      )}
    >
      {children}
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { MessageCircle, X } from 'lucide-react';

import { FeedbackPanel } from '@/components/feedback/feedback-dialog';
import {
  FEEDBACK_OPEN_EVENT,
  openManualFeedbackDialog,
} from '@/lib/feedback/feedback-events';
import type { FeedbackOpenContext } from '@/lib/feedback/types';
import { useAuthStore } from '@/lib/store/auth-store';
import { cn } from '@/lib/utils';

const SESSION_DISMISS_KEY = 'feedback_btn_dismissed';

/**
 * 全局反馈控制器 — 悬浮 icon 按钮，hover 时显示关闭 ×（本 session 维度）。
 */
export function FeedbackController() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const hasHydrated = useAuthStore((state) => state.hasHydrated);
  const [open, setOpen] = useState(false);
  const [context, setContext] = useState<FeedbackOpenContext | null>(null);
  const [isDismissed, setIsDismissed] = useState(false);

  /* 读取 session 维度的关闭状态 */
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (sessionStorage.getItem(SESSION_DISMISS_KEY) === '1') {
      setIsDismissed(true);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    /**
     * 监听全局打开反馈面板事件。
     */
    const handleOpenEvent = (event: Event) => {
      const customEvent = event as CustomEvent<FeedbackOpenContext>;
      setContext(customEvent.detail);
      setOpen(true);
    };

    window.addEventListener(FEEDBACK_OPEN_EVENT, handleOpenEvent as EventListener);
    return () => window.removeEventListener(FEEDBACK_OPEN_EVENT, handleOpenEvent as EventListener);
  }, []);

  if (!hasHydrated || !isAuthenticated || isDismissed) return null;

  const handleToggle = () => {
    if (open) {
      setOpen(false);
    } else {
      openManualFeedbackDialog();
    }
  };

  /**
   * 关闭悬浮按钮，本次会话不再显示。
   */
  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    sessionStorage.setItem(SESSION_DISMISS_KEY, '1');
    setIsDismissed(true);
    setOpen(false);
  };

  return (
    <>
      {/* 悬浮按钮容器（group 用于 hover 联动） */}
      <div className="group/launcher fixed bottom-6 right-6 z-[61]">
        {/* Tooltip — 未打开时显示 */}
        <span
          className={cn(
            'pointer-events-none absolute bottom-full right-0 mb-2 whitespace-nowrap',
            'rounded-lg border border-sage-200 bg-[#faf8f2]/95 px-2.5 py-1',
            'text-[10px] font-medium tracking-wide text-sage-700 shadow-sm',
            'opacity-0 transition-opacity duration-200 group-hover/launcher:opacity-100',
            open && 'hidden',
          )}
        >
          Feedback
        </span>

        {/* 关闭（dismiss）按钮 — hover 时出现在右上角 */}
        <button
          type="button"
          onClick={handleDismiss}
          aria-label="Dismiss feedback button"
          className={cn(
            'absolute -right-1.5 -top-1.5 z-10',
            'flex h-4.5 w-4.5 items-center justify-center rounded-full',
            'border border-stone-200 bg-[#faf8f2] shadow-sm',
            'text-stone-400 hover:text-stone-600',
            'transition-all duration-150',
            /* hover 联动 */
            'pointer-events-none opacity-0',
            'group-hover/launcher:pointer-events-auto group-hover/launcher:opacity-100',
          )}
        >
          <X className="h-2.5 w-2.5" />
        </button>

        {/* 主按钮 */}
        <button
          type="button"
          onClick={handleToggle}
          aria-label={open ? 'Close feedback' : 'Open feedback'}
          className={cn(
            'flex h-10 w-10 items-center justify-center rounded-full',
            'border border-sage-300/70 bg-[#faf8f2]/95 backdrop-blur-sm',
            'shadow-[0_6px_20px_-6px_rgba(47,66,53,0.25)]',
            'transition-all duration-200',
            'hover:scale-105 hover:border-sage-400/70 hover:shadow-[0_8px_24px_-6px_rgba(47,66,53,0.35)]',
            'active:scale-95',
            open ? 'text-sage-700' : 'text-sage-500 hover:text-sage-700',
          )}
        >
          {open ? (
            <X className="h-4 w-4 transition-transform duration-200" />
          ) : (
            <MessageCircle className="h-4 w-4 transition-transform duration-200" />
          )}
        </button>
      </div>

      <FeedbackPanel open={open} context={context} onOpenChange={setOpen} />
    </>
  );
}

'use client';

import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useTranslations } from 'next-intl';
import { Loader2, Star } from 'lucide-react';
import { toast } from 'sonner';

import { feedbackApi } from '@/lib/api/endpoints/feedback';
import type { FeedbackCategory, FeedbackOpenContext } from '@/lib/feedback/types';
import { cn } from '@/lib/utils';

interface FeedbackPanelProps {
  open: boolean;
  context: FeedbackOpenContext | null;
  onOpenChange: (open: boolean) => void;
}

const CATEGORIES: Array<{ value: FeedbackCategory; label: string }> = [
  { value: 'bug', label: 'Bug' },
  { value: 'improvement', label: 'Improve' },
  { value: 'question', label: 'Question' },
  { value: 'new_feature', label: 'Feature' },
];

/**
 * 紧凑反馈浮层 — 网站奶油 + sage 主题，右下角弹出，单文本框极简设计。
 */
export function FeedbackPanel({ open, context, onOpenChange }: FeedbackPanelProps) {
  const t = useTranslations('feedback');
  const [mounted, setMounted] = useState(false);
  const [rating, setRating] = useState(5);
  const [hoverRating, setHoverRating] = useState(0);
  const [category, setCategory] = useState<FeedbackCategory>('improvement');
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const panelRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => setMounted(true), []);

  /* 打开时重置表单并聚焦 */
  useEffect(() => {
    if (!open) return;
    setRating(context?.contextType === 'concept_completed' ? 4 : 5);
    setCategory(context?.contextType === 'generation_completed' ? 'improvement' : 'bug');
    setMessage('');
    const timer = setTimeout(() => textareaRef.current?.focus(), 250);
    return () => clearTimeout(timer);
  }, [context, open]);

  /* 点击面板外部关闭 — 延迟 100ms 避免与触发按钮的点击冲突 */
  useEffect(() => {
    if (!open) return;

    const handleOutsideClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onOpenChange(false);
      }
    };

    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleOutsideClick);
    }, 100);

    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [open, onOpenChange]);

  /* Escape 键关闭 */
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onOpenChange(false);
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onOpenChange]);

  /**
   * 提交反馈 — 首行作为 summary，全文作为 details。
   */
  const handleSubmit = async () => {
    if (!context) return;

    const trimmed = message.trim();
    if (!trimmed) {
      toast.error(t('errors.summaryRequired'));
      return;
    }

    const firstLine = trimmed.split('\n')[0];
    const summary = (firstLine || trimmed).slice(0, 200);

    setIsSubmitting(true);
    try {
      await feedbackApi.submitUserFeedback({
        rating,
        category,
        summary,
        details: trimmed,
        pageUrl: context.pageUrl ?? window.location.href,
        contextType: context.contextType,
        roadmapId: context.roadmapId,
        conceptId: context.conceptId,
        taskId: context.taskId,
        screenshotFile: null,
      });
      toast.success(t('success'));
      onOpenChange(false);
    } catch (err) {
      console.error('[FeedbackPanel]', err);
      toast.error(t('errors.submitFailed'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const placeholder = (() => {
    switch (context?.contextType) {
      case 'generation_completed':
        return t('detailsPlaceholders.generationCompleted');
      case 'concept_completed':
        return t('detailsPlaceholders.conceptCompleted');
      default:
        return t('detailsPlaceholders.manual');
    }
  })();

  if (!mounted) return null;

  return createPortal(
    <div
      ref={panelRef}
      role="dialog"
      aria-modal="true"
      aria-label="Feedback"
      className={cn(
        /* 定位 */
        'fixed bottom-[72px] right-6 z-[60] w-[320px]',
        /* 外观 — 奶油底 + sage 边框 */
        'overflow-hidden rounded-2xl',
        'border border-sage-200/80 bg-[#faf8f2]/98 backdrop-blur-sm',
        'shadow-[0_20px_48px_-12px_rgba(47,66,53,0.22),0_4px_12px_-4px_rgba(47,66,53,0.08)]',
        /* 进出场动画 */
        'transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]',
        open
          ? 'pointer-events-auto translate-y-0 scale-100 opacity-100'
          : 'pointer-events-none translate-y-3 scale-[0.97] opacity-0',
      )}
    >
      {/* 顶部 sage 渐变高光 */}
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-sage-300/50 to-transparent" />

      <div className="space-y-3.5 p-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-sage-500">
            Feedback
          </span>
          {(context?.contextType === 'generation_completed' ||
            context?.contextType === 'concept_completed') && (
            <span className="rounded-full border border-sage-200 bg-sage-50 px-2 py-0.5 text-[10px] font-medium text-sage-600">
              {context.contextType === 'generation_completed' ? 'Roadmap' : 'Concept'}
            </span>
          )}
        </div>

        {/* 评分 */}
        <div className="flex items-center gap-0.5">
          {[1, 2, 3, 4, 5].map((v) => {
            const filled = v <= (hoverRating || rating);
            return (
              <button
                key={v}
                type="button"
                onClick={() => setRating(v)}
                onMouseEnter={() => setHoverRating(v)}
                onMouseLeave={() => setHoverRating(0)}
                className="p-0.5 transition-transform duration-100 hover:scale-110 active:scale-95"
                aria-label={`${v} stars`}
              >
                <Star
                  className={cn(
                    'h-[17px] w-[17px] transition-all duration-150',
                    filled
                      ? 'fill-amber-400 text-amber-400'
                      : 'fill-stone-200 text-stone-200',
                  )}
                />
              </button>
            );
          })}
        </div>

        {/* 分类 chips */}
        <div className="flex flex-wrap gap-1.5">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              type="button"
              onClick={() => setCategory(cat.value)}
              className={cn(
                'rounded-full px-2.5 py-[3px] text-[11px] font-medium transition-all duration-150',
                category === cat.value
                  ? 'bg-sage-700 text-white shadow-sm'
                  : 'border border-sage-200 bg-sage-50/80 text-sage-600 hover:border-sage-300 hover:bg-sage-100/80',
              )}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* 消息输入框 */}
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={placeholder}
          rows={4}
          className={cn(
            'w-full resize-none rounded-xl',
            'border border-stone-200/80 bg-white/70',
            'px-3 py-2.5 text-[13px] leading-relaxed text-stone-800',
            'placeholder:text-stone-400',
            'focus:border-sage-300 focus:outline-none focus:ring-1 focus:ring-sage-200',
            'transition-colors duration-200',
          )}
        />

        {/* 底部操作栏 */}
        <div className="flex items-center justify-end gap-2 pt-0.5">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
            className="rounded-lg px-3 py-1.5 text-[12px] font-medium text-stone-400 transition-colors hover:text-stone-600"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting || !message.trim()}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-3.5 py-1.5',
              'text-[12px] font-medium text-white',
              'bg-gradient-to-r from-sage-700 via-sage-600 to-emerald-600',
              'shadow-sm shadow-sage-900/15',
              'transition-all duration-150',
              'hover:from-sage-800 hover:to-emerald-700 hover:shadow-md',
              'disabled:cursor-not-allowed disabled:opacity-40',
              'active:scale-95',
            )}
          >
            {isSubmitting ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
            {isSubmitting ? 'Sending…' : 'Send →'}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

/**
 * 兼容旧名称导出，保持其他文件无需修改。
 *
 * @deprecated 使用 FeedbackPanel 替代
 */
export { FeedbackPanel as FeedbackDialog };

'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Loader2, MessageSquarePlus, Sparkles, Star } from 'lucide-react';
import { toast } from 'sonner';

import { feedbackApi } from '@/lib/api/endpoints/feedback';
import type { FeedbackCategory } from '@/lib/feedback/types';
import { cn } from '@/lib/utils';

const CATEGORIES: Array<{ value: FeedbackCategory; label: string; description: string }> = [
  { value: 'bug', label: 'Bug', description: '遇到了问题或异常' },
  { value: 'improvement', label: 'Improvement', description: '体验可以更好' },
  { value: 'question', label: 'Question', description: '有疑问需要解答' },
  { value: 'new_feature', label: 'Feature Request', description: '希望看到新功能' },
];

const RATING_LABELS: Record<number, string> = {
  1: 'Very poor',
  2: 'Poor',
  3: 'Okay',
  4: 'Good',
  5: 'Excellent',
};

/**
 * 专属反馈页面客户端组件。
 */
export default function FeedbackPage() {
  const t = useTranslations('feedback');
  const router = useRouter();

  const [rating, setRating] = useState(5);
  const [hoverRating, setHoverRating] = useState(0);
  const [category, setCategory] = useState<FeedbackCategory>('improvement');
  const [summary, setSummary] = useState('');
  const [details, setDetails] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const summaryRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    summaryRef.current?.focus();
  }, []);

  /**
   * 提交反馈。
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedSummary = summary.trim();
    const trimmedDetails = details.trim() || trimmedSummary;

    if (!trimmedSummary) {
      toast.error(t('errors.summaryRequired'));
      summaryRef.current?.focus();
      return;
    }

    setIsSubmitting(true);
    try {
      await feedbackApi.submitUserFeedback({
        rating,
        category,
        summary: trimmedSummary,
        details: trimmedDetails,
        pageUrl: window.location.href,
        contextType: 'manual',
        screenshotFile: null,
      });
      setSubmitted(true);
    } catch (err) {
      console.error('[FeedbackPage]', err);
      toast.error(t('errors.submitFailed'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const displayRating = hoverRating || rating;

  /* 提交成功页面 */
  if (submitted) {
    return (
      <div className="flex min-h-full flex-col items-center justify-center px-6 py-24">
        <div className="flex flex-col items-center gap-5 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full border border-sage-200 bg-sage-50">
            <Sparkles className="h-7 w-7 text-sage-600" />
          </div>
          <div className="space-y-2">
            <h2 className="font-serif text-2xl text-stone-900">Thank you!</h2>
            <p className="max-w-xs text-sm leading-relaxed text-stone-500">
              {t('success')}
            </p>
          </div>
          <button
            type="button"
            onClick={() => router.back()}
            className="mt-2 rounded-lg border border-sage-200 bg-white px-5 py-2 text-sm font-medium text-sage-700 shadow-sm transition-colors hover:bg-sage-50"
          >
            Go back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full px-6 py-10 md:px-10">
      <div className="mx-auto max-w-2xl">
        {/* 页头 */}
        <div className="mb-10 space-y-3">
          <div className="inline-flex items-center gap-2 rounded-full border border-sage-200 bg-sage-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.2em] text-sage-700">
            <MessageSquarePlus className="h-3.5 w-3.5" />
            <span>Feedback</span>
          </div>
          <h1 className="font-serif text-3xl text-stone-900">
            Tell us what you think.
          </h1>
          <p className="max-w-md text-sm leading-relaxed text-stone-500">
            Your notes go straight into our Linear board. We read every single one.
          </p>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 评分 */}
          <div className="space-y-3">
            <label className="block text-xs font-semibold uppercase tracking-[0.15em] text-stone-400">
              Overall rating
            </label>
            <div className="flex items-center gap-3">
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((v) => (
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
                        'h-7 w-7 transition-all duration-150',
                        v <= displayRating
                          ? 'fill-amber-400 text-amber-400'
                          : 'fill-stone-100 text-stone-200',
                      )}
                    />
                  </button>
                ))}
              </div>
              <span
                className={cn(
                  'text-sm font-medium transition-all duration-150',
                  displayRating >= 4 ? 'text-sage-600' : displayRating >= 3 ? 'text-stone-500' : 'text-rose-400',
                )}
              >
                {RATING_LABELS[displayRating]}
              </span>
            </div>
          </div>

          {/* 分类 */}
          <div className="space-y-3">
            <label className="block text-xs font-semibold uppercase tracking-[0.15em] text-stone-400">
              Category
            </label>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.value}
                  type="button"
                  onClick={() => setCategory(cat.value)}
                  className={cn(
                    'flex flex-col gap-0.5 rounded-xl border px-3 py-2.5 text-left transition-all duration-150',
                    category === cat.value
                      ? 'border-sage-300 bg-sage-50 shadow-sm'
                      : 'border-stone-200/80 bg-white hover:border-sage-200 hover:bg-sage-50/50',
                  )}
                >
                  <span
                    className={cn(
                      'text-[12px] font-semibold',
                      category === cat.value ? 'text-sage-800' : 'text-stone-700',
                    )}
                  >
                    {cat.label}
                  </span>
                  <span className="text-[11px] leading-tight text-stone-400">
                    {cat.description}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* 主题摘要 */}
          <div className="space-y-2">
            <label
              htmlFor="feedback-summary"
              className="block text-xs font-semibold uppercase tracking-[0.15em] text-stone-400"
            >
              One-line summary
              <span className="ml-1 text-rose-400">*</span>
            </label>
            <input
              ref={summaryRef}
              id="feedback-summary"
              type="text"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder={t('summaryPlaceholder')}
              maxLength={200}
              className={cn(
                'w-full rounded-xl border border-stone-200 bg-white px-4 py-3',
                'text-sm text-stone-800 placeholder:text-stone-300',
                'focus:border-sage-300 focus:outline-none focus:ring-2 focus:ring-sage-100',
                'transition-colors duration-200',
              )}
            />
          </div>

          {/* 详细描述 */}
          <div className="space-y-2">
            <label
              htmlFor="feedback-details"
              className="block text-xs font-semibold uppercase tracking-[0.15em] text-stone-400"
            >
              Details
              <span className="ml-1.5 text-stone-300 normal-case tracking-normal font-normal">
                (optional)
              </span>
            </label>
            <textarea
              id="feedback-details"
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              placeholder="What happened, what did you expect, and how can we reproduce it?"
              rows={5}
              maxLength={5000}
              className={cn(
                'w-full resize-none rounded-xl border border-stone-200 bg-white px-4 py-3',
                'text-sm leading-relaxed text-stone-800 placeholder:text-stone-300',
                'focus:border-sage-300 focus:outline-none focus:ring-2 focus:ring-sage-100',
                'transition-colors duration-200',
              )}
            />
          </div>

          {/* 操作 */}
          <div className="flex items-center justify-between border-t border-stone-100 pt-5">
            <button
              type="button"
              onClick={() => router.back()}
              className="text-sm text-stone-400 transition-colors hover:text-stone-600"
            >
              ← Back
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !summary.trim()}
              className={cn(
                'flex items-center gap-2 rounded-xl px-6 py-2.5',
                'text-sm font-medium text-white',
                'bg-gradient-to-r from-sage-700 via-sage-600 to-emerald-600',
                'shadow-sm shadow-sage-900/15',
                'transition-all duration-150',
                'hover:from-sage-800 hover:to-emerald-700 hover:shadow-md',
                'disabled:cursor-not-allowed disabled:opacity-40',
                'active:scale-[0.98]',
              )}
            >
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {isSubmitting ? 'Sending…' : 'Send to Linear →'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

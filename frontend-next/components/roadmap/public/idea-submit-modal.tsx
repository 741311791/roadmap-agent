'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

interface IdeaSubmitModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isSubmitting: boolean;
  onSubmit: (payload: {
    title: string;
    description?: string | null;
    submitter_email?: string | null;
  }) => Promise<unknown>;
}

/**
 * 提交新想法弹窗
 */
export function IdeaSubmitModal({
  open,
  onOpenChange,
  isSubmitting,
  onSubmit,
}: IdeaSubmitModalProps) {
  const t = useTranslations('publicRoadmap.ideaModal');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [submitterEmail, setSubmitterEmail] = useState('');

  const handleSubmit = async () => {
    if (!title.trim()) {
      return;
    }

    await onSubmit({
      title: title.trim(),
      description: description.trim() || null,
      submitter_email: submitterEmail.trim() || null,
    });

    setTitle('');
    setDescription('');
    setSubmitterEmail('');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="font-serif text-3xl">{t('title')}</DialogTitle>
          <DialogDescription className="text-base leading-7">
            {t('description')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {t('featureTitleLabel')}
            </label>
            <Input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder={t('featureTitlePlaceholder')}
              maxLength={255}
            />
          </div>

          <div className="space-y-2">
            <label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {t('detailLabel')}
            </label>
            <Textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder={t('detailPlaceholder')}
              rows={5}
            />
          </div>

          <div className="space-y-2">
            <label className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {t('emailLabel')}
            </label>
            <Input
              type="email"
              value={submitterEmail}
              onChange={(event) => setSubmitterEmail(event.target.value)}
              placeholder={t('emailPlaceholder')}
              maxLength={255}
            />
          </div>
        </div>

        <DialogFooter className="mt-2 gap-2">
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            {t('cancel')}
          </Button>
          <Button
            type="button"
            variant="sage"
            disabled={isSubmitting || !title.trim()}
            onClick={handleSubmit}
          >
            {isSubmitting ? t('submitting') : t('submit')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

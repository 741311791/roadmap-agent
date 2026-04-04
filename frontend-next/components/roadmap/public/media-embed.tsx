'use client';

import { useMemo, useState } from 'react';
import { Play, Video } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface MediaEmbedProps {
  url?: string | null;
  title: string;
  className?: string;
}

/**
 * 解析媒体链接并转换为可嵌入地址
 */
function resolveEmbedConfig(url?: string | null): { platform: string; embedUrl: string } | null {
  if (!url) {
    return null;
  }

  try {
    const parsed = new URL(url);
    const hostname = parsed.hostname.toLowerCase();

    if (hostname.includes('youtube.com')) {
      const videoId = parsed.searchParams.get('v');
      if (!videoId) {
        return null;
      }
      return {
        platform: 'YouTube',
        embedUrl: `https://www.youtube-nocookie.com/embed/${videoId}?rel=0`,
      };
    }

    if (hostname.includes('youtu.be')) {
      const videoId = parsed.pathname.replace('/', '');
      if (!videoId) {
        return null;
      }
      return {
        platform: 'YouTube',
        embedUrl: `https://www.youtube-nocookie.com/embed/${videoId}?rel=0`,
      };
    }

    if (hostname.includes('bilibili.com')) {
      const match = parsed.pathname.match(/\/video\/(BV[0-9A-Za-z]+)/i);
      if (!match) {
        return null;
      }
      return {
        platform: 'Bilibili',
        embedUrl: `https://player.bilibili.com/player.html?bvid=${match[1]}`,
      };
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * 媒体演示嵌入组件
 */
export function MediaEmbed({ url, title, className }: MediaEmbedProps) {
  const t = useTranslations('publicRoadmap.media');
  const [isPlaying, setIsPlaying] = useState(false);

  const config = useMemo(() => resolveEmbedConfig(url), [url]);

  if (!config) {
    return (
      <div
        className={cn(
          'rounded-2xl border border-border bg-background/80 p-5 text-sm text-muted-foreground',
          className
        )}
      >
        <div className="flex items-center gap-3">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-sage-100 text-sage-700">
            <Video className="h-4 w-4" />
          </span>
          <div>
            <p className="font-medium text-foreground">{t('demoPendingTitle')}</p>
            <p className="text-xs text-muted-foreground">{t('demoPendingDescription')}</p>
          </div>
        </div>
      </div>
    );
  }

  if (isPlaying) {
    return (
      <div className={cn('overflow-hidden rounded-2xl border border-border bg-background shadow-sm', className)}>
        <div className="aspect-video">
          <iframe
            title={title}
            src={config.embedUrl}
            className="h-full w-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-sage-50/70 via-background to-stone-50/70 shadow-sm',
        className
      )}
    >
      <div className="aspect-video px-6 py-8">
        <div className="flex h-full flex-col items-center justify-center gap-4 rounded-[1.25rem] border border-dashed border-border bg-background/70">
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="h-14 w-14 rounded-full border-sage-200 bg-background text-sage-700 hover:border-sage-300 hover:bg-sage-50"
            onClick={() => setIsPlaying(true)}
          >
            <Play className="h-5 w-5 fill-current" />
          </Button>
          <div className="text-center">
            <p className="text-sm font-medium text-foreground">{t('platformDemo', { platform: config.platform })}</p>
            <p className="mt-1 text-xs uppercase tracking-[0.24em] text-muted-foreground">{t('clickToPlay')}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

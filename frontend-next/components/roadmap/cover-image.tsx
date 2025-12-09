/**
 * CoverImage 组件
 * 
 * 显示路线图封面图片，支持降级显示为渐变色背景
 */
'use client';

import { useState, useCallback } from 'react';
import Image from 'next/image';
import { getCoverImage, getGradientFallback, getTopicInitial } from '@/lib/cover-image';

interface CoverImageProps {
  topic: string;
  title: string;
  className?: string;
}

export function CoverImage({ topic, title, className = '' }: CoverImageProps) {
  const [imageError, setImageError] = useState(false);
  const imageUrl = getCoverImage(topic);
  const gradient = getGradientFallback(title);
  const initial = getTopicInitial(title);

  const handleError = useCallback(() => {
    setImageError(true);
  }, []);

  if (imageError) {
    return (
      <div
        className={`aspect-[16/9] ${gradient.className} flex items-center justify-center ${className}`}
      >
        <span className={`text-3xl font-serif font-bold ${gradient.text} opacity-80`}>
          {initial}
        </span>
      </div>
    );
  }

  return (
    <div className={`aspect-[16/9] relative overflow-hidden ${className}`}>
      <Image
        src={imageUrl}
        alt={title}
        fill
        className="object-cover transition-transform duration-500 group-hover:scale-105"
        onError={handleError}
        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent" />
    </div>
  );
}

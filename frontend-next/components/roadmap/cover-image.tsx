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
        className={`aspect-[16/9] ${gradient.className} flex items-center justify-center relative overflow-hidden ${className}`}
      >
        {/* 背景装饰圆圈 */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-0 right-0 w-24 h-24 bg-white rounded-full blur-2xl transform translate-x-1/3 -translate-y-1/3 group-hover:scale-150 transition-transform duration-700" />
          <div className="absolute bottom-0 left-0 w-32 h-32 bg-white rounded-full blur-3xl transform -translate-x-1/3 translate-y-1/3 group-hover:scale-150 transition-transform duration-700" />
        </div>
        
        <span className={`text-4xl font-serif font-bold ${gradient.text} opacity-90 relative z-10 group-hover:scale-110 transition-transform duration-500`}>
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
        className="object-cover transition-transform duration-700 group-hover:scale-110"
        onError={handleError}
        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-black/10 to-transparent" />
      {/* 悬停时的光晕效果 */}
      <div className="absolute inset-0 bg-gradient-to-br from-sage-400/0 via-sage-300/0 to-sage-500/0 group-hover:from-sage-400/20 group-hover:via-sage-300/10 group-hover:to-sage-500/20 transition-all duration-700" />
    </div>
  );
}

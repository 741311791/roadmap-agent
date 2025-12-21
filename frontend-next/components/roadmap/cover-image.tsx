/**
 * CoverImage 组件
 * 
 * 显示路线图封面图片，支持降级显示为渐变色背景
 * 优先使用后端生成的封面图，降级到 Unsplash
 */
'use client';

import { useState, useCallback, useEffect } from 'react';
import Image from 'next/image';
import { getCoverImage, getGradientFallback, getTopicInitial, fetchCoverImageFromAPI } from '@/lib/cover-image';

interface CoverImageProps {
  roadmapId?: string;  // 新增：路线图 ID
  topic: string;
  title: string;
  className?: string;
}

export function CoverImage({ roadmapId, topic, title, className = '' }: CoverImageProps) {
  const [imageError, setImageError] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);
  const [imageUrl, setImageUrl] = useState(getCoverImage(topic));
  const gradient = getGradientFallback(title);
  const initial = getTopicInitial(title);
  
  // 检查是否为 R2.dev 的图片（不使用 Next.js 图片优化）
  const isR2Image = imageUrl.includes('r2.dev');
  
  // 尝试从 API 获取封面图
  useEffect(() => {
    if (roadmapId) {
      setImageLoading(true);
      fetchCoverImageFromAPI(roadmapId).then((apiUrl) => {
        if (apiUrl) {
          setImageUrl(apiUrl);
        }
        setImageLoading(false);
      }).catch(() => {
        setImageLoading(false);
      });
    } else {
      setImageLoading(false);
    }
  }, [roadmapId]);

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
      {/* 加载骨架屏 */}
      {imageLoading && (
        <div className="absolute inset-0 bg-gradient-to-br from-sage-200 to-sage-100 animate-pulse" />
      )}
      
      {/* R2.dev 图片使用普通 img 标签，避免 Next.js 优化导致的连接问题 */}
      {isR2Image ? (
        <img
          src={imageUrl}
          alt={title}
          className={`absolute inset-0 w-full h-full object-cover transition-all duration-700 group-hover:scale-105 ${
            imageLoading ? 'opacity-0' : 'opacity-100'
          }`}
          onLoad={() => setImageLoading(false)}
          onError={handleError}
          loading="lazy"
        />
      ) : (
        <Image
          src={imageUrl}
          alt={title}
          fill
          className={`object-cover transition-all duration-700 group-hover:scale-105 ${
            imageLoading ? 'opacity-0' : 'opacity-100'
          }`}
          onLoad={() => setImageLoading(false)}
          onError={handleError}
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
          priority={false}
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-black/10 to-transparent" />
      {/* 悬停时的光晕效果 */}
      <div className="absolute inset-0 bg-gradient-to-br from-sage-400/0 via-sage-300/0 to-sage-500/0 group-hover:from-sage-400/20 group-hover:via-sage-300/10 group-hover:to-sage-500/20 transition-all duration-700" />
    </div>
  );
}

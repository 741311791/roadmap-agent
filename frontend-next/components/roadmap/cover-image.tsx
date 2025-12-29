/**
 * CoverImage 组件
 * 
 * 显示路线图封面图片，支持降级显示为渐变色背景
 * 优先使用后端生成的封面图，降级到 Unsplash
 * 支持手动重试失败的封面图生成
 */
'use client';

import { useState, useCallback, useEffect } from 'react';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';
import { getCoverImage, getGradientFallback, getTopicInitial, fetchCoverImageFromAPI } from '@/lib/cover-image';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface CoverImageProps {
  roadmapId?: string;  // 路线图 ID
  topic: string;
  title: string;
  className?: string;
  coverImageUrl?: string;  // 可选的封面图 URL（如果提供，则跳过 API 调用）
}

export function CoverImage({ roadmapId, topic, title, className = '', coverImageUrl }: CoverImageProps) {
  const [imageError, setImageError] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);
  const [imageUrl, setImageUrl] = useState(getCoverImage(topic));
  const [coverStatus, setCoverStatus] = useState<'pending' | 'generating' | 'success' | 'failed' | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const gradient = getGradientFallback(title);
  const initial = getTopicInitial(title);
  
  // 检查是否为 R2.dev 的图片（不使用 Next.js 图片优化）
  const isR2Image = imageUrl.includes('r2.dev');
  
  // 获取封面图状态
  useEffect(() => {
    const fetchCoverStatus = async () => {
      if (!roadmapId) {
        setImageLoading(false);
        return;
      }
      
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/roadmap/${roadmapId}/cover-image`, {
          credentials: 'include',
        });
        
        if (response.ok) {
          const data = await response.json();
          setCoverStatus(data.status);
          
          // 如果状态为 success 且有 URL，更新图片
          if (data.status === 'success' && data.cover_image_url) {
            setImageUrl(data.cover_image_url);
          }
        }
      } catch (error) {
        console.error('Failed to fetch cover status:', error);
      } finally {
        setImageLoading(false);
      }
    };
    
    // 如果提供了 coverImageUrl（包括 null），直接使用，跳过 API 调用
    if (coverImageUrl !== undefined) {
      if (coverImageUrl) {
        setImageUrl(coverImageUrl);
        setCoverStatus('success');
      }
      setImageLoading(false);
      return;
    }
    
    // 否则从 API 获取状态
    fetchCoverStatus();
  }, [roadmapId, coverImageUrl]);

  const handleError = useCallback(() => {
    setImageError(true);
  }, []);

  // 手动重试封面图生成
  const handleRetry = useCallback(async () => {
    if (!roadmapId) return;
    
    setIsRetrying(true);
    setCoverStatus('generating');
    
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/roadmap/${roadmapId}/cover-image/generate`,
        {
          method: 'POST',
          credentials: 'include',
        }
      );
      
      if (!response.ok) {
        throw new Error('Failed to trigger cover generation');
      }
      
      // 轮询状态，等待生成完成
      let attempts = 0;
      const maxAttempts = 30; // 最多轮询 30 次（30 秒）
      
      const pollStatus = async () => {
        attempts++;
        if (attempts > maxAttempts) {
          setCoverStatus('failed');
          setIsRetrying(false);
          return;
        }
        
        try {
          const statusResponse = await fetch(
            `${API_BASE_URL}/api/v1/roadmap/${roadmapId}/cover-image`,
            { credentials: 'include' }
          );
          
          if (statusResponse.ok) {
            const statusData = await statusResponse.json();
            
            if (statusData.status === 'success' && statusData.cover_image_url) {
              setImageUrl(statusData.cover_image_url);
              setCoverStatus('success');
              setIsRetrying(false);
            } else if (statusData.status === 'failed') {
              setCoverStatus('failed');
              setIsRetrying(false);
            } else {
              // 继续轮询
              setTimeout(pollStatus, 1000);
            }
          } else {
            setCoverStatus('failed');
            setIsRetrying(false);
          }
        } catch (error) {
          console.error('Failed to poll cover status:', error);
          setCoverStatus('failed');
          setIsRetrying(false);
        }
      };
      
      // 开始轮询
      setTimeout(pollStatus, 1000);
      
    } catch (error) {
      console.error('Failed to retry cover generation:', error);
      setCoverStatus('failed');
      setIsRetrying(false);
    }
  }, [roadmapId]);

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
      
      {/* 失败时显示重试按钮 */}
      {coverStatus === 'failed' && roadmapId && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <Button 
            size="sm" 
            variant="outline"
            onClick={handleRetry}
            disabled={isRetrying}
            className="bg-white/90 hover:bg-white text-foreground shadow-lg gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isRetrying ? 'animate-spin' : ''}`} />
            {isRetrying ? 'Generating...' : 'Retry Cover Generation'}
          </Button>
        </div>
      )}
    </div>
  );
}

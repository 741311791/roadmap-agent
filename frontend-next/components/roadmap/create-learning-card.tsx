/**
 * CreateLearningCard - 创建新学习路线卡片组件
 * 
 * 使用 FlippingCard 实现的 3D 翻转设计
 * - 正面：显示创建邀请和图标
 * - 背面：显示功能介绍和快速操作
 */
'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { FlippingCard } from '@/components/ui/flipping-card';
import { Plus, ChevronRight, Sparkles, Target, BookOpen } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CreateLearningCardProps {
  className?: string;
}

/**
 * 卡片正面内容
 */
function CardFront() {
  const t = useTranslations();
  return (
    <div className="flex flex-col h-full w-full">
      {/* 装饰背景 */}
      <div className="relative w-full h-40 overflow-hidden rounded-t-xl bg-gradient-to-br from-sage-50 via-white to-sage-100">
        {/* 背景装饰 */}
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-0 left-0 w-24 h-24 bg-sage-300 rounded-full blur-3xl transform -translate-x-1/2 -translate-y-1/2" />
          <div className="absolute bottom-0 right-0 w-24 h-24 bg-sage-400 rounded-full blur-3xl transform translate-x-1/2 translate-y-1/2" />
        </div>
        
        {/* 居中的图标 */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-sage-100 to-sage-200 flex items-center justify-center shadow-lg hover:shadow-xl hover:scale-110 transition-all duration-300">
            <Plus size={32} className="text-sage-600" />
          </div>
        </div>

      </div>

      {/* 内容区域 */}
      <div className="flex flex-col flex-1 p-4">
        {/* 标题 */}
        <h3 className="font-serif font-semibold text-base text-foreground text-center mb-3 min-h-[48px] flex items-center justify-center">
          {t('createCard.createRoadmap')}
        </h3>

        {/* 描述 */}
        <p className="text-xs text-muted-foreground text-center mb-3">
          {t('createCard.startJourney')}
        </p>

        {/* 底部占位 */}
        <div className="mt-auto opacity-0">
          <div className="h-4" />
        </div>
      </div>
    </div>
  );
}

/**
 * 卡片背面内容 - 显示功能介绍
 */
function CardBack() {
  const t = useTranslations();
  return (
    <div className="flex flex-col h-full w-full p-4">
      {/* 标题 */}
      <h3 className="font-serif font-semibold text-base text-foreground mb-3 text-center">
        {t('createCard.startLearningToday')}
      </h3>

      {/* 功能列表 */}
      <div className="flex-1 space-y-3">
        <div className="flex items-start gap-2 p-2 rounded-lg bg-sage-50/50">
          <div className="flex-shrink-0 w-6 h-6 rounded-full bg-sage-200 flex items-center justify-center mt-0.5">
            <Target className="w-3 h-3 text-sage-700" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-foreground">
              {t('createCard.setGoalsTitle')}
            </div>
            <div className="text-xs text-muted-foreground">
              {t('createCard.setGoalsDesc')}
            </div>
          </div>
        </div>

        <div className="flex items-start gap-2 p-2 rounded-lg bg-sage-50/50">
          <div className="flex-shrink-0 w-6 h-6 rounded-full bg-sage-200 flex items-center justify-center mt-0.5">
            <Sparkles className="w-3 h-3 text-sage-700" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-foreground">
              {t('createCard.aiPoweredTitle')}
            </div>
            <div className="text-xs text-muted-foreground">
              {t('createCard.aiPoweredDesc')}
            </div>
          </div>
        </div>

        <div className="flex items-start gap-2 p-2 rounded-lg bg-sage-50/50">
          <div className="flex-shrink-0 w-6 h-6 rounded-full bg-sage-200 flex items-center justify-center mt-0.5">
            <BookOpen className="w-3 h-3 text-sage-700" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-foreground">
              {t('createCard.trackProgressTitle')}
            </div>
            <div className="text-xs text-muted-foreground">
              {t('createCard.trackProgressDesc')}
            </div>
          </div>
        </div>
      </div>

      {/* 底部操作区域 */}
      <div className="flex items-center justify-end pt-3 border-t border-sage-100 mt-3">
        {/* 开始按钮 - 阻止事件冒泡 */}
        <div onClick={(e) => e.stopPropagation()}>
          <span className="flex items-center gap-1 text-xs font-medium text-sage-600 hover:text-sage-700 transition-colors cursor-pointer">
            {t('createCard.getStarted')}
            <ChevronRight className="w-3 h-3" />
          </span>
        </div>
      </div>
    </div>
  );
}

export function CreateLearningCard({ className }: CreateLearningCardProps) {
  return (
    <Link href="/new" className={cn('block', className)}>
      <FlippingCard
        width={280}
        height={350}
        frontContent={<CardFront />}
        backContent={<CardBack />}
        className="w-full"
      />
    </Link>
  );
}


'use client';

/**
 * Features 区域组件
 *
 * 特点：
 * - 左侧自动轮播的 5 个特性列表，每个特性与工作流节点 1:1 对应
 * - 激活项显示完整描述，非激活项只显示标题
 * - 顶部工作流演示指示器与轮播状态联动
 * - 右侧展示对应的交互卡片
 * - 支持自动轮播和手动切换
 */

import React, { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'motion/react';
import {
  Target,
  Layers,
  ShieldCheck,
  UserCheck,
  BookOpen,
} from 'lucide-react';
import {
  IntentAnalysisCard,
  RoadmapCard,
  ValidationCard,
  HumanReviewCard,
  ContentGenerationCard,
} from './feature-cards';
import { WorkflowDemoLanding } from './workflow-demo';

interface Feature {
  id: string;
  icon: React.ElementType;
  titleKey: string;
  descriptionKey: string;
  card: React.ComponentType;
}

export function FeaturesSection() {
  const t = useTranslations('features');
  const tHero = useTranslations('hero');

  const features: Feature[] = [
    {
      id: 'identify-gaps',
      icon: Target,
      titleKey: 'gapAnalysisTitle',
      descriptionKey: 'gapAnalysisDesc',
      card: IntentAnalysisCard,
    },
    {
      id: 'structured-path',
      icon: Layers,
      titleKey: 'structuredPathTitle',
      descriptionKey: 'structuredPathDesc',
      card: RoadmapCard,
    },
    {
      id: 'structure-validate',
      icon: ShieldCheck,
      titleKey: 'structureValidateTitle',
      descriptionKey: 'structureValidateDesc',
      card: ValidationCard,
    },
    {
      id: 'human-review',
      icon: UserCheck,
      titleKey: 'humanReviewTitle',
      descriptionKey: 'humanReviewDesc',
      card: HumanReviewCard,
    },
    {
      id: 'content-generation',
      icon: BookOpen,
      titleKey: 'contentGenerationTitle',
      descriptionKey: 'contentGenerationDesc',
      card: ContentGenerationCard,
    },
  ];
  
  const [activeFeature, setActiveFeature] = useState('identify-gaps');
  const [isPaused, setIsPaused] = useState(false);

  // 自动轮播逻辑
  useEffect(() => {
    if (isPaused) return;

    const interval = setInterval(() => {
      setActiveFeature((current) => {
        const currentIndex = features.findIndex((f) => f.id === current);
        const nextIndex = (currentIndex + 1) % features.length;
        return features[nextIndex].id;
      });
    }, 2000); // 每2秒切换

    return () => clearInterval(interval);
  }, [isPaused]);

  const activeFeatureData = features.find((f) => f.id === activeFeature);
  const ActiveCard = activeFeatureData?.card;

  return (
    <section className="py-24 px-6 bg-card">
      <div className="max-w-7xl mx-auto">
        {/* 标题 */}
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-muted border border-border rounded-full text-sage text-sm font-medium mb-6">
              {t('sectionBadge')}
            </div>
            <h2 className="text-4xl md:text-5xl font-serif font-bold text-foreground mb-4">
              {t('sectionTitle')}
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              {t('sectionDesc')}
            </p>
          </motion.div>
        </div>

        {/* 工作流演示 + 内容区域：整块悬停均暂停轮播 */}
        <div
          onMouseEnter={() => setIsPaused(true)}
          onMouseLeave={() => setIsPaused(false)}
        >
          {/* 工作流进度演示指示器 */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mb-12 bg-muted/40 border border-border rounded-2xl overflow-hidden"
          >
            <WorkflowDemoLanding
              activeFeatureId={activeFeature}
              onNodeSelect={(featureId) => {
                setActiveFeature(featureId);
                setIsPaused(true);
              }}
            />
          </motion.div>

        {/* 内容区域 */}
        <div className="grid lg:grid-cols-2 gap-16 items-start">
          {/* 左侧：特性列表 */}
          <div className="relative space-y-0">
            {/* 垂直指示线 */}
            <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-border" />

            {features.map((feature, index) => {
              const Icon = feature.icon;
              const isActive = activeFeature === feature.id;

              return (
                <motion.button
                  key={feature.id}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.05 }}
                  onClick={() => {
                    setActiveFeature(feature.id);
                    setIsPaused(true);
                  }}
                  className={`w-full text-left pl-8 pr-4 py-6 relative transition-all duration-500 group ${
                    isActive ? '' : 'hover:bg-muted/30'
                  }`}
                >
                  {/* 激活指示器 */}
                  <motion.div
                    initial={false}
                    animate={{
                      width: isActive ? '4px' : '0px',
                      opacity: isActive ? 1 : 0,
                    }}
                    transition={{ duration: 0.3 }}
                    className="absolute left-0 top-0 bottom-0 bg-sage"
                  />

                  <div className="flex items-start gap-4">
                    {/* 图标 */}
                    <motion.div
                      initial={false}
                      animate={{
                        scale: isActive ? 1.1 : 1,
                        backgroundColor: isActive ? 'rgb(134, 166, 144)' : 'rgb(243, 244, 246)',
                      }}
                      className="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-300"
                    >
                      <Icon
                        className={`w-5 h-5 transition-colors duration-300 ${
                          isActive ? 'text-white' : 'text-sage'
                        }`}
                      />
                    </motion.div>

                    {/* 内容区域 */}
                    <div className="flex-1 min-w-0">
                      <h3
                        className={`text-lg font-bold mb-1 transition-colors duration-300 ${
                          isActive ? 'text-foreground' : 'text-foreground/70'
                        }`}
                      >
                        {t(feature.titleKey as any)}
                      </h3>

                      {/* 描述文字 - 只在激活时显示 */}
                      <AnimatePresence mode="wait">
                        {isActive && (
                          <motion.p
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.3 }}
                            className="text-sm leading-relaxed text-muted-foreground"
                          >
                            {t(feature.descriptionKey as any)}
                          </motion.p>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                </motion.button>
              );
            })}

            {/* 自动播放提示 */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-6 ml-8 text-xs text-muted-foreground flex items-center gap-2"
            >
              <div className={`w-2 h-2 rounded-full ${isPaused ? 'bg-muted-foreground/30' : 'bg-sage animate-pulse'}`} />
              <span>{isPaused ? tHero('paused') : tHero('autoRotating')}</span>
            </motion.div>
          </div>

          {/* 右侧：展示卡片 */}
          <div className="sticky top-24">
            <AnimatePresence mode="wait">
              {ActiveCard && (
                <motion.div
                  key={activeFeature}
                  initial={{ opacity: 0, y: 20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -20, scale: 0.95 }}
                  transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                >
                  <ActiveCard />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
        </div>{/* 结束：整块悬停暂停容器 */}
      </div>
    </section>
  );
}

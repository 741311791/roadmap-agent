'use client';

/**
 * Features 区域组件
 * 
 * 基于 Magic UI feature-1 设计
 * 左侧展示特性列表，右侧展示对应的卡片
 * 
 * 使用全局设计令牌
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Target, BookOpen, RefreshCw, Lightbulb } from 'lucide-react';
import {
  IntentAnalysisCard,
  RoadmapCard,
  QuizCard,
  ResourceCard,
} from './feature-cards';

interface Feature {
  id: string;
  icon: React.ElementType;
  title: string;
  description: string;
  card: React.ComponentType;
}

const features: Feature[] = [
  {
    id: 'identify-gaps',
    icon: Target,
    title: 'Identify Gaps',
    description:
      'AI analyzes your goals and current knowledge to pinpoint exactly what you need to learn.',
    card: IntentAnalysisCard,
  },
  {
    id: 'structured-path',
    icon: BookOpen,
    title: 'Structured Path',
    description:
      'Stage-Module-Concept hierarchy creates clear, achievable milestones for systematic progress.',
    card: RoadmapCard,
  },
  {
    id: 'learn-by-doing',
    icon: RefreshCw,
    title: 'Learn by Doing',
    description:
      'Every concept ties to practical exercises and real-world projects to solidify understanding.',
    card: QuizCard,
  },
  {
    id: 'iterate-improve',
    icon: Lightbulb,
    title: 'Iterate & Improve',
    description:
      'Curated resources and continuous feedback loops help you master each skill through iteration.',
    card: ResourceCard,
  },
];

export function FeaturesSection() {
  const [activeFeature, setActiveFeature] = useState(features[0].id);

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
              Fast Learning Philosophy
            </div>
            <h2 className="text-4xl md:text-5xl font-serif font-bold text-foreground mb-4">
              Why Fast Learning Works
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Traditional learning is slow and passive. We flip the script with AI-powered active
              learning that adapts to you.
            </p>
          </motion.div>
        </div>

        {/* 内容区域 */}
        <div className="grid lg:grid-cols-2 gap-12 items-start">
          {/* 左侧：特性列表 */}
          <div className="space-y-4">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              const isActive = activeFeature === feature.id;

              return (
                <motion.button
                  key={feature.id}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  onClick={() => setActiveFeature(feature.id)}
                  className={`w-full text-left p-6 rounded-2xl border-2 transition-all duration-300 ${
                    isActive
                      ? 'border-sage bg-muted shadow-lg'
                      : 'border-border bg-card hover:border-accent hover:bg-muted/50'
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div
                      className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${
                        isActive ? 'bg-sage' : 'bg-muted'
                      }`}
                    >
                      <Icon
                        className={`w-6 h-6 ${isActive ? 'text-white' : 'text-sage'}`}
                      />
                    </div>
                    <div className="flex-1">
                      <h3
                        className={`text-lg font-semibold mb-2 ${
                          isActive ? 'text-sage' : 'text-foreground'
                        }`}
                      >
                        {feature.title}
                      </h3>
                      <p
                        className={`text-sm leading-relaxed ${
                          isActive ? 'text-sage' : 'text-muted-foreground'
                        }`}
                      >
                        {feature.description}
                      </p>
                    </div>
                  </div>

                  {/* 激活指示器 */}
                  {isActive && (
                    <motion.div
                      layoutId="activeIndicator"
                      className="absolute left-0 top-0 bottom-0 w-1 bg-sage rounded-r-full"
                      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                    />
                  )}
                </motion.button>
              );
            })}
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
                  transition={{ duration: 0.3 }}
                >
                  <ActiveCard />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}

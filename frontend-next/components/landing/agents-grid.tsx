'use client';

/**
 * 8 个 AI Agent 展示网格
 * 
 * 基于用户提供的 hover effects 模板
 * 2 行 4 列布局，带有悬停效果
 * 使用全局设计令牌
 */

import React from 'react';
import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { cn } from '@/lib/utils';
import {
  IconBrain,
  IconTarget,
  IconShieldCheck,
  IconEdit,
  IconPencil,
  IconBook,
  IconSearch,
  IconCheckbox,
} from '@tabler/icons-react';

interface Agent {
  titleKey: string;
  descriptionKey: string;
  icon: React.ElementType;
  index: number;
}

function AgentCard({ titleKey, descriptionKey, icon: Icon, index }: Agent) {
  const t = useTranslations('agents');
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: index * 0.05 }}
      className={cn(
        'flex flex-col lg:border-r py-10 relative group/feature',
        (index === 0 || index === 4) && 'lg:border-l',
        index < 4 && 'lg:border-b',
        'border-border'
      )}
    >
      {/* 悬停渐变背景 - 上方卡片从底部渐变 */}
      {index < 4 && (
        <div className="opacity-0 group-hover/feature:opacity-100 transition duration-200 absolute inset-0 h-full w-full bg-gradient-to-t from-muted to-transparent pointer-events-none" />
      )}
      {/* 悬停渐变背景 - 下方卡片从顶部渐变 */}
      {index >= 4 && (
        <div className="opacity-0 group-hover/feature:opacity-100 transition duration-200 absolute inset-0 h-full w-full bg-gradient-to-b from-muted to-transparent pointer-events-none" />
      )}
      
      {/* 图标 */}
      <div className="mb-4 relative z-10 px-10 text-sage">
        <Icon size={28} stroke={1.5} />
      </div>
      
      {/* 标题 */}
      <div className="text-lg font-bold mb-2 relative z-10 px-10">
        {/* 左侧动画条 */}
        <div className="absolute left-0 inset-y-0 h-6 group-hover/feature:h-8 w-1 rounded-tr-full rounded-br-full bg-border group-hover/feature:bg-sage transition-all duration-200 origin-center" />
        <span className="group-hover/feature:translate-x-2 transition duration-200 inline-block text-foreground">
          {t(titleKey as any)}
        </span>
      </div>
      
      {/* 描述 */}
      <p className="text-sm text-muted-foreground max-w-xs relative z-10 px-10 leading-relaxed">
        {t(descriptionKey as any)}
      </p>
    </motion.div>
  );
}

export function AgentsGrid() {
  const t = useTranslations('agents');
  
  const agents: Agent[] = [
    {
      titleKey: 'intentAnalyzer',
      descriptionKey: 'intentAnalyzerDesc',
      icon: IconBrain,
      index: 0,
    },
    {
      titleKey: 'curriculumArchitect',
      descriptionKey: 'curriculumArchitectDesc',
      icon: IconTarget,
      index: 1,
    },
    {
      titleKey: 'structureValidator',
      descriptionKey: 'structureValidatorDesc',
      icon: IconShieldCheck,
      index: 2,
    },
    {
      titleKey: 'editPlanAnalyzer',
      descriptionKey: 'editPlanAnalyzerDesc',
      icon: IconEdit,
      index: 3,
    },
    {
      titleKey: 'roadmapEditor',
      descriptionKey: 'roadmapEditorDesc',
      icon: IconPencil,
      index: 4,
    },
    {
      titleKey: 'tutorialGenerator',
      descriptionKey: 'tutorialGeneratorDesc',
      icon: IconBook,
      index: 5,
    },
    {
      titleKey: 'resourceRecommender',
      descriptionKey: 'resourceRecommenderDesc',
      icon: IconSearch,
      index: 6,
    },
    {
      titleKey: 'quizGenerator',
      descriptionKey: 'quizGeneratorDesc',
      icon: IconCheckbox,
      index: 7,
    },
  ];
  
  return (
    <section className="py-24 px-6 bg-gradient-to-b from-card via-muted/30 to-card">
      <div className="max-w-7xl mx-auto">
        {/* 标题 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
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

        {/* Agent 网格 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 relative z-10">
          {agents.map((agent) => (
            <AgentCard key={agent.index} {...agent} />
          ))}
        </div>
      </div>
    </section>
  );
}

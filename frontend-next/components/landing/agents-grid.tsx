'use client';

/**
 * 8 个 AI Agent 展示网格
 * 
 * 基于用户提供的 hover effects 模板
 * 2 行 4 列布局，带有悬停效果
 * 使用全局设计令牌
 */

import React from 'react';
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
  title: string;
  description: string;
  icon: React.ElementType;
  index: number;
}

const agents: Agent[] = [
  {
    title: 'Intent Analyzer',
    description: 'Analyzes learning goals and extracts key technologies from your requirements',
    icon: IconBrain,
    index: 0,
  },
  {
    title: 'Curriculum Architect',
    description: 'Designs structured roadmap with stages, modules, and concepts in logical order',
    icon: IconTarget,
    index: 1,
  },
  {
    title: 'Structure Validator',
    description: 'Validates roadmap structure, dependencies, and ensures learning prerequisites',
    icon: IconShieldCheck,
    index: 2,
  },
  {
    title: 'Edit Plan Analyzer',
    description: 'Creates precise modification plans from validation results and user feedback',
    icon: IconEdit,
    index: 3,
  },
  {
    title: 'Roadmap Editor',
    description: 'Executes precise edits to roadmap structure based on analysis and feedback',
    icon: IconPencil,
    index: 4,
  },
  {
    title: 'Tutorial Generator',
    description: 'Creates in-depth tutorials with theory, examples, and exercises for each concept',
    icon: IconBook,
    index: 5,
  },
  {
    title: 'Resource Recommender',
    description: 'Curates the best external resources, articles, videos, and tools for each topic',
    icon: IconSearch,
    index: 6,
  },
  {
    title: 'Quiz Generator',
    description: 'Creates adaptive quizzes with various question types to test understanding',
    icon: IconCheckbox,
    index: 7,
  },
];

function AgentCard({ title, description, icon: Icon, index }: Agent) {
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
          {title}
        </span>
      </div>
      
      {/* 描述 */}
      <p className="text-sm text-muted-foreground max-w-xs relative z-10 px-10 leading-relaxed">
        {description}
      </p>
    </motion.div>
  );
}

export function AgentsGrid() {
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
            Powered by Multi-Agent AI
          </div>
          <h2 className="text-4xl md:text-5xl font-serif font-bold text-foreground mb-4">
            How It Works
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Eight specialized AI agents collaborate to create and deliver your personalized
            learning experience
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

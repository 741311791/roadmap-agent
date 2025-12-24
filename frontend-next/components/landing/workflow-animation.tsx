'use client';

/**
 * 工作流动画组件
 * 
 * 3-5秒循环展示简化的学习路线图生成流程：
 * 1. 输入目标
 * 2. AI 分析
 * 3. 生成路线图
 * 4. 学习成长
 * 
 * 使用 motion 实现流畅的线条和点的动画
 */

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { User, Brain, Map, TrendingUp } from 'lucide-react';

interface Step {
  id: number;
  title: string;
  description: string;
  icon: React.ElementType;
  color: string;
}

const steps: Step[] = [
  {
    id: 1,
    title: 'Input Your Goal',
    description: 'Tell us what you want to learn',
    icon: User,
    color: 'hsl(var(--sage))',
  },
  {
    id: 2,
    title: 'AI Analysis',
    description: 'AI understands your needs',
    icon: Brain,
    color: 'hsl(var(--sage))',
  },
  {
    id: 3,
    title: 'Generate Roadmap',
    description: 'Create personalized learning path',
    icon: Map,
    color: 'hsl(var(--sage))',
  },
  {
    id: 4,
    title: 'Learn & Grow',
    description: 'Master skills efficiently',
    icon: TrendingUp,
    color: 'hsl(var(--sage))',
  },
];

export function WorkflowAnimation() {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % steps.length);
    }, 4000); // 4秒切换一次

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative w-full max-w-5xl mx-auto py-12">
      {/* 连接线容器 */}
      <div className="relative h-48 flex items-center justify-between px-8">
        {/* 水平连接线 */}
        <svg
          className="absolute top-1/2 left-0 w-full h-1 -translate-y-1/2"
          style={{ zIndex: 0 }}
        >
          <motion.line
            x1="10%"
            y1="50%"
            x2="90%"
            y2="50%"
            stroke="hsl(var(--sage))"
            strokeWidth="2"
            strokeDasharray="8 8"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 0.3 }}
            transition={{ duration: 1, ease: 'easeInOut' }}
          />
        </svg>

        {/* 移动的点 */}
        <motion.div
          className="absolute top-1/2 w-3 h-3 rounded-full bg-sage -translate-y-1/2"
          style={{ zIndex: 1 }}
          animate={{
            left: ['8%', '32%', '56%', '82%', '8%'],
          }}
          transition={{
            duration: 16,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />

        {/* 步骤节点 */}
        {steps.map((step, index) => {
          const Icon = step.icon;
          const isActive = index === activeStep;
          const isPast = index < activeStep;

          return (
            <div
              key={step.id}
              className="relative flex flex-col items-center"
              style={{ zIndex: 2, width: '20%' }}
            >
              {/* 图标容器 */}
              <motion.div
                className={`w-20 h-20 rounded-2xl flex items-center justify-center border-2 transition-all duration-500 ${
                  isActive
                    ? 'bg-sage border-sage shadow-lg shadow-accent/30'
                    : isPast
                    ? 'bg-muted border-border'
                    : 'bg-card border-border'
                }`}
                animate={{
                  scale: isActive ? [1, 1.1, 1] : 1,
                }}
                transition={{
                  duration: 0.5,
                  ease: 'easeInOut',
                }}
              >
                <Icon
                  className={`w-8 h-8 transition-colors duration-300 ${
                    isActive ? 'text-white' : isPast ? 'text-sage' : 'text-muted-foreground'
                  }`}
                />

                {/* 脉冲效果 */}
                {isActive && (
                  <motion.div
                    className="absolute inset-0 rounded-2xl border-2 border-sage"
                    initial={{ scale: 1, opacity: 0.6 }}
                    animate={{ scale: 1.3, opacity: 0 }}
                    transition={{
                      duration: 1.5,
                      repeat: Infinity,
                      ease: 'easeOut',
                    }}
                  />
                )}
              </motion.div>

              {/* 步骤信息 */}
              <AnimatePresence mode="wait">
                {isActive && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.3 }}
                    className="absolute top-24 text-center w-40"
                  >
                    <h3 className="text-sm font-semibold text-foreground mb-1">
                      {step.title}
                    </h3>
                    <p className="text-xs text-muted-foreground">{step.description}</p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>

      {/* 进度指示器 */}
      <div className="flex justify-center gap-2 mt-16">
        {steps.map((_, index) => (
          <motion.div
            key={index}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              index === activeStep ? 'w-8 bg-sage' : 'w-1.5 bg-border'
            }`}
          />
        ))}
      </div>
    </div>
  );
}


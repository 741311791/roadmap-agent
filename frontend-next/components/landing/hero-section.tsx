'use client';

/**
 * Hero 区域组件
 * 
 * 特点：
 * - 大标题和副标题
 * - 工作流动画展示
 * - 邮箱订阅表单
 * - 渐变背景
 */

import React from 'react';
import { motion } from 'motion/react';
import { WorkflowAnimation } from './workflow-animation';
import { WaitlistForm } from '@/components/ui/waitlist-form';
import { joinWaitlist } from '@/lib/api/endpoints';

export function HeroSection() {
  const handleJoin = async (email: string) => {
    await joinWaitlist({ email, source: 'hero_section' });
  };

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden pt-16 pb-20 px-6">
      {/* Fluid Background */}
      <div className="absolute inset-0 overflow-hidden -z-10 pointer-events-none">
        <motion.div 
          animate={{ 
            x: [0, 100, 0],
            y: [0, -50, 0],
            rotate: [0, 45, 0],
            scale: [1, 1.2, 1]
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "linear"
          }}
          className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-sage/20 rounded-full blur-[100px] opacity-50" 
        />
        <motion.div 
          animate={{ 
            x: [0, -100, 0],
            y: [0, 100, 0],
            rotate: [0, -45, 0],
            scale: [1, 1.5, 1]
          }}
          transition={{
            duration: 25,
            repeat: Infinity,
            ease: "linear"
          }}
          className="absolute bottom-1/4 right-1/4 w-[600px] h-[600px] bg-primary/5 rounded-full blur-[120px] opacity-40" 
        />
      </div>

      <div className="max-w-7xl mx-auto w-full relative z-10 grid lg:grid-cols-2 gap-12 items-center">
        {/* 标题区域 - 左侧 */}
        <div className="text-center lg:text-left">
          {/* 主标题 */}
          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-5xl md:text-6xl lg:text-7xl font-serif font-semibold text-foreground leading-tight mb-6"
          >
            Master Any Skill
            <br />
            <span className="text-sage italic">Faster Than Ever</span>
          </motion.h1>

          {/* 副标题 */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="text-xl text-muted-foreground max-w-xl mx-auto lg:mx-0 mb-10 leading-relaxed"
          >
            AI creates personalized learning roadmaps that adapt to your goals, experience, and learning style.
          </motion.p>

          {/* Email Waitlist Form */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
            className="max-w-lg mx-auto lg:mx-0"
          >
            <WaitlistForm onSubmit={handleJoin} className="w-full" />
            
            <p className="text-sm text-muted-foreground mt-4 text-center lg:text-left pl-2">
              Join 2,400+ learners building their future
            </p>
          </motion.div>
        </div>

        {/* 工作流动画 - 右侧布局 */}
        <motion.div
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 1, delay: 0.4 }}
          className="relative lg:h-[600px] flex items-center justify-center lg:justify-end"
        >
          <WorkflowAnimation />
        </motion.div>
      </div>
    </section>
  );
}

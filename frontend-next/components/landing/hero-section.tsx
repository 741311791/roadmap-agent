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

import React, { useState } from 'react';
import { motion } from 'motion/react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ArrowRight, Sparkles } from 'lucide-react';
import { WorkflowAnimation } from './workflow-animation';

export function HeroSection() {
  const [email, setEmail] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: 实现 waitlist 提交逻辑
    console.log('Email submitted:', email);
  };

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden pt-16 pb-20 px-6">
      {/* 背景渐变 */}
      <div className="absolute inset-0 bg-gradient-to-b from-muted/30 via-background to-card -z-10" />
      
      {/* 装饰性粒子 */}
      <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-accent/10 rounded-full blur-3xl -z-10" />
      <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-accent/15 rounded-full blur-3xl -z-10" />

      <div className="max-w-7xl mx-auto w-full">
        {/* 标题区域 */}
        <div className="text-center mb-12">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-muted border border-border rounded-full text-sage text-sm font-medium mb-8"
          >
            <Sparkles className="w-4 h-4" />
            AI-Powered Learning Platform
          </motion.div>

          {/* 主标题 */}
          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-5xl md:text-7xl lg:text-8xl font-serif font-bold text-foreground leading-tight mb-6"
          >
            Master Any Skill
            <br />
            <span className="text-sage">Faster Than Ever</span>
          </motion.h1>

          {/* 副标题 */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto mb-8"
          >
            AI creates personalized learning roadmaps that adapt to your goals, experience, and learning style.
          </motion.p>

          {/* 邮箱订阅表单 */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
          >
            <form
              onSubmit={handleSubmit}
              className="flex flex-col sm:flex-row items-center justify-center gap-3 max-w-md mx-auto mb-4"
            >
              <Input
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-12 px-5 text-base glass-input w-full sm:flex-1"
                required
              />
              <Button
                type="submit"
                size="lg"
                className="h-12 px-8 btn-sage gap-2 w-full sm:w-auto"
              >
                Get Started
                <ArrowRight className="w-4 h-4" />
              </Button>
            </form>
            <p className="text-sm text-muted-foreground">
              Join 2,400+ learners building their future
            </p>
          </motion.div>
        </div>

        {/* 工作流动画 */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.8 }}
          className="mt-20"
        >
          <WorkflowAnimation />
        </motion.div>
      </div>
    </section>
  );
}


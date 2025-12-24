'use client';

/**
 * CTA (Call to Action) 区域组件
 * 
 * 特点：
 * - 使用全局 sage 色彩令牌
 * - 粒子效果
 * - 邮箱订阅表单
 * - 参考 methodology 页面设计
 */

import React, { useState } from 'react';
import { motion } from 'motion/react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Particles } from '@/components/ui/particles';
import { ArrowRight } from 'lucide-react';

export function CTASection() {
  const [email, setEmail] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: 实现 waitlist 提交逻辑
    console.log('Email submitted:', email);
  };

  return (
    <section className="py-24 px-6 relative overflow-hidden bg-sage">
      {/* 背景渐变 */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-accent/30 via-transparent to-transparent -z-10" />
      
      {/* 纸质纹理 */}
      <div className="absolute inset-0 opacity-[0.03] bg-noise -z-10" />
      
      {/* 粒子背景效果 */}
      <Particles
        className="absolute inset-0"
        quantity={80}
        ease={50}
        color="#ffffff"
        refresh={false}
      />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="max-w-4xl mx-auto text-center relative z-10"
      >
        <h2 className="text-4xl md:text-5xl font-serif font-bold text-white mb-6">
          Start Your Learning Journey Today
        </h2>
        <p className="text-xl text-white/95 mb-10 max-w-2xl mx-auto">
          Join thousands of learners building their future with AI-powered personalized roadmaps
        </p>

        <form
          onSubmit={handleSubmit}
          className="flex flex-col sm:flex-row items-center justify-center gap-3 max-w-md mx-auto mb-6"
        >
          <Input
            type="email"
            placeholder="Enter your email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="h-12 px-5 text-base bg-card/98 border-0 rounded-xl w-full sm:flex-1 shadow-lg focus:shadow-xl transition-shadow"
            required
          />
          <Button
            type="submit"
            size="lg"
            className="h-12 px-8 rounded-xl font-semibold gap-2 bg-card text-sage hover:bg-card/90 w-full sm:w-auto shadow-lg hover:shadow-xl transition-all hover:scale-105 relative overflow-hidden group"
          >
            <span className="relative z-10">Get Started</span>
            <ArrowRight className="w-4 h-4 relative z-10" />
            {/* 光晕效果 */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-muted/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          </Button>
        </form>

        <p className="text-sm text-white/80">
          No credit card required · Start learning in minutes
        </p>

        {/* 或者直接开始 */}
        <div className="mt-8 pt-8 border-t border-white/20">
          <p className="text-white/90 mb-4">Already have an account?</p>
          <Link href="/login">
            <Button
              variant="outline"
              className="border-white/30 text-white hover:bg-white/10 hover:border-white/50"
            >
              Sign In
            </Button>
          </Link>
        </div>
      </motion.div>
    </section>
  );
}

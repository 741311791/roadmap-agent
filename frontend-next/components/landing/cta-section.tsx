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

import React from 'react';
import { motion } from 'motion/react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Particles } from '@/components/ui/particles';
import { WaitlistForm } from '@/components/ui/waitlist-form';
import { joinWaitlist } from '@/lib/api/endpoints';

export function CTASection() {
  const handleJoin = async (email: string) => {
    await joinWaitlist({ email, source: 'cta_section' });
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

        <div className="max-w-md mx-auto mb-6 text-left">
          <WaitlistForm onSubmit={handleJoin} className="w-full" />
        </div>

        <p className="text-sm text-white/80">
          No credit card required · Start learning in minutes
        </p>

        {/* 或者直接开始 */}
        <div className="mt-8 pt-8 border-t border-white/20">
          <p className="text-white/90 mb-4">Already have an account?</p>
          <Link href="/login">
            <Button
              variant="outline"
              className="bg-white/5 border-white/50 text-white hover:bg-white/15 hover:border-white"
            >
              Sign In
            </Button>
          </Link>
        </div>
      </motion.div>
    </section>
  );
}

'use client';

/**
 * 落地页主页
 * 
 * 使用 Motion 和 Magic UI 设计风格
 * 杂志风格 + 流畅的点线动画
 * 
 * 注意：Header 和 Footer 由 (marketing)/layout.tsx 统一管理
 */

import React from 'react';
import { HeroSection } from '@/components/landing/hero-section';
import { FeaturesSection } from '@/components/landing/features-section';
import { AgentsGrid } from '@/components/landing/agents-grid';
import { TestimonialsSection } from '@/components/landing/testimonials';
import { CTASection } from '@/components/landing/cta-section';

export default function LandingPage() {
  return (
    <>
      {/* Hero 区域 */}
      <HeroSection />

      {/* Features 区域 */}
      <FeaturesSection />

      {/* How It Works 区域 */}
      <AgentsGrid />

      {/* Social Proof 区域 */}
      <TestimonialsSection />

      {/* CTA 区域 */}
      <CTASection />
    </>
  );
}

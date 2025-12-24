'use client';

/**
 * 落地页 Mockup - 重构版
 * 
 * 使用 Motion 和 Magic UI 设计风格
 * 杂志风格 + 流畅的点线动画
 */

import React from 'react';
import { Navigation } from '@/components/landing/navigation';
import { HeroSection } from '@/components/landing/hero-section';
import { FeaturesSection } from '@/components/landing/features-section';
import { AgentsGrid } from '@/components/landing/agents-grid';
import { TestimonialsSection } from '@/components/landing/testimonials';
import { CTASection } from '@/components/landing/cta-section';
import { Footer } from '@/components/landing/footer';

export default function MockupPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* 导航栏区域 */}
      <Navigation />

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

      {/* Footer 区域 */}
      <Footer />
    </div>
  );
}

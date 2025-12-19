'use client';

import Link from 'next/link';
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ArrowRight, Sparkles, BookOpen, Brain, Zap, Target, Clock, Users, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { joinWaitlist } from '@/lib/api/endpoints';
import AnimatedShaderHero from '@/components/ui/animated-shader-hero';
import { WaitlistForm } from '@/components/ui/waitlist-form';
import { TextAnimate } from '@/components/ui/text-animate';
import { LearningPathDemo } from '@/components/ui/learning-path-demo';
import { BlurFade } from '@/components/ui/blur-fade';
import { BentoGrid, BentoCard } from '@/components/ui/bento-grid';
import { BorderBeam } from '@/components/ui/border-beam';
import { Particles } from '@/components/ui/particles';
import { ScrollProgress } from '@/components/ui/scroll-progress';

/**
 * Fast Learning 首页
 * 
 * 特点:
 * - 动态 WebGL Shader Hero
 * - 高端杂志风格设计
 * - Motion 动画效果
 * - Join Waitlist 功能
 * - 突出 Fast Learning 理念
 */

export default function LandingPage() {
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showThankYouDialog, setShowThankYouDialog] = useState(false);
  const [isNewUser, setIsNewUser] = useState(true);

  const handleJoinWaitlist = async (emailAddress: string) => {
    // 简单的邮箱格式验证
    if (!emailAddress || !emailAddress.includes('@')) {
      toast.error('Please enter a valid email address');
      throw new Error('Invalid email');
    }
    
    setIsSubmitting(true);
    
    try {
      const response = await joinWaitlist({
        email: emailAddress.toLowerCase().trim(),
        source: 'landing_page',
      });
      
      setIsNewUser(response.is_new);
      setEmail('');
    } catch (error) {
      console.error('Failed to join waitlist:', error);
      toast.error('Something went wrong. Please try again later.');
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* 全局滚动进度指示器 */}
      <ScrollProgress />
      
      {/* 感谢加入候补名单弹窗 */}
      <Dialog open={showThankYouDialog} onOpenChange={setShowThankYouDialog}>
        <DialogContent className="sm:max-w-md bg-card border-border">
          <DialogHeader className="text-center sm:text-center">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 200, damping: 15 }}
              className="mx-auto mb-4 w-16 h-16 bg-sage-100 rounded-full flex items-center justify-center"
            >
              <CheckCircle2 className="w-8 h-8 text-sage-600" />
            </motion.div>
            <DialogTitle className="text-2xl font-serif font-bold text-foreground">
              {isNewUser ? "You're on the List!" : "Welcome Back!"}
            </DialogTitle>
            <DialogDescription className="text-base text-muted-foreground mt-2">
              {isNewUser 
                ? "Thank you for your interest in Fast Learning. We'll notify you as soon as access becomes available."
                : "You're already on our waitlist. We'll be in touch soon!"
              }
            </DialogDescription>
          </DialogHeader>
          <div className="mt-6 flex flex-col gap-4">
            <div className="p-4 bg-sage-50/50 rounded-xl border border-sage-200/50">
              <p className="text-sm text-muted-foreground text-center">
                In the meantime, follow us for updates and learning tips.
              </p>
            </div>
            <Button
              onClick={() => setShowThankYouDialog(false)}
              variant="sage"
              className="w-full h-11 font-semibold"
            >
              Got it, Thanks!
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* 背景 - 简洁统一 */}
      <div className="fixed inset-0 bg-background -z-10" />
      {/* 纸质纹理效果 */}
      <div className="fixed inset-0 opacity-[0.015] bg-noise -z-10" />
      
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/90 backdrop-blur-md border-b border-border">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 bg-sage-500 rounded-full flex items-center justify-center shadow-sm group-hover:shadow-md transition-all group-hover:scale-105">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="font-serif font-bold text-xl tracking-tight text-foreground">Fast Learning</span>
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <Link href="/methodology" className="text-sm text-muted-foreground hover:text-foreground transition-colors font-medium">
              Methodology
            </Link>
            <Link href="/pricing" className="text-sm text-muted-foreground hover:text-foreground transition-colors font-medium">
              Pricing
            </Link>
            <Link href="/about" className="text-sm text-muted-foreground hover:text-foreground transition-colors font-medium">
              About
            </Link>
            <Link href="/login">
              <Button variant="outline" size="sm" className="font-medium border-sage-300 hover:border-sage-400 hover:bg-sage-50">
                Login
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section with Animated Shader */}
      <section className="relative w-full h-screen overflow-hidden bg-gradient-to-b from-background via-sage-50/30 to-background">
        {/* Shader Background - Fixed to viewport */}
        <AnimatedShaderHero className="h-screen">
          <div className="relative w-full h-full flex flex-col items-center justify-center pt-16 pb-8 px-6">
            <div className="text-center space-y-6 max-w-5xl mx-auto">
              {/* Animated Headline */}
              <div className="space-y-4">
                <TextAnimate
                  animation="blurInUp"
                  by="word"
                  delay={0.2}
                  duration={0.8}
                  className="text-5xl md:text-7xl font-serif font-bold text-sage-900 leading-tight"
                >
                  Master Any Skill
                </TextAnimate>
                <TextAnimate
                  animation="blurInUp"
                  by="word"
                  delay={0.5}
                  duration={0.8}
                  className="text-5xl md:text-7xl font-serif font-bold text-sage-800 leading-tight"
                >
                  Faster Than Ever
                </TextAnimate>
              </div>

              {/* Subtitle */}
              <TextAnimate
                animation="fadeIn"
                by="word"
                delay={1}
                duration={0.6}
                className="text-xl md:text-2xl text-sage-700 max-w-3xl mx-auto font-light"
              >
                Systematic Structure. Personalized Path. Real-time Evolution.
              </TextAnimate>

              {/* Enhanced Waitlist Form */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.5, duration: 0.5 }}
                className="mt-10"
              >
                <WaitlistForm 
                  onSubmit={handleJoinWaitlist}
                  isSubmitting={isSubmitting}
                />
              </motion.div>
            </div>
          </div>
        </AnimatedShaderHero>
      </section>

      {/* Learning Path Demo Section - Below Hero */}
      <section className="relative z-20 bg-gradient-to-b from-background via-background to-background py-24 px-6">
        <LearningPathDemo />
      </section>

      {/* Key Benefits Section - Bento Grid */}
      <section className="py-24 px-6 bg-gradient-to-b from-background to-sage-50/20">
        <div className="max-w-7xl mx-auto">
          <BlurFade delay={0.1} inView>
            <div className="text-center mb-16">
              <h2 className="text-4xl md:text-5xl font-serif font-bold text-foreground mb-4">
                Why Fast Learning Works
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Traditional learning is slow and passive. We flip the script with AI-powered 
                active learning that adapts to you.
              </p>
            </div>
          </BlurFade>

          <BentoGrid className="auto-rows-[20rem] md:grid-cols-3">
            <BlurFade delay={0.2} inView>
              <BentoCard
                name="Precision Learning"
                className="col-span-3 md:col-span-2 relative overflow-hidden group"
                background={
                  <div className="absolute inset-0 bg-gradient-to-br from-sage-100 via-sage-50 to-transparent opacity-60" />
                }
                Icon={Target}
                description="AI identifies your knowledge gaps and creates targeted strategies to fill them efficiently. No more wasted time on what you already know."
              />
            </BlurFade>
            
            <BlurFade delay={0.3} inView>
              <BentoCard
                name="Learn by Doing"
                className="col-span-3 md:col-span-1 relative overflow-hidden group"
                background={
                  <div className="absolute inset-0 bg-gradient-to-br from-sage-50 to-transparent opacity-40" />
                }
                Icon={Brain}
                description="Start building from day one. Our AI guides you through real projects, not endless tutorials."
              />
            </BlurFade>

            <BlurFade delay={0.4} inView>
              <BentoCard
                name="Accelerated Mastery"
                className="col-span-3 md:col-span-1 relative overflow-hidden group"
                background={
                  <div className="absolute inset-0 bg-gradient-to-br from-sage-50 to-transparent opacity-40" />
                }
                Icon={Clock}
                description="Structured roadmaps with clear milestones help you achieve competence in record time."
              />
            </BlurFade>

            <BlurFade delay={0.5} inView>
              <BentoCard
                name="AI-Powered Adaptation"
                className="col-span-3 md:col-span-2 relative overflow-hidden group"
                background={
                  <div className="absolute inset-0 bg-gradient-to-br from-sage-100 via-sage-50 to-transparent opacity-60" />
                }
                Icon={Zap}
                description="Your learning path evolves as you progress. The AI continuously optimizes your journey based on your performance and feedback."
              />
            </BlurFade>
          </BentoGrid>
        </div>
      </section>

      {/* How It Works Section - 3D Scroll Animation */}
      <section className="py-24 px-6 relative">
        <div className="max-w-6xl mx-auto">
          <BlurFade delay={0.1} inView>
            <div className="text-center mb-20">
              <h2 className="text-4xl md:text-5xl font-serif font-bold text-foreground mb-4">
                Your Learning Journey
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                From goal to mastery in four simple steps
              </p>
            </div>
          </BlurFade>

          <div className="relative">
            {/* Connecting Line */}
            <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-gradient-to-b from-sage-200 via-sage-300 to-sage-200 hidden md:block" />
            
            <div className="space-y-24">
              <BlurFade delay={0.2} inView>
                <motion.div
                  initial={{ opacity: 0, x: -50, rotateY: -15 }}
                  whileInView={{ opacity: 1, x: 0, rotateY: 0 }}
                  viewport={{ once: true, margin: "-100px" }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                  className="relative"
                  style={{ transformStyle: "preserve-3d" }}
                >
                  <StepCard3D
                    number={1}
                    title="Set Your Goal"
                    description="Tell us what you want to learn and your current experience level. Our AI analyzes your background to create the perfect starting point."
                    align="left"
                  />
                </motion.div>
              </BlurFade>

              <BlurFade delay={0.3} inView>
                <motion.div
                  initial={{ opacity: 0, x: 50, rotateY: 15 }}
                  whileInView={{ opacity: 1, x: 0, rotateY: 0 }}
                  viewport={{ once: true, margin: "-100px" }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                  className="relative"
                  style={{ transformStyle: "preserve-3d" }}
                >
                  <StepCard3D
                    number={2}
                    title="Get Your Roadmap"
                    description="AI creates a personalized curriculum with stages, modules, and concepts. Each step builds on the last for optimal learning."
                    align="right"
                  />
                </motion.div>
              </BlurFade>

              <BlurFade delay={0.4} inView>
                <motion.div
                  initial={{ opacity: 0, x: -50, rotateY: -15 }}
                  whileInView={{ opacity: 1, x: 0, rotateY: 0 }}
                  viewport={{ once: true, margin: "-100px" }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                  className="relative"
                  style={{ transformStyle: "preserve-3d" }}
                >
                  <StepCard3D
                    number={3}
                    title="Learn & Build"
                    description="Work through tutorials, quizzes, and hands-on projects at your pace. Practice makes perfect with real-world applications."
                    align="left"
                  />
                </motion.div>
              </BlurFade>

              <BlurFade delay={0.5} inView>
                <motion.div
                  initial={{ opacity: 0, x: 50, rotateY: 15 }}
                  whileInView={{ opacity: 1, x: 0, rotateY: 0 }}
                  viewport={{ once: true, margin: "-100px" }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                  className="relative"
                  style={{ transformStyle: "preserve-3d" }}
                >
                  <StepCard3D
                    number={4}
                    title="Achieve Mastery"
                    description="Track progress, get AI assistance, and reach your learning goals. Celebrate milestones as you become an expert."
                    align="right"
                  />
                </motion.div>
              </BlurFade>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid - Enhanced */}
      <section className="py-24 px-6 bg-sage-50/30 relative overflow-hidden">
        {/* Subtle particle background */}
        <Particles
          className="absolute inset-0"
          quantity={30}
          ease={80}
          color="#7d8f7d"
          refresh={false}
        />
        
        <div className="max-w-6xl mx-auto relative z-10">
          <BlurFade delay={0.1} inView>
            <div className="text-center mb-16">
              <h2 className="text-4xl md:text-5xl font-serif font-bold text-foreground mb-4">
                Everything You Need to Learn Fast
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Comprehensive tools and AI-powered features to accelerate your learning journey
              </p>
            </div>
          </BlurFade>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <BlurFade delay={0.2} inView>
              <FeatureCardEnhanced
                icon={BookOpen}
                title="AI-Generated Tutorials"
                description="In-depth content tailored to your level with real-world examples."
              />
            </BlurFade>
            <BlurFade delay={0.3} inView>
              <FeatureCardEnhanced
                icon={Sparkles}
                title="Adaptive Quizzes"
                description="Test your understanding with questions that adapt to your progress."
              />
            </BlurFade>
            <BlurFade delay={0.4} inView>
              <FeatureCardEnhanced
                icon={Zap}
                title="Curated Resources"
                description="The best articles, videos, and tools handpicked by AI for each topic."
              />
            </BlurFade>
            <BlurFade delay={0.5} inView>
              <FeatureCardEnhanced
                icon={Brain}
                title="Knowledge Graphs"
                description="Visualize connections between concepts and track your understanding."
              />
            </BlurFade>
            <BlurFade delay={0.6} inView>
              <FeatureCardEnhanced
                icon={Users}
                title="AI Mentor"
                description="Get explanations using everyday analogies. Ask anything, anytime."
              />
            </BlurFade>
            <BlurFade delay={0.7} inView>
              <FeatureCardEnhanced
                icon={Target}
                title="Progress Tracking"
                description="Clear milestones and completion tracking to keep you motivated."
              />
            </BlurFade>
          </div>
        </div>
      </section>

      {/* CTA Section - 奶油杂志风格 with 粒子效果 */}
      <section className="py-24 px-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-sage-500 to-sage-600 -z-10" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-sage-400/30 via-transparent to-transparent -z-10" />
        {/* 纸质纹理 */}
        <div className="absolute inset-0 opacity-[0.03] bg-noise -z-10" />
        {/* 粒子背景效果 - sage 色调 */}
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
          <BlurFade delay={0.1} inView>
            <h2 className="text-4xl md:text-5xl font-serif font-bold text-white mb-6">
              Ready to Learn Faster?
            </h2>
          </BlurFade>
          <BlurFade delay={0.2} inView>
            <p className="text-xl text-white/95 mb-10 max-w-2xl mx-auto">
              Join the waitlist and be among the first to experience 
              AI-powered learning that actually works.
            </p>
          </BlurFade>
          <BlurFade delay={0.3} inView>
            <form 
              onSubmit={async (e) => {
                e.preventDefault();
                if (email) {
                  try {
                    await handleJoinWaitlist(email);
                    setShowThankYouDialog(true);
                  } catch (error) {
                    // Error already handled in handleJoinWaitlist
                  }
                }
              }} 
              className="flex flex-col sm:flex-row items-center justify-center gap-3 max-w-md mx-auto"
            >
              <div className="relative w-full sm:w-80">
                <Input
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-12 px-5 text-base bg-white/98 border-0 rounded-xl w-full shadow-lg focus:shadow-xl transition-shadow"
                  disabled={isSubmitting}
                />
              </div>
              <div className="relative w-full sm:w-auto group">
                <Button
                  type="submit"
                  size="lg"
                  className="h-12 px-8 rounded-xl font-semibold gap-2 bg-white text-sage-600 hover:bg-white hover:text-sage-700 w-full sm:w-auto shadow-lg hover:shadow-xl transition-all hover:scale-105 relative overflow-hidden"
                  disabled={isSubmitting}
                >
                  <span className="relative z-10">
                    {isSubmitting ? 'Joining...' : 'Join Waitlist'}
                  </span>
                  <ArrowRight className="w-4 h-4 relative z-10" />
                  {/* 光晕效果 */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-sage-100/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 group-hover:animate-shimmer" />
                </Button>
              </div>
            </form>
          </BlurFade>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="py-16 px-6 border-t border-border">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-sage-500 rounded-full flex items-center justify-center shadow-sm">
                <Brain className="w-4 h-4 text-white" />
              </div>
              <span className="font-serif font-bold text-lg text-foreground">Fast Learning</span>
            </div>
            <div className="flex items-center gap-8 text-sm text-muted-foreground">
              <Link href="/methodology" className="hover:text-foreground transition-colors">
                Methodology
              </Link>
              <Link href="/pricing" className="hover:text-foreground transition-colors">
                Pricing
              </Link>
              <Link href="/about" className="hover:text-foreground transition-colors">
                About
              </Link>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t border-border/50 text-center text-sm text-muted-foreground">
            © 2024 Fast Learning. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}

/**
 * BenefitCard - 核心优势卡片
 */
function BenefitCard({
  icon: Icon,
  title,
  description,
  delay = 0,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      className="p-8 rounded-2xl border border-border bg-card shadow-sm hover:shadow-md transition-all hover:-translate-y-1"
    >
      <div className="w-14 h-14 rounded-xl bg-sage-100/80 flex items-center justify-center mb-6">
        <Icon className="w-7 h-7 text-sage-600" />
      </div>
      <h3 className="text-xl font-serif font-semibold text-foreground mb-3">
        {title}
      </h3>
      <p className="text-muted-foreground leading-relaxed">{description}</p>
    </motion.div>
  );
}

/**
 * StepCard - 流程步骤卡片
 */
function StepCard({
  number,
  title,
  description,
  delay = 0,
}: {
  number: number;
  title: string;
  description: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      className="text-center"
    >
      <div className="w-12 h-12 rounded-full bg-sage-500 text-white flex items-center justify-center font-serif font-bold text-lg mx-auto mb-4 shadow-sm">
        {number}
      </div>
      <h3 className="text-lg font-serif font-semibold text-foreground mb-2">
        {title}
      </h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
    </motion.div>
  );
}

function StepCard3D({
  number,
  title,
  description,
  align = "left",
}: {
  number: number;
  title: string;
  description: string;
  align?: "left" | "right";
}) {
  return (
    <div className={`flex items-center gap-8 ${align === "right" ? "md:flex-row-reverse" : ""}`}>
      <div className={`flex-1 ${align === "right" ? "md:text-right" : ""}`}>
        <div className="relative p-8 rounded-2xl bg-card border border-border shadow-lg hover:shadow-xl transition-all group">
          <BorderBeam size={100} duration={12} delay={number * 2} />
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-14 h-14 rounded-full bg-gradient-to-br from-sage-500 to-sage-600 text-white flex items-center justify-center font-serif font-bold text-xl shadow-md">
              {number}
            </div>
            <div className="flex-1">
              <h3 className="text-2xl font-serif font-bold text-foreground mb-3 group-hover:text-sage-700 transition-colors">
                {title}
              </h3>
              <p className="text-base text-muted-foreground leading-relaxed">
                {description}
              </p>
            </div>
          </div>
        </div>
      </div>
      <div className="hidden md:block w-8 h-8 rounded-full bg-sage-500 border-4 border-background shadow-md relative z-10" />
      <div className="flex-1 hidden md:block" />
    </div>
  );
}

/**
 * FeatureCard - 功能特性卡片
 */
function FeatureCard({
  icon: Icon,
  title,
  description,
  delay = 0,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      className="p-6 rounded-xl border border-border bg-card hover:shadow-md transition-all hover:-translate-y-0.5 group"
    >
      <div className="w-11 h-11 rounded-lg bg-sage-50/80 group-hover:bg-sage-100/80 flex items-center justify-center mb-4 transition-colors">
        <Icon className="w-5 h-5 text-sage-600" />
      </div>
      <h3 className="text-lg font-serif font-semibold text-foreground mb-2">
        {title}
      </h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
    </motion.div>
  );
}

/**
 * FeatureCardEnhanced - 增强版功能卡片，带有 BorderBeam 效果
 */
function FeatureCardEnhanced({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.5 }}
      className="relative p-8 rounded-2xl border border-border bg-card/80 backdrop-blur-sm hover:shadow-xl transition-all hover:-translate-y-1 group overflow-hidden"
    >
      {/* BorderBeam 效果 */}
      <BorderBeam 
        size={120} 
        duration={15} 
        borderWidth={1.5}
        colorFrom="#7d8f7d"
        colorTo="#a8b8a8"
      />
      
      {/* 悬停时的背景渐变效果 */}
      <div className="absolute inset-0 bg-gradient-to-br from-sage-50/0 via-sage-50/0 to-sage-100/0 group-hover:from-sage-50/40 group-hover:via-sage-50/20 group-hover:to-sage-100/40 transition-all duration-500 rounded-2xl -z-10" />
      
      <div className="relative z-10">
        <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-sage-100 to-sage-50 group-hover:from-sage-200 group-hover:to-sage-100 flex items-center justify-center mb-5 transition-all duration-300 shadow-sm group-hover:shadow-md group-hover:scale-110">
          <Icon className="w-7 h-7 text-sage-600 group-hover:text-sage-700 transition-colors" />
        </div>
        <h3 className="text-xl font-serif font-bold text-foreground mb-3 group-hover:text-sage-700 transition-colors">
          {title}
        </h3>
        <p className="text-base text-muted-foreground leading-relaxed">
          {description}
        </p>
      </div>
    </motion.div>
  );
}

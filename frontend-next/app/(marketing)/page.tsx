'use client';

import Link from 'next/link';
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ArrowRight, Sparkles, BookOpen, Brain, Zap, Target, Clock, Users } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';

/**
 * Fast Learning 首页
 * 
 * 特点:
 * - 高端杂志风格设计
 * - Motion 动画效果
 * - Join Waitlist 功能
 * - 突出 Fast Learning 理念
 */

/**
 * 知识粒子球组件 - 奶油杂志风格
 */
function KnowledgeSphere() {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isHovering, setIsHovering] = useState(false);

  // 生成粒子位置（球面分布算法）
  const particles = React.useMemo(() => {
    const particleCount = 50; // 减少粒子数以更精致
    const particles = [];
    
    for (let i = 0; i < particleCount; i++) {
      // 使用 Fibonacci Sphere 算法实现均匀分布
      const phi = Math.acos(-1 + (2 * i) / particleCount);
      const theta = Math.sqrt(particleCount * Math.PI) * phi;
      
      // 不同半径创建多层
      const layer = Math.floor(i / 17);
      const radius = 32 + layer * 9; // 调整半径分布
      
      const x = 50 + radius * Math.cos(theta) * Math.sin(phi);
      const y = 50 + radius * Math.sin(theta) * Math.sin(phi);
      const z = Math.cos(phi); // -1 to 1 (用于深度感)
      
      particles.push({
        id: i,
        x,
        y,
        z,
        layer,
        size: z > 0 ? 10 : 7, // 前景粒子更大
        brightness: (z + 1) / 2, // 0 到 1
      });
    }
    return particles;
  }, []);

  // 生成连接线（距离近的粒子连接）
  const connections = React.useMemo(() => {
    const connections = [];
    const maxDistance = 28; // 连接阈值
    
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < maxDistance) {
          connections.push({
            from: particles[i],
            to: particles[j],
            opacity: (1 - distance / maxDistance) * 0.25,
          });
        }
      }
    }
    return connections;
  }, [particles]);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setMousePosition({
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    });
  };

  return (
    <div 
      className="relative h-[400px] md:h-[500px] flex items-center justify-center"
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {/* 中央核心光晕 */}
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
        <motion.div
          className="w-20 h-20 md:w-28 md:h-28 rounded-full bg-sage-400/20 blur-3xl"
          animate={{
            scale: isHovering ? [1, 1.2, 1] : [1, 1.08, 1],
            opacity: [0.2, 0.35, 0.2],
          }}
          transition={{
            duration: 6,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      </div>

      <motion.div 
        animate={{ rotate: 360 }}
        transition={{ duration: 150, repeat: Infinity, ease: "linear" }}
        className="relative w-full h-full max-w-[400px] max-h-[400px] md:max-w-[480px] md:max-h-[480px]"
      >
        {/* SVG 容器 - 用于绘制连接线 */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
          <defs>
            {/* 发光效果滤镜 */}
            <filter id="sphereGlow">
              <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>

          {/* 绘制连接线 */}
          {connections.map((conn, i) => (
            <motion.line
              key={i}
              x1={`${conn.from.x}%`}
              y1={`${conn.from.y}%`}
              x2={`${conn.to.x}%`}
              y2={`${conn.to.y}%`}
              stroke="hsl(var(--sage))"
              strokeWidth="1"
              strokeOpacity={conn.opacity}
              initial={{ pathLength: 0 }}
              animate={{ 
                pathLength: 1,
                strokeOpacity: isHovering ? conn.opacity * 1.6 : conn.opacity,
              }}
              transition={{ 
                pathLength: { duration: 3.5, delay: i * 0.012, ease: "easeInOut" },
                strokeOpacity: { duration: 0.8, ease: "easeInOut" }
              }}
            />
          ))}

          {/* 轨道圈 */}
          {[28, 38, 48].map((r, i) => (
            <circle
              key={i}
              cx="50%"
              cy="50%"
              r={`${r}%`}
              stroke="hsl(var(--sage))"
              strokeWidth="0.5"
              fill="none"
              opacity={0.04 + i * 0.02}
              strokeDasharray="5 10"
            >
              <animateTransform
                attributeName="transform"
                type="rotate"
                from={`0 250 250`}
                to={`${360 * (i % 2 === 0 ? 1 : -1)} 250 250`}
                dur={`${60 + i * 20}s`}
                repeatCount="indefinite"
              />
            </circle>
          ))}
        </svg>

        {/* 粒子节点 */}
        {particles.map((particle) => {
          const distanceToMouse = isHovering
            ? Math.sqrt(
                Math.pow(particle.x - mousePosition.x, 2) +
                Math.pow(particle.y - mousePosition.y, 2)
              )
            : 100;
          const isNearMouse = distanceToMouse < 18;

          return (
            <motion.div
              key={particle.id}
              className="absolute rounded-full"
              style={{
                top: `${particle.y}%`,
                left: `${particle.x}%`,
                width: `${particle.size}px`,
                height: `${particle.size}px`,
                transform: 'translate(-50%, -50%)',
                zIndex: Math.floor(particle.brightness * 10),
              }}
              animate={{
                scale: isNearMouse ? [1, 1.6, 1.4] : [1, 1.1, 1],
                opacity: particle.brightness * 0.45 + 0.35,
              }}
              transition={{
                scale: {
                  duration: isNearMouse ? 0.6 : 4.5 + Math.random() * 2.5,
                  repeat: Infinity,
                  ease: "easeInOut",
                },
                opacity: {
                  duration: 5.5 + Math.random() * 2,
                  repeat: Infinity,
                  repeatType: "reverse",
                  ease: "easeInOut",
                },
              }}
            >
              {/* 粒子核心 */}
              <div 
                className="absolute inset-0 rounded-full"
                style={{
                  backgroundColor: 'hsl(var(--sage))',
                  boxShadow: `0 0 ${isNearMouse ? '16px' : '8px'} hsla(var(--sage), ${particle.brightness * 0.6})`,
                }}
              />
              
              {/* 粒子光晕 */}
              <motion.div
                className="absolute inset-0 rounded-full blur-sm"
                style={{
                  backgroundColor: 'hsl(var(--sage))',
                }}
                animate={{
                  scale: [1, 1.4, 1],
                  opacity: [0.25, 0.12, 0.25],
                }}
                transition={{
                  duration: 4.5,
                  repeat: Infinity,
                  delay: particle.id * 0.04,
                  ease: "easeInOut",
                }}
              />

              {/* 脉冲波纹（前景粒子特效）*/}
              {particle.z > 0.5 && (
                <motion.div
                  className="absolute inset-0 rounded-full border"
                  style={{
                    borderColor: 'hsl(var(--sage))',
                  }}
                  initial={{ scale: 1, opacity: 0.35 }}
                  animate={{
                    scale: [1, 2.4],
                    opacity: [0.35, 0],
                  }}
                  transition={{
                    duration: 4,
                    repeat: Infinity,
                    delay: particle.id * 0.08,
                    ease: "easeOut",
                  }}
                />
              )}
            </motion.div>
          );
        })}

        {/* 能量流动路径（随机出现的流光）*/}
        {[...Array(3)].map((_, i) => (
          <motion.div
            key={`flow-${i}`}
            className="absolute w-1 h-1 rounded-full blur-sm"
            style={{
              top: `${50 + 35 * Math.sin(i * 2.1)}%`,
              left: `${50 + 35 * Math.cos(i * 2.1)}%`,
              backgroundColor: 'hsl(var(--sage))',
            }}
            animate={{
              x: [0, Math.random() * 70 - 35, 0],
              y: [0, Math.random() * 70 - 35, 0],
              opacity: [0, 0.5, 0],
              scale: [0, 1.3, 0],
            }}
            transition={{
              duration: 7 + Math.random() * 3,
              repeat: Infinity,
              delay: i * 2.5,
              ease: "easeInOut",
            }}
          />
        ))}
      </motion.div>
    </div>
  );
}

export default function LandingPage() {
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleJoinWaitlist = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // 简单的邮箱格式验证
    if (!email || !email.includes('@')) {
      toast.error('Please enter a valid email address');
      return;
    }
    
    setIsSubmitting(true);
    
    // 模拟提交延迟
    await new Promise(resolve => setTimeout(resolve, 800));
    
    toast.success('Thank you for joining! We\'ll be in touch soon.');
    setEmail('');
    setIsSubmitting(false);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* 动态背景 - 奶油杂志风格 */}
      <div className="fixed inset-0 bg-gradient-to-br from-[#f5f0e8] via-background to-[#f8f4ed] -z-10" />
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-sage-100/15 via-transparent to-transparent -z-10" />
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
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-16 md:pb-24 px-6 relative overflow-hidden">
        {/* 背景光晕效果 - 柔和的奶油色调 */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-sage-200/20 rounded-full blur-[128px] animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[#e8dcc8]/30 rounded-full blur-[128px] animate-pulse delay-1000" />
        
        <div className="max-w-7xl mx-auto relative z-10">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            {/* 左侧：文本内容 */}
            <motion.div 
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className="space-y-8 text-center lg:text-left"
            >
              {/* Animated Badge */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="inline-flex items-center gap-2 px-4 py-2 bg-sage-50/80 border border-sage-300/50 rounded-full text-sage-700 text-sm font-medium shadow-sm"
              >
                <Sparkles className="w-4 h-4" />
                AI-Powered Rapid Skill Acquisition
              </motion.div>

              {/* Main Heading */}
              <h1 className="text-5xl md:text-6xl lg:text-7xl font-serif font-bold text-foreground leading-[1.1]">
                Master Any Skill{' '}
                <span className="text-sage-600 relative inline-block">
                  Faster
                  <svg className="absolute -bottom-2 left-0 w-full" viewBox="0 0 200 12" xmlns="http://www.w3.org/2000/svg">
                    <path d="M2 8 Q 50 2, 100 6 Q 150 10, 198 4" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round" className="text-sage-300"/>
                  </svg>
                </span>
              </h1>

              {/* Subtitle */}
              <p className="text-xl text-muted-foreground leading-relaxed max-w-xl lg:max-w-none">
                Learn through practice, not theory. Our AI creates personalized roadmaps 
                that get you building real projects from day one.
              </p>

              {/* Join Waitlist Form */}
              <form
                onSubmit={handleJoinWaitlist}
                className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 max-w-md mx-auto lg:mx-0"
              >
                <Input
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-12 px-5 text-base bg-card border-border focus:border-sage-400 focus:ring-sage-400/20 rounded-xl flex-1 shadow-sm"
                  disabled={isSubmitting}
                />
                <Button
                  type="submit"
                  variant="sage"
                  size="lg"
                  className="h-12 px-6 rounded-xl font-semibold gap-2 shadow-sm hover:shadow-md transition-all whitespace-nowrap"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Joining...' : 'Join Waitlist'}
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </form>

              <p className="text-xs text-muted-foreground">
                Be the first to experience the future of learning. No spam, ever.
              </p>
            </motion.div>

            {/* 右侧：知识粒子球（桌面端）*/}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
              className="hidden lg:block"
            >
              <KnowledgeSphere />
            </motion.div>
          </div>

          {/* 移动端：粒子球展示 */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3, ease: "easeOut" }}
            className="lg:hidden mt-12"
          >
            <KnowledgeSphere />
          </motion.div>
        </div>
      </section>

      {/* Key Benefits Section */}
      <section className="py-24 px-6 bg-gradient-to-b from-background to-sage-50/20">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-serif font-bold text-foreground mb-4">
              Why Fast Learning Works
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Traditional learning is slow and passive. We flip the script with AI-powered 
              active learning that adapts to you.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            <BenefitCard
              icon={Target}
              title="Precision Learning"
              description="AI identifies your knowledge gaps and creates targeted strategies to fill them efficiently."
              delay={0}
            />
            <BenefitCard
              icon={Brain}
              title="Learn by Doing"
              description="Start building from day one. Our AI guides you through real projects, not endless tutorials."
              delay={0.1}
            />
            <BenefitCard
              icon={Clock}
              title="Accelerated Mastery"
              description="Structured roadmaps with clear milestones help you achieve competence in record time."
              delay={0.2}
            />
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-serif font-bold text-foreground mb-4">
              Your Learning Journey
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              From goal to mastery in four simple steps
            </p>
          </motion.div>

          <div className="grid md:grid-cols-4 gap-6">
            <StepCard
              number={1}
              title="Set Your Goal"
              description="Tell us what you want to learn and your current experience level."
              delay={0}
            />
            <StepCard
              number={2}
              title="Get Your Roadmap"
              description="AI creates a personalized curriculum with stages, modules, and concepts."
              delay={0.1}
            />
            <StepCard
              number={3}
              title="Learn & Build"
              description="Work through tutorials, quizzes, and hands-on projects at your pace."
              delay={0.2}
            />
            <StepCard
              number={4}
              title="Achieve Mastery"
              description="Track progress, get AI assistance, and reach your learning goals."
              delay={0.3}
            />
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 px-6 bg-card">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-serif font-bold text-foreground mb-4">
              Everything You Need to Learn Fast
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard
              icon={BookOpen}
              title="AI-Generated Tutorials"
              description="In-depth content tailored to your level with real-world examples."
              delay={0}
            />
            <FeatureCard
              icon={Sparkles}
              title="Adaptive Quizzes"
              description="Test your understanding with questions that adapt to your progress."
              delay={0.1}
            />
            <FeatureCard
              icon={Zap}
              title="Curated Resources"
              description="The best articles, videos, and tools handpicked by AI for each topic."
              delay={0.2}
            />
            <FeatureCard
              icon={Brain}
              title="Knowledge Graphs"
              description="Visualize connections between concepts and track your understanding."
              delay={0.3}
            />
            <FeatureCard
              icon={Users}
              title="AI Mentor"
              description="Get explanations using everyday analogies. Ask anything, anytime."
              delay={0.4}
            />
            <FeatureCard
              icon={Target}
              title="Progress Tracking"
              description="Clear milestones and completion tracking to keep you motivated."
              delay={0.5}
            />
          </div>
        </div>
      </section>

      {/* CTA Section - 奶油杂志风格 */}
      <section className="py-24 px-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-sage-500 to-sage-600 -z-10" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-sage-400/30 via-transparent to-transparent -z-10" />
        {/* 纸质纹理 */}
        <div className="absolute inset-0 opacity-[0.03] bg-noise -z-10" />
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="max-w-4xl mx-auto text-center"
        >
          <h2 className="text-4xl md:text-5xl font-serif font-bold text-white mb-6">
            Ready to Learn Faster?
          </h2>
          <p className="text-xl text-white/95 mb-10 max-w-2xl mx-auto">
            Join the waitlist and be among the first to experience 
            AI-powered learning that actually works.
          </p>
          <form onSubmit={handleJoinWaitlist} className="flex flex-col sm:flex-row items-center justify-center gap-3 max-w-md mx-auto">
            <Input
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-12 px-5 text-base bg-white/98 border-0 rounded-xl w-full sm:w-80 shadow-sm"
              disabled={isSubmitting}
            />
            <Button
              type="submit"
              size="lg"
              className="h-12 px-6 rounded-xl font-semibold gap-2 bg-white text-sage-600 hover:bg-white/90 hover:text-sage-700 w-full sm:w-auto shadow-sm"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Joining...' : 'Join Waitlist'}
              <ArrowRight className="w-4 h-4" />
            </Button>
          </form>
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

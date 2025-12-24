'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Sparkles, Target, Brain, Heart, Zap, Github, Twitter, Mail } from 'lucide-react';
import { motion } from 'framer-motion';

/**
 * About Page - 关于页面
 * 
 * 内容:
 * - 项目愿景
 * - 创始故事
 * - 团队介绍
 * - 联系方式
 */
export default function AboutPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* 动态背景 */}
      <div className="fixed inset-0 bg-gradient-to-br from-sage-50/50 via-background to-stone-50/30 -z-10" />
      
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border/50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 bg-sage-600 rounded-xl flex items-center justify-center text-white font-serif font-bold text-sm shadow-sm group-hover:shadow-md transition-shadow">
              FL
            </div>
            <span className="font-serif font-bold text-xl tracking-tight">Fast Learning</span>
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <Link href="/methodology" className="text-sm text-muted-foreground hover:text-foreground transition-colors font-medium">
              Methodology
            </Link>
            <Link href="/pricing" className="text-sm text-muted-foreground hover:text-foreground transition-colors font-medium">
              Pricing
            </Link>
            <Link href="/about" className="text-sm text-foreground font-medium">
              About
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-16 px-6">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Link href="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors">
              <ArrowLeft className="w-4 h-4" /> Back to Home
            </Link>
          </motion.div>
          
          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-5xl md:text-6xl font-serif font-bold text-foreground mb-6"
          >
            About Fast Learning
          </motion.h1>
          
          <motion.p
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-xl text-muted-foreground leading-relaxed max-w-3xl"
          >
            We&apos;re building the future of education—where AI doesn&apos;t replace teachers, 
            but amplifies learning by creating truly personalized paths to mastery.
          </motion.p>
        </div>
      </section>

      {/* Vision Section */}
      <section className="py-20 px-6 bg-card">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl font-serif font-bold text-foreground mb-4">
              Our Vision
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              A world where anyone can master any skill—quickly, effectively, and affordably.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            <VisionCard
              icon={Target}
              title="Democratize Learning"
              description="Everyone deserves access to world-class education, regardless of background or location."
              delay={0}
            />
            <VisionCard
              icon={Brain}
              title="Personalized Paths"
              description="No two learners are the same. AI creates unique roadmaps tailored to individual needs."
              delay={0.1}
            />
            <VisionCard
              icon={Zap}
              title="Accelerate Mastery"
              description="Learn faster by doing, not just watching. Practice-first methodology that works."
              delay={0.2}
            />
          </div>
        </div>
      </section>

      {/* Story Section */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-3xl font-serif font-bold text-foreground mb-8">
              Why We Built This
            </h2>
            <div className="prose prose-lg prose-stone max-w-none">
              <p className="text-muted-foreground leading-relaxed mb-6">
                Traditional education is broken. It&apos;s one-size-fits-all, painfully slow, and 
                disconnected from real-world application. We&apos;ve all experienced the frustration 
                of sitting through lectures that don&apos;t match our level, or tutorials that never 
                quite get to the point.
              </p>
              <p className="text-muted-foreground leading-relaxed mb-6">
                Fast Learning was born from a simple observation: the best learning happens when 
                you&apos;re building something real, when content adapts to your level, and when you 
                have a mentor who understands exactly where you&apos;re struggling.
              </p>
              <p className="text-muted-foreground leading-relaxed">
                With advances in generative AI, we can finally create that experience at scale. 
                Our multi-agent system doesn&apos;t just generate content—it architects personalized 
                learning journeys, adapts to your progress, and guides you through practical 
                projects that cement understanding.
              </p>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Values Section */}
      <section className="py-20 px-6 bg-gradient-to-b from-background to-sage-50/30">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl font-serif font-bold text-foreground mb-4">
              Our Values
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-8">
            <ValueCard
              title="Learning by Doing"
              description="Theory without practice is forgettable. We believe in hands-on learning from day one, where every concept is tied to real application."
              delay={0}
            />
            <ValueCard
              title="Continuous Iteration"
              description="The best learners aren't afraid to make mistakes. Our system encourages experimentation and provides gentle correction."
              delay={0.1}
            />
            <ValueCard
              title="Radical Personalization"
              description="Your learning journey is unique. We adapt everything—content, pace, difficulty—to maximize your growth."
              delay={0.2}
            />
            <ValueCard
              title="Transparent AI"
              description="We believe AI should augment human potential, not replace human connection. Our AI explains its reasoning and learns from your feedback."
              delay={0.3}
            />
          </div>
        </div>
      </section>

      {/* Team Section */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-3xl font-serif font-bold text-foreground mb-4">
              Built with Love
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-12">
              Fast Learning is built by a small team passionate about education and AI. 
              We&apos;re constantly improving based on user feedback.
            </p>
            
            <div className="flex items-center justify-center gap-2 mb-8">
              <Heart className="w-5 h-5 text-sage-600" />
              <span className="text-muted-foreground">Made with passion for learners everywhere</span>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Contact Section */}
      <section className="py-20 px-6 bg-card">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-3xl font-serif font-bold text-foreground mb-4">
              Get in Touch
            </h2>
            <p className="text-lg text-muted-foreground mb-8">
              Have questions, feedback, or just want to say hi? We&apos;d love to hear from you.
            </p>
            
            <div className="flex items-center justify-center gap-6">
              <a 
                href="mailto:hello@fastlearning.app" 
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <Mail className="w-5 h-5" />
                <span>Email</span>
              </a>
              <a 
                href="https://twitter.com/fastlearningai" 
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <Twitter className="w-5 h-5" />
                <span>Twitter</span>
              </a>
              <a 
                href="https://github.com/fastlearning" 
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <Github className="w-5 h-5" />
                <span>GitHub</span>
              </a>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-16 px-6 border-t border-border">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-sage-600 rounded-xl flex items-center justify-center text-white font-serif font-bold text-xs">
                FL
              </div>
              <span className="font-serif font-bold text-lg">Fast Learning</span>
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
 * VisionCard - 愿景卡片
 */
function VisionCard({
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
      className="p-8 rounded-2xl border border-sage-100 bg-background text-center"
    >
      <div className="w-14 h-14 rounded-xl bg-sage-100 flex items-center justify-center mx-auto mb-6">
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
 * ValueCard - 价值观卡片
 */
function ValueCard({
  title,
  description,
  delay = 0,
}: {
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
      className="p-6 rounded-xl border border-border bg-white"
    >
      <div className="flex items-start gap-4">
        <div className="w-2 h-2 rounded-full bg-sage-500 mt-2 shrink-0" />
        <div>
          <h3 className="text-lg font-serif font-semibold text-foreground mb-2">
            {title}
          </h3>
          <p className="text-muted-foreground leading-relaxed">{description}</p>
        </div>
      </div>
    </motion.div>
  );
}


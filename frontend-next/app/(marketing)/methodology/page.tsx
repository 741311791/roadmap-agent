'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Brain, Users, Sparkles, Target, BookOpen, MessageSquare, Zap, Clock, Lightbulb, RefreshCw, GraduationCap } from 'lucide-react';
import { motion } from 'framer-motion';

/**
 * Methodology Page - 方法论页面
 * 
 * 内容:
 * - Fast Learning 核心理念
 * - 多 Agent 架构
 * - 两种学习模式
 * - 学习流程
 */
export default function MethodologyPage() {
  return (
    <div className="bg-background">
      {/* 动态背景 */}
      <div className="fixed inset-0 bg-gradient-to-br from-sage-50/50 via-background to-stone-50/30 -z-10" />
      
      {/* Hero */}
      <section className="pt-32 pb-16 px-6">
        <div className="max-w-4xl mx-auto">
          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-5xl md:text-6xl font-serif font-bold text-foreground mb-6"
          >
            The Fast Learning Method
          </motion.h1>
          
          <motion.p
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-xl text-muted-foreground leading-relaxed max-w-3xl"
          >
            Master new skills in record time through AI-powered personalization, 
            practice-first learning, and adaptive feedback loops.
          </motion.p>
        </div>
      </section>

      {/* Fast Learning Philosophy */}
      <section className="py-20 px-6 bg-card">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-16"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-sage-50 border border-sage-200 rounded-full text-sage-700 text-sm font-medium mb-6">
              <Zap className="w-4 h-4" />
              Core Philosophy
            </div>
            <h2 className="text-3xl font-serif font-bold text-foreground mb-4">
              Learn Faster by Doing, Not Just Watching
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Traditional learning is passive and slow. We flip the script with active, 
              project-based learning that gets you building from day one.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <PhilosophyCard
              icon={Target}
              title="Identify Gaps"
              description="AI analyzes your goals and current knowledge to pinpoint exactly what you need to learn."
              delay={0}
            />
            <PhilosophyCard
              icon={BookOpen}
              title="Structured Path"
              description="Stage-Module-Concept hierarchy creates clear, achievable milestones."
              delay={0.1}
            />
            <PhilosophyCard
              icon={RefreshCw}
              title="Learn by Doing"
              description="Every concept ties to practical exercises and real-world projects."
              delay={0.2}
            />
            <PhilosophyCard
              icon={Lightbulb}
              title="Iterate & Improve"
              description="Make mistakes, get feedback, correct course. Repeat until mastery."
              delay={0.3}
            />
          </div>
        </div>
      </section>

      {/* Two Learning Modes */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl font-serif font-bold text-foreground mb-4">
              Two Powerful Learning Modes
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Choose the mode that fits your learning style, or switch between them as needed.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-8">
            <LearningModeCard
              title="Companion Mode"
              subtitle="Learn with AI by your side"
              description="Your AI companion automatically detects what you're studying and provides real-life analogies to demystify complex concepts. Ask anything—it explains in plain language."
              features={[
                "Context-aware explanations",
                "Real-life analogies that stick",
                "Modify roadmap structure on request",
                "Adjust tutorial content and quizzes"
              ]}
              icon={Users}
              delay={0}
            />
            <LearningModeCard
              title="Guided Mode"
              subtitle="Learn through practice"
              description="Your AI guide presents practical challenges and lets you attempt them. Make mistakes—it's part of the process. The guide patiently corrects errors and repeats until mastery."
              features={[
                "Practice-first approach",
                "Immediate feedback on attempts",
                "Patient error correction",
                "Repeat until confident"
              ]}
              icon={GraduationCap}
              delay={0.1}
            />
          </div>
        </div>
      </section>

      {/* Multi-Agent Architecture */}
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
              Powered by Multi-Agent AI
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Six specialized AI agents collaborate to create and deliver your personalized learning experience.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-6">
            <AgentCard
              icon={Brain}
              name="Intent Analyzer"
              role="A1"
              description="Analyzes your learning goals, extracts key technologies, and creates a difficulty profile based on your background."
              delay={0}
            />
            <AgentCard
              icon={Target}
              name="Curriculum Architect"
              role="A2"
              description="Designs a structured roadmap with stages, modules, and concepts. Ensures logical progression and prerequisites."
              delay={0.1}
            />
            <AgentCard
              icon={BookOpen}
              name="Tutorial Generator"
              role="A4"
              description="Creates in-depth tutorials with theory, examples, and exercises tailored to your learning preferences."
              delay={0.2}
            />
            <AgentCard
              icon={Users}
              name="Resource Recommender"
              role="A5"
              description="Finds and curates the best external resources—articles, videos, courses, and tools—for each topic."
              delay={0.3}
            />
            <AgentCard
              icon={Sparkles}
              name="Quiz Generator"
              role="A6"
              description="Creates adaptive quizzes with various question types to test understanding and reinforce learning."
              delay={0.4}
            />
            <AgentCard
              icon={MessageSquare}
              name="Modification Agents"
              role="A7+"
              description="Allow you to modify tutorials, resources, and quizzes through natural language conversation."
              delay={0.5}
            />
          </div>
        </div>
      </section>

      {/* Learning Process */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl font-serif font-bold text-foreground mb-4">
              Your Journey to Mastery
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Four simple steps from beginner to expert
            </p>
          </motion.div>

          <div className="space-y-8">
            <ProcessStep
              number={1}
              title="Share Your Goals"
              description="Tell us what you want to learn, your current level, available time, and preferred learning style. Our Intent Analyzer extracts the key insights."
              delay={0}
            />
            <ProcessStep
              number={2}
              title="Receive Your Personalized Roadmap"
              description="The Curriculum Architect creates a structured path with clear stages, modules, and concepts. Each element builds on what came before."
              delay={0.1}
            />
            <ProcessStep
              number={3}
              title="Learn, Practice, and Build"
              description="Work through AI-generated tutorials, complete adaptive quizzes, and explore curated resources. Choose Companion or Guided mode based on your needs."
              delay={0.2}
            />
            <ProcessStep
              number={4}
              title="Adapt and Master"
              description="Chat with AI to modify content, get explanations, or adjust difficulty. Track your progress and celebrate milestones as you achieve mastery."
              delay={0.3}
            />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6 bg-sage-600 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-sage-500/30 via-transparent to-transparent -z-10" />
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="max-w-4xl mx-auto text-center"
        >
          <h2 className="text-4xl font-serif font-bold text-white mb-6">
            Ready to Experience Fast Learning?
          </h2>
          <p className="text-xl text-sage-100 mb-8 max-w-2xl mx-auto">
            Start your personalized learning journey today.
          </p>
          <Link href="/new">
            <Button size="lg" className="bg-white text-sage-700 hover:bg-sage-50 font-semibold px-8">
              Create Your Roadmap
            </Button>
          </Link>
        </motion.div>
      </section>
    </div>
  );
}

/**
 * PhilosophyCard - 理念卡片
 */
function PhilosophyCard({
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
      className="p-6 rounded-xl border border-border bg-background text-center"
    >
      <div className="w-12 h-12 rounded-lg bg-sage-100 flex items-center justify-center mx-auto mb-4">
        <Icon className="w-6 h-6 text-sage-600" />
      </div>
      <h3 className="text-lg font-serif font-semibold text-foreground mb-2">
        {title}
      </h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
    </motion.div>
  );
}

/**
 * LearningModeCard - 学习模式卡片
 */
function LearningModeCard({
  title,
  subtitle,
  description,
  features,
  icon: Icon,
  delay = 0,
}: {
  title: string;
  subtitle: string;
  description: string;
  features: string[];
  icon: React.ElementType;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      className="p-8 rounded-2xl border border-sage-200 bg-gradient-to-br from-white to-sage-50/50"
    >
      <div className="w-14 h-14 rounded-xl bg-sage-100 flex items-center justify-center mb-6">
        <Icon className="w-7 h-7 text-sage-600" />
      </div>
      <h3 className="text-2xl font-serif font-bold text-foreground mb-1">
        {title}
      </h3>
      <p className="text-sm text-sage-600 font-medium mb-4">{subtitle}</p>
      <p className="text-muted-foreground leading-relaxed mb-6">{description}</p>
      <ul className="space-y-2">
        {features.map((feature, index) => (
          <li key={index} className="flex items-start gap-2 text-sm">
            <div className="w-1.5 h-1.5 rounded-full bg-sage-500 mt-2 shrink-0" />
            <span className="text-foreground">{feature}</span>
          </li>
        ))}
      </ul>
    </motion.div>
  );
}

/**
 * AgentCard - AI Agent 卡片
 */
function AgentCard({
  icon: Icon,
  name,
  role,
  description,
  delay = 0,
}: {
  icon: React.ElementType;
  name: string;
  role: string;
  description: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      className="flex gap-5 p-6 rounded-xl border border-border bg-white"
    >
      <div className="flex-shrink-0">
        <div className="w-12 h-12 rounded-lg bg-sage-100 flex items-center justify-center">
          <Icon className="w-6 h-6 text-sage-600" />
        </div>
      </div>
      <div>
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-lg font-serif font-semibold text-foreground">
            {name}
          </h3>
          <span className="px-2 py-0.5 text-xs font-medium bg-sage-100 text-sage-700 rounded">
            {role}
          </span>
        </div>
        <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
      </div>
    </motion.div>
  );
}

/**
 * ProcessStep - 流程步骤
 */
function ProcessStep({
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
      initial={{ opacity: 0, x: -20 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      className="flex gap-6"
    >
      <div className="flex-shrink-0">
        <div className="w-12 h-12 rounded-xl bg-sage-600 text-white flex items-center justify-center font-serif font-bold text-lg shadow-sm">
          {number}
        </div>
      </div>
      <div className="pt-1">
        <h3 className="text-xl font-serif font-semibold text-foreground mb-2">
          {title}
        </h3>
        <p className="text-muted-foreground leading-relaxed">{description}</p>
      </div>
    </motion.div>
  );
}

'use client';

import { useTranslations } from 'next-intl';
import { Sparkles, Target, Brain, Heart, Zap, Github, Twitter, Mail } from 'lucide-react';
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
  const t = useTranslations('aboutPage');
  
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
            {t('title')}
          </motion.h1>
          
          <motion.p
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-xl text-muted-foreground leading-relaxed max-w-3xl"
          >
            {t('subtitle')}
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
              {t('ourVision')}
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              {t('visionDesc')}
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            <VisionCard
              icon={Target}
              title={t('democratize')}
              description={t('democratizeDesc')}
              delay={0}
            />
            <VisionCard
              icon={Brain}
              title={t('personalizedPaths')}
              description={t('personalizedPathsDesc')}
              delay={0.1}
            />
            <VisionCard
              icon={Zap}
              title={t('accelerateMastery')}
              description={t('accelerateMasteryDesc')}
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
              {t('whyWeBuilt')}
            </h2>
            <div className="prose prose-lg prose-stone max-w-none">
              <p className="text-muted-foreground leading-relaxed mb-6">
                {t('story1')}
              </p>
              <p className="text-muted-foreground leading-relaxed mb-6">
                {t('story2')}
              </p>
              <p className="text-muted-foreground leading-relaxed">
                {t('story3')}
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
              {t('ourValues')}
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-8">
            <ValueCard
              title={t('value1Title')}
              description={t('value1Desc')}
              delay={0}
            />
            <ValueCard
              title={t('value2Title')}
              description={t('value2Desc')}
              delay={0.1}
            />
            <ValueCard
              title={t('value3Title')}
              description={t('value3Desc')}
              delay={0.2}
            />
            <ValueCard
              title={t('value4Title')}
              description={t('value4Desc')}
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
              {t('builtWithLove')}
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-12">
              {t('teamDesc')}
            </p>
            
            <div className="flex items-center justify-center gap-2 mb-8">
              <Heart className="w-5 h-5 text-sage-600" />
              <span className="text-muted-foreground">{t('madeWithPassion')}</span>
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
              {t('getInTouch')}
            </h2>
            <p className="text-lg text-muted-foreground mb-8">
              {t('contactDesc')}
            </p>
            
            <div className="flex items-center justify-center gap-6">
              <a 
                href="mailto:hello@fastlearning.app" 
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <Mail className="w-5 h-5" />
                <span>{t('email')}</span>
              </a>
              <a 
                href="https://twitter.com/fastlearningai" 
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <Twitter className="w-5 h-5" />
                <span>{t('twitter')}</span>
              </a>
              <a 
                href="https://github.com/fastlearning" 
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <Github className="w-5 h-5" />
                <span>{t('github')}</span>
              </a>
            </div>
          </motion.div>
        </div>
      </section>
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


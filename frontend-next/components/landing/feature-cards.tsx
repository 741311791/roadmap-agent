'use client';

/**
 * Feature 卡片组件
 *
 * 5 张展示卡片，与工作流 5 个节点一一对应：
 * 1. IntentAnalysisCard  - 分析节点（需求分析）
 * 2. RoadmapCard         - 设计节点（学习路线图）
 * 3. ValidationCard      - 验证节点（结构验证，SVG 雷达图）
 * 4. HumanReviewCard     - 审核节点（人工审核与反馈模拟）
 * 5. ContentGenerationCard - 内容节点（教程 / 资源 / 测验 3 Tab）
 */

import React, { useState, useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'motion/react';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import {
  Target,
  Clock,
  TrendingUp,
  Layers,
  CheckCircle2,
  Circle,
  BookOpen,
  Video,
  FileText,
  Star,
  ShieldCheck,
  AlertCircle,
  Check,
  X,
  Loader2,
  UserCheck,
  Sparkles,
} from 'lucide-react';

/**
 * Intent Analysis Card - 需求分析卡片
 */
export function IntentAnalysisCard() {
  const t = useTranslations('featureCards.intentAnalysis');
  
  return (
    <Card className="p-6 border-border bg-gradient-to-br from-muted to-card shadow-xl">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <Target className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">{t('title')}</h3>
          <Badge variant="outline" className="ml-auto text-xs">{t('aiGenerated')}</Badge>
        </div>

        {/* 学习目标 */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-foreground">{t('learningGoal')}</p>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {t('goalText')}
          </p>
        </div>

        {/* 当前水平 */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-foreground">{t('currentExperience')}</p>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">{t('beginnerHtml')}</Badge>
            <Badge variant="secondary" className="text-xs">{t('basicJs')}</Badge>
          </div>
        </div>

        {/* 技术栈 */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-foreground">{t('recommendedTech')}</p>
          <div className="flex flex-wrap gap-1.5">
            <Badge variant="secondary" className="text-xs">React 18</Badge>
            <Badge variant="secondary" className="text-xs">Node.js</Badge>
            <Badge variant="secondary" className="text-xs">TypeScript</Badge>
            <Badge variant="secondary" className="text-xs">PostgreSQL</Badge>
            <Badge variant="secondary" className="text-xs">Express</Badge>
            <Badge variant="secondary" className="text-xs">Docker</Badge>
            <Badge variant="outline" className="text-xs border-dashed">+6 more</Badge>
          </div>
        </div>

        {/* 识别的知识缺口 */}
        <div className="space-y-2 pt-2">
          <p className="text-xs font-medium text-foreground">{t('identifiedGaps')}</p>
          <div className="space-y-1.5">
            {[
              t('gap1'),
              t('gap2'),
              t('gap3'),
              t('gap4'),
            ].map((gap, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground">
                <div className="w-1.5 h-1.5 rounded-full bg-sage" />
                <span>{gap}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 难度和时长 */}
        <div className="grid grid-cols-3 gap-3 pt-3 border-t border-border">
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock className="w-3.5 h-3.5" />
              <span>{t('duration')}</span>
            </div>
            <p className="text-sm font-semibold text-foreground">12 {t('weeks')}</p>
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>{t('level')}</span>
            </div>
            <Badge className="bg-orange-100 text-orange-700 hover:bg-orange-200 text-xs">
              {t('intermediate')}
            </Badge>
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Layers className="w-3.5 h-3.5" />
              <span>{t('concepts')}</span>
            </div>
            <p className="text-sm font-semibold text-foreground">89</p>
          </div>
        </div>
      </div>
    </Card>
  );
}

/**
 * Roadmap Card - 路线图卡片
 */
export function RoadmapCard() {
  const t = useTranslations('featureCards.roadmap');
  
  return (
    <Card className="p-6 border-border bg-gradient-to-br from-card to-muted shadow-xl">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">{t('title')}</h3>
          <Badge variant="outline" className="ml-auto text-xs">3 {t('stages')}</Badge>
        </div>

        {/* 路线图层级 */}
        <div className="space-y-4">
          {/* Stage 1 - Completed */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-sage" />
              <span className="text-sm font-bold text-foreground">
                {t('stage1')}
              </span>
              <Badge variant="secondary" className="ml-auto text-xs">{t('completed')}</Badge>
            </div>
            
            {/* Module */}
            <div className="ml-4 pl-3 border-l-2 border-sage/30 space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-sage" />
                <span className="text-xs text-foreground font-medium">{t('module11')}</span>
              </div>
              
              {/* Concepts */}
              <div className="ml-5 space-y-1">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <CheckCircle2 className="w-2.5 h-2.5 text-sage" />
                  <span>{t('concept1')}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <CheckCircle2 className="w-2.5 h-2.5 text-sage" />
                  <span>{t('concept2')}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <CheckCircle2 className="w-2.5 h-2.5 text-sage" />
                  <span>{t('concept3')}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Stage 2 - In Progress */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-full border-2 border-sage flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-sage animate-pulse" />
              </div>
              <span className="text-sm font-bold text-foreground">
                {t('stage2')}
              </span>
              <Badge className="ml-auto text-xs bg-blue-100 text-blue-700">{t('inProgress')}</Badge>
            </div>
            
            <div className="ml-4 pl-3 border-l-2 border-border space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-sage" />
                <span className="text-xs text-foreground font-medium">{t('module21')}</span>
              </div>
              
              <div className="ml-5 space-y-1">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <CheckCircle2 className="w-2.5 h-2.5 text-sage" />
                  <span>{t('concept4')}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-sage font-medium">
                  <Circle className="w-2.5 h-2.5" />
                  <span>{t('concept5')}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground/50">
                  <Circle className="w-2.5 h-2.5" />
                  <span>{t('concept6')}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Stage 3 - Locked */}
          <div className="space-y-2 opacity-50">
            <div className="flex items-center gap-2">
              <Circle className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-bold text-muted-foreground">
                {t('stage3')}
              </span>
              <Badge variant="outline" className="ml-auto text-xs">{t('locked')}</Badge>
            </div>
          </div>
        </div>

        {/* 进度统计 */}
        <div className="pt-3 border-t border-border space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>{t('overallProgress')}</span>
            <span className="font-semibold text-foreground">45%</span>
          </div>
          <Progress value={45} className="h-2" />
          
          <div className="grid grid-cols-3 gap-2 pt-2">
            <div className="text-center">
              <p className="text-lg font-bold text-foreground">32</p>
              <p className="text-xs text-muted-foreground">{t('completed')}</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-sage">5</p>
              <p className="text-xs text-muted-foreground">{t('inProgress')}</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-muted-foreground">52</p>
              <p className="text-xs text-muted-foreground">{t('remaining')}</p>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

/**
 * Quiz Card - 测验卡片
 */
export function QuizCard() {
  const t = useTranslations('featureCards.quiz');
  
  return (
    <Card className="p-6 border-border bg-gradient-to-br from-muted to-card shadow-xl">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">{t('title')}</h3>
          <Badge className="ml-auto text-xs bg-sage/10 text-sage border border-sage/20">{t('interactive')}</Badge>
        </div>

        {/* 问题标签 */}
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">JavaScript</Badge>
          <Badge variant="outline" className="text-xs">Data Types</Badge>
          <Badge variant="outline" className="text-xs">{t('medium')}</Badge>
        </div>

        {/* 问题 */}
        <div className="space-y-3">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">{t('questionOf')}</p>
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">1:45 {t('remaining')}</span>
              </div>
            </div>
            <p className="text-sm font-medium text-foreground leading-relaxed">
              {t('question')}{' '}
              <code className="px-2 py-1 bg-muted rounded text-xs font-mono">typeof []</code>?
            </p>
          </div>

          {/* 选项 */}
          <div className="space-y-2">
            {[
              { id: 'A', text: '"array"', correct: false },
              { id: 'B', text: '"object"', correct: true, explanation: 'Arrays are objects in JavaScript' },
              { id: 'C', text: '"undefined"', correct: false },
              { id: 'D', text: '"null"', correct: false },
            ].map((option) => (
              <motion.button
                key={option.id}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                className={`w-full p-3 text-left rounded-lg border-2 transition-all group ${
                  option.correct
                    ? 'border-sage bg-sage/5'
                    : 'border-border bg-card hover:border-accent/50 hover:bg-accent/5'
                }`}
              >
                <div className="flex items-center gap-2">
                  <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-colors ${
                    option.correct 
                      ? 'border-sage text-sage' 
                      : 'border-border text-muted-foreground group-hover:border-accent'
                  }`}>
                    {option.id}
                  </div>
                  <span className="text-sm font-medium text-foreground">
                    {option.text}
                  </span>
                  {option.correct && (
                    <CheckCircle2 className="w-4 h-4 text-sage ml-auto" />
                  )}
                </div>
              </motion.button>
            ))}
          </div>

          {/* 解释说明 */}
          <div className="p-3 bg-sage/5 border border-sage/20 rounded-lg">
            <p className="text-xs text-muted-foreground leading-relaxed">
              💡 <span className="font-medium">{t('tip')}</span> {t('tipText')} <code className="px-1 bg-muted rounded">Array.isArray()</code> {t('toCheck')}
            </p>
          </div>
        </div>

        {/* 统计 */}
        <div className="pt-3 border-t border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1 text-sage">
                <Star className="w-3.5 h-3.5 fill-current" />
                <span className="text-xs font-semibold">8/10 {t('correct')}</span>
              </div>
              <div className="flex items-center gap-1 text-muted-foreground">
                <TrendingUp className="w-3.5 h-3.5" />
                <span className="text-xs">+12 XP</span>
              </div>
            </div>
            <Progress value={80} className="h-1.5 w-20" />
          </div>
        </div>
      </div>
    </Card>
  );
}

/**
 * Resource Card - 资源推荐卡片
 */
export function ResourceCard() {
  const t = useTranslations('featureCards.resource');
  
  return (
    <Card className="p-6 border-border bg-gradient-to-br from-card to-muted shadow-xl">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">{t('title')}</h3>
          <Badge className="ml-auto text-xs bg-sage/10 text-sage border border-sage/20">14 {t('resources')}</Badge>
        </div>

        {/* 筛选标签 */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <Badge variant="default" className="text-xs bg-sage text-white">{t('all')}</Badge>
          <Badge variant="outline" className="text-xs">{t('articles')}</Badge>
          <Badge variant="outline" className="text-xs">{t('videos')}</Badge>
          <Badge variant="outline" className="text-xs">{t('projects')}</Badge>
        </div>

        {/* 资源列表 */}
        <div className="space-y-2.5">
          {/* Article 1 */}
          <motion.div
            whileHover={{ scale: 1.01 }}
            className="flex gap-3 p-3 rounded-lg glass-panel hover:border-sage/50 transition-all cursor-pointer group"
          >
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-sage/10 flex items-center justify-center">
              <FileText className="w-5 h-5 text-sage" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate group-hover:text-sage transition-colors">
                {t('resource1Title')}
              </p>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-muted-foreground">{t('resource1Source')}</span>
                <div className="flex items-center gap-0.5">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className={`w-2.5 h-2.5 ${
                        i < 4 ? 'text-sage fill-current' : 'text-border'
                      }`}
                    />
                  ))}
                  <span className="text-xs text-muted-foreground ml-1">4.8</span>
                </div>
              </div>
            </div>
            <CheckCircle2 className="w-4 h-4 text-sage flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
          </motion.div>

          {/* Video 1 */}
          <motion.div
            whileHover={{ scale: 1.01 }}
            className="flex gap-3 p-3 rounded-lg glass-panel hover:border-sage/50 transition-all cursor-pointer group"
          >
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-sage/10 flex items-center justify-center">
              <Video className="w-5 h-5 text-sage" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate group-hover:text-sage transition-colors">
                {t('resource2Title')}
              </p>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-muted-foreground">{t('resource2Source')}</span>
                <div className="flex items-center gap-0.5">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className={`w-2.5 h-2.5 ${
                        i < 5 ? 'text-sage fill-current' : 'text-border'
                      }`}
                    />
                  ))}
                  <span className="text-xs text-muted-foreground ml-1">5.0</span>
                </div>
              </div>
            </div>
            <CheckCircle2 className="w-4 h-4 text-sage flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
          </motion.div>

          {/* Article 2 */}
          <motion.div
            whileHover={{ scale: 1.01 }}
            className="flex gap-3 p-3 rounded-lg glass-panel hover:border-sage/50 transition-all cursor-pointer group"
          >
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-sage/10 flex items-center justify-center">
              <FileText className="w-5 h-5 text-sage" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate group-hover:text-sage transition-colors">
                {t('resource3Title')}
              </p>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-muted-foreground">{t('resource3Source')}</span>
                <div className="flex items-center gap-0.5">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className={`w-2.5 h-2.5 ${
                        i < 4 ? 'text-sage fill-current' : 'text-border'
                      }`}
                    />
                  ))}
                  <span className="text-xs text-muted-foreground ml-1">4.7</span>
                </div>
              </div>
            </div>
            <CheckCircle2 className="w-4 h-4 text-sage flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
          </motion.div>

          {/* Project */}
          <motion.div
            whileHover={{ scale: 1.01 }}
            className="flex gap-3 p-3 rounded-lg glass-panel hover:border-sage/50 transition-all cursor-pointer group border-dashed"
          >
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-sage/10 flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-sage" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate group-hover:text-sage transition-colors">
                {t('resource4Title')}
              </p>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-muted-foreground">{t('resource4Source')}</span>
                <Badge className="text-xs bg-sage/10 text-sage border border-sage/20">
                  {t('project')}
                </Badge>
              </div>
            </div>
            <CheckCircle2 className="w-4 h-4 text-sage flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
          </motion.div>
        </div>

        {/* 统计与操作 */}
        <div className="pt-3 border-t border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1 text-sage">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span className="font-semibold">8 {t('completed')}</span>
              </div>
              <div className="h-3 w-px bg-border" />
              <span className="text-muted-foreground">10 {t('moreAvailable')}</span>
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="text-xs font-medium text-sage hover:text-sage/80 transition-colors"
            >
              {t('viewAll')}
            </motion.button>
          </div>
        </div>
      </div>
    </Card>
  );
}

/**
 * Validation Card - 结构验证卡片
 *
 * 使用纯 SVG 绘制五维雷达图，展示路线图结构评分。
 * 包含问题列表与「已自动修复」动画。
 */
export function ValidationCard() {
  const t = useTranslations('featureCards.validation');
  const [animated, setAnimated] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // 进入视口时触发雷达图绘制动画
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setAnimated(true); },
      { threshold: 0.3 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  // 五个维度的得分（满分 100）
  const scores = [92, 88, 95, 85, 90];
  const labels = [
    t('dimension1'),
    t('dimension2'),
    t('dimension3'),
    t('dimension4'),
    t('dimension5'),
  ];

  // 五边形雷达图坐标计算
  const center = 80;
  const maxR = 60;
  const angleOffset = -Math.PI / 2;

  /** 极坐标转 SVG 坐标 */
  const toXY = (score: number, index: number, total: number, r = maxR) => {
    const angle = angleOffset + (index * 2 * Math.PI) / total;
    const radius = (score / 100) * r;
    return {
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
    };
  };

  /** 生成五边形网格 path */
  const gridPath = (ratio: number) =>
    Array.from({ length: 5 }, (_, i) => {
      const { x, y } = toXY(100 * ratio, i, 5);
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ') + ' Z';

  /** 分值多边形 path（动画前为 center 点，动画后为真实分值） */
  const scorePath = Array.from({ length: 5 }, (_, i) => {
    const { x, y } = toXY(animated ? scores[i] : 0, i, 5);
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ') + ' Z';

  return (
    <Card ref={ref} className="p-6 border-border bg-gradient-to-br from-muted to-card shadow-xl">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">{t('title')}</h3>
          <Badge className="ml-auto text-xs bg-sage/10 text-sage border border-sage/20">
            {t('passed')}
          </Badge>
        </div>

        {/* 雷达图区域 */}
        <div className="flex items-center justify-between gap-4">
          <svg
            viewBox="0 0 160 160"
            className="w-36 h-36 flex-shrink-0"
            aria-label="Radar chart"
          >
            {/* 网格线 */}
            {[0.25, 0.5, 0.75, 1].map((ratio) => (
              <path
                key={ratio}
                d={gridPath(ratio)}
                fill="none"
                stroke="hsl(var(--border))"
                strokeWidth="1"
              />
            ))}
            {/* 轴线 */}
            {Array.from({ length: 5 }, (_, i) => {
              const { x, y } = toXY(100, i, 5);
              return (
                <line
                  key={i}
                  x1={center}
                  y1={center}
                  x2={x.toFixed(1)}
                  y2={y.toFixed(1)}
                  stroke="hsl(var(--border))"
                  strokeWidth="1"
                />
              );
            })}
            {/* 得分多边形（动画） */}
            <motion.path
              d={scorePath}
              fill="hsl(var(--sage) / 0.18)"
              stroke="hsl(var(--sage))"
              strokeWidth="2"
              strokeLinejoin="round"
              initial={{ opacity: 0, scale: 0.1 }}
              animate={animated ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.1 }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              style={{ transformOrigin: `${center}px ${center}px` }}
            />
            {/* 得分顶点圆点 */}
            {scores.map((score, i) => {
              const { x, y } = toXY(score, i, 5);
              return (
                <motion.circle
                  key={i}
                  cx={x.toFixed(1)}
                  cy={y.toFixed(1)}
                  r="3"
                  fill="hsl(var(--sage))"
                  initial={{ opacity: 0, scale: 0 }}
                  animate={animated ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0 }}
                  transition={{ duration: 0.4, delay: 0.7 + i * 0.05 }}
                  style={{ transformOrigin: `${x.toFixed(1)}px ${y.toFixed(1)}px` }}
                />
              );
            })}
          </svg>

          {/* 维度得分列表 */}
          <div className="flex-1 space-y-1.5">
            {labels.map((label, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground truncate max-w-[80px]">{label}</span>
                <motion.span
                  className="font-semibold text-sage"
                  initial={{ opacity: 0 }}
                  animate={animated ? { opacity: 1 } : { opacity: 0 }}
                  transition={{ delay: 0.5 + i * 0.1 }}
                >
                  {scores[i]}
                </motion.span>
              </div>
            ))}
          </div>
        </div>

        {/* 综合评分 */}
        <div className="flex items-center justify-between px-3 py-2 bg-sage/5 rounded-lg border border-sage/20">
          <span className="text-sm font-medium text-foreground">{t('overallScore')}</span>
          <motion.span
            className="text-xl font-bold text-sage"
            initial={{ opacity: 0, scale: 0.5 }}
            animate={animated ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.5 }}
            transition={{ delay: 1, type: 'spring', stiffness: 200 }}
          >
            90
          </motion.span>
        </div>

        {/* 已发现并修复的问题 */}
        <div className="space-y-2">
          {[
            { desc: t('issueDesc1') },
            { desc: t('issueDesc2') },
          ].map((issue, i) => (
            <motion.div
              key={i}
              className="flex items-center gap-2 p-2 rounded-lg bg-muted/60 border border-border"
              initial={{ opacity: 0, x: -8 }}
              animate={animated ? { opacity: 1, x: 0 } : { opacity: 0, x: -8 }}
              transition={{ delay: 1.1 + i * 0.15 }}
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-sage flex-shrink-0" />
              <span className="text-xs text-muted-foreground flex-1 truncate">{issue.desc}</span>
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0 flex-shrink-0">
                {t('fixedLabel')}
              </Badge>
            </motion.div>
          ))}
        </div>
      </div>
    </Card>
  );
}

/**
 * HumanReviewCard - 人工审核卡片
 *
 * 模拟用户审核路线图的交互流程：
 * idle → feedbackOpen → submitting → aiUpdated → idle（循环）
 */
export function HumanReviewCard() {
  const t = useTranslations('featureCards.humanReview');

  type ReviewState = 'idle' | 'feedbackOpen' | 'submitting' | 'aiUpdated';
  const [state, setState] = useState<ReviewState>('idle');
  const [feedback, setFeedback] = useState('');

  /** 自动演示循环 */
  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];

    const runDemo = () => {
      setState('idle');
      timers.push(setTimeout(() => setState('feedbackOpen'), 2000));
      timers.push(setTimeout(() => {
        setFeedback(t('feedbackExample'));
      }, 2600));
      timers.push(setTimeout(() => setState('submitting'), 4200));
      timers.push(setTimeout(() => setState('aiUpdated'), 6000));
      timers.push(setTimeout(() => {
        setState('idle');
        setFeedback('');
      }, 10000));
    };

    runDemo();
    const loop = setInterval(runDemo, 12000);
    return () => {
      clearInterval(loop);
      timers.forEach(clearTimeout);
    };
  }, []);

  return (
    <Card className="p-6 border-border bg-gradient-to-br from-card to-muted shadow-xl overflow-hidden">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <UserCheck className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">{t('title')}</h3>
        </div>

        {/* 路线图信息预览 */}
        <div className="p-3 bg-muted/60 rounded-lg border border-border space-y-1">
          <p className="text-sm font-semibold text-foreground">{t('roadmapTitle')}</p>
          <p className="text-xs text-muted-foreground">{t('stagesInfo')}</p>
        </div>

        {/* 动态内容区 */}
        <AnimatePresence mode="wait">
          {state === 'idle' && (
            <motion.div
              key="idle"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              className="space-y-2"
            >
              <p className="text-xs text-center text-muted-foreground font-medium">
                {t('reviewRequired')}
              </p>
              <div className="flex gap-2">
                <div className="flex-1 flex items-center justify-center gap-1.5 h-9 rounded-lg border-2 border-border bg-card text-sm text-muted-foreground cursor-default">
                  <X className="w-3.5 h-3.5" />
                  {t('requestChanges')}
                </div>
                <div className="flex-1 flex items-center justify-center gap-1.5 h-9 rounded-lg bg-sage text-white text-sm font-medium cursor-default shadow-sm">
                  <Check className="w-3.5 h-3.5" />
                  {t('approve')}
                </div>
              </div>
            </motion.div>
          )}

          {state === 'feedbackOpen' && (
            <motion.div
              key="feedback"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              className="space-y-2"
            >
              <div className="w-full min-h-[64px] p-3 text-xs text-foreground bg-card border border-border rounded-lg leading-relaxed">
                {feedback}
                <span className="animate-pulse ml-0.5">|</span>
              </div>
              <div className="flex gap-2">
                <div className="flex-1 flex items-center justify-center h-8 rounded-lg border border-border text-xs text-muted-foreground cursor-default">
                  {t('cancel')}
                </div>
                <div className="flex-1 flex items-center justify-center gap-1.5 h-8 rounded-lg bg-sage text-white text-xs font-medium cursor-default">
                  {t('submit')}
                </div>
              </div>
            </motion.div>
          )}

          {state === 'submitting' && (
            <motion.div
              key="submitting"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-2 py-3"
            >
              <Loader2 className="w-6 h-6 text-sage animate-spin" />
              <p className="text-xs text-muted-foreground">{t('aiProcessing')}</p>
            </motion.div>
          )}

          {state === 'aiUpdated' && (
            <motion.div
              key="updated"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
              className="p-3 bg-sage/8 border border-sage/30 rounded-lg space-y-1.5"
            >
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-sage flex-shrink-0" />
                <p className="text-sm font-semibold text-foreground">{t('aiUpdated')}</p>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {t('aiUpdateDetail')}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Card>
  );
}

/**
 * ContentGenerationCard - 内容生成卡片
 *
 * 通过 3 个 Tab（教程 / 资源 / 测验）展示全面的内容生成能力，
 * 整合原有的 QuizCard 和 ResourceCard 内容。
 */
export function ContentGenerationCard() {
  const t = useTranslations('featureCards.contentGeneration');
  const tQuiz = useTranslations('featureCards.quiz');
  const tResource = useTranslations('featureCards.resource');

  type Tab = 'tutorial' | 'resource' | 'quiz';
  const [activeTab, setActiveTab] = useState<Tab>('tutorial');

  const tabs: { id: Tab; label: string }[] = [
    { id: 'tutorial', label: t('tabTutorial') },
    { id: 'resource', label: t('tabResource') },
    { id: 'quiz', label: t('tabQuiz') },
  ];

  return (
    <Card className="p-6 border-border bg-gradient-to-br from-muted to-card shadow-xl">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">{t('title')}</h3>
          <Badge className="ml-auto text-xs bg-sage/10 text-sage border border-sage/20">
            {t('aiCurated')}
          </Badge>
        </div>

        {/* Tab 切换栏 */}
        <div className="flex gap-1 p-1 bg-muted rounded-lg">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={[
                'flex-1 py-1.5 text-xs font-medium rounded-md transition-all duration-200',
                activeTab === tab.id
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground',
              ].join(' ')}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab 内容 */}
        <AnimatePresence mode="wait">
          {activeTab === 'tutorial' && (
            <motion.div
              key="tutorial"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className="space-y-3"
            >
              {/* 概念标题 */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] text-muted-foreground">{t('conceptLabel')}</p>
                  <p className="text-sm font-semibold text-foreground">{t('conceptName')}</p>
                </div>
                <div className="flex items-center gap-1 text-muted-foreground">
                  <Clock className="w-3 h-3" />
                  <span className="text-xs">8 {t('minutes')}</span>
                </div>
              </div>

              {/* 理论基础 */}
              <div className="space-y-1">
                <p className="text-xs font-medium text-foreground">{t('theoryLabel')}</p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {t('theoryText')}
                </p>
              </div>

              {/* 代码示例 */}
              <div className="space-y-1">
                <p className="text-xs font-medium text-foreground">{t('exampleLabel')}</p>
                <div className="p-3 bg-zinc-900 rounded-lg font-mono text-xs text-green-400 leading-relaxed overflow-x-auto">
                  <span className="text-blue-400">const</span>{' '}
                  <span className="text-white">[count, setCount]</span>{' '}
                  <span className="text-yellow-400">=</span>{' '}
                  <span className="text-blue-300">useState</span>
                  <span className="text-white">(0);</span>
                  <br />
                  <span className="text-blue-400">const</span>{' '}
                  <span className="text-white">increment</span>{' '}
                  <span className="text-yellow-400">=</span>{' '}
                  <span className="text-white">{'() =>'}</span>{' '}
                  <span className="text-blue-300">setCount</span>
                  <span className="text-white">(c</span>{' '}
                  <span className="text-yellow-400">+</span>{' '}
                  <span className="text-white">1);</span>
                </div>
              </div>

              {/* 练习任务 */}
              <div className="p-3 bg-sage/5 border border-sage/20 rounded-lg">
                <p className="text-xs font-medium text-sage mb-1">{t('practiceLabel')}</p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {t('practiceText')}
                </p>
              </div>
            </motion.div>
          )}

          {activeTab === 'resource' && (
            <motion.div
              key="resource"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className="space-y-2"
            >
              {[
                { icon: FileText, title: tResource('resource1Title'), source: tResource('resource1Source'), stars: 4 },
                { icon: Video, title: tResource('resource2Title'), source: tResource('resource2Source'), stars: 5 },
                { icon: FileText, title: tResource('resource3Title'), source: tResource('resource3Source'), stars: 4 },
                { icon: BookOpen, title: tResource('resource4Title'), source: tResource('resource4Source'), stars: 5, isProject: true },
              ].map((item, i) => {
                const ItemIcon = item.icon;
                return (
                  <div
                    key={i}
                    className="flex gap-3 p-2.5 rounded-lg border border-border bg-card/60 hover:border-sage/40 transition-colors"
                  >
                    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-sage/10 flex items-center justify-center">
                      <ItemIcon className="w-4 h-4 text-sage" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-foreground truncate">{item.title}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-muted-foreground">{item.source}</span>
                        <div className="flex items-center gap-0.5">
                          {Array.from({ length: 5 }, (_, si) => (
                            <Star
                              key={si}
                              className={`w-2 h-2 ${si < item.stars ? 'text-sage fill-current' : 'text-border'}`}
                            />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </motion.div>
          )}

          {activeTab === 'quiz' && (
            <motion.div
              key="quiz"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
              className="space-y-3"
            >
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground">{tQuiz('questionOf')}</p>
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">1:45 {tQuiz('remaining')}</span>
                </div>
              </div>

              <p className="text-sm font-medium text-foreground leading-relaxed">
                {tQuiz('question')}{' '}
                <code className="px-1.5 py-0.5 bg-muted rounded text-xs font-mono">typeof []</code>?
              </p>

              <div className="space-y-1.5">
                {[
                  { id: 'A', text: '"array"', correct: false },
                  { id: 'B', text: '"object"', correct: true },
                  { id: 'C', text: '"undefined"', correct: false },
                  { id: 'D', text: '"null"', correct: false },
                ].map((option) => (
                  <div
                    key={option.id}
                    className={`w-full p-2.5 rounded-lg border-2 flex items-center gap-2 ${
                      option.correct
                        ? 'border-sage bg-sage/5'
                        : 'border-border bg-card'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                        option.correct ? 'border-sage text-sage' : 'border-border text-muted-foreground'
                      }`}
                    >
                      {option.id}
                    </div>
                    <span className="text-sm text-foreground">{option.text}</span>
                    {option.correct && <CheckCircle2 className="w-4 h-4 text-sage ml-auto" />}
                  </div>
                ))}
              </div>

              <div className="p-2.5 bg-sage/5 border border-sage/20 rounded-lg">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  💡 <span className="font-medium">{tQuiz('tip')}</span>{' '}
                  {tQuiz('tipText')}{' '}
                  <code className="px-1 bg-muted rounded">Array.isArray()</code>{' '}
                  {tQuiz('toCheck')}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Card>
  );
}

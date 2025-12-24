'use client';

/**
 * Feature 卡片组件
 * 
 * 4 个精美的展示卡片，使用全局设计令牌：
 * 1. Intent Analysis - 需求分析
 * 2. Roadmap - 路线图
 * 3. Quiz - 测验
 * 4. Resource - 资源推荐
 */

import React from 'react';
import { motion } from 'motion/react';
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
  Star
} from 'lucide-react';

/**
 * Intent Analysis Card - 需求分析卡片
 */
export function IntentAnalysisCard() {
  return (
    <Card className="p-6 border-border bg-gradient-to-br from-muted to-card">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <Target className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">Intent Analysis</h3>
        </div>

        {/* 学习目标 */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-foreground">Learning Goal</p>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Master full-stack web development with React and Node.js
          </p>
        </div>

        {/* 技术栈 */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-foreground">Key Technologies</p>
          <div className="flex flex-wrap gap-1.5">
            <Badge variant="secondary" className="text-xs">React</Badge>
            <Badge variant="secondary" className="text-xs">Node.js</Badge>
            <Badge variant="secondary" className="text-xs">TypeScript</Badge>
            <Badge variant="secondary" className="text-xs">PostgreSQL</Badge>
            <Badge variant="outline" className="text-xs border-dashed">+4 more</Badge>
          </div>
        </div>

        {/* 难度和时长 */}
        <div className="grid grid-cols-2 gap-3 pt-3 border-t border-border">
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock className="w-3.5 h-3.5" />
              <span>Duration</span>
            </div>
            <p className="text-sm font-semibold text-foreground">12 weeks</p>
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>Difficulty</span>
            </div>
            <Badge className="bg-orange-100 text-orange-700 hover:bg-orange-200">
              Intermediate
            </Badge>
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
  return (
    <Card className="p-6 border-border bg-gradient-to-br from-card to-muted">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">Learning Roadmap</h3>
        </div>

        {/* 路线图层级 */}
        <div className="space-y-3">
          {/* Stage */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-sage" />
              <span className="text-sm font-semibold text-foreground">
                Stage 1: Foundations
              </span>
            </div>
            
            {/* Module */}
            <div className="ml-4 pl-3 border-l-2 border-border space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-sage" />
                <span className="text-xs text-foreground">Module 1.1: JavaScript Basics</span>
              </div>
              
              {/* Concepts */}
              <div className="ml-6 space-y-1.5">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <CheckCircle2 className="w-3 h-3 text-sage" />
                  <span>Variables & Data Types</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <CheckCircle2 className="w-3 h-3 text-sage" />
                  <span>Functions & Scope</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-sage">
                  <Circle className="w-3 h-3" />
                  <span>Async Programming</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 进度 */}
        <div className="pt-3 border-t border-border">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Overall Progress</span>
            <span className="font-semibold">45%</span>
          </div>
          <Progress value={45} className="h-2" />
        </div>
      </div>
    </Card>
  );
}

/**
 * Quiz Card - 测验卡片
 */
export function QuizCard() {
  return (
    <Card className="p-6 border-border bg-gradient-to-br from-muted to-card">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">Practice Quiz</h3>
        </div>

        {/* 问题 */}
        <div className="space-y-3">
          <p className="text-sm font-medium text-foreground">
            What is the output of: <code className="px-1.5 py-0.5 bg-muted rounded text-xs">typeof []</code>?
          </p>

          {/* 选项 */}
          <div className="space-y-2">
            {[
              { id: 'A', text: '"array"', correct: false },
              { id: 'B', text: '"object"', correct: true },
              { id: 'C', text: '"undefined"', correct: false },
              { id: 'D', text: '"null"', correct: false },
            ].map((option) => (
              <motion.button
                key={option.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className={`w-full p-3 text-left rounded-lg border-2 transition-colors ${
                  option.correct
                    ? 'border-accent bg-muted'
                    : 'border-border bg-card hover:border-accent/50'
                }`}
              >
                <span className="text-xs font-medium text-foreground">
                  {option.id}. {option.text}
                </span>
              </motion.button>
            ))}
          </div>
        </div>

        {/* 统计 */}
        <div className="pt-3 border-t border-border">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Question 3 of 10</span>
            <div className="flex items-center gap-1 text-sage">
              <Star className="w-3.5 h-3.5 fill-current" />
              <span className="font-semibold">8/10 correct</span>
            </div>
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
  return (
    <Card className="p-6 border-border bg-gradient-to-br from-card to-muted">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">Curated Resources</h3>
        </div>

        {/* 资源列表 */}
        <div className="space-y-3">
          {/* Article */}
          <div className="flex gap-3 p-3 rounded-lg glass-panel hover:border-accent/50 transition-colors">
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                Async/Await Deep Dive
              </p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-muted-foreground">javascript.info</span>
                <div className="flex items-center gap-0.5">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className={`w-3 h-3 ${
                        i < 4 ? 'text-yellow-400 fill-current' : 'text-border'
                      }`}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Video */}
          <div className="flex gap-3 p-3 rounded-lg glass-panel hover:border-accent/50 transition-colors">
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-red-50 flex items-center justify-center">
              <Video className="w-5 h-5 text-red-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                Promises Explained
              </p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-muted-foreground">YouTube · 18 min</span>
                <div className="flex items-center gap-0.5">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className={`w-3 h-3 ${
                        i < 5 ? 'text-yellow-400 fill-current' : 'text-border'
                      }`}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 总数 */}
        <div className="pt-3 border-t border-border text-center">
          <p className="text-xs text-muted-foreground">
            12 more resources available
          </p>
        </div>
      </div>
    </Card>
  );
}

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
    <Card className="p-6 border-border bg-gradient-to-br from-muted to-card shadow-xl">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <Target className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">Intent Analysis</h3>
          <Badge variant="outline" className="ml-auto text-xs">AI-Generated</Badge>
        </div>

        {/* 学习目标 */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-foreground">Learning Goal</p>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Master full-stack web development with React and Node.js, focusing on modern best practices and scalable architecture
          </p>
        </div>

        {/* 当前水平 */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-foreground">Current Experience</p>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">Beginner HTML/CSS</Badge>
            <Badge variant="secondary" className="text-xs">Basic JavaScript</Badge>
          </div>
        </div>

        {/* 技术栈 */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-foreground">Recommended Tech Stack</p>
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
          <p className="text-xs font-medium text-foreground">Identified Gaps</p>
          <div className="space-y-1.5">
            {[
              'Component architecture & state management',
              'RESTful API design & authentication',
              'Database modeling & migrations',
              'Deployment & DevOps basics',
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
              <span>Duration</span>
            </div>
            <p className="text-sm font-semibold text-foreground">12 weeks</p>
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>Level</span>
            </div>
            <Badge className="bg-orange-100 text-orange-700 hover:bg-orange-200 text-xs">
              Intermediate
            </Badge>
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Layers className="w-3.5 h-3.5" />
              <span>Concepts</span>
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
  return (
    <Card className="p-6 border-border bg-gradient-to-br from-card to-muted shadow-xl">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">Learning Roadmap</h3>
          <Badge variant="outline" className="ml-auto text-xs">3 Stages</Badge>
        </div>

        {/* 路线图层级 */}
        <div className="space-y-4">
          {/* Stage 1 - Completed */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-sage" />
              <span className="text-sm font-bold text-foreground">
                Stage 1: Foundations
              </span>
              <Badge variant="secondary" className="ml-auto text-xs">Completed</Badge>
            </div>
            
            {/* Module */}
            <div className="ml-4 pl-3 border-l-2 border-sage/30 space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-sage" />
                <span className="text-xs text-foreground font-medium">Module 1.1: JavaScript Basics</span>
              </div>
              
              {/* Concepts */}
              <div className="ml-5 space-y-1">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <CheckCircle2 className="w-2.5 h-2.5 text-sage" />
                  <span>Variables & Data Types</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <CheckCircle2 className="w-2.5 h-2.5 text-sage" />
                  <span>Functions & Scope</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <CheckCircle2 className="w-2.5 h-2.5 text-sage" />
                  <span>Objects & Arrays</span>
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
                Stage 2: React Development
              </span>
              <Badge className="ml-auto text-xs bg-blue-100 text-blue-700">In Progress</Badge>
            </div>
            
            <div className="ml-4 pl-3 border-l-2 border-border space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-sage" />
                <span className="text-xs text-foreground font-medium">Module 2.1: React Fundamentals</span>
              </div>
              
              <div className="ml-5 space-y-1">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <CheckCircle2 className="w-2.5 h-2.5 text-sage" />
                  <span>Components & Props</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-sage font-medium">
                  <Circle className="w-2.5 h-2.5" />
                  <span>State & Lifecycle</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground/50">
                  <Circle className="w-2.5 h-2.5" />
                  <span>Hooks (useState, useEffect)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Stage 3 - Locked */}
          <div className="space-y-2 opacity-50">
            <div className="flex items-center gap-2">
              <Circle className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-bold text-muted-foreground">
                Stage 3: Full-Stack Integration
              </span>
              <Badge variant="outline" className="ml-auto text-xs">Locked</Badge>
            </div>
          </div>
        </div>

        {/* 进度统计 */}
        <div className="pt-3 border-t border-border space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Overall Progress</span>
            <span className="font-semibold text-foreground">45%</span>
          </div>
          <Progress value={45} className="h-2" />
          
          <div className="grid grid-cols-3 gap-2 pt-2">
            <div className="text-center">
              <p className="text-lg font-bold text-foreground">32</p>
              <p className="text-xs text-muted-foreground">Completed</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-sage">5</p>
              <p className="text-xs text-muted-foreground">In Progress</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-muted-foreground">52</p>
              <p className="text-xs text-muted-foreground">Remaining</p>
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
  return (
    <Card className="p-6 border-border bg-gradient-to-br from-muted to-card shadow-xl">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">Practice Quiz</h3>
          <Badge className="ml-auto text-xs bg-sage/10 text-sage border border-sage/20">Interactive</Badge>
        </div>

        {/* 问题标签 */}
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">JavaScript</Badge>
          <Badge variant="outline" className="text-xs">Data Types</Badge>
          <Badge variant="outline" className="text-xs">Medium</Badge>
        </div>

        {/* 问题 */}
        <div className="space-y-3">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">Question 3 of 10</p>
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">1:45 remaining</span>
              </div>
            </div>
            <p className="text-sm font-medium text-foreground leading-relaxed">
              What is the output of:{' '}
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
              💡 <span className="font-medium">Tip:</span> In JavaScript, arrays are actually a special type of object. Use <code className="px-1 bg-muted rounded">Array.isArray()</code> to check for arrays specifically.
            </p>
          </div>
        </div>

        {/* 统计 */}
        <div className="pt-3 border-t border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1 text-sage">
                <Star className="w-3.5 h-3.5 fill-current" />
                <span className="text-xs font-semibold">8/10 correct</span>
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
  return (
    <Card className="p-6 border-border bg-gradient-to-br from-card to-muted shadow-xl">
      <div className="space-y-4">
        {/* 标题 */}
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-sage" />
          <h3 className="text-lg font-semibold text-foreground">Curated Resources</h3>
          <Badge className="ml-auto text-xs bg-sage/10 text-sage border border-sage/20">14 Resources</Badge>
        </div>

        {/* 筛选标签 */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <Badge variant="default" className="text-xs bg-sage text-white">All</Badge>
          <Badge variant="outline" className="text-xs">Articles</Badge>
          <Badge variant="outline" className="text-xs">Videos</Badge>
          <Badge variant="outline" className="text-xs">Projects</Badge>
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
                Async/Await Deep Dive
              </p>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-muted-foreground">javascript.info · 12 min read</span>
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
                Promises Explained Visually
              </p>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-muted-foreground">YouTube · 18 min</span>
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
                Error Handling Best Practices
              </p>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-muted-foreground">MDN Web Docs · 8 min read</span>
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
                Build a Weather App with Async
              </p>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-muted-foreground">Hands-on Project · 2 hours</span>
                <Badge className="text-xs bg-sage/10 text-sage border border-sage/20">
                  Project
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
                <span className="font-semibold">8 completed</span>
              </div>
              <div className="h-3 w-px bg-border" />
              <span className="text-muted-foreground">10 more available</span>
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="text-xs font-medium text-sage hover:text-sage/80 transition-colors"
            >
              View All →
            </motion.button>
          </div>
        </div>
      </div>
    </Card>
  );
}

'use client';

/**
 * ValidationResultPanel - 验证结果展示组件（重构版）
 * 
 * 展示 structure_validation 的详细验证结果
 * 
 * 功能：
 * - 展示 5 个维度的评分（DimensionScores）
 * - 展示结构化改进建议（ImprovementSuggestions）
 * - 分类展示 critical/warning 问题（移除 suggestion）
 * - 使用 Accordion 实现可折叠的问题列表
 * - 使用不同颜色标记不同严重级别
 * - 显示总体评分和验证轮次
 */

import { 
  AlertCircle, 
  AlertTriangle, 
  Lightbulb, 
  CheckCircle,
  XCircle,
  TrendingUp,
  Target,
  ArrowRight,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { cn } from '@/lib/utils';
import type { ValidationResult, ValidationIssue, DimensionScore, StructuralSuggestion } from '@/types/validation';

interface ValidationResultPanelProps {
  validationResult: ValidationResult;
  className?: string;
}

/**
 * 获取严重级别的显示配置
 */
function getSeverityConfig(severity: string) {
  const configs = {
    critical: {
      label: 'Critical',
      icon: XCircle,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      badgeClass: 'bg-red-100 text-red-700 border-red-300',
    },
    warning: {
      label: 'Warning',
      icon: AlertTriangle,
      color: 'text-amber-600',
      bgColor: 'bg-amber-50',
      borderColor: 'border-amber-200',
      badgeClass: 'bg-amber-100 text-amber-700 border-amber-300',
    },
  };
  return configs[severity as keyof typeof configs] || configs.warning;
}

/**
 * 维度标签映射
 */
const DIMENSION_LABELS: Record<string, string> = {
  knowledge_completeness: 'Knowledge Completeness',
  knowledge_progression: 'Knowledge Progression',
  stage_coherence: 'Stage Coherence',
  module_clarity: 'Module Clarity',
  user_alignment: 'User Alignment',
};

/**
 * 操作类型标签映射
 */
const ACTION_LABELS: Record<string, string> = {
  add_concept: 'Add Concept',
  add_module: 'Add Module',
  add_stage: 'Add Stage',
  modify_concept: 'Modify Concept',
  reorder_stage: 'Reorder Stage',
  merge_modules: 'Merge Modules',
};

/**
 * 维度评分展示组件
 */
function DimensionScoresDisplay({ scores }: { scores: DimensionScore[] }) {
  if (!scores || scores.length === 0) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <TrendingUp className="w-4 h-4 text-blue-600" />
        <h4 className="text-sm font-semibold">Dimension Scores</h4>
      </div>
      <div className="space-y-3">
        {scores.map((score, idx) => (
          <div key={idx} className="space-y-1.5">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-foreground">
                {DIMENSION_LABELS[score.dimension] || score.dimension}
              </span>
              <span className={cn(
                'font-bold',
                score.score >= 80 ? 'text-green-600' : score.score >= 60 ? 'text-blue-600' : 'text-amber-600'
              )}>
                {score.score.toFixed(0)}/100
              </span>
            </div>
            <div className="relative">
              <Progress value={score.score} className="h-2 bg-gray-200" />
              <div 
                className={cn(
                  'absolute top-0 left-0 h-2 rounded-full transition-all',
                  score.score >= 80 ? 'bg-green-500' : score.score >= 60 ? 'bg-blue-500' : 'bg-amber-500'
                )}
                style={{ width: `${score.score}%` }}
              />
            </div>
            {score.rationale && (
              <p className="text-xs text-muted-foreground leading-relaxed">
                {score.rationale}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * 改进建议卡片组件
 */
function SuggestionCard({ suggestion }: { suggestion: StructuralSuggestion }) {
  return (
    <div className="p-4 rounded-lg border bg-blue-50 border-blue-200">
      <div className="flex gap-3">
        <Lightbulb className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="outline" className="text-xs bg-blue-100 text-blue-700 border-blue-300">
              {ACTION_LABELS[suggestion.action] || suggestion.action}
            </Badge>
            <ArrowRight className="w-3 h-3 text-blue-400" />
            <span className="text-xs text-muted-foreground">
              {suggestion.target_location}
            </span>
          </div>
          <p className="text-sm font-medium text-foreground">
            {suggestion.content}
          </p>
          {suggestion.reason && (
            <p className="text-xs text-muted-foreground">
              <span className="font-medium">Reason:</span> {suggestion.reason}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * 问题项组件
 */
function IssueItem({ issue }: { issue: ValidationIssue }) {
  const config = getSeverityConfig(issue.severity);
  const Icon = config.icon;

  return (
    <div className={cn('p-4 rounded-lg border', config.bgColor, config.borderColor)}>
      <div className="flex gap-3">
        <Icon className={cn('w-5 h-5 shrink-0 mt-0.5', config.color)} />
        <div className="flex-1 space-y-2">
          {/* 位置标签 */}
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="outline" className="text-xs">
              {issue.location}
            </Badge>
            <Badge variant="outline" className={cn('text-xs', config.badgeClass)}>
              {config.label}
            </Badge>
            {issue.category && (
              <Badge variant="outline" className="text-xs bg-gray-100 text-gray-600">
                {issue.category.replace(/_/g, ' ')}
              </Badge>
            )}
          </div>
          
          {/* 问题描述 */}
          <p className="text-sm text-foreground font-medium">
            {issue.issue}
          </p>
          
          {/* 改进建议 */}
          {issue.suggestion && (
            <div className="pt-2 border-t border-gray-200">
              <p className="text-xs text-muted-foreground">
                <span className="font-medium">Suggestion:</span> {issue.suggestion}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function ValidationResultPanel({ validationResult, className }: ValidationResultPanelProps) {
  // 按严重级别分类问题（只有 critical 和 warning）
  const criticalIssues = validationResult.issues.filter(i => i.severity === 'critical');
  const warningIssues = validationResult.issues.filter(i => i.severity === 'warning');
  
  // 改进建议来自独立字段
  const improvementSuggestions = validationResult.improvement_suggestions || [];

  // 计算评分颜色
  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 75) return 'text-blue-600';
    if (score >= 60) return 'text-amber-600';
    return 'text-red-600';
  };

  const getProgressColor = (score: number) => {
    if (score >= 90) return 'bg-green-500';
    if (score >= 75) return 'bg-blue-500';
    if (score >= 60) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <Card className={cn('p-6 space-y-6', className)}>
      {/* 标题和总览 */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {validationResult.is_valid ? (
              <CheckCircle className="w-6 h-6 text-green-600" />
            ) : (
              <AlertCircle className="w-6 h-6 text-amber-600" />
            )}
            <div>
              <h3 className="text-lg font-semibold">
                Validation Results
                <span className="text-sm text-muted-foreground font-normal ml-2">
                  (Round {validationResult.validation_round})
                </span>
              </h3>
              <p className="text-sm text-muted-foreground">
                {validationResult.is_valid 
                  ? 'Roadmap structure passed validation' 
                  : 'Issues found - AI is refining the structure'}
              </p>
            </div>
          </div>
          
          {/* 评分 */}
          <div className="text-right">
            <div className={cn('text-3xl font-bold', getScoreColor(validationResult.overall_score))}>
              {validationResult.overall_score.toFixed(0)}
            </div>
            <div className="text-xs text-muted-foreground">Quality Score</div>
          </div>
        </div>
        
        {/* 进度条 */}
        <div className="space-y-2">
          <div className="relative">
            <Progress 
              value={validationResult.overall_score} 
              className="h-2 bg-gray-200"
            />
            <div 
              className={cn('absolute top-0 left-0 h-2 rounded-full transition-all', getProgressColor(validationResult.overall_score))}
              style={{ width: `${validationResult.overall_score}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>0</span>
            <span>100</span>
          </div>
        </div>

        {/* 验证摘要 */}
        {validationResult.validation_summary && (
          <div className="p-3 rounded-lg bg-gray-50 border border-gray-200">
            <p className="text-sm text-foreground leading-relaxed">
              {validationResult.validation_summary}
            </p>
          </div>
        )}
      </div>

      {/* 问题统计 */}
      <div className="grid grid-cols-3 gap-4">
        <div className={cn('p-3 rounded-lg border', criticalIssues.length > 0 ? 'bg-red-50 border-red-200' : 'bg-gray-50 border-gray-200')}>
          <div className="flex items-center gap-2">
            <XCircle className={cn('w-4 h-4', criticalIssues.length > 0 ? 'text-red-600' : 'text-gray-400')} />
            <span className="text-xs font-medium text-muted-foreground">Critical</span>
          </div>
          <div className={cn('text-2xl font-bold mt-1', criticalIssues.length > 0 ? 'text-red-600' : 'text-gray-600')}>
            {criticalIssues.length}
          </div>
        </div>
        
        <div className={cn('p-3 rounded-lg border', warningIssues.length > 0 ? 'bg-amber-50 border-amber-200' : 'bg-gray-50 border-gray-200')}>
          <div className="flex items-center gap-2">
            <AlertTriangle className={cn('w-4 h-4', warningIssues.length > 0 ? 'text-amber-600' : 'text-gray-400')} />
            <span className="text-xs font-medium text-muted-foreground">Warnings</span>
          </div>
          <div className={cn('text-2xl font-bold mt-1', warningIssues.length > 0 ? 'text-amber-600' : 'text-gray-600')}>
            {warningIssues.length}
          </div>
        </div>
        
        <div className={cn('p-3 rounded-lg border', improvementSuggestions.length > 0 ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200')}>
          <div className="flex items-center gap-2">
            <Lightbulb className={cn('w-4 h-4', improvementSuggestions.length > 0 ? 'text-blue-600' : 'text-gray-400')} />
            <span className="text-xs font-medium text-muted-foreground">Suggestions</span>
          </div>
          <div className={cn('text-2xl font-bold mt-1', improvementSuggestions.length > 0 ? 'text-blue-600' : 'text-gray-600')}>
            {improvementSuggestions.length}
          </div>
        </div>
      </div>

      {/* 维度评分 */}
      {validationResult.dimension_scores && validationResult.dimension_scores.length > 0 && (
        <DimensionScoresDisplay scores={validationResult.dimension_scores} />
      )}

      {/* 改进建议 */}
      {improvementSuggestions.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Target className="w-4 h-4 text-blue-600" />
            <h4 className="text-sm font-semibold">Improvement Suggestions</h4>
          </div>
          <div className="space-y-3">
            {improvementSuggestions.map((suggestion, idx) => (
              <SuggestionCard key={idx} suggestion={suggestion} />
            ))}
          </div>
        </div>
      )}

      {/* 问题详情 - 使用 Accordion */}
      {validationResult.issues.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-foreground">Issue Details</h4>
          
          <Accordion type="multiple" className="space-y-2">
            {/* Critical Issues */}
            {criticalIssues.length > 0 && (
              <AccordionItem value="critical" className="border rounded-lg">
                <AccordionTrigger className="px-4 hover:no-underline">
                  <div className="flex items-center gap-2">
                    <XCircle className="w-4 h-4 text-red-600" />
                    <span className="font-medium">Critical Issues ({criticalIssues.length})</span>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 space-y-3">
                  {criticalIssues.map((issue, idx) => (
                    <IssueItem key={idx} issue={issue} />
                  ))}
                </AccordionContent>
              </AccordionItem>
            )}
            
            {/* Warnings */}
            {warningIssues.length > 0 && (
              <AccordionItem value="warnings" className="border rounded-lg">
                <AccordionTrigger className="px-4 hover:no-underline">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-600" />
                    <span className="font-medium">Warnings ({warningIssues.length})</span>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 space-y-3">
                  {warningIssues.map((issue, idx) => (
                    <IssueItem key={idx} issue={issue} />
                  ))}
                </AccordionContent>
              </AccordionItem>
            )}
          </Accordion>
        </div>
      )}

      {/* 如果没有问题且没有建议 */}
      {validationResult.issues.length === 0 && improvementSuggestions.length === 0 && (
        <div className="text-center py-8">
          <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">
            No issues found. The roadmap structure is excellent!
          </p>
        </div>
      )}
    </Card>
  );
}

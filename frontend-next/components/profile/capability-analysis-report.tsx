'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  Sparkles,
  Target,
  BookOpen,
  Award,
} from 'lucide-react';
import type { CapabilityAnalysisResult } from '@/types/assessment';
import { cn } from '@/lib/utils';

interface CapabilityAnalysisReportProps {
  result: CapabilityAnalysisResult;
  onClose?: () => void;
  showActions?: boolean;
}

export function CapabilityAnalysisReport({
  result,
  onClose,
  showActions = true,
}: CapabilityAnalysisReportProps) {
  // 防御性检查：确保所有必需的数组字段存在
  const safeResult = {
    ...result,
    strengths: result.strengths || [],
    weaknesses: result.weaknesses || [],
    knowledge_gaps: result.knowledge_gaps || [],
    learning_suggestions: result.learning_suggestions || [],
  };

  // 获取优先级配置
  const getPriorityConfig = (priority: string) => {
    switch (priority) {
      case 'high':
        return {
          icon: AlertTriangle,
          color: 'text-sage-800',
          bgColor: 'bg-sage-50/70',
          borderColor: 'border-sage-300',
          badge: 'destructive',
          label: 'High Priority',
        };
      case 'medium':
        return {
          icon: AlertCircle,
          color: 'text-sage-600',
          bgColor: 'bg-sage-50/40',
          borderColor: 'border-sage-200',
          badge: 'warning',
          label: 'Medium Priority',
        };
      default:
        return {
          icon: BookOpen,
          color: 'text-sage-500',
          bgColor: 'bg-muted/50',
          borderColor: 'border-border',
          badge: 'secondary',
          label: 'Low Priority',
        };
    }
  };

  // 获取能力验证图标
  const getVerificationIcon = () => {
    const { claimed_level, verified_level } = safeResult.proficiency_verification || {};
    if (!claimed_level || !verified_level) {
      return <Minus className="w-5 h-5 text-muted-foreground" />;
    }
    if (verified_level === claimed_level) {
      return <CheckCircle2 className="w-5 h-5 text-sage-700" />;
    } else if (verified_level < claimed_level) {
      return <TrendingDown className="w-5 h-5 text-muted-foreground" />;
    } else {
      return <TrendingUp className="w-5 h-5 text-sage-600" />;
    }
  };

  // 获取置信度颜色
  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'high':
        return 'text-sage-700';
      case 'medium':
        return 'text-sage-500';
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <div className="space-y-6 py-4">
      {/* 整体评价 */}
      <Card className="border-2 border-sage-200 bg-gradient-to-br from-sage-50 to-white">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sage-900">
            <Sparkles className="w-5 h-5" />
            Overall Assessment
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
            {safeResult.overall_assessment || 'No assessment available'}
          </p>
        </CardContent>
      </Card>

      {/* 优势与薄弱点 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 优势领域 */}
        <Card className="border-2 border-sage-200 bg-sage-50/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sage-900 text-lg">
              <CheckCircle2 className="w-5 h-5" />
              Strengths
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {safeResult.strengths.length > 0 ? (
              safeResult.strengths.map((strength, index) => (
                <div
                  key={index}
                  className="flex items-start gap-2 text-sm text-sage-800"
                >
                  <span className="text-sage-600 mt-0.5">✓</span>
                  <span className="whitespace-pre-wrap">{strength}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No data available</p>
            )}
          </CardContent>
        </Card>

        {/* 薄弱环节 */}
        <Card className="border-2 border-border bg-muted/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-foreground text-lg">
              <AlertCircle className="w-5 h-5" />
              Weaknesses
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {safeResult.weaknesses.length > 0 ? (
              safeResult.weaknesses.map((weakness, index) => (
                <div
                  key={index}
                  className="flex items-start gap-2 text-sm text-muted-foreground"
                >
                  <span className="text-muted-foreground mt-0.5">•</span>
                  <span className="whitespace-pre-wrap">{weakness}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No data available</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 知识缺口 */}
      {safeResult.knowledge_gaps.length > 0 && (
        <Card className="border-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5 text-sage-600" />
              Knowledge Gaps
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {safeResult.knowledge_gaps.map((gap, index) => {
              const config = getPriorityConfig(gap.priority);
              const IconComponent = config.icon;

              return (
                <Card
                  key={index}
                  className={cn(
                    'border-2',
                    config.borderColor,
                    config.bgColor
                  )}
                >
                  <CardContent className="p-4 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-2 flex-1">
                        <IconComponent className={cn('w-5 h-5 mt-0.5', config.color)} />
                        <div className="flex-1">
                          <h4 className="font-semibold text-foreground">
                            {gap.topic}
                          </h4>
                        </div>
                      </div>
                      <Badge variant={config.badge as any} className="shrink-0">
                        {config.label}
                      </Badge>
                    </div>

                    <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                      {gap.description}
                    </p>

                    {gap.recommendations.length > 0 && (
                      <div className="space-y-2 pt-2 border-t">
                        <div className="flex items-center gap-1.5 text-sm font-medium text-foreground">
                          <BookOpen className="w-4 h-4" />
                          Recommendations
                        </div>
                        <ul className="space-y-1.5">
                          {gap.recommendations.map((rec, recIndex) => (
                            <li
                              key={recIndex}
                              className="text-sm text-muted-foreground flex items-start gap-2"
                            >
                              <span className="text-sage-600 mt-0.5">•</span>
                              <span className="whitespace-pre-wrap">{rec}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </CardContent>
        </Card>
      )}

      {/* 学习建议 */}
      {safeResult.learning_suggestions.length > 0 && (
        <Card className="border-2 border-sage-200 bg-sage-50/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sage-900">
              <BookOpen className="w-5 h-5" />
              Learning Suggestions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {safeResult.learning_suggestions.map((suggestion, index) => (
                <li
                  key={index}
                  className="text-sm text-sage-800 flex items-start gap-2"
                >
                  <span className="text-sage-600 mt-0.5">→</span>
                  <span className="whitespace-pre-wrap">{suggestion}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* 能力级别验证 */}
      <Card className="border-2">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Award className="w-5 h-5 text-sage-600" />
            Proficiency Verification
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {safeResult.proficiency_verification ? (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="text-sm text-muted-foreground">Claimed Level</div>
                  <div className="text-lg font-semibold text-foreground">
                    {safeResult.proficiency_verification.claimed_level || 'N/A'}
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="text-sm text-muted-foreground">Verified Level</div>
                  <div className="flex items-center gap-2">
                    {getVerificationIcon()}
                    <span className="text-lg font-semibold text-foreground">
                      {safeResult.proficiency_verification.verified_level || 'N/A'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Confidence</span>
                  <span
                    className={cn(
                      'text-sm font-medium',
                      getConfidenceColor(safeResult.proficiency_verification.confidence || 'low')
                    )}
                  >
                    {safeResult.proficiency_verification.confidence === 'high'
                      ? 'High'
                      : safeResult.proficiency_verification.confidence === 'medium'
                      ? 'Medium'
                      : 'Low'}
                  </span>
                </div>
              </div>

              <div className="pt-3 border-t">
                <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                  {safeResult.proficiency_verification.reasoning || 'No reasoning available'}
                </p>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No verification data available</p>
          )}
        </CardContent>
      </Card>

      {/* 分数细分 */}
      <Card className="border-2">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="w-5 h-5 text-sage-600" />
            Score Breakdown
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {safeResult.score_breakdown ? (
            <>
              {/* Beginner */}
              {safeResult.score_breakdown.beginner && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Beginner Questions</span>
                    <span className="text-sm text-muted-foreground">
                      {safeResult.score_breakdown.beginner.correct}/{safeResult.score_breakdown.beginner.total} (
                      {safeResult.score_breakdown.beginner.percentage.toFixed(1)}%)
                    </span>
                  </div>
                  <Progress value={safeResult.score_breakdown.beginner.percentage} className="h-2" />
                </div>
              )}

              {/* Intermediate */}
              {safeResult.score_breakdown.intermediate && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Intermediate Questions</span>
                    <span className="text-sm text-muted-foreground">
                      {safeResult.score_breakdown.intermediate.correct}/{safeResult.score_breakdown.intermediate.total} (
                      {safeResult.score_breakdown.intermediate.percentage.toFixed(1)}%)
                    </span>
                  </div>
                  <Progress value={safeResult.score_breakdown.intermediate.percentage} className="h-2" />
                </div>
              )}

              {/* Expert */}
              {safeResult.score_breakdown.expert && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Expert Questions</span>
                    <span className="text-sm text-muted-foreground">
                      {safeResult.score_breakdown.expert.correct}/{safeResult.score_breakdown.expert.total} (
                      {safeResult.score_breakdown.expert.percentage.toFixed(1)}%)
                    </span>
                  </div>
                  <Progress value={safeResult.score_breakdown.expert.percentage} className="h-2" />
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No score breakdown available</p>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      {showActions && onClose && (
        <div className="flex gap-3 pt-2">
          <Button
            variant="outline"
            className="flex-1"
            onClick={onClose}
            size="lg"
          >
            Close
          </Button>
          <Button
            className="flex-1 bg-sage-600 hover:bg-sage-700"
            onClick={onClose}
            size="lg"
          >
            Back to Profile
          </Button>
        </div>
      )}
    </div>
  );
}


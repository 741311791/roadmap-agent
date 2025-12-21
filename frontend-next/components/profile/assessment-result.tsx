'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle2, AlertCircle, XCircle, Sparkles, Loader2 } from 'lucide-react';
import { useUserProfileStore } from '@/lib/store/user-profile-store';
import type { AssessmentEvaluationResult, CapabilityAnalysisResult } from '@/types/assessment';

interface AssessmentResultProps {
  result: AssessmentEvaluationResult;
  technology: string;
  proficiency: string;
  assessmentId: string;
  answers: string[];
  userId: string;
  onClose: () => void;
  onAnalysisComplete?: (analysis: CapabilityAnalysisResult) => void;
}

export function AssessmentResult({
  result,
  technology,
  proficiency,
  assessmentId,
  answers,
  userId,
  onClose,
  onAnalysisComplete,
}: AssessmentResultProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  
  // 从 Zustand store 获取更新函数
  const { updateTechStack } = useUserProfileStore();

  const handleAnalyze = async () => {
    try {
      setIsAnalyzing(true);
      setAnalysisError(null);

      const { analyzeTechCapability } = await import('@/lib/api/endpoints');
      
      // 调用能力分析API，但不保存到后端
      const analysisResult = await analyzeTechCapability(
        technology,
        proficiency,
        userId,
        assessmentId,
        answers,
        false // 不保存到后端，由前端更新 store
      );
      
      // 更新 Zustand store 中的技术栈项
      // 将能力分析结果附加到技术栈项
      updateTechStack(technology, {
        proficiency: proficiency as 'beginner' | 'intermediate' | 'expert',
        capability_analysis: analysisResult as any, // 添加能力分析结果
      });

      console.log('[AssessmentResult] Capability analysis saved to store:', technology);
      onAnalysisComplete?.(analysisResult);
    } catch (err: any) {
      console.error('Failed to analyze capability:', err);
      setAnalysisError(err.message || 'Capability analysis failed, please try again later');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getRecommendationConfig = () => {
    if (result.recommendation === 'confirmed') {
      return {
        icon: CheckCircle2,
        iconColor: 'text-sage-700',
        bgColor: 'bg-sage-50',
        borderColor: 'border-sage-200',
        title: 'Skill Confirmed',
        subtitle: 'Your skill level matches the current proficiency',
      };
    } else if (result.recommendation === 'adjust') {
      return {
        icon: AlertCircle,
        iconColor: 'text-sage-600',
        bgColor: 'bg-sage-50/50',
        borderColor: 'border-sage-200',
        title: 'Maintain Level',
        subtitle: 'Consider staying at this level and strengthening weak areas',
      };
    } else {
      return {
        icon: XCircle,
        iconColor: 'text-muted-foreground',
        bgColor: 'bg-muted',
        borderColor: 'border-border',
        title: 'Adjust Level',
        subtitle: 'Consider selecting a more foundational level to progress gradually',
      };
    }
  };

  const config = getRecommendationConfig();
  const IconComponent = config.icon;

  return (
    <div className="space-y-6 py-4">
      {/* Result Summary */}
      <div className="text-center space-y-4">
        <div className={`w-20 h-20 mx-auto rounded-full ${config.bgColor} flex items-center justify-center border-2 ${config.borderColor}`}>
          <IconComponent className={`w-10 h-10 ${config.iconColor}`} />
        </div>
        
        <div>
          <h3 className="text-2xl font-bold text-foreground">{config.title}</h3>
          <p className="text-muted-foreground mt-2">{config.subtitle}</p>
        </div>
      </div>

      {/* Score Details */}
      <Card className="border-2">
        <CardContent className="p-6">
          <div className="grid grid-cols-3 gap-6 text-center">
            <div className="space-y-1">
              <div className="text-4xl font-bold text-foreground">
                {result.score}
              </div>
              <div className="text-sm text-muted-foreground">Total Score</div>
              <div className="text-xs text-muted-foreground">
                out of {result.max_score}
              </div>
            </div>
            
            <div className="space-y-1">
              <div className="text-4xl font-bold text-foreground">
                {result.percentage.toFixed(1)}%
              </div>
              <div className="text-sm text-muted-foreground">Accuracy</div>
            </div>
            
            <div className="space-y-1">
              <div className="text-4xl font-bold text-foreground">
                {result.correct_count}/{result.total_questions}
              </div>
              <div className="text-sm text-muted-foreground">Correct</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Additional Info */}
      <Card className={`${config.bgColor} border-2 ${config.borderColor}`}>
        <CardContent className="p-5">
          <div className="space-y-2">
            <h4 className="font-semibold text-foreground">Scoring Rules</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Easy questions: 1 point each</li>
              <li>• Medium questions: 2 points each</li>
              <li>• Hard questions: 3 points each</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Message */}
      <div className="text-center">
        <p className="text-sm text-muted-foreground">
          {result.message}
        </p>
      </div>

      {/* Error Message */}
      {analysisError && (
        <Card className="bg-red-50 border-2 border-red-200">
          <CardContent className="p-4">
            <p className="text-sm text-red-600">{analysisError}</p>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <Button
          variant="outline"
          className="flex-1"
          onClick={onClose}
          size="lg"
        >
          Got It
        </Button>
        <Button
          className="flex-1 bg-gradient-to-r from-sage-600 to-sage-700 hover:from-sage-700 hover:to-sage-800 text-white"
          onClick={handleAnalyze}
          disabled={isAnalyzing}
          size="lg"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-4 w-4" />
              Capability Analysis
            </>
          )}
        </Button>
      </div>
    </div>
  );
}


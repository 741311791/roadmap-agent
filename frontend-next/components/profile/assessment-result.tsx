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
      
      // 触发异步能力分析任务
      const taskResponse = await analyzeTechCapability(
        technology,
        proficiency,
        {
          user_id: userId,
          assessment_id: assessmentId,
          answers: answers,
          save_to_profile: true, // 保存到后端用户画像
        }
      );
      
      console.log('[AssessmentResult] Capability analysis task triggered:', {
        task_id: taskResponse.task_id,
        technology: taskResponse.technology,
        status: taskResponse.status,
      });

      // 显示成功提示并关闭对话框
      alert(
        `✨ ${taskResponse.message}\n\n` +
        `任务ID: ${taskResponse.task_id}\n\n` +
        `分析完成后，结果将自动保存到您的用户画像中。`
      );
      
      // 关闭对话框
      onClose();
    } catch (err: any) {
      console.error('Failed to trigger capability analysis:', err);
      setAnalysisError(err.message || 'Failed to start capability analysis, please try again later');
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
    <div className="space-y-4 sm:space-y-6 py-4">
      {/* Result Summary */}
      <div className="text-center space-y-3 sm:space-y-4">
        <div className={`w-16 h-16 sm:w-20 sm:h-20 mx-auto rounded-full ${config.bgColor} flex items-center justify-center border-2 ${config.borderColor}`}>
          <IconComponent className={`w-8 h-8 sm:w-10 sm:h-10 ${config.iconColor}`} />
        </div>
        
        <div className="px-4">
          <h3 className="text-xl sm:text-2xl font-bold text-foreground">{config.title}</h3>
          <p className="text-sm sm:text-base text-muted-foreground mt-2">{config.subtitle}</p>
        </div>
      </div>

      {/* Score Details */}
      <Card className="border-2">
        <CardContent className="p-4 sm:p-6">
          <div className="grid grid-cols-3 gap-3 sm:gap-6 text-center">
            <div className="space-y-1">
              <div className="text-2xl sm:text-4xl font-bold text-foreground">
                {result.score}
              </div>
              <div className="text-xs sm:text-sm text-muted-foreground">Total Score</div>
              <div className="text-xs text-muted-foreground">
                out of {result.max_score}
              </div>
            </div>
            
            <div className="space-y-1">
              <div className="text-2xl sm:text-4xl font-bold text-foreground">
                {result.percentage.toFixed(1)}%
              </div>
              <div className="text-xs sm:text-sm text-muted-foreground">Accuracy</div>
            </div>
            
            <div className="space-y-1">
              <div className="text-2xl sm:text-4xl font-bold text-foreground">
                {result.correct_count}/{result.total_questions}
              </div>
              <div className="text-xs sm:text-sm text-muted-foreground">Correct</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Additional Info */}
      <Card className={`${config.bgColor} border-2 ${config.borderColor}`}>
        <CardContent className="p-4 sm:p-5">
          <div className="space-y-2">
            <h4 className="text-sm sm:text-base font-semibold text-foreground">Scoring Rules</h4>
            <ul className="text-xs sm:text-sm text-muted-foreground space-y-1">
              <li>• Easy questions: 1 point each</li>
              <li>• Medium questions: 2 points each</li>
              <li>• Hard questions: 3 points each</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Message */}
      <div className="text-center px-4">
        <p className="text-xs sm:text-sm text-muted-foreground whitespace-pre-wrap break-words">
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
      <div className="flex flex-col sm:flex-row gap-3 pt-2">
        <Button
          variant="outline"
          className="flex-1 w-full text-sm sm:text-base"
          onClick={onClose}
          size="lg"
        >
          Got It
        </Button>
        <Button
          className="flex-1 w-full bg-gradient-to-r from-sage-600 to-sage-700 hover:from-sage-700 hover:to-sage-800 text-white text-sm sm:text-base"
          onClick={handleAnalyze}
          disabled={isAnalyzing}
          size="lg"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="mr-2 h-3 w-3 sm:h-4 sm:w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-3 w-3 sm:h-4 sm:w-4" />
              Capability Analysis
            </>
          )}
        </Button>
      </div>
    </div>
  );
}


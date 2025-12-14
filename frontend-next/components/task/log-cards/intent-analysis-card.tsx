/**
 * IntentAnalysisCard - 需求分析输出卡片
 * 
 * 展示AI对用户学习需求的理解和分析结果
 */
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Target, Clock, TrendingUp, Lightbulb } from 'lucide-react';

interface IntentAnalysisCardProps {
  outputSummary: {
    learning_goal: string;
    key_technologies: string[];
    difficulty_level: string;
    estimated_duration_weeks: number;
    estimated_hours_per_week?: number;
    skill_gaps?: Array<{
      skill_name: string;
      current_level: string;
      required_level: string;
    }>;
    learning_strategies?: string[];
  };
}

/**
 * 获取难度等级的显示配置
 */
const getDifficultyConfig = (level: string) => {
  const configs: Record<string, { label: string; className: string }> = {
    beginner: { label: 'Beginner', className: 'bg-sage-100 text-sage-700 border-sage-300' },
    intermediate: { label: 'Intermediate', className: 'bg-sage-200 text-sage-800 border-sage-400' },
    advanced: { label: 'Advanced', className: 'bg-sage-300 text-sage-900 border-sage-500' },
    expert: { label: 'Expert', className: 'bg-amber-100 text-amber-700 border-amber-300' },
  };
  return configs[level] || configs.intermediate;
};

export function IntentAnalysisCard({ outputSummary }: IntentAnalysisCardProps) {
  const difficultyConfig = getDifficultyConfig(outputSummary.difficulty_level);

  return (
    <Card className="border-sage-200 bg-sage-50/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-sage-600" />
          AI's Understanding
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {/* 学习目标 */}
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Target className="w-3 h-3" />
            <span className="font-medium">Learning Goal</span>
          </div>
          <p className="text-foreground">{outputSummary.learning_goal}</p>
        </div>

        {/* 关键技术栈 */}
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground font-medium">Tech Stack</div>
          <div className="flex flex-wrap gap-1.5">
            {outputSummary.key_technologies.map((tech, index) => (
              <Badge key={index} variant="secondary" className="text-xs">
                {tech}
              </Badge>
            ))}
          </div>
        </div>

        {/* 预计时长和难度 */}
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Clock className="w-3 h-3" />
              <span className="font-medium">Duration</span>
            </div>
            <p className="text-foreground font-semibold">
              {outputSummary.estimated_duration_weeks} weeks
              {outputSummary.estimated_hours_per_week && (
                <span className="text-xs text-muted-foreground font-normal ml-1">
                  ({outputSummary.estimated_hours_per_week}h/week)
                </span>
              )}
            </p>
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <TrendingUp className="w-3 h-3" />
              <span className="font-medium">Difficulty</span>
            </div>
            <Badge variant="outline" className={difficultyConfig.className}>
              {difficultyConfig.label}
            </Badge>
          </div>
        </div>

        {/* 技能差距（如果有） */}
        {outputSummary.skill_gaps && outputSummary.skill_gaps.length > 0 && (
          <details className="text-xs">
            <summary className="cursor-pointer text-sage-600 hover:text-sage-700 font-medium">
              View skill gaps ({outputSummary.skill_gaps.length})
            </summary>
            <ul className="mt-2 space-y-1 pl-4">
              {outputSummary.skill_gaps.map((gap, index) => (
                <li key={index} className="text-muted-foreground">
                  <strong>{gap.skill_name}</strong>: {gap.current_level} → {gap.required_level}
                </li>
              ))}
            </ul>
          </details>
        )}

        {/* 学习策略（如果有） */}
        {outputSummary.learning_strategies && outputSummary.learning_strategies.length > 0 && (
          <details className="text-xs">
            <summary className="cursor-pointer text-sage-600 hover:text-sage-700 font-medium">
              View learning strategies
            </summary>
            <ul className="mt-2 space-y-1 pl-4 list-disc">
              {outputSummary.learning_strategies.map((strategy, index) => (
                <li key={index} className="text-muted-foreground">
                  {strategy}
                </li>
              ))}
            </ul>
          </details>
        )}
      </CardContent>
    </Card>
  );
}


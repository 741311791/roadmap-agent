/**
 * CurriculumDesignCard - 课程设计输出卡片
 * 
 * 展示路线图架构设计的详细信息
 */
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BookOpen, Layers, Box, Clock } from 'lucide-react';
import { StatBadge } from './stat-badge';

interface CurriculumDesignCardProps {
  outputSummary: {
    roadmap_id: string;
    title: string;
    total_stages: number;
    total_modules: number;
    total_concepts: number;
    total_hours: number;
    completion_weeks: number;
    stages: Array<{
      name: string;
      description: string;
      modules_count: number;
      estimated_hours: number;
    }>;
  };
}

export function CurriculumDesignCard({ outputSummary }: CurriculumDesignCardProps) {
  return (
    <Card className="border-sage-200 bg-sage-50/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-sage-600" />
          Roadmap Structure
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 路线图标题 */}
        <div>
          <h4 className="font-semibold text-foreground">{outputSummary.title}</h4>
          <p className="text-xs text-muted-foreground font-mono mt-1">
            ID: {outputSummary.roadmap_id}
          </p>
        </div>

        {/* 统计数据网格 */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <StatBadge
            label="Stages"
            value={outputSummary.total_stages}
            className="bg-sage-100 border-sage-200"
          />
          <StatBadge
            label="Modules"
            value={outputSummary.total_modules}
            className="bg-sage-100 border-sage-200"
          />
          <StatBadge
            label="Concepts"
            value={outputSummary.total_concepts}
            className="bg-sage-100 border-sage-200"
          />
          <StatBadge
            label="Hours"
            value={outputSummary.total_hours}
            className="bg-sage-100 border-sage-200"
          />
        </div>

        {/* 预计完成时间 */}
        <div className="flex items-center gap-2 p-2 bg-sage-100 rounded-md">
          <Clock className="w-4 h-4 text-sage-600" />
          <span className="text-sm">
            Estimated completion: <strong>{outputSummary.completion_weeks} weeks</strong>
          </span>
        </div>

        {/* 阶段列表（可展开） */}
        <details className="text-xs">
          <summary className="cursor-pointer text-sage-600 hover:text-sage-700 font-medium">
            View stages breakdown ({outputSummary.stages.length})
          </summary>
          <div className="mt-3 space-y-2">
            {outputSummary.stages.map((stage, index) => (
              <div
                key={index}
                className="p-3 bg-background rounded-md border border-sage-200"
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <h5 className="font-medium text-foreground">{stage.name}</h5>
                  <Badge variant="outline" className="text-[10px] shrink-0">
                    {stage.modules_count} modules
                  </Badge>
                </div>
                <p className="text-muted-foreground text-xs mb-2">{stage.description}</p>
                <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                  <Clock className="w-3 h-3" />
                  <span>{stage.estimated_hours}h</span>
                </div>
              </div>
            ))}
          </div>
        </details>
      </CardContent>
    </Card>
  );
}


/**
 * ContentProgressCard - 内容生成进度卡片
 * 
 * 展示单个概念的内容生成进度
 */
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, CheckCircle2, XCircle, FileText, Link as LinkIcon, HelpCircle } from 'lucide-react';

interface ContentProgressCardProps {
  logType: 'content_generation_start' | 'concept_completed' | 'content_generation_failed';
  details: any;
  message: string;
}

export function ContentProgressCard({ logType, details, message }: ContentProgressCardProps) {
  // 开始生成
  if (logType === 'content_generation_start') {
    return (
      <Card className="border-sage-200 bg-sage-50/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs flex items-center gap-2">
            <Loader2 className="w-3 h-3 text-sage-600 animate-spin" />
            Generating Content
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs">
          <div className="flex items-center justify-between">
            <span className="font-medium text-foreground">{details.concept?.name}</span>
            {details.concept?.difficulty && (
              <Badge variant="outline" className="text-[10px]">
                {details.concept.difficulty}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  // 生成完成
  if (logType === 'concept_completed') {
    const summary = details.content_summary || {};
    return (
      <Card className="border-sage-200 bg-sage-50/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs flex items-center gap-2">
            <CheckCircle2 className="w-3 h-3 text-sage-600" />
            Content Generated
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs">
          <div className="font-medium text-foreground">{details.concept_name}</div>

          {/* 内容统计 */}
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
            {summary.tutorial_chars > 0 && (
              <span className="flex items-center gap-1">
                <FileText className="w-3 h-3" />
                Tutorial ({Math.round(summary.tutorial_chars / 1000)}k chars)
              </span>
            )}
            {summary.resource_count > 0 && (
              <span className="flex items-center gap-1">
                <LinkIcon className="w-3 h-3" />
                {summary.resource_count} resources
              </span>
            )}
            {summary.quiz_questions > 0 && (
              <span className="flex items-center gap-1">
                <HelpCircle className="w-3 h-3" />
                {summary.quiz_questions} questions
              </span>
            )}
          </div>

          {/* 耗时 */}
          {details.total_duration_ms && (
            <div className="text-[10px] text-muted-foreground">
              Completed in {(details.total_duration_ms / 1000).toFixed(1)}s
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  // 生成失败
  if (logType === 'content_generation_failed') {
    return (
      <Card className="border-red-200 bg-red-50/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs flex items-center gap-2">
            <XCircle className="w-3 h-3 text-red-600" />
            Generation Failed
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs">
          <div className="font-medium text-foreground">{details.concept_name}</div>
          <div className="p-2 bg-white rounded border border-red-200 text-[10px]">
            <div className="text-muted-foreground mb-1">Error:</div>
            <p className="text-red-600">{details.error || 'Unknown error'}</p>
          </div>
          {details.error_type && (
            <Badge variant="outline" className="text-[10px] bg-red-100 text-red-700">
              {details.error_type}
            </Badge>
          )}
        </CardContent>
      </Card>
    );
  }

  return null;
}


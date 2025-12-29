/**
 * ValidationResultCard - 结构验证结果卡片
 * 
 * 展示路线图结构验证的结果
 */
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, AlertTriangle, XCircle, Info } from 'lucide-react';

interface ValidationResultCardProps {
  logType: 'validation_passed' | 'validation_failed' | 'validation_skipped';
  details: any;
}

export function ValidationResultCard({ logType, details }: ValidationResultCardProps) {
  // 验证跳过
  if (logType === 'validation_skipped') {
    return (
      <Card className="border-gray-300 bg-gray-50/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Info className="w-4 h-4 text-gray-600" />
            Validation Skipped
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-muted-foreground">
            Structure validation was skipped ({details.reason || 'fast mode enabled'})
          </p>
        </CardContent>
      </Card>
    );
  }

  // 验证通过
  if (logType === 'validation_passed') {
    return (
      <Card className="border-sage-200 bg-sage-50/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-sage-600" />
            Validation Passed
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-foreground">
            All quality checks passed successfully!
          </p>

          {/* 检查项 */}
          {details.checks_performed && details.checks_performed.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground font-medium">Checks Performed</div>
              <div className="flex flex-wrap gap-1.5">
                {details.checks_performed.map((check: any, index: number) => (
                  <Badge key={index} variant="outline" className="text-xs bg-white">
                    ✓ {typeof check === 'string' ? check.replace(/_/g, ' ') : check.name}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* 统计信息 */}
          {details.structure_summary && (
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="p-2 bg-white rounded border border-sage-200">
                <div className="text-muted-foreground">Stages</div>
                <div className="text-lg font-bold text-sage-700">{details.structure_summary.total_stages}</div>
              </div>
              <div className="p-2 bg-white rounded border border-sage-200">
                <div className="text-muted-foreground">Modules</div>
                <div className="text-lg font-bold text-sage-700">{details.structure_summary.total_modules}</div>
              </div>
              <div className="p-2 bg-white rounded border border-sage-200">
                <div className="text-muted-foreground">Concepts</div>
                <div className="text-lg font-bold text-sage-700">{details.structure_summary.total_concepts}</div>
              </div>
            </div>
          )}
          
          {/* 问题统计 */}
          {details.issues_summary && (
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              {details.issues_summary.warnings > 0 && (
                <span>
                  <strong className="text-amber-600">{details.issues_summary.warnings}</strong> warnings
                </span>
              )}
              {details.issues_summary.suggestions > 0 && (
                <span>
                  <strong className="text-blue-600">{details.issues_summary.suggestions}</strong> suggestions
                </span>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  // 验证失败
  if (logType === 'validation_failed') {
    return (
      <Card className="border-red-200 bg-red-50/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <XCircle className="w-4 h-4 text-red-600" />
            Validation Found Issues
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-foreground">
            Found {details.issues_breakdown?.critical || details.critical_issues?.length || 0} critical
            issues that need attention
          </p>

          {/* 问题统计 */}
          {details.issues_breakdown && (
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="p-2 bg-white rounded border border-red-200">
                <div className="text-muted-foreground">Critical</div>
                <div className="text-lg font-bold text-red-700">{details.issues_breakdown.critical}</div>
              </div>
              <div className="p-2 bg-white rounded border border-amber-200">
                <div className="text-muted-foreground">Warnings</div>
                <div className="text-lg font-bold text-amber-700">{details.issues_breakdown.warnings}</div>
              </div>
              <div className="p-2 bg-white rounded border border-blue-200">
                <div className="text-muted-foreground">Suggestions</div>
                <div className="text-lg font-bold text-blue-700">{details.issues_breakdown.suggestions}</div>
              </div>
            </div>
          )}

          {/* 关键问题列表 */}
          {details.critical_issues && details.critical_issues.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground font-medium">Critical Issues</div>
              <div className="space-y-2">
                {details.critical_issues.map((issue: any, index: number) => (
                  <div
                    key={index}
                    className="p-2 bg-white rounded border border-red-200 text-xs"
                  >
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="w-3 h-3 text-red-600 shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="outline" className="h-4 text-[10px]">
                            {issue.location}
                          </Badge>
                        </div>
                        <p className="text-foreground font-medium mb-1">{issue.issue}</p>
                        {issue.suggestion && (
                          <p className="text-muted-foreground">
                            💡 {issue.suggestion}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  return null;
}


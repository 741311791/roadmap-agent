'use client';

import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { RotateCw, Edit, Clock, ExternalLink, CheckCircle2, Loader2 } from 'lucide-react';
import { getLatestTutorial, downloadTutorialContent, getResourcesByConceptId, getQuizByConceptId, regenerateTutorial, getTutorialVersions } from '@/lib/api/endpoints';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { useAuthStore } from '@/lib/store/auth-store';
import type { LearningPreferences } from '@/types/generated/models';
import 'highlight.js/styles/github-dark.css';

interface TutorialDialogProps {
  roadmapId: string;
  conceptId: string;
  onClose: () => void;
  onRegenerate?: () => void;
  onModify?: () => void;
  userPreferences?: LearningPreferences;
}

export function TutorialDialog({
  roadmapId,
  conceptId,
  onClose,
  onRegenerate,
  onModify,
  userPreferences,
}: TutorialDialogProps) {
  const { getUserId } = useAuthStore();
  const [tutorial, setTutorial] = useState<any>(null);
  const [content, setContent] = useState<string>('');
  const [resources, setResources] = useState<any[]>([]);
  const [quiz, setQuiz] = useState<any>(null);
  const [versions, setVersions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [contentLoading, setContentLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('content');
  const [isRegenerating, setIsRegenerating] = useState(false);

  useEffect(() => {
    loadTutorialData();
  }, [roadmapId, conceptId]);

  const loadTutorialData = async () => {
    setLoading(true);
    try {
      // Load tutorial metadata
      const tutorialMeta = await getLatestTutorial(roadmapId, conceptId);
      setTutorial(tutorialMeta);

      // Load tutorial content if available
      if (tutorialMeta.content_url) {
        setContentLoading(true);
        try {
          const markdownContent = await downloadTutorialContent(tutorialMeta.content_url);
          setContent(markdownContent);
        } catch (error) {
          console.error('Failed to load tutorial content:', error);
          setContent('# 加载内容失败\n\n无法下载教程内容。请稍后重试。');
        } finally {
          setContentLoading(false);
        }
      }
    } catch (error) {
      console.error('Failed to load tutorial:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadResources = async () => {
    try {
      const resourceData = await getResourcesByConceptId(roadmapId, conceptId);
      setResources(resourceData.resources || []);
    } catch (error) {
      console.error('Failed to load resources:', error);
    }
  };

  const loadQuiz = async () => {
    try {
      const quizData = await getQuizByConceptId(roadmapId, conceptId);
      setQuiz(quizData);
    } catch (error) {
      console.error('Failed to load quiz:', error);
    }
  };

  const loadVersions = async () => {
    try {
      const versionsData = await getTutorialVersions(roadmapId, conceptId);
      setVersions(versionsData.tutorials || []);
    } catch (error) {
      console.error('Failed to load versions:', error);
    }
  };

  const handleTabChange = (value: string) => {
    setActiveTab(value);
    if (value === 'resources' && resources.length === 0) {
      loadResources();
    } else if (value === 'quiz' && !quiz) {
      loadQuiz();
    } else if (value === 'versions' && versions.length === 0) {
      loadVersions();
    }
  };

  const handleRegenerate = async () => {
    if (!userPreferences) {
      alert('缺少用户偏好设置');
      return;
    }

    if (!confirm('确定要重新生成这个教程吗?这将创建一个新版本。')) {
      return;
    }

    setIsRegenerating(true);
    try {
      const result = await regenerateTutorial(roadmapId, conceptId, {
        user_id: 'temp-user-001',
        preferences: userPreferences,
      });

      alert(`重新生成成功! 新版本: v${result.content_version}`);
      
      // Reload tutorial data
      await loadTutorialData();
      
      if (onRegenerate) {
        onRegenerate();
      }
    } catch (error) {
      console.error('Regeneration failed:', error);
      alert(`重新生成失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setIsRegenerating(false);
    }
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] p-0">
        {loading ? (
          <>
            <DialogHeader className="px-6 pt-6 pb-4">
              <DialogTitle>加载中...</DialogTitle>
              <DialogDescription>正在加载教程内容</DialogDescription>
            </DialogHeader>
            <div className="px-6 pb-6 space-y-4">
              <Skeleton className="h-8 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-64 w-full" />
            </div>
          </>
        ) : (
          <>
            <DialogHeader className="px-6 pt-6 pb-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <DialogTitle className="text-2xl">{tutorial?.title}</DialogTitle>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  {tutorial?.content_version && (
                    <Badge variant="outline">v{tutorial.content_version}</Badge>
                  )}
                  {tutorial?.estimated_completion_time && (
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {tutorial.estimated_completion_time} 分钟
                    </div>
                  )}
                </div>
              </div>
              <DialogDescription className="mt-2">
                {tutorial?.summary || '查看教程内容、学习资源和练习测验'}
              </DialogDescription>
            </DialogHeader>

            <Tabs value={activeTab} onValueChange={handleTabChange} className="flex-1">
              <div className="px-6">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="content">教程内容</TabsTrigger>
                  <TabsTrigger value="resources">学习资源</TabsTrigger>
                  <TabsTrigger value="quiz">练习测验</TabsTrigger>
                  <TabsTrigger value="versions">版本历史</TabsTrigger>
                </TabsList>
              </div>

              <TabsContent value="content" className="px-6 pb-6 mt-4">
                <ScrollArea className="h-[50vh]">
                  {contentLoading ? (
                    <div className="space-y-3">
                      {[1, 2, 3, 4, 5].map((i) => (
                        <Skeleton key={i} className="h-4 w-full" />
                      ))}
                    </div>
                  ) : (
                    <div className="prose prose-sm max-w-none dark:prose-invert">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypeHighlight]}
                        components={{
                          // Customize markdown rendering
                          a: ({ node, ...props }) => (
                            <a {...props} target="_blank" rel="noopener noreferrer" />
                          ),
                        }}
                      >
                        {content || '# 暂无内容\n\n教程内容尚未生成。'}
                      </ReactMarkdown>
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>

              <TabsContent value="resources" className="px-6 pb-6 mt-4">
                <ScrollArea className="h-[50vh]">
                  {resources.length === 0 ? (
                    <div className="text-center text-muted-foreground py-12">
                      暂无资源推荐
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {resources.map((resource, idx) => (
                        <div
                          key={idx}
                          className="border rounded-lg p-4 hover:bg-accent transition-colors"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <h3 className="font-semibold mb-1">{resource.title}</h3>
                              <p className="text-sm text-muted-foreground mb-2">
                                {resource.description}
                              </p>
                              <div className="flex items-center gap-2">
                                <Badge variant="secondary">{resource.type}</Badge>
                                {resource.relevance_score && (
                                  <span className="text-xs text-muted-foreground">
                                    相关度: {Math.round(resource.relevance_score * 100)}%
                                  </span>
                                )}
                              </div>
                            </div>
                            <a
                              href={resource.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="shrink-0"
                            >
                              <Button variant="ghost" size="sm">
                                <ExternalLink className="h-4 w-4" />
                              </Button>
                            </a>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>

              <TabsContent value="quiz" className="px-6 pb-6 mt-4">
                <ScrollArea className="h-[50vh]">
                  {!quiz || quiz.questions.length === 0 ? (
                    <div className="text-center text-muted-foreground py-12">
                      暂无测验题目
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {quiz.questions.map((question: any, idx: number) => (
                        <div key={idx} className="border rounded-lg p-4">
                          <div className="flex items-start gap-3 mb-3">
                            <Badge variant="outline">{idx + 1}</Badge>
                            <div className="flex-1">
                              <p className="font-medium mb-2">{question.question}</p>
                              <Badge variant="secondary" className="text-xs">
                                {question.difficulty}
                              </Badge>
                            </div>
                          </div>

                          <div className="space-y-2 ml-10">
                            {question.options.map((option: string, optIdx: number) => (
                              <div
                                key={optIdx}
                                className={`p-2 rounded border ${
                                  question.correct_answer.includes(optIdx)
                                    ? 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800'
                                    : 'bg-gray-50 dark:bg-gray-900'
                                }`}
                              >
                                <div className="flex items-center gap-2">
                                  {question.correct_answer.includes(optIdx) && (
                                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                                  )}
                                  <span className="text-sm">{option}</span>
                                </div>
                              </div>
                            ))}
                          </div>

                          {question.explanation && (
                            <div className="mt-3 ml-10 p-3 bg-blue-50 dark:bg-blue-950 rounded text-sm">
                              <p className="font-medium text-blue-900 dark:text-blue-100 mb-1">
                                解析:
                              </p>
                              <p className="text-blue-800 dark:text-blue-200">
                                {question.explanation}
                              </p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>

              <TabsContent value="versions" className="px-6 pb-6 mt-4">
                <ScrollArea className="h-[50vh]">
                  {versions.length === 0 ? (
                    <div className="text-center text-muted-foreground py-12">
                      暂无版本历史
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {versions.map((version) => (
                        <div
                          key={version.tutorial_id}
                          className={`border rounded-lg p-4 ${
                            version.is_latest
                              ? 'bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800'
                              : 'hover:bg-accent'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-4 mb-2">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <h3 className="font-semibold">{version.title}</h3>
                                {version.is_latest && (
                                  <Badge variant="default">当前版本</Badge>
                                )}
                                <Badge variant="outline">v{version.content_version}</Badge>
                              </div>
                              <p className="text-sm text-muted-foreground mb-2">
                                {version.summary}
                              </p>
                              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                <span>
                                  生成时间: {new Date(version.generated_at).toLocaleString('zh-CN')}
                                </span>
                                <Badge variant="secondary" className="text-xs">
                                  {version.content_status}
                                </Badge>
                              </div>
                            </div>
                            <a
                              href={version.content_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="shrink-0"
                            >
                              <Button variant="ghost" size="sm">
                                <ExternalLink className="h-4 w-4" />
                              </Button>
                            </a>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>
            </Tabs>

            <div className="flex items-center justify-end gap-2 px-6 pb-6 pt-4 border-t">
              <Button
                variant="outline"
                onClick={handleRegenerate}
                disabled={isRegenerating}
              >
                {isRegenerating ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RotateCw className="mr-2 h-4 w-4" />
                )}
                重新生成
              </Button>
              {onModify && (
                <Button variant="outline" onClick={onModify}>
                  <Edit className="mr-2 h-4 w-4" />
                  修改内容
                </Button>
              )}
              <Button onClick={onClose}>关闭</Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}


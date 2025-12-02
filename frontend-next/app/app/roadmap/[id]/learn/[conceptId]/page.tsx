'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ChevronLeft,
  ChevronRight,
  Clock,
  CheckCircle2,
  BookOpen,
  FileQuestion,
  ExternalLink,
  ListTree,
  PanelLeft,
  Loader2,
} from 'lucide-react';
import { 
  getConceptQuiz, 
  getConceptResources, 
  getLatestTutorial, 
  downloadTutorialContent,
  getRoadmap,
  type QuizResponse, 
  type ResourcesResponse 
} from '@/lib/api/endpoints';

export default function LearningPage() {
  const params = useParams();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('tutorial');
  const [isTocCollapsed, setIsTocCollapsed] = useState(false);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, number>>({});
  const [showResults, setShowResults] = useState(false);

  // Data states
  const [concept, setConcept] = useState<any>(null);
  const [tutorial, setTutorial] = useState<string>('');
  const [quiz, setQuiz] = useState<QuizResponse | null>(null);
  const [resources, setResources] = useState<ResourcesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const roadmapId = params.id as string;
  const conceptId = params.conceptId as string;

  // Fetch data on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        // 1. Get roadmap to find concept details
        const roadmapData = await getRoadmap(roadmapId);
        
        // Find the concept in the roadmap
        let foundConcept: any = null;
        let stageName = '';
        let moduleName = '';
        
        for (const stage of roadmapData.stages) {
          for (const module of stage.modules) {
            const conceptMatch = module.concepts.find((c: any) => c.concept_id === conceptId);
            if (conceptMatch) {
              foundConcept = conceptMatch;
              stageName = stage.name;
              moduleName = module.name;
              break;
            }
          }
          if (foundConcept) break;
        }

        if (!foundConcept) {
          setError('概念不存在');
          return;
        }

        setConcept({ ...foundConcept, stageName, moduleName });

        // 2. Fetch tutorial content
        try {
          const tutorialData = await getLatestTutorial(roadmapId, conceptId);
          if (tutorialData.content_url) {
            const content = await downloadTutorialContent(tutorialData.content_url);
            setTutorial(content);
          } else {
            setTutorial('# 教程内容生成中\n\n教程内容正在生成，请稍后刷新页面。');
          }
        } catch (err) {
          console.error('Failed to load tutorial:', err);
          setTutorial('# 教程内容暂未生成\n\n该概念的教程内容尚未生成。');
        }

        // 3. Fetch quiz
        try {
          const quizData = await getConceptQuiz(roadmapId, conceptId);
          setQuiz(quizData);
        } catch (err) {
          console.error('Failed to load quiz:', err);
          setQuiz(null);
        }

        // 4. Fetch resources
        try {
          const resourcesData = await getConceptResources(roadmapId, conceptId);
          setResources(resourcesData);
        } catch (err) {
          console.error('Failed to load resources:', err);
          setResources(null);
        }

      } catch (err: any) {
        console.error('Failed to load data:', err);
        setError(err.message || '加载数据失败');
      } finally {
        setLoading(false);
      }
    };

    if (roadmapId && conceptId) {
      fetchData();
    }
  }, [roadmapId, conceptId]);

  // Parse TOC from markdown
  const tocItems = tutorial
    .split('\n')
    .filter((line) => line.startsWith('## '))
    .map((line) => ({
      id: line.replace('## ', '').toLowerCase().replace(/\s+/g, '-'),
      label: line.replace('## ', ''),
    }));

  const handleAnswerSelect = (questionId: string, answerIndex: number) => {
    if (showResults) return;
    setSelectedAnswers((prev) => ({
      ...prev,
      [questionId]: answerIndex,
    }));
  };

  const handleSubmitQuiz = () => {
    setShowResults(true);
  };

  const getQuizScore = () => {
    if (!quiz) return 0;
    let correct = 0;
    quiz.questions.forEach((q) => {
      if (selectedAnswers[q.question_id] === q.correct_answer[0]) {
        correct++;
      }
    });
    return correct;
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-sage-600" />
          <p className="text-muted-foreground">加载学习内容中...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !concept) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-semibold mb-2">加载失败</h2>
          <p className="text-muted-foreground mb-4">{error || '无法加载概念信息'}</p>
          <Button onClick={() => router.back()}>返回</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-background">
      {/* TOC Sidebar */}
      <div
        className={`border-r border-border/5 bg-background transition-all duration-300 ${
          isTocCollapsed ? 'w-12' : 'w-64'
        }`}
      >
        <div className="h-14 flex items-center justify-between px-3 border-b border-border/5">
          {!isTocCollapsed && (
            <Link
              href={`/app/roadmap/${params.id}`}
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ChevronLeft size={16} />
              <span>Back</span>
            </Link>
          )}
          <button
            onClick={() => setIsTocCollapsed(!isTocCollapsed)}
            className="p-2 hover:bg-muted rounded transition-colors"
          >
            {isTocCollapsed ? (
              <PanelLeft size={16} className="text-muted-foreground" />
            ) : (
              <ListTree size={16} className="text-muted-foreground" />
            )}
          </button>
        </div>

        {!isTocCollapsed && (
          <ScrollArea className="h-[calc(100%-3.5rem)] p-4">
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
              Table of Contents
            </div>
            <nav className="space-y-1">
              {tocItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    document
                      .getElementById(item.id)
                      ?.scrollIntoView({ behavior: 'smooth' });
                  }}
                  className="block w-full text-left text-sm py-2 px-3 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  {item.label}
                </button>
              ))}
            </nav>
          </ScrollArea>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-[85ch] mx-auto py-12 px-8">
          {/* Paper Container */}
          <div className="bg-white shadow-sm border border-stone-100 rounded-xl p-12 md:p-16 min-h-[80vh]">
            {/* Header */}
            <header className="mb-12 border-b border-stone-100 pb-8">
              <div className="flex items-center gap-2 text-sm text-sage-600 font-medium mb-4">
                <span className="text-muted-foreground">
                  {concept.stageName} → {concept.moduleName}
                </span>
              </div>
              <div className="flex items-center gap-2 mb-4">
                <Badge variant="sage">{concept.difficulty}</Badge>
                <span className="flex items-center gap-1 text-sm text-muted-foreground">
                  <Clock size={14} /> {concept.estimated_hours}h
                </span>
              </div>
              <h1 className="text-4xl md:text-5xl font-serif font-bold text-stone-900 mb-4 leading-tight">
                {concept.name}
              </h1>
              <p className="text-lg text-stone-500 leading-relaxed">
                {concept.description}
              </p>
            </header>

            {/* Tabs */}
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="mb-8">
                <TabsTrigger value="tutorial" className="gap-2">
                  <BookOpen size={16} /> Tutorial
                </TabsTrigger>
                <TabsTrigger value="quiz" className="gap-2">
                  <FileQuestion size={16} /> Quiz
                </TabsTrigger>
                <TabsTrigger value="resources" className="gap-2">
                  <ExternalLink size={16} /> Resources
                </TabsTrigger>
              </TabsList>

              {/* Tutorial Tab */}
              <TabsContent value="tutorial">
                <article
                  className="prose prose-stone prose-lg max-w-none 
                  prose-headings:font-serif prose-headings:font-bold prose-headings:text-stone-800
                  prose-p:text-stone-600 prose-p:leading-loose
                  prose-blockquote:border-l-sage-400 prose-blockquote:bg-sage-50/50 prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:not-italic prose-blockquote:text-stone-700
                  prose-code:text-sage-700 prose-code:bg-sage-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:before:content-none prose-code:after:content-none
                  prose-pre:bg-stone-900 prose-pre:shadow-lg prose-pre:rounded-xl
                  prose-li:text-stone-600
                  prose-strong:text-stone-800 prose-strong:font-semibold"
                >
                  <ReactMarkdown>{tutorial}</ReactMarkdown>
                </article>
              </TabsContent>

              {/* Quiz Tab */}
              <TabsContent value="quiz">
                {!quiz || quiz.total_questions === 0 ? (
                  <div className="text-center py-12">
                    <FileQuestion className="h-16 w-16 text-muted-foreground/50 mx-auto mb-4" />
                    <h3 className="text-lg font-medium mb-2">暂无测验</h3>
                    <p className="text-muted-foreground">该概念的测验内容尚未生成</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {showResults && (
                      <Card className="bg-sage-50 border-sage-200">
                        <CardContent className="py-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <h3 className="font-semibold text-sage-800">
                                测验结果
                              </h3>
                              <p className="text-sage-600">
                                得分：{getQuizScore()} / {quiz.total_questions}
                              </p>
                            </div>
                            <Button
                              variant="outline"
                              onClick={() => {
                                setShowResults(false);
                                setSelectedAnswers({});
                              }}
                            >
                              重新测验
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    )}

                    {quiz.questions.map((question, qIndex) => (
                      <Card key={question.question_id}>
                        <CardHeader>
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-lg font-medium">
                              {qIndex + 1}. {question.question}
                            </CardTitle>
                            <Badge variant={
                              question.difficulty === 'easy' ? 'default' :
                              question.difficulty === 'medium' ? 'secondary' :
                              'destructive'
                            }>
                              {question.difficulty === 'easy' ? '简单' :
                               question.difficulty === 'medium' ? '中等' : '困难'}
                            </Badge>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2">
                            {question.options.map((option, oIndex) => {
                              const isSelected =
                                selectedAnswers[question.question_id] === oIndex;
                              const isCorrect =
                                question.correct_answer[0] === oIndex;
                              const showCorrect = showResults && isCorrect;
                              const showWrong =
                                showResults && isSelected && !isCorrect;

                              return (
                                <button
                                  key={oIndex}
                                  onClick={() =>
                                    handleAnswerSelect(question.question_id, oIndex)
                                  }
                                  disabled={showResults}
                                  className={`w-full p-4 rounded-lg border text-left transition-colors ${
                                    showCorrect
                                      ? 'border-green-500 bg-green-50'
                                      : showWrong
                                      ? 'border-red-500 bg-red-50'
                                      : isSelected
                                      ? 'border-sage-500 bg-sage-50'
                                      : 'border-border hover:border-sage-300'
                                  }`}
                                >
                                  {option}
                                </button>
                              );
                            })}
                          </div>
                          {showResults && (
                            <p className="mt-4 text-sm text-muted-foreground bg-muted p-4 rounded-lg">
                              <strong>解析：</strong> {question.explanation}
                            </p>
                          )}
                        </CardContent>
                      </Card>
                    ))}

                    {!showResults && (
                      <Button
                        onClick={handleSubmitQuiz}
                        variant="sage"
                        className="w-full"
                        disabled={
                          Object.keys(selectedAnswers).length < quiz.total_questions
                        }
                      >
                        提交测验
                      </Button>
                    )}
                  </div>
                )}
              </TabsContent>

              {/* Resources Tab */}
              <TabsContent value="resources">
                {!resources || resources.resources_count === 0 ? (
                  <div className="text-center py-12">
                    <ExternalLink className="h-16 w-16 text-muted-foreground/50 mx-auto mb-4" />
                    <h3 className="text-lg font-medium mb-2">暂无学习资源</h3>
                    <p className="text-muted-foreground">该概念的学习资源尚未生成</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {resources.resources.map((resource, index) => (
                      <a
                        key={`${resource.url}-${index}`}
                        href={resource.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block p-4 rounded-lg border border-border hover:border-sage-300 hover:bg-sage-50/50 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="font-medium text-foreground">
                                {resource.title}
                              </h3>
                              <ExternalLink size={14} className="text-muted-foreground" />
                            </div>
                            <p className="text-sm text-muted-foreground mb-2">
                              {resource.description}
                            </p>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              <Badge variant="outline" className="text-xs">
                                {resource.type === 'article' ? '文章' :
                                 resource.type === 'video' ? '视频' :
                                 resource.type === 'book' ? '书籍' :
                                 resource.type === 'course' ? '课程' :
                                 resource.type === 'documentation' ? '文档' :
                                 resource.type === 'tool' ? '工具' : resource.type}
                              </Badge>
                              <span>相关度：{Math.round(resource.relevance_score * 100)}%</span>
                            </div>
                          </div>
                        </div>
                      </a>
                    ))}
                  </div>
                )}
              </TabsContent>
            </Tabs>

            {/* Footer Actions */}
            <div className="mt-16 pt-8 border-t border-stone-100 flex justify-between items-center">
              <span className="text-sm text-muted-foreground">
                Last updated: Just now
              </span>
              <Button variant="sage" className="gap-2">
                Mark as Complete <CheckCircle2 size={16} />
              </Button>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex justify-between mt-8">
            <Button variant="outline" className="gap-2">
              <ChevronLeft size={16} /> Previous Concept
            </Button>
            <Button variant="outline" className="gap-2">
              Next Concept <ChevronRight size={16} />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}


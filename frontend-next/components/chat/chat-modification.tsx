'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, CheckCircle2, XCircle, AlertCircle, Send } from 'lucide-react';
import { chatModificationStream } from '@/lib/api/endpoints';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { useAuthStore } from '@/lib/store/auth-store';
import type { ChatModificationEvent } from '@/lib/schemas/sse-events';
import type { LearningPreferences } from '@/types/generated/models';

interface ChatModificationProps {
  roadmapId: string;
  currentConceptId?: string | null;
  userPreferences: LearningPreferences;
  onModificationComplete?: () => void;
}

interface ModificationIntent {
  modification_type: string;
  target_id: string;
  target_name: string;
  specific_requirements: string[];
  priority: string;
}

interface ModificationResult {
  modification_type: string;
  target_id: string;
  target_name: string;
  success: boolean;
  modification_summary: string;
  new_version?: number;
  error_message?: string;
}

export function ChatModification({
  roadmapId,
  currentConceptId,
  userPreferences,
  onModificationComplete,
}: ChatModificationProps) {
  const { getUserId } = useAuthStore();
  const [message, setMessage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<string>('');
  const [intents, setIntents] = useState<ModificationIntent[]>([]);
  const [results, setResults] = useState<ModificationResult[]>([]);
  const [clarificationNeeded, setClarificationNeeded] = useState(false);
  const [clarificationQuestions, setClarificationQuestions] = useState<string[]>([]);
  
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [results, intents]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();

    if (!message.trim() || isProcessing) return;

    setIsProcessing(true);
    setCurrentPhase('analyzing');
    setIntents([]);
    setResults([]);
    setClarificationNeeded(false);
    setClarificationQuestions([]);

    try {
      await chatModificationStream(
        roadmapId,
        {
          user_id: 'temp-user-001', // TODO: Replace with real user ID
          user_message: message,
          preferences: userPreferences,
          context: currentConceptId ? { concept_id: currentConceptId } : undefined,
        },
        {
          onEvent: (event: ChatModificationEvent) => {
            // Handle each event type independently with switch
            switch (event.type) {
              case 'analyzing': {
                setCurrentPhase('analyzing');
                break;
              }
              case 'intents': {
                const intentsEvent = event;
                setCurrentPhase('intents');
                setIntents(intentsEvent.intents as ModificationIntent[]);
                if (intentsEvent.needs_clarification) {
                  setClarificationNeeded(true);
                  setClarificationQuestions(intentsEvent.clarification_questions || []);
                  setIsProcessing(false);
                }
                break;
              }
              case 'modifying': {
                setCurrentPhase('modifying');
                break;
              }
              case 'agent_progress': {
                const progressEvent = event;
                // Can show detailed progress if needed
                console.log(`[${progressEvent.agent}] ${progressEvent.step}: ${progressEvent.details || ''}`);
                break;
              }
              case 'result': {
                const resultEvent = event;
                const result: ModificationResult = {
                  modification_type: resultEvent.modification_type || '',
                  target_id: resultEvent.target_id,
                  target_name: resultEvent.target_name,
                  success: resultEvent.success,
                  modification_summary: resultEvent.modification_summary || '',
                  new_version: resultEvent.new_version,
                  error_message: resultEvent.error_message,
                };
                setResults((prev) => [...prev, result]);
                break;
              }
              case 'done': {
                setCurrentPhase('done');
                setIsProcessing(false);
                if (onModificationComplete) {
                  setTimeout(() => {
                    onModificationComplete();
                  }, 1000);
                }
                break;
              }
              case 'modification_error': {
                const modErrorEvent = event;
                alert(`错误: ${modErrorEvent.message}`);
                setCurrentPhase('error');
                setIsProcessing(false);
                break;
              }
              case 'error': {
                const genericErrorEvent = event;
                alert(`错误: ${genericErrorEvent.message}`);
                setCurrentPhase('error');
                setIsProcessing(false);
                break;
              }
            }
          },
          onComplete: () => {
            setIsProcessing(false);
          },
          onError: (error) => {
            alert(`连接错误: ${error.message}`);
            setCurrentPhase('error');
            setIsProcessing(false);
          },
        }
      );
    } catch (error) {
      console.error('Failed to start modification stream:', error);
      alert(`发起修改失败: ${error instanceof Error ? error.message : '未知错误'}`);
      setIsProcessing(false);
    }
  };

  const getPhaseTitle = () => {
    switch (currentPhase) {
      case 'analyzing':
        return '正在分析修改意图...';
      case 'intents':
        return '意图分析完成';
      case 'modifying':
        return '正在执行修改...';
      case 'done':
        return '修改完成';
      case 'error':
        return '发生错误';
      default:
        return '';
    }
  };

  const getPhaseIcon = () => {
    switch (currentPhase) {
      case 'analyzing':
      case 'modifying':
        return <Loader2 className="h-5 w-5 animate-spin" />;
      case 'done':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-600" />;
      case 'intents':
        return <AlertCircle className="h-5 w-5 text-blue-600" />;
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b">
        <h2 className="font-semibold text-lg">聊天式修改</h2>
        <p className="text-sm text-muted-foreground">
          描述你想要的修改,AI 将自动分析并执行
        </p>
      </div>

      {/* Content Area */}
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-4">
          {/* Current Phase */}
          {currentPhase && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  {getPhaseIcon()}
                  {getPhaseTitle()}
                </CardTitle>
              </CardHeader>
            </Card>
          )}

          {/* Intents Display */}
          {intents.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">检测到的修改意图</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {intents.map((intent, idx) => (
                  <div
                    key={idx}
                    className="p-3 border rounded-lg bg-blue-50 dark:bg-blue-950"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline">{intent.modification_type}</Badge>
                      <span className="font-medium text-sm">{intent.target_name}</span>
                      <Badge variant="secondary" className="ml-auto text-xs">
                        {intent.priority}
                      </Badge>
                    </div>
                    <ul className="text-sm text-muted-foreground space-y-1">
                      {intent.specific_requirements.map((req, reqIdx) => (
                        <li key={reqIdx}>• {req}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Clarification Questions */}
          {clarificationNeeded && clarificationQuestions.length > 0 && (
            <Card className="border-yellow-200 bg-yellow-50 dark:bg-yellow-950 dark:border-yellow-800">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-yellow-600" />
                  需要更多信息
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-3">
                  请回答以下问题以便更好地理解你的需求:
                </p>
                <ul className="text-sm space-y-2">
                  {clarificationQuestions.map((question, idx) => (
                    <li key={idx} className="flex gap-2">
                      <span className="font-medium">{idx + 1}.</span>
                      <span>{question}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Results Display */}
          {results.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">修改结果</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {results.map((result, idx) => (
                  <div
                    key={idx}
                    className={`p-3 border rounded-lg ${
                      result.success
                        ? 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800'
                        : 'bg-red-50 border-red-200 dark:bg-red-950 dark:border-red-800'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      {result.success ? (
                        <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-sm">{result.target_name}</span>
                          <Badge variant="outline" className="text-xs">
                            {result.modification_type}
                          </Badge>
                          {result.new_version && (
                            <Badge variant="secondary" className="text-xs">
                              v{result.new_version}
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {result.success
                            ? result.modification_summary
                            : result.error_message}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="p-4 border-t">
        <form onSubmit={handleSubmit} className="space-y-3">
          <Textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={
              currentConceptId
                ? '描述你想要的修改,例如: 把这个教程改得更详细一些,增加更多代码示例'
                : '描述你想要的修改,例如: 把 React Hooks 教程改得更详细一些'
            }
            disabled={isProcessing}
            rows={3}
            className="resize-none"
          />
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              {currentConceptId
                ? '当前上下文: 正在查看的概念'
                : '提示: 点击某个概念后再修改,可获得更精准的结果'}
            </p>
            <Button type="submit" disabled={isProcessing || !message.trim()}>
              {isProcessing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  处理中...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  发送
                </>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}


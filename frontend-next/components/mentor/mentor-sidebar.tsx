"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AssistantRuntimeProvider,
  useThread,
  type ThreadMessageLike,
} from "@assistant-ui/react";
import type { Concept } from "@/types/generated/models";

import { useTranslations } from "next-intl";
import { Bot, PanelRightClose } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

import { DeerFlowTodoList } from "@/components/deerflow-chat-test/deerflow-todo-list";
import type { DeerFlowTodo } from "@/components/deerflow-chat-test/deerflow-thread-context";
import {
  extractTodosFromDeerFlowThreadMessages,
  mapDeerFlowMessagesToThreadMessages,
  mapDeerFlowThreadToThreadRecord,
} from "@/components/mentor/mentor-deerflow-adapter";
import {
  deleteMentorDeerFlowThread,
  listMentorDeerFlowMessages,
  listMentorDeerFlowModels,
  listMentorDeerFlowThreads,
  warmupMentorDeerFlowContext,
} from "@/components/mentor/mentor-deerflow-api";
import {
  mapMentorMessagesToThreadMessages,
  mapMentorSessionToThreadRecord,
} from "@/components/mentor/mentor-adapter";
import {
  deleteMentorSession,
  listMentorMessages,
  listMentorModels,
  listMentorSessions,
  type MentorModelDto,
  type MentorChatMetaEvent,
  warmupMentorContext,
} from "@/components/mentor/mentor-api";
import { MentorComposer } from "@/components/mentor/mentor-composer";
import { MentorThread } from "@/components/mentor/mentor-thread";
import { MentorThreadHistory } from "@/components/mentor/mentor-thread-history";
import type {
  MentorAgentKind,
  MentorChapterContext,
  MentorModelOption,
  MentorQaStyle,
  MentorQuickAction,
} from "@/components/mentor/types";
import { ensureMentorModelOption } from "@/components/mentor/types";
import { useMentorDeerFlowRuntime } from "@/components/mentor/use-mentor-deerflow-runtime";
import { useMentorRuntime } from "@/components/mentor/use-mentor-runtime";
import { useMentorThreads } from "@/components/mentor/use-mentor-threads";
import { cn } from "@/lib/utils";

const ENABLE_DEERFLOW_MENTOR =
  process.env.NEXT_PUBLIC_ENABLE_DEERFLOW_MENTOR === "true";

interface MentorSidebarProps {
  roadmapId: string;
  activeConcept: Concept | null;
  onCollapse?: () => void;
}

interface MentorThreadStateSyncProps {
  onMessagesChange: (messages: ThreadMessageLike[]) => void;
}

interface MentorRuntimeShellProps {
  threadId: string;
  agentKind: MentorAgentKind;
  qaStyle: MentorQaStyle;
  modelId: string;
  remoteSessionId?: string;
  chapterContext: MentorChapterContext;
  initialMessages: ThreadMessageLike[];
  onMessagesChange: (messages: ThreadMessageLike[]) => void;
  onNewThread: () => void;
  onOpenHistory: () => void;
  onAgentKindChange: (agentKind: MentorAgentKind) => void;
  onQaStyleChange: (qaStyle: MentorQaStyle) => void;
  modelOptions: MentorModelOption[];
  isModelsLoading?: boolean;
  onModelChange: (modelId: string) => void;
  onQuickAction: (action: MentorQuickAction) => void;
  onSessionBound: (params: { sessionId: string; traceId?: string }) => void;
  onMetaEvent: (event: MentorChatMetaEvent) => void;
  onRuntimeStateChange: (params: {
    status: "idle" | "streaming" | "error";
    errorMessage?: string;
    traceId?: string;
  }) => void;
}

interface QueuedMentorAction {
  nonce: string;
  action: MentorQuickAction;
}

/**
 * MentorThreadStateSync - 将 assistant-ui 线程状态同步回本地线程仓库
 */
function MentorThreadStateSync({ onMessagesChange }: MentorThreadStateSyncProps) {
  const messages = useThread((state) => state.messages);

  useEffect(() => {
    onMessagesChange(messages as ThreadMessageLike[]);
  }, [messages, onMessagesChange]);

  return null;
}

/**
 * buildChapterContext - 根据当前选中的 Concept 构造上下文
 */
function buildChapterContext(roadmapId: string, activeConcept: Concept | null): MentorChapterContext {
  return {
    roadmapId,
    conceptId: activeConcept?.concept_id,
    conceptName: activeConcept?.name,
    conceptSummary: activeConcept?.content_summary ?? activeConcept?.description,
  };
}

/**
 * mapMentorModelDtoToOption - 将后端模型 DTO 映射为前端下拉项
 */
function mapMentorModelDtoToOption(model: MentorModelDto): MentorModelOption {
  return {
    id: model.model_id,
    label: model.display_name,
    description: model.description ?? undefined,
    provider: model.provider,
    isDefault: model.is_default,
  };
}

/**
 * MentorRuntimeShell - 按线程实例化 assistant-ui runtime
 */
function MentorRuntimeShell({
  threadId,
  agentKind,
  qaStyle,
  modelId,
  remoteSessionId,
  chapterContext,
  initialMessages,
  onMessagesChange,
  onNewThread,
  onOpenHistory,
  onAgentKindChange,
  onQaStyleChange,
  modelOptions,
  isModelsLoading = false,
  onModelChange,
  onQuickAction,
  onSessionBound,
  onMetaEvent,
  onRuntimeStateChange,
}: MentorRuntimeShellProps) {
  const [queuedAction, setQueuedAction] = useState<QueuedMentorAction | null>(null);

  /**
   * handleQuickActionSelect - 统一处理所有快捷动作点击
   */
  const handleQuickActionSelect = useCallback(
    (action: MentorQuickAction) => {
      setQueuedAction({
        nonce: crypto.randomUUID(),
        action,
      });
      onQuickAction(action);
    },
    [onQuickAction]
  );

  /**
   * handleRuntimeStateChangeForward - 转发运行状态并清空一次性意图提示
   */
  const handleRuntimeStateChangeForward = useCallback(
    (params: {
      status: "idle" | "streaming" | "error";
      errorMessage?: string;
      traceId?: string;
    }) => {
      onRuntimeStateChange(params);
    },
    [onRuntimeStateChange]
  );

  const runtime = useMentorRuntime({
    agentKind,
    qaStyle,
    modelId,
    threadId,
    remoteSessionId,
    chapterContext,
    initialMessages,
    onSessionBound,
    onMetaEvent,
    onRuntimeStateChange: handleRuntimeStateChangeForward,
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <MentorThreadStateSync onMessagesChange={onMessagesChange} />

      <MentorThread
        onQuickAction={handleQuickActionSelect}
        footer={
          <MentorComposer
            threadId={threadId}
            chapterName={chapterContext.conceptName}
            agentKind={agentKind}
            qaStyle={qaStyle}
            modelId={modelId}
            modelOptions={modelOptions}
            isModelsLoading={isModelsLoading}
            queuedAction={queuedAction}
            onQueuedActionConsumed={() => setQueuedAction(null)}
            onQuickAction={handleQuickActionSelect}
            onAgentKindChange={onAgentKindChange}
            onQaStyleChange={onQaStyleChange}
            onModelChange={onModelChange}
            onNewThread={onNewThread}
            onOpenHistory={onOpenHistory}
          />
        }
      />
    </AssistantRuntimeProvider>
  );
}

/**
 * MentorDeerFlowRuntimeShell - Deer-Flow 模式下的 assistant-ui runtime 壳层
 */
function MentorDeerFlowRuntimeShell({
  threadId,
  agentKind,
  qaStyle,
  modelId,
  remoteSessionId,
  chapterContext,
  initialMessages,
  onMessagesChange,
  onNewThread,
  onOpenHistory,
  onAgentKindChange,
  onQaStyleChange,
  modelOptions,
  isModelsLoading = false,
  onModelChange,
  onQuickAction,
  onSessionBound,
  onRuntimeStateChange,
}: Omit<MentorRuntimeShellProps, "onMetaEvent">) {
  const [queuedAction, setQueuedAction] = useState<QueuedMentorAction | null>(null);
  const [deerFlowTodos, setDeerFlowTodos] = useState<DeerFlowTodo[]>(() =>
    extractTodosFromDeerFlowThreadMessages(initialMessages)
  );

  const handleTodosSnapshot = useCallback((nextTodos: DeerFlowTodo[]) => {
    setDeerFlowTodos(nextTodos);
  }, []);

  /**
   * 历史消息补拉或父级刷新 initialMessages 时，从已持久化的 write_todos 恢复列表；
   * 仅在解析到非空时写入，避免流式中途尚无工具片段时清空 onTodosSnapshot 已更新的状态。
   */
  useEffect(() => {
    const parsed = extractTodosFromDeerFlowThreadMessages(initialMessages);
    if (parsed.length > 0) {
      setDeerFlowTodos(parsed);
    }
  }, [initialMessages]);

  const handleQuickActionSelect = useCallback(
    (action: MentorQuickAction) => {
      setQueuedAction({
        nonce: crypto.randomUUID(),
        action,
      });
      onQuickAction(action);
    },
    [onQuickAction]
  );

  const runtime = useMentorDeerFlowRuntime({
    agentKind,
    qaStyle,
    modelId,
    threadId,
    remoteSessionId,
    chapterContext,
    initialMessages,
    onSessionBound,
    onRuntimeStateChange,
    onTodosSnapshot: handleTodosSnapshot,
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <MentorThreadStateSync onMessagesChange={onMessagesChange} />

      <MentorThread
        onQuickAction={handleQuickActionSelect}
        footer={
          <div
            className={cn(
              "mx-auto w-full max-w-2xl px-0 pb-1",
              deerFlowTodos.length > 0 &&
                "overflow-hidden rounded-xl border border-border/60 bg-background shadow-sm"
            )}
          >
            {deerFlowTodos.length > 0 ? (
              <>
                <DeerFlowTodoList
                  combinedCardStack
                  className="shrink-0"
                  hidden={false}
                  todos={deerFlowTodos}
                />
                <MentorComposer
                  isDockedWithTodosAbove
                  className="shrink-0"
                  threadId={threadId}
                  chapterName={chapterContext.conceptName}
                  agentKind={agentKind}
                  qaStyle={qaStyle}
                  modelId={modelId}
                  modelOptions={modelOptions}
                  isModelsLoading={isModelsLoading}
                  queuedAction={queuedAction}
                  onQueuedActionConsumed={() => setQueuedAction(null)}
                  onQuickAction={handleQuickActionSelect}
                  onAgentKindChange={onAgentKindChange}
                  onQaStyleChange={onQaStyleChange}
                  onModelChange={onModelChange}
                  onNewThread={onNewThread}
                  onOpenHistory={onOpenHistory}
                />
              </>
            ) : (
              <MentorComposer
                className="shrink-0"
                threadId={threadId}
                chapterName={chapterContext.conceptName}
                agentKind={agentKind}
                qaStyle={qaStyle}
                modelId={modelId}
                modelOptions={modelOptions}
                isModelsLoading={isModelsLoading}
                queuedAction={queuedAction}
                onQueuedActionConsumed={() => setQueuedAction(null)}
                onQuickAction={handleQuickActionSelect}
                onAgentKindChange={onAgentKindChange}
                onQaStyleChange={onQaStyleChange}
                onModelChange={onModelChange}
                onNewThread={onNewThread}
                onOpenHistory={onOpenHistory}
              />
            )}
          </div>
        }
      />
    </AssistantRuntimeProvider>
  );
}

/**
 * MentorSidebar - AI 伴学右侧侧栏
 */
export function MentorSidebar({ roadmapId, activeConcept, onCollapse }: MentorSidebarProps) {
  const isDeerFlowMentorEnabled = ENABLE_DEERFLOW_MENTOR;
  const chapterContext = useMemo(
    () => buildChapterContext(roadmapId, activeConcept),
    [activeConcept, roadmapId]
  );
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [deletingThreadId, setDeletingThreadId] = useState<string | null>(null);
  const [modelOptions, setModelOptions] = useState<MentorModelOption[]>([]);
  const [defaultModelId, setDefaultModelId] = useState("");
  const [isModelsLoading, setIsModelsLoading] = useState(true);
  const [runtimeRevision, setRuntimeRevision] = useState(0);
  const runtimeThreadIdRef = useRef<string | null>(null);
  const runtimeInitialMessagesRef = useRef<ThreadMessageLike[]>([]);
  const runtimeRemoteSessionIdRef = useRef<string | null>(null);
  const hasAutoSelectedSyncedThreadRef = useRef(false);
  const {
    threads,
    currentThread,
    currentThreadId,
    setCurrentThreadId,
    createThread,
    deleteThread,
    updateThread,
    replaceCurrentThreadMessages,
    switchThread,
    syncThreadSession,
    setThreadStatus,
    upsertRemoteThreads,
  } = useMentorThreads({
    roadmapId,
    activeChapterContext: chapterContext,
    defaultModelId,
  });
  const selectedAgentKind: MentorAgentKind = currentThread?.agentKind ?? "qa";
  const selectedQaStyle: MentorQaStyle = currentThread?.qaStyle ?? "casual";
  const effectiveModelOptions = useMemo(
    () => ensureMentorModelOption(modelOptions, currentThread?.modelId),
    [currentThread?.modelId, modelOptions]
  );
  const selectedModelId = currentThread?.modelId || defaultModelId || effectiveModelOptions[0]?.id || "";

  /**
   * hydrateThreadMessages - 从后端刷新线程消息并重建 runtime
   */
  const hydrateThreadMessages = useCallback(
    async (params: {
      threadId: string;
      remoteSessionId: string;
      withLoadingState?: boolean;
    }) => {
      if (params.withLoadingState ?? true) {
        setThreadStatus({
          threadId: params.threadId,
          status: "streaming",
        });
      }

      try {
        let messageCount = 0;
        let mappedMessages: ThreadMessageLike[] = [];

        if (isDeerFlowMentorEnabled) {
          const messages = await listMentorDeerFlowMessages(params.remoteSessionId);
          mappedMessages = mapDeerFlowMessagesToThreadMessages(messages);
          messageCount = messages.length;
        } else {
          const messages = await listMentorMessages(params.remoteSessionId);
          mappedMessages = mapMentorMessagesToThreadMessages(messages);
          messageCount = messages.length;
        }

        updateThread({
          id: params.threadId,
          patch: {
            messages: mappedMessages,
            messageCount,
            isHydrated: true,
            status: "idle",
            lastError: undefined,
          },
        });

        if (currentThreadId === params.threadId) {
          runtimeInitialMessagesRef.current = mappedMessages;
          setRuntimeRevision((previousRevision) => previousRevision + 1);
        }
      } catch (error) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : "Failed to hydrate mentor thread from backend.";
        setThreadStatus({
          threadId: params.threadId,
          status: "error",
          lastError: errorMessage,
        });
        console.error("[MentorSidebar] Failed to hydrate mentor thread:", error);
      }
    },
    [currentThreadId, isDeerFlowMentorEnabled, setThreadStatus, updateThread]
  );

  useEffect(() => {
    let isCancelled = false;

    async function loadMentorModels() {
      try {
        setIsModelsLoading(true);
        const response = isDeerFlowMentorEnabled
          ? await listMentorDeerFlowModels()
          : await listMentorModels();
        if (isCancelled) {
          return;
        }

        const nextOptions = response.items.map(mapMentorModelDtoToOption);
        setModelOptions(nextOptions);
        setDefaultModelId(response.default_model_id ?? nextOptions[0]?.id ?? "");
      } catch (error) {
        if (isCancelled) {
          return;
        }
        console.error("[MentorSidebar] Failed to load mentor models:", error);
        toast.error("Failed to load mentor models.");
      } finally {
        if (!isCancelled) {
          setIsModelsLoading(false);
        }
      }
    }

    void loadMentorModels();

    return () => {
      isCancelled = true;
    };
  }, [isDeerFlowMentorEnabled]);

  useEffect(() => {
    if (!currentThread || currentThread.modelId || !defaultModelId) {
      return;
    }

    updateThread({
      id: currentThread.id,
      patch: {
        modelId: defaultModelId,
      },
    });
  }, [currentThread, defaultModelId, updateThread]);

  /**
   * 当 sidebar 挂载或用户切换到新章节时，预热 Redis 缓存。
   * fire-and-forget：失败静默处理，不影响任何 UI 状态。
   */
  useEffect(() => {
    if (isDeerFlowMentorEnabled) {
      void warmupMentorDeerFlowContext({
        roadmap_id: roadmapId,
        concept_id: chapterContext.conceptId,
        concept_title: chapterContext.conceptName,
      });
      return;
    }

    void warmupMentorContext({
      roadmap_id: roadmapId,
      concept_id: chapterContext.conceptId,
      concept_title: chapterContext.conceptName,
    });
  }, [chapterContext.conceptId, chapterContext.conceptName, isDeerFlowMentorEnabled, roadmapId]);

  useEffect(() => {
    let isCancelled = false;

    /**
     * loadRemoteSessions - 拉取后端历史会话并合并到本地线程
     */
    async function loadRemoteSessions() {
      try {
        let nextThreads = [];

        if (isDeerFlowMentorEnabled) {
          const sessions = await listMentorDeerFlowThreads({
            roadmapId,
            conceptId: chapterContext.conceptId,
          });
          nextThreads = sessions.map((session) => {
            const thread = mapDeerFlowThreadToThreadRecord(session);

            if (session.concept_id && session.concept_id === chapterContext.conceptId) {
              return {
                ...thread,
                chapterContext: {
                  ...thread.chapterContext,
                  conceptName: chapterContext.conceptName,
                  conceptSummary: chapterContext.conceptSummary,
                },
              };
            }

            return thread;
          });
        } else {
          const sessions = await listMentorSessions({
            roadmapId,
            conceptId: chapterContext.conceptId,
          });
          nextThreads = sessions.map((session) => {
            const thread = mapMentorSessionToThreadRecord(session);

            if (session.concept_id && session.concept_id === chapterContext.conceptId) {
              return {
                ...thread,
                chapterContext: {
                  ...thread.chapterContext,
                  conceptName: chapterContext.conceptName,
                  conceptSummary: chapterContext.conceptSummary,
                },
              };
            }

            return thread;
          });
        }
        if (isCancelled) {
          return;
        }

        upsertRemoteThreads(nextThreads);
      } catch (error) {
        console.error("[MentorSidebar] Failed to load mentor sessions:", error);
      }
    }

    void loadRemoteSessions();

    return () => {
      isCancelled = true;
    };
  }, [
    chapterContext.conceptId,
    chapterContext.conceptName,
    chapterContext.conceptSummary,
    isDeerFlowMentorEnabled,
    roadmapId,
    upsertRemoteThreads,
  ]);

  useEffect(() => {
    hasAutoSelectedSyncedThreadRef.current = false;
  }, [chapterContext.conceptId, roadmapId]);

  useEffect(() => {
    if (hasAutoSelectedSyncedThreadRef.current) {
      return;
    }

    const currentThreadIsEmptyDraft =
      !currentThread?.remoteSessionId &&
      (currentThread?.messages.length ?? 0) === 0;
    const mostRecentSyncedThread = threads.find((thread) => Boolean(thread.remoteSessionId));

    if (!mostRecentSyncedThread) {
      return;
    }

    if (!currentThreadId || currentThreadIsEmptyDraft) {
      hasAutoSelectedSyncedThreadRef.current = true;
      setCurrentThreadId(mostRecentSyncedThread.id);
      return;
    }

    if (currentThread?.remoteSessionId) {
      hasAutoSelectedSyncedThreadRef.current = true;
    }
  }, [currentThread, currentThreadId, setCurrentThreadId, threads]);

  useEffect(() => {
    runtimeRemoteSessionIdRef.current = currentThread?.remoteSessionId ?? null;
  }, [currentThread?.remoteSessionId]);

  useEffect(() => {
    const currentThreadRemoteSessionId = currentThread?.remoteSessionId;
    const currentThreadIsHydrated = currentThread?.isHydrated ?? false;
    const currentThreadLocalId = currentThread?.id;
    const currentThreadStatus = currentThread?.status;

    if (!currentThreadLocalId || !currentThreadRemoteSessionId || currentThreadIsHydrated) {
      return;
    }

    // 流式传输尚未结束时不要提前 hydrate，否则会重建 runtime 并打断 SSE。
    if (currentThreadStatus === "streaming") {
      return;
    }

    const threadId = currentThreadLocalId;
    const remoteSessionId = currentThreadRemoteSessionId;

    let isCancelled = false;

    void (async () => {
      await hydrateThreadMessages({
        threadId,
        remoteSessionId,
        withLoadingState: true,
      });
      if (isCancelled) {
        return;
      }
    })();

    return () => {
      isCancelled = true;
    };
  }, [
    currentThreadId,
    currentThread?.id,
    currentThread?.isHydrated,
    currentThread?.remoteSessionId,
    currentThread?.status,
    hydrateThreadMessages,
  ]);

  if (currentThread && runtimeThreadIdRef.current !== currentThread.id) {
    runtimeThreadIdRef.current = currentThread.id;
    runtimeInitialMessagesRef.current = currentThread.messages;
  }

  const handleSessionBound = (params: { sessionId: string; traceId?: string }) => {
    if (!currentThread) {
      return;
    }

    runtimeRemoteSessionIdRef.current = params.sessionId;
    syncThreadSession({
      threadId: currentThread.id,
      remoteSessionId: params.sessionId,
      traceId: params.traceId,
    });
  };

  /**
   * handleMetaEvent - 同步后端返回的自动路由结果
   */
  const handleMetaEvent = (event: MentorChatMetaEvent) => {
    if (!currentThread) {
      return;
    }

    updateThread({
      id: currentThread.id,
      patch: {
        agentKind: event.agent_kind ?? currentThread.agentKind,
        qaStyle: event.qa_style ?? currentThread.qaStyle,
        emotionLabel: event.emotion_label ?? currentThread.emotionLabel,
        emotionSummary: event.emotion_summary ?? currentThread.emotionSummary,
      },
    });
  };

  const handleRuntimeStateChange = (params: {
    status: "idle" | "streaming" | "error";
    errorMessage?: string;
    traceId?: string;
  }) => {
    if (!currentThread) {
      return;
    }

    setThreadStatus({
      threadId: currentThread.id,
      status: params.status,
      lastError: params.errorMessage,
      traceId: params.traceId,
    });

    if (params.status !== "idle") {
      return;
    }

    const remoteSessionId = currentThread.remoteSessionId ?? runtimeRemoteSessionIdRef.current;
    if (!remoteSessionId) {
      return;
    }

    void hydrateThreadMessages({
      threadId: currentThread.id,
      remoteSessionId,
      withLoadingState: false,
    });
  };

  const runtimeKey = `${currentThread?.id ?? "new"}:${selectedAgentKind}:${selectedQaStyle}:${selectedModelId}:${runtimeRevision}`;

  /**
   * handleCreateThread - 创建新线程并切换到该线程
   */
  const handleCreateThread = () => {
    createThread({
      agentKind: selectedAgentKind,
      qaStyle: selectedQaStyle,
      modelId: selectedModelId,
      chapterContext,
    });
  };

  /**
   * handleAgentKindChange - 切换当前线程的聊天 Agent
   */
  const handleAgentKindChange = (nextAgentKind: MentorAgentKind) => {
    if (!currentThread || nextAgentKind === currentThread.agentKind) {
      return;
    }

    updateThread({
      id: currentThread.id,
      patch: {
        agentKind: nextAgentKind,
      },
    });
  };

  /**
   * handleQaStyleChange - 切换答疑风格
   */
  const handleQaStyleChange = (nextQaStyle: MentorQaStyle) => {
    if (!currentThread || nextQaStyle === currentThread.qaStyle) {
      return;
    }

    updateThread({
      id: currentThread.id,
      patch: {
        qaStyle: nextQaStyle,
      },
    });
  };

  /**
   * handleModelChange - 切换当前线程的模型
   */
  const handleModelChange = (nextModelId: string) => {
    if (!currentThread || nextModelId === currentThread.modelId) {
      return;
    }

    updateThread({
      id: currentThread.id,
      patch: {
        modelId: nextModelId,
      },
    });
  };

  const t = useTranslations("mentor");

  /**
   * handleDeleteThread - 删除当前章节作用域下的历史会话
   */
  const handleDeleteThread = async (threadId: string) => {
    if (deletingThreadId) {
      return;
    }

    const targetThread = threads.find((thread) => thread.id === threadId);
    if (!targetThread) {
      return;
    }

    if (targetThread.status === "streaming") {
      toast.error(t("deleteThreadStreaming"));
      return;
    }

    try {
      setDeletingThreadId(threadId);

      if (targetThread.remoteSessionId) {
        if (isDeerFlowMentorEnabled) {
          await deleteMentorDeerFlowThread(targetThread.remoteSessionId);
        } else {
          await deleteMentorSession(targetThread.remoteSessionId);
        }
      }

      deleteThread(threadId);
      toast.success(t("deleteThreadSuccess"));
    } catch (error) {
      console.error("[MentorSidebar] Failed to delete mentor thread:", error);
      toast.error(t("deleteThreadFailed"));
    } finally {
      setDeletingThreadId(null);
    }
  };

  if (!currentThreadId || !currentThread) {
    return (
      <div className="flex h-full items-center justify-center border-l border-border/60 bg-slate-50 text-sm text-muted-foreground">
        {t("preparing")}
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col border-l border-border/60 bg-background shadow-[-4px_0_24px_-12px_rgba(0,0,0,0.1)]">
      <div className="flex items-center justify-between border-b border-border/60 bg-background/95 px-4 py-3 backdrop-blur-sm">
        <div className="flex items-center gap-2 text-slate-800">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-sage-100 text-sage-700">
            <Bot className="h-4 w-4" />
          </div>
          <span className="font-semibold">{t("title")}</span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-full text-slate-500 hover:bg-slate-100 hover:text-slate-900"
          onClick={onCollapse}
          title={t("collapse")}
        >
          <PanelRightClose className="h-4 w-4" />
        </Button>
      </div>

      <div className="min-h-0 flex-1">
        {isDeerFlowMentorEnabled ? (
          <MentorDeerFlowRuntimeShell
            key={runtimeKey}
            threadId={currentThreadId}
            agentKind={selectedAgentKind}
            qaStyle={selectedQaStyle}
            modelId={selectedModelId}
            remoteSessionId={currentThread.remoteSessionId}
            chapterContext={currentThread.chapterContext}
            initialMessages={runtimeInitialMessagesRef.current}
            onMessagesChange={replaceCurrentThreadMessages}
            onNewThread={handleCreateThread}
            onOpenHistory={() => setIsHistoryOpen(true)}
            onAgentKindChange={handleAgentKindChange}
            onQaStyleChange={handleQaStyleChange}
            modelOptions={effectiveModelOptions}
            isModelsLoading={isModelsLoading}
            onModelChange={handleModelChange}
            onQuickAction={() => undefined}
            onSessionBound={handleSessionBound}
            onRuntimeStateChange={handleRuntimeStateChange}
          />
        ) : (
          <MentorRuntimeShell
            key={runtimeKey}
            threadId={currentThreadId}
            agentKind={selectedAgentKind}
            qaStyle={selectedQaStyle}
            modelId={selectedModelId}
            remoteSessionId={currentThread.remoteSessionId}
            chapterContext={currentThread.chapterContext}
            initialMessages={runtimeInitialMessagesRef.current}
            onMessagesChange={replaceCurrentThreadMessages}
            onNewThread={handleCreateThread}
            onOpenHistory={() => setIsHistoryOpen(true)}
            onAgentKindChange={handleAgentKindChange}
            onQaStyleChange={handleQaStyleChange}
            modelOptions={effectiveModelOptions}
            isModelsLoading={isModelsLoading}
            onModelChange={handleModelChange}
            onQuickAction={() => undefined}
            onSessionBound={handleSessionBound}
            onMetaEvent={handleMetaEvent}
            onRuntimeStateChange={handleRuntimeStateChange}
          />
        )}
      </div>

      <MentorThreadHistory
        open={isHistoryOpen}
        onOpenChange={setIsHistoryOpen}
        threads={threads}
        currentThreadId={currentThreadId}
        onSwitchThread={switchThread}
        onDeleteThread={handleDeleteThread}
        deletingThreadId={deletingThreadId}
        historyDescription={
          chapterContext.conceptId ? t("historyDescConcept") : t("historyDescRoadmap")
        }
      />
    </div>
  );
}

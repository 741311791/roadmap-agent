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

import {
  mapMentorMessagesToThreadMessages,
  mapMentorSessionToThreadRecord,
} from "@/components/mentor/mentor-adapter";
import {
  deleteMentorSession,
  listMentorMessages,
  listMentorSessions,
  warmupMentorContext,
} from "@/components/mentor/mentor-api";
import { MentorComposer } from "@/components/mentor/mentor-composer";
import { MentorThread } from "@/components/mentor/mentor-thread";
import { MentorThreadHistory } from "@/components/mentor/mentor-thread-history";
import type {
  MentorAgentType,
  MentorChapterContext,
} from "@/components/mentor/types";
import { DEFAULT_MENTOR_MODEL_ID, normalizeMentorModelId } from "@/components/mentor/types";
import { useMentorRuntime } from "@/components/mentor/use-mentor-runtime";
import { useMentorThreads } from "@/components/mentor/use-mentor-threads";

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
  agentType: MentorAgentType;
  modelId: string;
  remoteSessionId?: string;
  chapterContext: MentorChapterContext;
  initialMessages: ThreadMessageLike[];
  onMessagesChange: (messages: ThreadMessageLike[]) => void;
  onNewThread: () => void;
  onOpenHistory: () => void;
  onAgentChange: (agentType: MentorAgentType) => void;
  onModelChange: (modelId: string) => void;
  onSessionBound: (params: { sessionId: string; traceId?: string }) => void;
  onRuntimeStateChange: (params: {
    status: "idle" | "streaming" | "error";
    errorMessage?: string;
    traceId?: string;
  }) => void;
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
 * MentorRuntimeShell - 按线程实例化 assistant-ui runtime
 */
function MentorRuntimeShell({
  threadId,
  agentType,
  modelId,
  remoteSessionId,
  chapterContext,
  initialMessages,
  onMessagesChange,
  onNewThread,
  onOpenHistory,
  onAgentChange,
  onModelChange,
  onSessionBound,
  onRuntimeStateChange,
}: MentorRuntimeShellProps) {
  const runtime = useMentorRuntime({
    agentType,
    modelId,
    threadId,
    remoteSessionId,
    chapterContext,
    initialMessages,
    onSessionBound,
    onRuntimeStateChange,
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <MentorThreadStateSync onMessagesChange={onMessagesChange} />

      <MentorThread
        footer={
          <MentorComposer
            threadId={threadId}
            chapterName={chapterContext.conceptName}
            agentType={agentType}
            modelId={modelId}
            onAgentChange={onAgentChange}
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
 * MentorSidebar - AI 伴学右侧侧栏
 */
export function MentorSidebar({ roadmapId, activeConcept, onCollapse }: MentorSidebarProps) {
  const chapterContext = useMemo(
    () => buildChapterContext(roadmapId, activeConcept),
    [activeConcept, roadmapId]
  );
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [deletingThreadId, setDeletingThreadId] = useState<string | null>(null);
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
  });
  const selectedAgentType: MentorAgentType = currentThread?.agentType ?? "company";
  const selectedModelId = normalizeMentorModelId(currentThread?.modelId || DEFAULT_MENTOR_MODEL_ID);

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
        const messages = await listMentorMessages(params.remoteSessionId);
        const mappedMessages = mapMentorMessagesToThreadMessages(messages);

        updateThread({
          id: params.threadId,
          patch: {
            messages: mappedMessages,
            messageCount: messages.length,
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
    [currentThreadId, setThreadStatus, updateThread]
  );

  /**
   * 当 sidebar 挂载或用户切换到新章节时，预热 Redis 缓存。
   * fire-and-forget：失败静默处理，不影响任何 UI 状态。
   */
  useEffect(() => {
    void warmupMentorContext({
      roadmap_id: roadmapId,
      concept_id: chapterContext.conceptId,
      concept_title: chapterContext.conceptName,
    });
  }, [roadmapId, chapterContext.conceptId, chapterContext.conceptName]);

  useEffect(() => {
    let isCancelled = false;

    /**
     * loadRemoteSessions - 拉取后端历史会话并合并到本地线程
     */
    async function loadRemoteSessions() {
      try {
        const sessions = await listMentorSessions({
          roadmapId,
          conceptId: chapterContext.conceptId,
        });
        if (isCancelled) {
          return;
        }

        upsertRemoteThreads(
          sessions.map((session) => {
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
          })
        );
      } catch (error) {
        console.error("[MentorSidebar] Failed to load mentor sessions:", error);
      }
    }

    void loadRemoteSessions();

    return () => {
      isCancelled = true;
    };
  }, [chapterContext.conceptId, chapterContext.conceptName, chapterContext.conceptSummary, roadmapId, upsertRemoteThreads]);

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

  const runtimeKey = `${currentThread?.id ?? "new"}:${selectedAgentType}:${selectedModelId}:${runtimeRevision}`;

  /**
   * handleCreateThread - 创建新线程并切换到该线程
   */
  const handleCreateThread = () => {
    createThread({
      agentType: selectedAgentType,
      modelId: selectedModelId,
      chapterContext,
    });
  };

  /**
   * handleAgentChange - 切换当前线程的 Agent
   */
  const handleAgentChange = (nextAgentType: MentorAgentType) => {
    if (!currentThread || nextAgentType === currentThread.agentType) {
      return;
    }

    updateThread({
      id: currentThread.id,
      patch: {
        agentType: nextAgentType,
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
        await deleteMentorSession(targetThread.remoteSessionId);
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
        <MentorRuntimeShell
          key={runtimeKey}
          threadId={currentThreadId}
          agentType={selectedAgentType}
          modelId={selectedModelId}
          remoteSessionId={currentThread.remoteSessionId}
          chapterContext={currentThread.chapterContext}
          initialMessages={runtimeInitialMessagesRef.current}
          onMessagesChange={replaceCurrentThreadMessages}
          onNewThread={handleCreateThread}
          onOpenHistory={() => setIsHistoryOpen(true)}
          onAgentChange={handleAgentChange}
          onModelChange={handleModelChange}
          onSessionBound={handleSessionBound}
          onRuntimeStateChange={handleRuntimeStateChange}
        />
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

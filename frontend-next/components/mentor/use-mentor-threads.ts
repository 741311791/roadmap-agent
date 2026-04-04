"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ThreadMessageLike } from "@assistant-ui/react";

import type {
  MentorAgentKind,
  MentorChapterContext,
  MentorQaStyle,
  MentorThreadRecord,
  MentorThreadStatus,
} from "@/components/mentor/types";
import { MAX_MENTOR_THREAD_HISTORY } from "@/components/mentor/types";

interface UseMentorThreadsOptions {
  roadmapId: string;
  activeChapterContext: MentorChapterContext;
  defaultModelId?: string;
}

interface CreateMentorThreadOptions {
  agentKind: MentorAgentKind;
  qaStyle: MentorQaStyle;
  modelId: string;
  chapterContext: MentorChapterContext;
  messages?: ThreadMessageLike[];
}

interface UpdateMentorThreadOptions {
  id: string;
  patch: Partial<MentorThreadRecord>;
}

const ROADMAP_SCOPE_ID = "__roadmap__";

/**
 * getStorageKey - 生成 localStorage key
 */
function getStorageKey(roadmapId: string): string {
  return `mentor_threads_${roadmapId}`;
}

/**
 * getThreadScopeId - 生成章节作用域标识
 */
function getThreadScopeId(chapterContext: MentorChapterContext): string {
  return chapterContext.conceptId ?? ROADMAP_SCOPE_ID;
}

/**
 * getThreadScopeKey - 生成完整作用域 key
 */
function getThreadScopeKey(chapterContext: MentorChapterContext): string {
  return `${chapterContext.roadmapId}:${getThreadScopeId(chapterContext)}`;
}

/**
 * isThreadInScope - 判断线程是否属于当前章节作用域
 */
function isThreadInScope(
  thread: MentorThreadRecord,
  chapterContext: MentorChapterContext
): boolean {
  return getThreadScopeKey(thread.chapterContext) === getThreadScopeKey(chapterContext);
}

/**
 * createThreadId - 创建线程 ID
 */
function createThreadId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `mentor-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * normalizeMessageLike - 规范化消息结构，避免 Date 在 JSON 中丢失类型
 */
function normalizeMessageLike(message: ThreadMessageLike): ThreadMessageLike {
  const normalizedContent =
    typeof message.content === "string"
      ? message.content
      : message.content.map((part) => {
          if ("type" in part && part.type === "reasoning") {
            return part;
          }

          return part;
        });

  return {
    ...message,
    content: normalizedContent,
    createdAt: message.createdAt ? new Date(message.createdAt) : undefined,
  };
}

/**
 * normalizeMessages - 批量规范化消息结构
 */
function normalizeMessages(messages: ThreadMessageLike[]): ThreadMessageLike[] {
  return messages.map(normalizeMessageLike);
}

/**
 * extractMessageText - 从 assistant-ui 消息中提取纯文本
 */
function extractMessageText(message: ThreadMessageLike): string {
  if (typeof message.content === "string") {
    return message.content;
  }

  return message.content
    .map((part) => {
      if (part.type === "text" || part.type === "reasoning") {
        return part.text;
      }

      return "";
    })
    .join("")
    .trim();
}

/**
 * deriveThreadTitle - 根据第一条用户消息生成会话标题
 */
function deriveThreadTitle(messages: ThreadMessageLike[]): string {
  const firstUserMessage = messages.find((message) => message.role === "user");
  const fallbackTitle = "New thread";

  if (!firstUserMessage) {
    return fallbackTitle;
  }

  const plainText = extractMessageText(firstUserMessage).replace(/\s+/g, " ").trim();

  if (!plainText) {
    return fallbackTitle;
  }

  return plainText.length > 20 ? `${plainText.slice(0, 20)}...` : plainText;
}

/**
 * createEmptyThreadTitle - 为空线程生成默认标题
 */
function createEmptyThreadTitle(chapterContext: MentorChapterContext): string {
  return chapterContext.conceptName ?? "New thread";
}

/**
 * sortAndLimitThreads - 按章节作用域分别排序并限制数量上限
 */
function sortAndLimitThreads(threads: MentorThreadRecord[]): MentorThreadRecord[] {
  const groupedThreads = new Map<string, MentorThreadRecord[]>();

  threads.forEach((thread) => {
    const scopeKey = getThreadScopeKey(thread.chapterContext);
    const scopeThreads = groupedThreads.get(scopeKey) ?? [];
    scopeThreads.push(thread);
    groupedThreads.set(scopeKey, scopeThreads);
  });

  return [...groupedThreads.values()]
    .flatMap((scopeThreads) =>
      [...scopeThreads]
        .sort((left, right) => right.updatedAt - left.updatedAt)
        .slice(0, MAX_MENTOR_THREAD_HISTORY)
    )
    .sort((left, right) => right.updatedAt - left.updatedAt);
}

/**
 * createMentorThreadRecord - 创建线程记录
 */
function createMentorThreadRecord(options: CreateMentorThreadOptions): MentorThreadRecord {
  const now = Date.now();
  const messages = normalizeMessages(options.messages ?? []);
  const title = messages.length > 0 ? deriveThreadTitle(messages) : createEmptyThreadTitle(options.chapterContext);

  return {
    id: createThreadId(),
    title,
    agentKind: options.agentKind,
    qaStyle: options.qaStyle,
    modelId: options.modelId,
    chapterContext: options.chapterContext,
    messages,
    status: "idle",
    isHydrated: false,
    createdAt: now,
    updatedAt: now,
  };
}

/**
 * parseStoredThreads - 解析并恢复持久化线程
 */
function parseStoredThreads(rawValue: string | null, roadmapId: string): MentorThreadRecord[] {
  if (!rawValue) {
    return [];
  }

  try {
    const parsed = JSON.parse(rawValue) as MentorThreadRecord[];

    if (!Array.isArray(parsed) || parsed.length === 0) {
      return [];
    }

    return sortAndLimitThreads(
      parsed.map((thread) => ({
        ...thread,
        chapterContext: {
          ...thread.chapterContext,
          roadmapId,
        },
        messages: normalizeMessages((thread.messages ?? []) as ThreadMessageLike[]),
        agentKind: thread.agentKind ?? "qa",
        qaStyle: thread.qaStyle ?? "casual",
        messageCount: thread.messageCount ?? thread.messages?.length ?? 0,
        modelId: thread.modelId ?? "",
        remoteSessionId: thread.remoteSessionId ?? undefined,
        lastTraceId: thread.lastTraceId ?? undefined,
        emotionLabel: thread.emotionLabel ?? undefined,
        emotionSummary: thread.emotionSummary ?? undefined,
        status: thread.status ?? ("idle" as MentorThreadStatus),
        lastError: thread.lastError ?? undefined,
        isHydrated: thread.isHydrated ?? false,
      }))
    );
  } catch {
    return [];
  }
}

/**
 * createDefaultThread - 为当前章节作用域创建默认空线程
 */
function createDefaultThread(
  chapterContext: MentorChapterContext,
  defaultModelId: string = ""
): MentorThreadRecord {
  return createMentorThreadRecord({
    agentKind: "qa",
    qaStyle: "casual",
    modelId: defaultModelId,
    chapterContext,
  });
}

/**
 * useMentorThreads - 管理右侧侧栏的历史线程状态
 */
export function useMentorThreads({
  roadmapId,
  activeChapterContext,
  defaultModelId = "",
}: UseMentorThreadsOptions) {
  const [threads, setThreads] = useState<MentorThreadRecord[]>([]);
  const [currentThreadIdsByScope, setCurrentThreadIdsByScope] = useState<Record<string, string | null>>(
    {}
  );
  const activeScopeKey = useMemo(
    () => getThreadScopeKey(activeChapterContext),
    [activeChapterContext]
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const storedThreads = parseStoredThreads(
      window.localStorage.getItem(getStorageKey(roadmapId)),
      roadmapId
    );

    setThreads(storedThreads);
    setCurrentThreadIdsByScope({});
  }, [roadmapId]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(getStorageKey(roadmapId), JSON.stringify(threads));
  }, [roadmapId, threads]);

  const scopedThreads = useMemo(
    () => threads.filter((thread) => isThreadInScope(thread, activeChapterContext)),
    [activeChapterContext, threads]
  );
  const currentThreadId = currentThreadIdsByScope[activeScopeKey] ?? null;
  const currentThread = useMemo(
    () => scopedThreads.find((thread) => thread.id === currentThreadId) ?? null,
    [currentThreadId, scopedThreads]
  );

  useEffect(() => {
    if (currentThread) {
      return;
    }

    if (scopedThreads.length > 0) {
      setCurrentThreadIdsByScope((previousMap) => ({
        ...previousMap,
        [activeScopeKey]: scopedThreads[0]?.id ?? null,
      }));
      return;
    }

    const nextThread = createDefaultThread(activeChapterContext, defaultModelId);
    setThreads((previousThreads) => sortAndLimitThreads([nextThread, ...previousThreads]));
    setCurrentThreadIdsByScope((previousMap) => ({
      ...previousMap,
      [activeScopeKey]: nextThread.id,
    }));
  }, [activeChapterContext, activeScopeKey, currentThread, defaultModelId, scopedThreads]);

  /**
   * createThread - 新建线程并切换为当前线程
   */
  const createThread = useCallback((options: CreateMentorThreadOptions) => {
    const nextThread = createMentorThreadRecord(options);
    const scopeKey = getThreadScopeKey(options.chapterContext);

    setThreads((previousThreads) => sortAndLimitThreads([nextThread, ...previousThreads]));
    setCurrentThreadIdsByScope((previousMap) => ({
      ...previousMap,
      [scopeKey]: nextThread.id,
    }));

    return nextThread;
  }, []);

  /**
   * updateThread - 更新指定线程
   */
  const updateThread = useCallback(({ id, patch }: UpdateMentorThreadOptions) => {
    setThreads((previousThreads) =>
      sortAndLimitThreads(
        previousThreads.map((thread) => {
          if (thread.id !== id) {
            return thread;
          }

          const nextMessages = patch.messages
            ? normalizeMessages(patch.messages as ThreadMessageLike[])
            : thread.messages;
          const nextTitle =
            nextMessages.length > 0
              ? deriveThreadTitle(nextMessages)
              : patch.title ?? thread.title ?? createEmptyThreadTitle(thread.chapterContext);

          return {
            ...thread,
            ...patch,
            messages: nextMessages,
            messageCount: patch.messageCount ?? nextMessages.length,
            title: nextTitle,
            isHydrated: patch.isHydrated ?? thread.isHydrated,
            updatedAt: patch.updatedAt ?? Date.now(),
          };
        })
      )
    );
  }, []);

  /**
   * deleteThread - 删除指定线程
   */
  const deleteThread = useCallback((threadId: string) => {
    const deletedThread = threads.find((thread) => thread.id === threadId) ?? null;

    if (!deletedThread) {
      return;
    }

    setThreads((previousThreads) => previousThreads.filter((thread) => thread.id !== threadId));

    const scopeKey = getThreadScopeKey(deletedThread.chapterContext);
    setCurrentThreadIdsByScope((previousMap) => {
      if (previousMap[scopeKey] !== threadId) {
        return previousMap;
      }

      return {
        ...previousMap,
        [scopeKey]: null,
      };
    });
  }, [threads]);

  /**
   * syncThreadSession - 将本地线程绑定到远端会话
   */
  const syncThreadSession = useCallback(
    (params: { threadId: string; remoteSessionId: string; traceId?: string }) => {
      updateThread({
        id: params.threadId,
        patch: {
          remoteSessionId: params.remoteSessionId,
          lastTraceId: params.traceId,
          status: "streaming",
          lastError: undefined,
          isHydrated: false,
        },
      });
    },
    [updateThread]
  );

  /**
   * setThreadStatus - 更新线程状态
   */
  const setThreadStatus = useCallback(
    (params: {
      threadId: string;
      status: MentorThreadStatus;
      lastError?: string;
      traceId?: string;
    }) => {
      updateThread({
        id: params.threadId,
        patch: {
          status: params.status,
          lastError: params.lastError,
          lastTraceId: params.traceId,
        },
      });
    },
    [updateThread]
  );

  /**
   * upsertRemoteThreads - 合并远端线程列表
   */
  const upsertRemoteThreads = useCallback(
    (remoteThreads: MentorThreadRecord[]) => {
      setThreads((previousThreads) => {
        const mergedThreads = [...previousThreads];

        remoteThreads.forEach((remoteThread) => {
          const existingIndex = mergedThreads.findIndex(
            (thread) =>
              thread.remoteSessionId === remoteThread.remoteSessionId ||
              thread.id === remoteThread.id
          );

          if (existingIndex === -1) {
            mergedThreads.push(remoteThread);
            return;
          }

          const existingThread = mergedThreads[existingIndex];
          mergedThreads[existingIndex] = {
            ...remoteThread,
            ...existingThread,
            title:
              existingThread.messages.length > 0 || existingThread.title !== "New thread"
                ? existingThread.title
                : remoteThread.title,
            agentKind: existingThread.agentKind || remoteThread.agentKind,
            qaStyle: existingThread.qaStyle ?? remoteThread.qaStyle ?? "casual",
            modelId: existingThread.modelId || remoteThread.modelId,
            chapterContext: {
              ...remoteThread.chapterContext,
              ...existingThread.chapterContext,
              roadmapId,
            },
            messageCount: existingThread.messageCount ?? remoteThread.messageCount,
            remoteSessionId: remoteThread.remoteSessionId,
            emotionLabel: existingThread.emotionLabel ?? remoteThread.emotionLabel,
            emotionSummary: existingThread.emotionSummary ?? remoteThread.emotionSummary,
            updatedAt: Math.max(existingThread.updatedAt, remoteThread.updatedAt),
          };
        });

        return sortAndLimitThreads(mergedThreads);
      });
    },
    [roadmapId]
  );

  /**
   * replaceCurrentThreadMessages - 同步当前运行中的线程消息
   */
  const replaceCurrentThreadMessages = useCallback(
    (messages: ThreadMessageLike[]) => {
      if (!currentThreadId) {
        return;
      }

      updateThread({
        id: currentThreadId,
        patch: {
          messages,
          messageCount: messages.length,
        },
      });
    },
    [currentThreadId, updateThread]
  );

  /**
   * switchThread - 切换到指定线程
   */
  const switchThread = useCallback((threadId: string) => {
    setCurrentThreadIdsByScope((previousMap) => ({
      ...previousMap,
      [activeScopeKey]: threadId,
    }));
  }, [activeScopeKey]);

  /**
   * setCurrentThreadId - 设置当前章节作用域下的线程
   */
  const setCurrentThreadId = useCallback(
    (threadId: string | null) => {
      setCurrentThreadIdsByScope((previousMap) => ({
        ...previousMap,
        [activeScopeKey]: threadId,
      }));
    },
    [activeScopeKey]
  );

  return {
    threads: scopedThreads,
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
  };
}

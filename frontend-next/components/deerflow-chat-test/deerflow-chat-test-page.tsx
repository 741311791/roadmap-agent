"use client";

import type { ChatStatus } from "ai";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  ChevronDown,
  Compass,
  MessageSquarePlus,
  PanelLeft,
  RefreshCw,
  Sparkles,
  Trash2,
} from "lucide-react";

import { DeerFlowArtifactTrigger } from "@/components/deerflow-chat-test/deerflow-artifact-trigger";
import { useDeerFlowArtifacts } from "@/components/deerflow-chat-test/deerflow-artifacts-context";
import { DeerFlowChatBox } from "@/components/deerflow-chat-test/deerflow-chat-box";
import { DeerFlowChatProviders } from "@/components/deerflow-chat-test/deerflow-chat-providers";
import {
  DeerFlowInputBox,
  DEERFLOW_INPUT_OUTER_CARD_CLASSNAME,
  type DeerFlowInputMode,
} from "@/components/deerflow-chat-test/deerflow-input-box";
import { DeerFlowMessageList } from "@/components/deerflow-chat-test/deerflow-message-list";
import { DeerFlowTodoList } from "@/components/deerflow-chat-test/deerflow-todo-list";
import {
  applyStreamMessageChunk,
  buildFollowupSuggestions,
  createOptimisticAssistantPlaceholder,
  createOptimisticUserMessage,
  deriveThreadTitleFromPrompt,
  extractArtifactsFromMessages,
  extractTodosFromMessages,
  extractTodosFromThreadMetadata,
  finalizeStreamingMessages,
  mapPersistedMessage,
  normalizeMessageEventPayload,
  upsertAssistantDraftFromValues,
  type DeerFlowChatMessage,
  type DeerFlowValuesPayload,
} from "@/components/deerflow-chat-test/deerflow-chat-state";
import {
  DeerFlowThreadProvider,
  type DeerFlowThreadState,
} from "@/components/deerflow-chat-test/deerflow-thread-context";
import { type PromptInputMessage } from "@/components/deerflow-native/ai-elements/prompt-input";
import {
  createDeerFlowStandaloneThread,
  deleteDeerFlowStandaloneThread,
  listDeerFlowStandaloneMessages,
  listDeerFlowStandaloneModels,
  listDeerFlowStandaloneThreads,
  streamDeerFlowStandaloneChat,
  type DeerFlowStandaloneChatContextPayload,
  type MentorModelDto,
  type DeerFlowMentorThreadDto,
} from "@/components/deerflow-chat-test/deerflow-standalone-api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * 与官方一致：不设独立 Effort 控件，由 Mode 映射 reasoning_effort 供上游使用。
 */
const REASONING_EFFORT_BY_MODE: Record<
  DeerFlowInputMode,
  NonNullable<DeerFlowStandaloneChatContextPayload["reasoning_effort"]>
> = {
  flash: "minimal",
  thinking: "low",
  pro: "medium",
  ultra: "high",
};

/**
 * Deer-Flow 风格独立测试页。
 */
export function DeerFlowChatTestPage() {
  return (
    <DeerFlowChatProviders>
      <DeerFlowChatTestWorkspace />
    </DeerFlowChatProviders>
  );
}

function DeerFlowChatTestWorkspace() {
  const { setArtifacts } = useDeerFlowArtifacts();

  const [threads, setThreads] = useState<DeerFlowMentorThreadDto[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<DeerFlowChatMessage[]>([]);
  const [chatStatus, setChatStatus] = useState<ChatStatus>("ready");
  const [isLoadingThreads, setIsLoadingThreads] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isLoadingModels, setIsLoadingModels] = useState(true);
  const [followupSuggestions, setFollowupSuggestions] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [modelOptions, setModelOptions] = useState<MentorModelDto[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  const [mode, setMode] = useState<DeerFlowInputMode>("pro");
  const abortControllerRef = useRef<AbortController | null>(null);
  /**
   * 正在流式写入的线程 ID。
   *
   * 首条消息会先乐观写入本地，再 `createThread` 并 `setCurrentThreadId`；
   * 若此时 effect 立刻 `loadMessages`，服务端仍为空，会清空乐观消息。
   * 在流式结束前跳过「按 threadId 自动拉历史」，由 handleSubmit 结束后再统一 load。
   */
  const streamingThreadIdRef = useRef<string | null>(null);

  const currentThread = useMemo(
    () => threads.find((thread) => thread.thread_id === currentThreadId) ?? null,
    [currentThreadId, threads]
  );
  const threadArtifacts = useMemo(() => {
    const rawArtifacts = currentThread?.metadata?.artifacts;
    const artifactsFromThread = Array.isArray(rawArtifacts)
      ? rawArtifacts.filter((item: unknown): item is string => typeof item === "string")
      : [];
    const artifactsFromMessages = extractArtifactsFromMessages(messages);
    return Array.from(new Set([...artifactsFromThread, ...artifactsFromMessages]));
  }, [currentThread?.metadata, messages]);
  const threadTodos = useMemo(() => {
    const todosFromMetadata = extractTodosFromThreadMetadata(currentThread?.metadata);
    if (todosFromMetadata.length > 0) {
      return todosFromMetadata;
    }

    return extractTodosFromMessages(messages);
  }, [currentThread?.metadata, messages]);
  const threadState = useMemo<DeerFlowThreadState>(
    () => ({
      id: currentThreadId ?? "deerflow-chat-test",
      title: currentThread?.title?.trim() || "Deer-Flow Chatbot",
      messages,
      artifacts: threadArtifacts,
      todos: threadTodos,
    }),
    [currentThread?.title, currentThreadId, messages, threadArtifacts, threadTodos]
  );

  const loadThreads = useCallback(async () => {
    setIsLoadingThreads(true);
    try {
      const nextThreads = await listDeerFlowStandaloneThreads();
      setThreads(nextThreads);
      setCurrentThreadId((previousThreadId) => {
        if (previousThreadId && nextThreads.some((thread) => thread.thread_id === previousThreadId)) {
          return previousThreadId;
        }

        // 首屏不自动选中历史线程，避免直接进入「有消息」态导致输入区体验与官方新对话不一致
        return null;
      });
    } catch (error) {
      console.error("[DeerFlowChatTestPage] Failed to load threads:", error);
      setErrorMessage("Failed to load Deer-Flow threads.");
    } finally {
      setIsLoadingThreads(false);
    }
  }, []);

  const loadMessages = useCallback(async (threadId: string) => {
    setIsLoadingMessages(true);
    try {
      const nextMessages = await listDeerFlowStandaloneMessages(threadId);
      const mappedMessages = nextMessages.map(mapPersistedMessage);
      setMessages(mappedMessages);
      setFollowupSuggestions([]);
      setErrorMessage(null);
      return mappedMessages;
    } catch (error) {
      console.error("[DeerFlowChatTestPage] Failed to load messages:", error);
      setErrorMessage("Failed to load Deer-Flow messages.");
      throw error;
    } finally {
      setIsLoadingMessages(false);
    }
  }, []);

  useEffect(() => {
    void loadThreads();
  }, [loadThreads]);

  useEffect(() => {
    let isCancelled = false;

    async function loadModels() {
      try {
        setIsLoadingModels(true);
        const response = await listDeerFlowStandaloneModels();
        if (isCancelled) {
          return;
        }

        setModelOptions(response.items);
        setSelectedModelId(
          (previousModelId) =>
            previousModelId || response.default_model_id || response.items[0]?.model_id || ""
        );
      } catch (error) {
        if (!isCancelled) {
          console.error("[DeerFlowChatTestPage] Failed to load Deer-Flow models:", error);
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingModels(false);
        }
      }
    }

    void loadModels();

    return () => {
      isCancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!currentThreadId) {
      setMessages([]);
      return;
    }

    if (streamingThreadIdRef.current === currentThreadId) {
      return;
    }

    void loadMessages(currentThreadId);
  }, [currentThreadId, loadMessages]);

  useEffect(() => {
    setArtifacts(threadArtifacts);
  }, [setArtifacts, threadArtifacts]);

  useEffect(() => {
    if (currentThread?.model_id) {
      setSelectedModelId(currentThread.model_id);
    }
  }, [currentThread?.model_id]);

  useEffect(() => {
    const selectedModel =
      modelOptions.find((model) => model.model_id === selectedModelId) ??
      modelOptions[0];
    const supportsThinking = selectedModel?.supports_thinking ?? false;

    if (!supportsThinking && mode !== "flash") {
      setMode("flash");
    }
  }, [mode, modelOptions, selectedModelId]);

  const handleCreateThread = useCallback(async () => {
    try {
      const createdThread = await createDeerFlowStandaloneThread({
        title: "New Chat",
        model_id: selectedModelId || undefined,
      });
      setThreads((previousThreads) => [createdThread, ...previousThreads]);
      setCurrentThreadId(createdThread.thread_id);
      setMessages([]);
      setFollowupSuggestions([]);
      setErrorMessage(null);
    } catch (error) {
      console.error("[DeerFlowChatTestPage] Failed to create thread:", error);
      setErrorMessage("Failed to create Deer-Flow thread.");
    }
  }, [selectedModelId]);

  const handleDeleteThread = useCallback(async (threadId: string) => {
    try {
      await deleteDeerFlowStandaloneThread(threadId);
      setThreads((previousThreads) =>
        previousThreads.filter((thread) => thread.thread_id !== threadId)
      );
      if (currentThreadId === threadId) {
        setCurrentThreadId(null);
        setMessages([]);
        setFollowupSuggestions([]);
      }
    } catch (error) {
      console.error("[DeerFlowChatTestPage] Failed to delete thread:", error);
      setErrorMessage("Failed to delete Deer-Flow thread.");
    }
  }, [currentThreadId]);

  /**
   * handleStopStreaming - 中断当前 Deer-Flow 流式请求
   */
  const handleStopStreaming = useCallback(async () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    streamingThreadIdRef.current = null;
    setChatStatus("ready");
    setMessages((previousMessages) => finalizeStreamingMessages(previousMessages));

    if (currentThreadId) {
      await loadMessages(currentThreadId).catch(() => undefined);
    }
  }, [currentThreadId, loadMessages]);

  const handleSubmit = useCallback(async (message: PromptInputMessage) => {
    const prompt = message.text.trim();
    if (!prompt || chatStatus === "submitted" || chatStatus === "streaming") {
      return;
    }

    setChatStatus("submitted");
    setErrorMessage(null);
    setFollowupSuggestions([]);

    const optimisticUserMessage = createOptimisticUserMessage(prompt);
    const optimisticAssistantPlaceholder = createOptimisticAssistantPlaceholder();
    setMessages((previousMessages) => [
      ...previousMessages,
      optimisticUserMessage,
      optimisticAssistantPlaceholder,
    ]);

    let activeThreadId = currentThreadId;
    if (!activeThreadId) {
      try {
        const createdThread = await createDeerFlowStandaloneThread({
          title: deriveThreadTitleFromPrompt(prompt),
          model_id: selectedModelId || undefined,
        });
        activeThreadId = createdThread.thread_id;
        streamingThreadIdRef.current = activeThreadId;
        setThreads((previousThreads) => [createdThread, ...previousThreads]);
        setCurrentThreadId(createdThread.thread_id);
      } catch (error) {
        console.error("[DeerFlowChatTestPage] Failed to create thread before sending:", error);
        setErrorMessage("Failed to create Deer-Flow thread.");
        setChatStatus("error");
        return;
      }
    } else {
      streamingThreadIdRef.current = activeThreadId;
    }

    let latestThreadId = activeThreadId;
    let receivedIncrementalMessage = false;
    let shouldKeepErrorStatus = false;
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      for await (const event of streamDeerFlowStandaloneChat(
        {
          thread_id: latestThreadId ?? undefined,
          message: prompt,
          context: {
            mode,
            reasoning_effort: REASONING_EFFORT_BY_MODE[mode],
          },
          model_id: selectedModelId || undefined,
        },
        abortController.signal
      )) {
        if (event.event === "metadata") {
          const metadata = event.data as { thread_id: string };
          latestThreadId = metadata.thread_id;
          streamingThreadIdRef.current = latestThreadId;
          setCurrentThreadId(metadata.thread_id);
          continue;
        }

        if (event.event === "error") {
          const message =
            typeof event.data === "object" &&
            event.data !== null &&
            "message" in event.data &&
            typeof event.data.message === "string"
              ? event.data.message
              : "Deer-Flow stream failed.";
          throw new Error(message);
        }

        if (event.event === "messages" || event.event === "messages-tuple") {
          const serializedMessage = normalizeMessageEventPayload(event.data);
          if (!serializedMessage) {
            continue;
          }

          receivedIncrementalMessage = true;
          setChatStatus("streaming");
          setMessages((previousMessages) => applyStreamMessageChunk(previousMessages, serializedMessage));
          continue;
        }

        if (event.event === "values" && !receivedIncrementalMessage) {
          setChatStatus("streaming");
          setMessages((previousMessages) =>
            upsertAssistantDraftFromValues(previousMessages, event.data as DeerFlowValuesPayload)
          );
        }

      }

      if (latestThreadId) {
        const persistedMessages = await loadMessages(latestThreadId);
        await loadThreads();
        setFollowupSuggestions(buildFollowupSuggestions(persistedMessages));
      }
      setChatStatus("ready");
    } catch (error) {
      console.error("[DeerFlowChatTestPage] Failed to stream chat:", error);
      const isAbortError =
        error instanceof DOMException && error.name === "AbortError";
      if (!isAbortError) {
        setErrorMessage(error instanceof Error ? error.message : "Failed to stream Deer-Flow reply.");
        setChatStatus("error");
        shouldKeepErrorStatus = true;
      }
      setMessages((previousMessages) => finalizeStreamingMessages(previousMessages));
      if (latestThreadId && !isAbortError) {
        await loadMessages(latestThreadId);
        setFollowupSuggestions([]);
      }
    } finally {
      abortControllerRef.current = null;
      streamingThreadIdRef.current = null;
      if (!shouldKeepErrorStatus) {
        setChatStatus("ready");
      }
    }
  }, [
    chatStatus,
    currentThreadId,
    loadMessages,
    loadThreads,
    mode,
    selectedModelId,
  ]);

  const showMessageTimeline = messages.length > 0 || isLoadingMessages;

  return (
    <DeerFlowThreadProvider value={{ thread: threadState }}>
      <div className="flex h-screen w-full overflow-hidden bg-[#f9f9f7] text-slate-900">
          <aside
            className={cn(
              "border-r border-black/10 bg-[#f1f0e8] transition-all duration-300",
              historyOpen ? "w-[272px]" : "w-0 overflow-hidden"
            )}
          >
            <div className="flex h-full flex-col">
              <div className="flex items-center justify-between border-b border-black/10 px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-black text-white">
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold">DeerFlow</div>
                    <div className="text-[11px] text-slate-500">Workspace</div>
                  </div>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setHistoryOpen(false)}>
                  <ChevronDown className="h-4 w-4 rotate-90" />
                </Button>
              </div>

              <div className="border-b border-black/10 px-4 py-3">
                <Button
                  className="h-10 w-full justify-center rounded-xl bg-black text-white hover:bg-black/90"
                  onClick={() => void handleCreateThread()}
                >
                  <MessageSquarePlus className="mr-2 h-4 w-4" />
                  新对话
                </Button>
              </div>

              <div className="border-b border-black/10 px-3 py-3">
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    className="flex items-center gap-2 rounded-xl bg-white px-3 py-2 text-sm font-medium text-slate-900 shadow-sm"
                  >
                    <Bot className="h-4 w-4" />
                    对话
                  </button>
                  <button
                    type="button"
                    className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-500"
                  >
                    <Compass className="h-4 w-4" />
                    智能体
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between px-4 pb-2 pt-3 text-[11px] uppercase tracking-[0.18em] text-slate-500">
                <span>Chats</span>
                <Button
                  className="h-7 w-7 rounded-lg"
                  size="icon"
                  type="button"
                  variant="ghost"
                  onClick={() => void loadThreads()}
                >
                  <RefreshCw className={cn("h-3.5 w-3.5", isLoadingThreads && "animate-spin")} />
                </Button>
              </div>

              <div className="flex-1 overflow-y-auto px-3 pb-3">
                {threads.map((thread) => {
                  const isActive = thread.thread_id === currentThreadId;
                  return (
                    <button
                      key={thread.thread_id}
                      type="button"
                      onClick={() => setCurrentThreadId(thread.thread_id)}
                      className={cn(
                        "mb-2 flex w-full items-start justify-between rounded-2xl px-3 py-3 text-left transition-colors",
                        isActive
                          ? "bg-black text-white shadow-sm"
                          : "bg-transparent hover:bg-white/80"
                      )}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-medium leading-6">
                          {thread.title?.trim() || "Untitled"}
                        </div>
                        <div className={cn("mt-1 text-xs", isActive ? "text-slate-300" : "text-slate-500")}>
                          {thread.message_count} messages
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          void handleDeleteThread(thread.thread_id);
                        }}
                        className={cn(
                          "ml-3 rounded-lg p-1 transition-colors",
                          isActive ? "hover:bg-white/10" : "hover:bg-slate-100"
                        )}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </button>
                  );
                })}
              </div>
            </div>
          </aside>

          <main className="relative flex min-w-0 flex-1 flex-col bg-[#f9f9f7]">
            <header className="flex h-14 shrink-0 items-center justify-between bg-[#f9f9f7]/95 px-4 backdrop-blur-sm">
              <div className="flex items-center gap-3">
                <Button variant="ghost" size="icon" onClick={() => setHistoryOpen((value) => !value)}>
                  <PanelLeft className="h-4 w-4" />
                </Button>
                <div>
                  <div className="text-sm font-semibold">
                    {currentThread?.title?.trim() || "新对话"}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <DeerFlowStatusPill status={chatStatus} />
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <DeerFlowArtifactTrigger />
              </div>
            </header>

            <DeerFlowChatBox>
              <div
                className={cn(
                  "flex size-full min-h-0 flex-col",
                  !showMessageTimeline && "justify-center"
                )}
              >
                {showMessageTimeline ? (
                  <DeerFlowMessageList
                    messages={messages}
                    isLoading={isLoadingMessages}
                    status={chatStatus}
                    threadId={currentThreadId ?? undefined}
                  />
                ) : null}
                <div
                  className={cn(
                    "shrink-0 bg-[#f9f9f7] px-6 py-6",
                    !showMessageTimeline && "flex flex-1 flex-col justify-center"
                  )}
                >
                  <div className="mx-auto w-full max-w-3xl">
                    {threadTodos.length > 0 ? (
                      <div className={DEERFLOW_INPUT_OUTER_CARD_CLASSNAME}>
                        <DeerFlowTodoList combinedCardStack todos={threadTodos} hidden={false} />
                        <DeerFlowInputBox
                          isDockedWithTodosAbove
                          autoFocus={chatStatus === "ready" && messages.length === 0}
                          disabled={false}
                          followupSuggestions={followupSuggestions}
                          isFollowupsLoading={chatStatus === "streaming" && followupSuggestions.length === 0}
                          isNewThread={messages.length === 0}
                          isModelsLoading={isLoadingModels}
                          mode={mode}
                          models={modelOptions}
                          onModeChange={setMode}
                          selectedModelId={selectedModelId}
                          onModelChange={setSelectedModelId}
                          onDismissFollowups={() => setFollowupSuggestions([])}
                          onFollowupClick={(suggestion) =>
                            setFollowupSuggestions((previousSuggestions) =>
                              previousSuggestions.filter((item) => item !== suggestion)
                            )
                          }
                          onStop={() => void handleStopStreaming()}
                          status={chatStatus}
                          onSubmit={handleSubmit}
                        />
                      </div>
                    ) : (
                      <DeerFlowInputBox
                        autoFocus={chatStatus === "ready" && messages.length === 0}
                        disabled={false}
                        followupSuggestions={followupSuggestions}
                        isFollowupsLoading={chatStatus === "streaming" && followupSuggestions.length === 0}
                        isNewThread={messages.length === 0}
                        isModelsLoading={isLoadingModels}
                        mode={mode}
                        models={modelOptions}
                        onModeChange={setMode}
                        selectedModelId={selectedModelId}
                        onModelChange={setSelectedModelId}
                        onDismissFollowups={() => setFollowupSuggestions([])}
                        onFollowupClick={(suggestion) =>
                          setFollowupSuggestions((previousSuggestions) =>
                            previousSuggestions.filter((item) => item !== suggestion)
                          )
                        }
                        onStop={() => void handleStopStreaming()}
                        status={chatStatus}
                        onSubmit={handleSubmit}
                      />
                    )}

                    {errorMessage ? (
                      <div className="mt-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                        {errorMessage}
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            </DeerFlowChatBox>
          </main>
      </div>
    </DeerFlowThreadProvider>
  );
}

/**
 * DeerFlowStatusPill - 顶部工作区状态提示
 */
function DeerFlowStatusPill({ status }: { status: ChatStatus }) {
  if (status === "ready") {
    return (
      <span className="inline-flex items-center gap-1.5 text-[11px] text-slate-500">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
        Ready
      </span>
    );
  }

  if (status === "error") {
    return (
      <span className="inline-flex items-center gap-1.5 text-[11px] text-rose-600">
        <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
        Error
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] text-amber-600">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" />
      {status === "submitted" ? "Submitting" : "Streaming"}
    </span>
  );
}

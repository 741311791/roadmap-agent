"use client";

import type { ChatStatus } from "ai";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Clock,
  BookOpen,
  ChevronRight,
  ArrowLeft,
} from "lucide-react";

import { DeerFlowArtifactTrigger } from "@/components/deerflow-chat-test/deerflow-artifact-trigger";
import { useDeerFlowArtifacts } from "@/components/deerflow-chat-test/deerflow-artifacts-context";
import { DeerFlowChatBox } from "@/components/deerflow-chat-test/deerflow-chat-box";
import { DeerFlowChatProviders } from "@/components/deerflow-chat-test/deerflow-chat-providers";
import {
  DeerFlowInputBox,
  DEERFLOW_INPUT_OUTER_CARD_CLASSNAME,
  DEERFLOW_TEST_INTERACTION_SCOPE_CLASS,
  type DeerFlowInputMode,
} from "@/components/deerflow-chat-test/deerflow-input-box";
import { DeerFlowMessageList } from "@/components/deerflow-chat-test/deerflow-message-list";
import { DeerFlowTodoList } from "@/components/deerflow-chat-test/deerflow-todo-list";
import {
  applyStreamMessageChunk,
  createOptimisticAssistantPlaceholder,
  createOptimisticUserMessage,
  deriveThreadTitleFromPrompt,
  extractArtifactsFromMessages,
  extractTodosFromMessages,
  extractTodosFromStreamValuesPayload,
  extractTodosFromThreadMetadata,
  finalizeStreamingMessages,
  hasTodosFieldInStreamValuesPayload,
  mapPersistedMessage,
  normalizeDeerFlowStreamValuesPayload,
  normalizeMessageEventPayload,
  upsertAssistantDraftFromValues,
  type DeerFlowChatMessage,
  type DeerFlowValuesPayload,
} from "@/components/deerflow-chat-test/deerflow-chat-state";
import {
  DeerFlowThreadProvider,
  type DeerFlowThreadState,
  type DeerFlowTodo,
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

const REASONING_EFFORT_BY_MODE: Record<
  DeerFlowInputMode,
  NonNullable<DeerFlowStandaloneChatContextPayload["reasoning_effort"]>
> = {
  flash: "minimal",
  thinking: "low",
  pro: "medium",
  ultra: "high",
};

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
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [modelOptions, setModelOptions] = useState<MentorModelDto[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  const [mode, setMode] = useState<DeerFlowInputMode>("pro");
  const [streamValuesTodos, setStreamValuesTodos] = useState<DeerFlowTodo[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);
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
    if (streamValuesTodos.length > 0) return streamValuesTodos;
    const todosFromMetadata = extractTodosFromThreadMetadata(currentThread?.metadata);
    if (todosFromMetadata.length > 0) return todosFromMetadata;
    return extractTodosFromMessages(messages);
  }, [currentThread?.metadata, messages, streamValuesTodos]);

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
    setStreamValuesTodos([]);
  }, [currentThreadId]);

  useEffect(() => {
    let isCancelled = false;
    async function loadModels() {
      try {
        setIsLoadingModels(true);
        const response = await listDeerFlowStandaloneModels();
        if (isCancelled) return;
        setModelOptions(response.items);
        setSelectedModelId(
          (previousModelId) =>
            previousModelId || response.default_model_id || response.items[0]?.model_id || ""
        );
      } catch (error) {
        if (!isCancelled) console.error("[DeerFlowChatTestPage] Failed to load models:", error);
      } finally {
        if (!isCancelled) setIsLoadingModels(false);
      }
    }
    void loadModels();
    return () => { isCancelled = true; };
  }, []);

  useEffect(() => {
    if (!currentThreadId) {
      setMessages([]);
      return;
    }
    if (streamingThreadIdRef.current === currentThreadId) return;
    void loadMessages(currentThreadId);
  }, [currentThreadId, loadMessages]);

  useEffect(() => {
    setArtifacts(threadArtifacts);
  }, [setArtifacts, threadArtifacts]);

  useEffect(() => {
    if (currentThread?.model_id) setSelectedModelId(currentThread.model_id);
  }, [currentThread?.model_id]);

  useEffect(() => {
    const selectedModel = modelOptions.find((model) => model.model_id === selectedModelId) ?? modelOptions[0];
    const supportsThinking = selectedModel?.supports_thinking ?? false;
    if (!supportsThinking && mode !== "flash") setMode("flash");
  }, [mode, modelOptions, selectedModelId]);

  const handleStopStreaming = useCallback(async () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    streamingThreadIdRef.current = null;
    setChatStatus("ready");
    setStreamValuesTodos([]);
    setMessages((previousMessages) => finalizeStreamingMessages(previousMessages));

    if (currentThreadId) {
      await loadMessages(currentThreadId).catch(() => undefined);
    }
  }, [currentThreadId, loadMessages]);

  const handleSubmit = useCallback(async (message: PromptInputMessage) => {
    const prompt = message.text.trim();
    if (!prompt || chatStatus === "submitted" || chatStatus === "streaming") return;

    setChatStatus("submitted");
    setErrorMessage(null);
    setStreamValuesTodos([]);

    const optimisticUserMessage = createOptimisticUserMessage(prompt);
    const optimisticAssistantPlaceholder = createOptimisticAssistantPlaceholder();
    setMessages((prev) => [...prev, optimisticUserMessage, optimisticAssistantPlaceholder]);

    let activeThreadId = currentThreadId;
    if (!activeThreadId) {
      try {
        const createdThread = await createDeerFlowStandaloneThread({
          title: deriveThreadTitleFromPrompt(prompt),
          model_id: selectedModelId || undefined,
        });
        activeThreadId = createdThread.thread_id;
        streamingThreadIdRef.current = activeThreadId;
        setThreads((prev) => [createdThread, ...prev]);
        setCurrentThreadId(createdThread.thread_id);
      } catch (error) {
        console.error("Failed to create thread before sending:", error);
        setErrorMessage("Failed to create Deer-Flow thread.");
        setChatStatus("error");
        return;
      }
    } else {
      streamingThreadIdRef.current = activeThreadId;
    }

    let latestThreadId = activeThreadId;
    let shouldKeepErrorStatus = false;
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      for await (const event of streamDeerFlowStandaloneChat(
        {
          thread_id: latestThreadId ?? undefined,
          message: prompt,
          context: { mode, reasoning_effort: REASONING_EFFORT_BY_MODE[mode] },
          model_id: selectedModelId || undefined,
        },
        abortController.signal
      )) {
        const sseEvent = typeof event.event === "string" ? event.event.trim().toLowerCase() : "";

        if (sseEvent === "values" && event.data && hasTodosFieldInStreamValuesPayload(event.data)) {
          setStreamValuesTodos(extractTodosFromStreamValuesPayload(event.data));
        }

        if (event.event === "metadata") {
          const metadata = event.data as { thread_id: string };
          latestThreadId = metadata.thread_id;
          streamingThreadIdRef.current = latestThreadId;
          setCurrentThreadId(metadata.thread_id);
          continue;
        }

        if (event.event === "error") {
          const message = typeof event.data === "object" && event.data !== null && "message" in event.data && typeof event.data.message === "string"
              ? event.data.message
              : "Deer-Flow stream failed.";
          throw new Error(message);
        }

        if (sseEvent === "messages" || sseEvent === "messages-tuple") {
          const serializedMessage = normalizeMessageEventPayload(event.data);
          if (!serializedMessage) continue;

          setChatStatus("streaming");
          setMessages((prev) => applyStreamMessageChunk(prev, serializedMessage));
          continue;
        }

        if (sseEvent === "values") {
          const valuesPayload = normalizeDeerFlowStreamValuesPayload(event.data) ?? (event.data as DeerFlowValuesPayload);
          setChatStatus("streaming");
          setMessages((prev) => upsertAssistantDraftFromValues(prev, valuesPayload));
        }
      }

      if (latestThreadId) {
        await loadMessages(latestThreadId);
        await loadThreads();
      }
      setStreamValuesTodos([]);
      setChatStatus("ready");
    } catch (error) {
      const isAbortError = error instanceof DOMException && error.name === "AbortError";
      if (!isAbortError) {
        setErrorMessage(error instanceof Error ? error.message : "Failed to stream Deer-Flow reply.");
        setChatStatus("error");
        shouldKeepErrorStatus = true;
      }
      setMessages((prev) => finalizeStreamingMessages(prev));
      if (latestThreadId && !isAbortError) await loadMessages(latestThreadId);
      setStreamValuesTodos([]);
    } finally {
      abortControllerRef.current = null;
      streamingThreadIdRef.current = null;
      if (!shouldKeepErrorStatus) setChatStatus("ready");
    }
  }, [chatStatus, currentThreadId, loadMessages, loadThreads, mode, selectedModelId]);

  const showMessageTimeline = messages.length > 0 || isLoadingMessages;

  return (
    <DeerFlowThreadProvider value={{ thread: threadState }}>
      <div
        className={cn(
          DEERFLOW_TEST_INTERACTION_SCOPE_CLASS,
          "flex h-screen w-full overflow-hidden bg-[#fafaf9] text-slate-900"
        )}
      >
        <main className="relative flex min-w-0 flex-1 flex-col bg-[#fafaf9]">
          
          {/* Header for Chat View */}
          {showMessageTimeline && (
            <header className="flex h-14 shrink-0 items-center justify-between bg-[#fafaf9]/95 px-4 backdrop-blur-md border-b border-black/5 z-10">
              <div className="flex items-center gap-3">
                <Button 
                  variant="ghost" 
                  size="icon" 
                  onClick={() => setCurrentThreadId(null)}
                  className="rounded-full hover:bg-slate-100"
                >
                  <ArrowLeft className="h-5 w-5 text-slate-600" />
                </Button>
                <div>
                  <div className="text-[15px] font-semibold text-slate-900">
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
          )}

          <DeerFlowChatBox>
            <div className={cn("flex size-full min-h-0 flex-col", !showMessageTimeline && "justify-center pt-8 overflow-y-auto")}>
              
              {/* Home View Header (Centered) */}
              {!showMessageTimeline && (
                <div className="flex flex-col items-center justify-center px-4 w-full max-w-4xl mx-auto mt-10 md:mt-16 animate-fade-in-up">
                  <div className="text-center mb-8">
                    <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-4 flex items-center justify-center gap-[2px] font-serif">
                      <span className="text-slate-900">Fast</span>
                      <span className="text-sage-600">Learning</span>
                    </h1>
                    <p className="text-slate-500 text-base md:text-[17px] tracking-wide">
                      Your AI-native workspace for accelerated mastery.
                    </p>
                  </div>
                </div>
              )}

              {showMessageTimeline && (
                <DeerFlowMessageList
                  messages={messages}
                  isLoading={isLoadingMessages}
                  status={chatStatus}
                  threadId={currentThreadId ?? undefined}
                />
              )}

              <div className={cn("shrink-0 px-4 sm:px-6", showMessageTimeline ? "py-6 bg-[#fafaf9]" : "flex flex-col items-center w-full pb-20")}>
                <div className={cn("w-full transition-all duration-500", showMessageTimeline ? "max-w-3xl mx-auto" : "max-w-[720px]")}>
                  
                  {/* Input Box Wrapper */}
                  <div className={cn("relative z-20", !showMessageTimeline && "shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-[24px]")}>
                    {threadTodos.length > 0 && showMessageTimeline ? (
                      <div className={DEERFLOW_INPUT_OUTER_CARD_CLASSNAME}>
                        <DeerFlowTodoList combinedCardStack todos={threadTodos} hidden={false} />
                        <DeerFlowInputBox
                          isDockedWithTodosAbove
                          autoFocus={chatStatus === "ready" && messages.length === 0}
                          disabled={false}
                          isNewThread={!showMessageTimeline}
                          isModelsLoading={isLoadingModels}
                          mode={mode}
                          models={modelOptions}
                          onModeChange={setMode}
                          selectedModelId={selectedModelId}
                          onModelChange={setSelectedModelId}
                          onStop={() => void handleStopStreaming()}
                          status={chatStatus}
                          onSubmit={handleSubmit}
                        />
                      </div>
                    ) : (
                      <DeerFlowInputBox
                        autoFocus={chatStatus === "ready" && messages.length === 0}
                        disabled={false}
                        isNewThread={!showMessageTimeline}
                        isModelsLoading={isLoadingModels}
                        mode={mode}
                        models={modelOptions}
                        onModeChange={setMode}
                        selectedModelId={selectedModelId}
                        onModelChange={setSelectedModelId}
                        onStop={() => void handleStopStreaming()}
                        status={chatStatus}
                        onSubmit={handleSubmit}
                      />
                    )}
                  </div>

                  {errorMessage && (
                    <div className="mt-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 animate-fade-in-up">
                      {errorMessage}
                    </div>
                  )}

                  {/* Home View - Resume Learning Cards */}
                  {!showMessageTimeline && threads.length > 0 && (
                    <div className="w-full mt-16 animate-fade-in-up" style={{ animationDelay: "150ms" }}>
                      <div className="flex items-center justify-between mb-5 px-1">
                        <div className="flex items-center gap-2.5 text-slate-900 font-semibold">
                          <Clock className="w-5 h-5 text-sage-600" />
                          <span className="text-[15px]">Resume Learning</span>
                        </div>
                        <button className="text-[13px] text-sage-600 font-medium hover:text-slate-900 transition-colors">
                          View All
                        </button>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {threads.slice(0, 4).map((thread) => (
                          <button
                            key={thread.thread_id}
                            onClick={() => setCurrentThreadId(thread.thread_id)}
                            className="group flex items-center p-4 bg-white rounded-[20px] border border-slate-200/60 shadow-[0_2px_8px_rgb(0,0,0,0.02)] hover:shadow-[0_8px_24px_rgb(0,0,0,0.06)] hover:border-sage-200 transition-all duration-300 text-left"
                          >
                            <div className="w-11 h-11 rounded-xl bg-sage-50 text-sage-600 flex items-center justify-center shrink-0 mr-4 group-hover:scale-105 transition-transform duration-300">
                              <BookOpen className="w-5 h-5" />
                            </div>
                            <div className="flex-1 min-w-0 pr-2">
                              <h3 className="font-semibold text-[15px] text-slate-900 truncate mb-1.5 group-hover:text-sage-700 transition-colors">
                                {thread.title?.trim() || "Untitled Session"}
                              </h3>
                              <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                                <div className="bg-sage-500 h-full w-[0%]" />
                              </div>
                              <p className="text-[10px] font-bold text-slate-400 mt-2 uppercase tracking-wider">
                                0% COMPLETE
                              </p>
                            </div>
                            <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-sage-600 group-hover:translate-x-0.5 transition-all duration-300" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                </div>
              </div>
            </div>
          </DeerFlowChatBox>
        </main>
      </div>
    </DeerFlowThreadProvider>
  );
}

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

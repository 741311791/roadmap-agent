"use client";

import type { DeerFlowMentorMessageDto } from "@/components/mentor/mentor-deerflow-api";
import type { DeerFlowTodo } from "@/components/deerflow-chat-test/deerflow-thread-context";

/**
 * Deer-Flow 聊天文本片段。
 */
export interface DeerFlowChatMessagePartText {
  type: "text";
  text: string;
}

/**
 * Deer-Flow 思考片段。
 */
export interface DeerFlowChatMessagePartThinking {
  type: "thinking";
  text: string;
}

/**
 * Deer-Flow 工具片段。
 */
export interface DeerFlowChatMessagePartTool {
  type: "tool";
  name: string;
  toolCallId?: string;
  arguments?: Record<string, unknown>;
  state?: "running" | "completed";
  result?: string;
  isError?: boolean;
}

/**
 * Deer-Flow 可视消息片段。
 */
export type DeerFlowChatMessagePart =
  | DeerFlowChatMessagePartText
  | DeerFlowChatMessagePartThinking
  | DeerFlowChatMessagePartTool;

/**
 * Deer-Flow 测试页消息结构。
 */
export interface DeerFlowChatMessage {
  id: string;
  role: "user" | "assistant";
  parts: DeerFlowChatMessagePart[];
  createdAt: string;
  isStreaming?: boolean;
}

function normalizeTodoStatus(status: unknown): string {
  if (typeof status !== "string" || !status.trim()) {
    return "pending";
  }

  const normalized = status.trim().toLowerCase();
  if (normalized === "done" || normalized === "complete") {
    return "completed";
  }

  return status.trim();
}

function normalizeTodoItem(todo: unknown): DeerFlowTodo | null {
  if (!todo || typeof todo !== "object") {
    return null;
  }

  const candidate = todo as Record<string, unknown>;
  // 上游与模型可能使用 content / title / task 等键表示待办正文，需一并兼容。
  const content =
    (typeof candidate.content === "string" && candidate.content.trim()) ||
    (typeof candidate.title === "string" && candidate.title.trim()) ||
    (typeof candidate.task === "string" && candidate.task.trim()) ||
    (typeof candidate.description === "string" && candidate.description.trim()) ||
    "";
  if (!content) {
    return null;
  }

  return {
    id:
      typeof candidate.id === "string" && candidate.id.trim()
        ? candidate.id
        : `todo-${content}`,
    content,
    status: normalizeTodoStatus(candidate.status),
  };
}

/**
 * 解析 write_todos 等工具载荷中的 todo 列表（与后端多种形态兼容）。
 */
export function parseTodosPayload(value: unknown): DeerFlowTodo[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => normalizeTodoItem(item))
      .filter((item): item is DeerFlowTodo => item !== null);
  }

  if (typeof value === "string") {
    try {
      return parseTodosPayload(JSON.parse(value));
    } catch {
      return [];
    }
  }

  if (value && typeof value === "object") {
    const candidate = value as Record<string, unknown>;
    if (Array.isArray(candidate.todos)) {
      return parseTodosPayload(candidate.todos);
    }
  }

  return [];
}

/**
 * Deer-Flow 流式阶段。
 */
export type DeerFlowStreamingPhase = "idle" | "submitted" | "streaming" | "error";

/**
 * Deer-Flow 序列化工具调用。
 */
export interface DeerFlowSerializedToolCall {
  id?: string;
  name?: string;
  args?: Record<string, unknown> | string;
  /** 部分上游序列化使用 `arguments` 字段名 */
  arguments?: unknown;
  /** OpenAI Chat Completions 形态：参数在 function.arguments（JSON 字符串） */
  function?: {
    name?: string;
    arguments?: unknown;
  };
}

/**
 * 从任意上游 tool_call 对象提取原始参数字段（未做 JSON 解析）。
 * 兼容 LangChain `args`、部分网关的 `arguments`、以及 OpenAI `function.arguments`。
 *
 * Args:
 *   toolCall: SSE / state 中的单条 tool_call
 *
 * Returns:
 *   dict、JSON 字符串或 undefined
 */
export function extractDeerFlowToolCallArguments(toolCall: unknown): unknown {
  if (!toolCall || typeof toolCall !== "object") {
    return undefined;
  }

  const tc = toolCall as DeerFlowSerializedToolCall & Record<string, unknown>;
  if (tc.args !== undefined) {
    return tc.args;
  }
  if (tc.arguments !== undefined) {
    return tc.arguments;
  }
  const fn = tc.function;
  if (fn && typeof fn === "object" && !Array.isArray(fn)) {
    const f = fn as { arguments?: unknown };
    if (f.arguments !== undefined) {
      return f.arguments;
    }
  }
  return undefined;
}

/**
 * 从序列化 tool_call 中取出参数载荷（供内部 normalize 使用）。
 */
function pickSerializedToolCallArgs(toolCall: DeerFlowSerializedToolCall): unknown {
  return extractDeerFlowToolCallArguments(toolCall);
}

/**
 * Deer-Flow 序列化消息。
 */
export interface DeerFlowSerializedMessage {
  id?: string;
  type?: string;
  content?: unknown;
  additional_kwargs?: {
    reasoning_content?: string;
  };
  tool_calls?: DeerFlowSerializedToolCall[];
  /** LangChain 流式片段：args 为 JSON 字符串分片，需按 id 拼接 */
  tool_call_chunks?: unknown;
  tool_call_id?: string;
  name?: string;
  status?: string;
}

/**
 * Deer-Flow values 事件载荷。
 */
export interface DeerFlowValuesPayload {
  messages?: DeerFlowSerializedMessage[];
  title?: string;
  /** LangGraph 线程状态中的待办列表（与官方 thread.values.todos 一致） */
  todos?: unknown;
}

/**
 * 将 LangGraph / 网关下发的 values SSE 数据规范为扁平快照（兼容外层再包一层 `values`）。
 *
 * Args:
 *   data: 单帧 `values` 事件的 JSON 载荷
 *
 * Returns:
 *   扁平后的快照；无法识别时返回 null
 */
export function normalizeDeerFlowStreamValuesPayload(data: unknown): DeerFlowValuesPayload | null {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return null;
  }

  const obj = data as Record<string, unknown>;
  if ("messages" in obj || "todos" in obj || "title" in obj) {
    return obj as DeerFlowValuesPayload;
  }

  const inner = obj.values;
  if (inner && typeof inner === "object" && !Array.isArray(inner)) {
    return inner as DeerFlowValuesPayload;
  }

  return null;
}

/**
 * 从 Deer-Flow content 中提取纯文本。
 */
export function extractSerializedMessageText(content: unknown): string {
  if (typeof content === "string") {
    return content;
  }

  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (typeof part === "string") {
          return part;
        }

        if (
          typeof part === "object" &&
          part !== null &&
          "text" in part &&
          typeof part.text === "string"
        ) {
          return part.text;
        }

        return "";
      })
      .join("");
  }

  return "";
}

/**
 * 将连续多条助手消息合并为一条时间线（对齐官方对同一轮 LangGraph 多段 ai 消息的聚合展示）。
 *
 * Args:
 *   messages: 原始消息序列（含持久化加载出的多条 assistant）
 *
 * Returns:
 *   合并后的消息序列；用户消息之间的助手块各自合并
 */
export function coalesceConsecutiveAssistantMessages(
  messages: DeerFlowChatMessage[]
): DeerFlowChatMessage[] {
  const result: DeerFlowChatMessage[] = [];

  for (const message of messages) {
    if (message.role !== "assistant") {
      result.push(message);
      continue;
    }

    const previous = result[result.length - 1];
    if (previous?.role === "assistant") {
      previous.parts = [...previous.parts, ...message.parts.map((part) => ({ ...part }))];
      previous.isStreaming = Boolean(previous.isStreaming || message.isStreaming);
      const previousTime = new Date(previous.createdAt).getTime();
      const currentTime = new Date(message.createdAt).getTime();
      if (currentTime > previousTime) {
        previous.createdAt = message.createdAt;
      }
      continue;
    }

    result.push({
      ...message,
      parts: [...message.parts],
    });
  }

  return result;
}

/**
 * extractMessagePlainText - 提取消息中的纯文本内容
 */
export function extractMessagePlainText(message: DeerFlowChatMessage): string {
  return message.parts
    .filter((part): part is DeerFlowChatMessagePartText => part.type === "text")
    .map((part) => part.text)
    .join("")
    .trim();
}

/**
 * extractTodosFromMessages - 从消息中的 write_todos 工具调用提取 to-do 列表
 */
export function extractTodosFromMessages(messages: DeerFlowChatMessage[]): DeerFlowTodo[] {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    for (const part of message.parts) {
      if (part.type !== "tool" || part.name !== "write_todos") {
        continue;
      }

      const todosFromArgs = parseTodosPayload(part.arguments);
      if (todosFromArgs.length > 0) {
        return todosFromArgs;
      }

      const todosFromResult = parseTodosPayload(part.result);
      if (todosFromResult.length > 0) {
        return todosFromResult;
      }
    }
  }

  return [];
}

/**
 * extractTodosFromThreadMetadata - 从线程元数据中提取 todos
 */
export function extractTodosFromThreadMetadata(metadata: unknown): DeerFlowTodo[] {
  if (!metadata || typeof metadata !== "object") {
    return [];
  }

  const candidate = metadata as Record<string, unknown>;
  return parseTodosPayload(candidate.todos ?? candidate.todo_list ?? candidate.todoList);
}

/**
 * 判断 LangGraph `values` 流式帧是否携带待办字段（避免用无 todos 键的快照误清空上一帧列表）。
 */
export function hasTodosFieldInStreamValuesPayload(data: unknown): boolean {
  if (!data || typeof data !== "object") {
    return false;
  }

  const root = data as Record<string, unknown>;
  if ("todos" in root || "todo_list" in root || "todoList" in root) {
    return true;
  }

  const nested = root.values;
  if (nested && typeof nested === "object" && !Array.isArray(nested)) {
    const values = nested as Record<string, unknown>;
    return "todos" in values || "todo_list" in values || "todoList" in values;
  }

  return false;
}

/**
 * 从 `values` SSE 载荷解析线程级 todos（与官方 thread.values.todos 对齐，兼容一层 values 包裹）。
 */
export function extractTodosFromStreamValuesPayload(data: unknown): DeerFlowTodo[] {
  if (!data || typeof data !== "object") {
    return [];
  }

  const root = data as Record<string, unknown>;
  if ("todos" in root || "todo_list" in root || "todoList" in root) {
    return parseTodosPayload(root.todos ?? root.todo_list ?? root.todoList);
  }

  const nested = root.values;
  if (nested && typeof nested === "object" && !Array.isArray(nested)) {
    const values = nested as Record<string, unknown>;
    if ("todos" in values || "todo_list" in values || "todoList" in values) {
      return parseTodosPayload(values.todos ?? values.todo_list ?? values.todoList);
    }
  }

  return [];
}

/**
 * 归一化 Deer-Flow 消息类型。
 */
function normalizeSerializedMessageType(type: string | undefined): DeerFlowSerializedMessage["type"] {
  if (!type) {
    return undefined;
  }

  const normalizedType = type.toLowerCase();
  if (normalizedType === "human" || normalizedType.includes("human")) {
    return "human";
  }
  if (normalizedType === "ai" || normalizedType.includes("ai")) {
    return "ai";
  }
  if (normalizedType === "tool" || normalizedType.includes("tool")) {
    return "tool";
  }
  if (normalizedType === "system" || normalizedType.includes("system")) {
    return "system";
  }

  return type;
}

/**
 * 追加文本片段。
 */
function mergeStreamText(existingText: string, incomingText: string): string {
  if (!existingText) {
    return incomingText;
  }

  if (!incomingText || incomingText === existingText) {
    return existingText;
  }

  // Deer-Flow 有时返回累计文本前缀，有时返回纯增量，这里统一做兼容合并。
  if (incomingText.startsWith(existingText)) {
    return incomingText;
  }

  if (existingText.startsWith(incomingText) || existingText.endsWith(incomingText)) {
    return existingText;
  }

  const maxOverlap = Math.min(existingText.length, incomingText.length);
  for (let overlap = maxOverlap; overlap > 0; overlap -= 1) {
    if (existingText.slice(-overlap) === incomingText.slice(0, overlap)) {
      return `${existingText}${incomingText.slice(overlap)}`;
    }
  }

  return `${existingText}${incomingText}`;
}

function appendTextPart(parts: DeerFlowChatMessagePart[], text: string): void {
  if (!text) {
    return;
  }

  const lastPart = parts.at(-1);
  if (lastPart?.type === "text") {
    lastPart.text = mergeStreamText(lastPart.text, text);
    return;
  }

  parts.push({
    type: "text",
    text,
  });
}

/**
 * 追加思考片段。
 */
function appendThinkingPart(parts: DeerFlowChatMessagePart[], text: string): void {
  if (!text) {
    return;
  }

  const lastPart = parts.at(-1);
  if (lastPart?.type === "thinking") {
    lastPart.text = mergeStreamText(lastPart.text, text);
    return;
  }

  parts.push({
    type: "thinking",
    text,
  });
}

/**
 * 将上游 tool_call 的 args 规范为对象（部分流式事件会携带 JSON 字符串或未定义）。
 */
function normalizeSerializedToolArgs(raw: unknown): Record<string, unknown> | undefined {
  if (raw === undefined || raw === null) {
    return undefined;
  }

  if (typeof raw === "string") {
    const trimmed = raw.trim();
    if (!trimmed) {
      return undefined;
    }

    try {
      const parsed: unknown = JSON.parse(trimmed);
      if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
    } catch {
      return undefined;
    }

    return undefined;
  }

  if (typeof raw === "object" && !Array.isArray(raw)) {
    return raw as Record<string, unknown>;
  }

  return undefined;
}

/**
 * 合并工具参数：流式阶段常见「先空对象、后补全 query」或「完成事件不带 args」，禁止用空对象覆盖已有字段。
 */
function mergeToolCallArguments(
  previous: Record<string, unknown> | undefined,
  incoming: Record<string, unknown> | undefined
): Record<string, unknown> {
  const base: Record<string, unknown> = { ...(previous ?? {}) };

  if (!incoming || Object.keys(incoming).length === 0) {
    return base;
  }

  for (const [key, value] of Object.entries(incoming)) {
    if (value === undefined) {
      continue;
    }

    if (typeof value === "string") {
      const prevVal = base[key];
      if (typeof prevVal === "string" && prevVal.length > value.length) {
        continue;
      }

      base[key] = value;
      continue;
    }

    if (
      typeof value === "object" &&
      value !== null &&
      !Array.isArray(value) &&
      typeof base[key] === "object" &&
      base[key] !== null &&
      !Array.isArray(base[key])
    ) {
      base[key] = mergeToolCallArguments(
        base[key] as Record<string, unknown>,
        value as Record<string, unknown>
      );
      continue;
    }

    base[key] = value;
  }

  return base;
}

/**
 * 将流式 tool_call_chunks 中同一 tool_call_id 的 args 片段拼接为 JSON 并解析（补全仅含空 args 的 chunk）。
 */
function mergeToolArgsFromToolCallChunks(
  toolCallId: string | undefined,
  chunks: unknown
): Record<string, unknown> | undefined {
  if (!toolCallId || !Array.isArray(chunks)) {
    return undefined;
  }

  const rows = chunks.filter((c): c is Record<string, unknown> => typeof c === "object" && c !== null);
  const matched = rows.filter((c) => String(c.id ?? "") === String(toolCallId));
  if (matched.length === 0) {
    return undefined;
  }

  matched.sort((a, b) => {
    const ia = typeof a.index === "number" ? a.index : Number(a.index ?? 0);
    const ib = typeof b.index === "number" ? b.index : Number(b.index ?? 0);
    return ia - ib;
  });

  const joined = matched
    .map((c) => (typeof c.args === "string" ? c.args : ""))
    .join("")
    .trim();
  if (!joined) {
    return undefined;
  }

  try {
    const parsed: unknown = JSON.parse(joined);
    if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    return undefined;
  }
  return undefined;
}

/**
 * 合并 pick 结果与 tool_call_chunks，供单次 upsertToolPart 使用。
 */
function buildToolCallArgumentsForUpsert(
  toolCall: DeerFlowSerializedToolCall,
  message: DeerFlowSerializedMessage
): unknown {
  const primary = pickSerializedToolCallArgs(toolCall);
  const fromChunks = mergeToolArgsFromToolCallChunks(toolCall.id, message.tool_call_chunks);
  if (!fromChunks) {
    return primary;
  }
  const primaryNorm = normalizeSerializedToolArgs(primary);
  return mergeToolCallArguments(primaryNorm, fromChunks);
}

/**
 * 将工具参数规范为对象（供 Mentor Deer-Flow runtime 等非 chat-state 模块复用）。
 */
export function coerceDeerFlowToolArgumentsToRecord(raw: unknown): Record<string, unknown> {
  return normalizeSerializedToolArgs(raw) ?? {};
}

/**
 * 更新工具片段。
 */
function upsertToolPart(params: {
  parts: DeerFlowChatMessagePart[];
  toolName: string;
  toolCallId?: string;
  /** 未传或传 undefined 表示不改动已有 arguments（用于 tool 完成事件仅带回 result） */
  arguments?: unknown;
  state?: "running" | "completed";
  result?: string;
  isError?: boolean;
}): void {
  const existingIndex = params.parts.findIndex(
    (part) =>
      part.type === "tool" &&
      (part.toolCallId
        ? part.toolCallId === params.toolCallId
        : part.name === params.toolName)
  );

  const existingPart =
    existingIndex >= 0 && params.parts[existingIndex]?.type === "tool"
      ? (params.parts[existingIndex] as DeerFlowChatMessagePartTool)
      : undefined;

  const normalizedIncoming =
    params.arguments !== undefined ? normalizeSerializedToolArgs(params.arguments) : undefined;

  const mergedArguments =
    existingPart !== undefined
      ? mergeToolCallArguments(
          existingPart.arguments,
          normalizedIncoming === undefined ? undefined : normalizedIncoming
        )
      : (normalizedIncoming ?? {});

  const nextPart: DeerFlowChatMessagePartTool = {
    type: "tool",
    name: params.toolName,
    toolCallId: params.toolCallId,
    arguments: mergedArguments,
    state:
      params.state ??
      (params.result !== undefined ? "completed" : existingPart?.state ?? "running"),
    result: params.result !== undefined ? params.result : existingPart?.result,
    isError:
      params.isError !== undefined ? params.isError : (existingPart?.isError ?? false),
  };

  if (existingIndex >= 0) {
    params.parts[existingIndex] = nextPart;
    return;
  }

  params.parts.push(nextPart);
}

/**
 * 构建基于 values 快照的 assistant 草稿。
 */
export function buildAssistantDraftFromValues(
  payload: DeerFlowValuesPayload
): DeerFlowChatMessage | null {
  const messages = Array.isArray(payload.messages) ? payload.messages : [];
  const lastHumanIndex = messages.map((message) => message.type).lastIndexOf("human");
  const visibleMessages = lastHumanIndex >= 0 ? messages.slice(lastHumanIndex + 1) : messages;
  const parts: DeerFlowChatMessagePart[] = [];
  let messageId = "";

  for (const rawMessage of visibleMessages) {
    const message = {
      ...rawMessage,
      type: normalizeSerializedMessageType(rawMessage.type),
    };

    if (message.type === "system") {
      continue;
    }

    if (message.type === "ai") {
      messageId = message.id || messageId;

      const reasoningContent = message.additional_kwargs?.reasoning_content?.trim();
      if (reasoningContent) {
        appendThinkingPart(parts, reasoningContent);
      }

      for (const toolCall of message.tool_calls ?? []) {
        if (!toolCall.name) {
          continue;
        }

        upsertToolPart({
          parts,
          toolName: toolCall.name,
          toolCallId: toolCall.id,
          arguments: buildToolCallArgumentsForUpsert(toolCall, message),
          state: "running",
        });
      }

      const text = extractSerializedMessageText(message.content).trim();
      if (text) {
        appendTextPart(parts, text);
      }
      continue;
    }

    if (message.type === "tool" && message.tool_call_id) {
      upsertToolPart({
        parts,
        toolName: message.name ?? "tool",
        toolCallId: message.tool_call_id,
        state: "completed",
        result: extractSerializedMessageText(message.content).trim(),
        isError: String(message.status || "").toLowerCase() === "error",
      });
    }
  }

  if (parts.length === 0) {
    return null;
  }

  return {
    id: messageId || `assistant-draft-${Date.now()}`,
    role: "assistant",
    parts,
    createdAt: new Date().toISOString(),
    isStreaming: true,
  };
}

/**
 * createOptimisticUserMessage - 创建乐观用户消息
 */
export function createOptimisticUserMessage(prompt: string): DeerFlowChatMessage {
  return {
    id: `user-${Date.now()}`,
    role: "user",
    parts: [
      {
        type: "text",
        text: prompt,
      },
    ],
    createdAt: new Date().toISOString(),
  };
}

/**
 * createOptimisticAssistantPlaceholder - 创建发送后立即出现的助手占位消息
 */
export function createOptimisticAssistantPlaceholder(): DeerFlowChatMessage {
  return {
    id: `assistant-pending-${Date.now()}`,
    role: "assistant",
    parts: [],
    createdAt: new Date().toISOString(),
    isStreaming: true,
  };
}

/**
 * upsertAssistantDraftFromValues - 把 values 草稿同步到当前消息列表
 */
export function upsertAssistantDraftFromValues(
  messages: DeerFlowChatMessage[],
  payload: DeerFlowValuesPayload
): DeerFlowChatMessage[] {
  const draftMessage = buildAssistantDraftFromValues(payload);
  if (!draftMessage) {
    return messages;
  }

  const nextMessages = [...messages];
  const existingIndex = nextMessages.findIndex(
    (message) => message.role === "assistant" && message.id === draftMessage.id
  );
  if (existingIndex >= 0) {
    nextMessages[existingIndex] = draftMessage;
    return nextMessages;
  }

  let lastUserIndex = -1;
  for (let index = nextMessages.length - 1; index >= 0; index -= 1) {
    if (nextMessages[index].role === "user") {
      lastUserIndex = index;
      break;
    }
  }

  let trailingAssistantIndex = -1;
  for (let index = nextMessages.length - 1; index > lastUserIndex; index -= 1) {
    if (nextMessages[index].role === "assistant") {
      trailingAssistantIndex = index;
      break;
    }
  }

  if (trailingAssistantIndex >= 0) {
    nextMessages[trailingAssistantIndex] = {
      ...draftMessage,
      id: nextMessages[trailingAssistantIndex]?.id || draftMessage.id,
    };
  } else {
    nextMessages.push(draftMessage);
  }

  return nextMessages;
}

/**
 * 把后端已持久化消息映射到测试页结构。
 */
export function mapPersistedMessage(message: DeerFlowMentorMessageDto): DeerFlowChatMessage {
  const rawMetadata = (message.message_metadata ?? {}) as Record<string, unknown>;
  const rawParts =
    (rawMetadata.contentParts as Array<Record<string, unknown>> | undefined) ??
    (rawMetadata.content_parts as Array<Record<string, unknown>> | undefined);

  const parts: DeerFlowChatMessagePart[] = [];
  for (const part of rawParts ?? []) {
    if (part.type === "thinking" && typeof part.text === "string") {
      parts.push({
        type: "thinking",
        text: part.text,
      });
      continue;
    }

    if (part.type === "text" && typeof part.text === "string") {
      parts.push({
        type: "text",
        text: part.text,
      });
      continue;
    }

    if (part.type === "tool-call" && typeof part.toolName === "string") {
      parts.push({
        type: "tool",
        name: part.toolName,
        toolCallId:
          typeof part.toolCallId === "string" ? part.toolCallId : undefined,
        arguments:
          typeof part.arguments === "object" && part.arguments !== null
            ? (part.arguments as Record<string, unknown>)
            : undefined,
        state:
          part.state === "completed" || part.state === "running"
            ? part.state
            : undefined,
        result: typeof part.result === "string" ? part.result : undefined,
        isError: part.isError === true,
      });
    }
  }

  if (parts.length === 0) {
    parts.push({
      type: "text",
      text: message.content,
    });
  }

  return {
    id: message.message_id,
    role: message.role === "assistant" ? "assistant" : "user",
    parts,
    createdAt: message.created_at,
  };
}

/**
 * 生成线程标题。
 */
export function deriveThreadTitleFromPrompt(prompt: string): string {
  const normalizedPrompt = prompt.replace(/\s+/g, " ").trim();
  if (!normalizedPrompt) {
    return "New Chat";
  }

  return normalizedPrompt.length > 32
    ? `${normalizedPrompt.slice(0, 32)}...`
    : normalizedPrompt;
}

/**
 * 从 Deer-Flow messages 事件中提取消息块。
 */
export function normalizeMessageEventPayload(data: unknown): DeerFlowSerializedMessage | null {
  if (Array.isArray(data) && data.length > 0) {
    const chunk = data[0];
    if (typeof chunk === "object" && chunk !== null) {
      return {
        ...(chunk as DeerFlowSerializedMessage),
        type: normalizeSerializedMessageType((chunk as DeerFlowSerializedMessage).type),
      };
    }
  }

  if (typeof data === "object" && data !== null) {
    return {
      ...(data as DeerFlowSerializedMessage),
      type: normalizeSerializedMessageType((data as DeerFlowSerializedMessage).type),
    };
  }

  return null;
}

/**
 * 将单个增量消息事件合并到当前消息列表。
 */
export function applyStreamMessageChunk(
  messages: DeerFlowChatMessage[],
  serializedMessage: DeerFlowSerializedMessage
): DeerFlowChatMessage[] {
  if (serializedMessage.type !== "ai" && serializedMessage.type !== "tool") {
    return messages;
  }

  const nextMessages = [...messages];
  let lastUserIndex = -1;
  for (let index = nextMessages.length - 1; index >= 0; index -= 1) {
    if (nextMessages[index].role === "user") {
      lastUserIndex = index;
      break;
    }
  }

  let resolvedAssistantIndex = -1;
  for (let index = nextMessages.length - 1; index >= 0; index -= 1) {
    const message = nextMessages[index];
    if (message.role !== "assistant") {
      continue;
    }
    if (index > lastUserIndex) {
      resolvedAssistantIndex = index;
      break;
    }
  }

  const assistantMessage =
    resolvedAssistantIndex >= 0
      ? {
          ...nextMessages[resolvedAssistantIndex],
          parts: [...nextMessages[resolvedAssistantIndex].parts],
          isStreaming: true,
        }
      : {
          id: serializedMessage.id || `assistant-draft-${Date.now()}`,
          role: "assistant" as const,
          parts: [] as DeerFlowChatMessagePart[],
          createdAt: new Date().toISOString(),
          isStreaming: true,
        };

  if (serializedMessage.id) {
    assistantMessage.id = serializedMessage.id;
  }

  if (serializedMessage.type === "ai") {
    const reasoningContent = serializedMessage.additional_kwargs?.reasoning_content ?? "";
    appendThinkingPart(assistantMessage.parts, reasoningContent);

    for (const toolCall of serializedMessage.tool_calls ?? []) {
      if (!toolCall.name) {
        continue;
      }

      upsertToolPart({
        parts: assistantMessage.parts,
        toolName: toolCall.name,
        toolCallId: toolCall.id,
        arguments: buildToolCallArgumentsForUpsert(toolCall, serializedMessage),
        state: "running",
      });
    }

    appendTextPart(assistantMessage.parts, extractSerializedMessageText(serializedMessage.content));
  }

  if (serializedMessage.type === "tool" && serializedMessage.tool_call_id) {
    upsertToolPart({
      parts: assistantMessage.parts,
      toolName: serializedMessage.name ?? "tool",
      toolCallId: serializedMessage.tool_call_id,
      state: "completed",
      result: extractSerializedMessageText(serializedMessage.content).trim(),
      isError: String(serializedMessage.status || "").toLowerCase() === "error",
    });
  }

  if (resolvedAssistantIndex >= 0) {
    nextMessages[resolvedAssistantIndex] = assistantMessage;
    return nextMessages;
  }

  nextMessages.push(assistantMessage);
  return nextMessages;
}

/**
 * finalizeStreamingMessages - 在流结束或中断后清理 streaming 标记
 */
export function finalizeStreamingMessages(
  messages: DeerFlowChatMessage[]
): DeerFlowChatMessage[] {
  return messages.map((message) =>
    message.isStreaming
      ? {
          ...message,
          isStreaming: false,
        }
      : message
  );
}

/**
 * 从消息片段中提取 present_files 暴露出的产物路径。
 */
export function extractArtifactsFromMessages(
  messages: DeerFlowChatMessage[]
): string[] {
  const artifactSet = new Set<string>();

  for (const message of messages) {
    for (const part of message.parts) {
      if (part.type !== "tool" || part.name !== "present_files") {
        continue;
      }

      const filepaths = part.arguments?.filepaths;
      if (!Array.isArray(filepaths)) {
        continue;
      }

      for (const filepath of filepaths) {
        if (typeof filepath === "string" && filepath.trim()) {
          artifactSet.add(filepath);
        }
      }
    }
  }

  return Array.from(artifactSet);
}

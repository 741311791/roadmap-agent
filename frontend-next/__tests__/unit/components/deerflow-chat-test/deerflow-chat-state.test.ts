import { describe, expect, it } from "vitest";

import {
  applyStreamMessageChunk,
  coerceDeerFlowToolArgumentsToRecord,
  coalesceConsecutiveAssistantMessages,
  createOptimisticAssistantPlaceholder,
  createOptimisticUserMessage,
  extractDeerFlowToolCallArguments,
  extractTodosFromMessages,
  extractTodosFromStreamValuesPayload,
  extractTodosFromThreadMetadata,
  extractArtifactsFromMessages,
  hasTodosFieldInStreamValuesPayload,
  finalizeStreamingMessages,
  normalizeDeerFlowStreamValuesPayload,
  normalizeMessageEventPayload,
  upsertAssistantDraftFromValues,
} from "@/components/deerflow-chat-test/deerflow-chat-state";

describe("extractDeerFlowToolCallArguments", () => {
  it("should read OpenAI function.arguments JSON string", () => {
    const raw = extractDeerFlowToolCallArguments({
      id: "1",
      type: "function",
      function: { name: "read_file", arguments: '{"path":"/tmp/a.md"}' },
    });
    expect(coerceDeerFlowToolArgumentsToRecord(raw)).toEqual({ path: "/tmp/a.md" });
  });
});

describe("normalizeDeerFlowStreamValuesPayload", () => {
  it("should unwrap nested values wrapper", () => {
    const inner = { messages: [{ type: "ai", id: "a1" }] };
    expect(normalizeDeerFlowStreamValuesPayload({ values: inner })).toEqual(inner);
  });

  it("should pass through flat snapshots", () => {
    const flat = { messages: [], todos: [] };
    expect(normalizeDeerFlowStreamValuesPayload(flat)).toEqual(flat);
  });
});

describe("normalizeMessageEventPayload", () => {
  it("should unwrap deer-flow messages tuple payloads", () => {
    const payload = normalizeMessageEventPayload([
      {
        id: "ai-1",
        type: "AIMessageChunk",
        content: "Hello",
      },
      {
        langgraph_node: "agent",
      },
    ]);

    expect(payload).toEqual({
      id: "ai-1",
      type: "ai",
      content: "Hello",
    });
  });
});

describe("applyStreamMessageChunk", () => {
  it("should accumulate text and tool outputs during streaming", () => {
    const afterAiChunk = applyStreamMessageChunk([], {
      id: "ai-1",
      type: "ai",
      content: "Hello",
      additional_kwargs: {
        reasoning_content: "先分析问题。",
      },
      tool_calls: [
        {
          id: "tool-1",
          name: "search_docs",
        },
      ],
    });

    const afterToolChunk = applyStreamMessageChunk(afterAiChunk, {
      id: "tool-msg-1",
      type: "tool",
      tool_call_id: "tool-1",
      name: "search_docs",
      content: "找到 3 条结果",
    });

    const afterFinalText = applyStreamMessageChunk(afterToolChunk, {
      id: "ai-1",
      type: "ai",
      content: " world",
    });

    expect(afterFinalText).toEqual([
      {
        id: "ai-1",
        role: "assistant",
        createdAt: expect.any(String),
        isStreaming: true,
        parts: [
          {
            type: "thinking",
            text: "先分析问题。",
          },
          {
            type: "tool",
            name: "search_docs",
            toolCallId: "tool-1",
            arguments: {},
            state: "completed",
            result: "找到 3 条结果",
            isError: false,
          },
          {
            type: "text",
            text: "Hello world",
          },
        ],
      },
    ]);
  });

  it("should merge tool args across streaming chunks and preserve them when the tool finishes", () => {
    const step1 = applyStreamMessageChunk([], {
      id: "ai-1",
      type: "ai",
      content: "",
      tool_calls: [{ id: "tc-1", name: "web_search" }],
    });

    const step2 = applyStreamMessageChunk(step1, {
      id: "ai-1",
      type: "ai",
      content: "",
      tool_calls: [{ id: "tc-1", name: "web_search", args: { query: "deer-flow github" } }],
    });

    const step3 = applyStreamMessageChunk(step2, {
      id: "tool-msg-1",
      type: "tool",
      tool_call_id: "tc-1",
      name: "web_search",
      content: "[]",
    });

    const toolPart = step3[0]?.parts.find((part) => part.type === "tool");
    expect(toolPart?.arguments).toEqual({ query: "deer-flow github" });
    expect(toolPart?.state).toBe("completed");
  });

  it("should merge read_file path from tool_call_chunks when streaming args are empty", () => {
    const merged = applyStreamMessageChunk([], {
      id: "ai-1",
      type: "ai",
      content: "",
      tool_calls: [{ id: "read_file:0", name: "read_file", args: {} }],
      tool_call_chunks: [
        {
          id: "read_file:0",
          name: "read_file",
          args: '{"path":"/mnt/skills/x.md","description":"load"}',
          index: 0,
          type: "tool_call_chunk",
        },
      ],
    });

    const toolPart = merged[0]?.parts.find((part) => part.type === "tool");
    expect(toolPart?.arguments).toEqual({
      path: "/mnt/skills/x.md",
      description: "load",
    });
  });

  it("should append the streamed assistant reply after the latest user message", () => {
    const streamed = applyStreamMessageChunk(
      [
        {
          id: "assistant-old",
          role: "assistant",
          createdAt: new Date().toISOString(),
          parts: [{ type: "text", text: "Earlier answer" }],
        },
        {
          id: "user-new",
          role: "user",
          createdAt: new Date().toISOString(),
          parts: [{ type: "text", text: "New question" }],
        },
      ],
      {
        id: "assistant-new",
        type: "ai",
        content: "New streamed answer",
      }
    );

    expect(streamed).toEqual([
      {
        id: "assistant-old",
        role: "assistant",
        createdAt: expect.any(String),
        parts: [{ type: "text", text: "Earlier answer" }],
      },
      {
        id: "user-new",
        role: "user",
        createdAt: expect.any(String),
        parts: [{ type: "text", text: "New question" }],
      },
      {
        id: "assistant-new",
        role: "assistant",
        createdAt: expect.any(String),
        isStreaming: true,
        parts: [{ type: "text", text: "New streamed answer" }],
      },
    ]);
  });

  it("should merge cumulative text chunks without duplication", () => {
    const firstChunk = applyStreamMessageChunk([], {
      id: "ai-cumulative",
      type: "ai",
      content: "What is",
    });

    const secondChunk = applyStreamMessageChunk(firstChunk, {
      id: "ai-cumulative",
      type: "ai",
      content: "What is broadcasting",
    });

    const thirdChunk = applyStreamMessageChunk(secondChunk, {
      id: "ai-cumulative",
      type: "ai",
      content: "What is broadcasting in NumPy?",
    });

    expect(thirdChunk).toEqual([
      {
        id: "ai-cumulative",
        role: "assistant",
        createdAt: expect.any(String),
        isStreaming: true,
        parts: [{ type: "text", text: "What is broadcasting in NumPy?" }],
      },
    ]);
  });

  it("should collect present_files artifacts from message parts", () => {
    const artifacts = extractArtifactsFromMessages([
      {
        id: "ai-1",
        role: "assistant",
        createdAt: new Date().toISOString(),
        parts: [
          {
            type: "tool",
            name: "present_files",
            toolCallId: "tool-2",
            arguments: {
              filepaths: ["/mnt/user-data/outputs/report.md", "/mnt/user-data/outputs/plot.png"],
            },
            state: "completed",
          },
        ],
      },
    ]);

    expect(artifacts).toEqual([
      "/mnt/user-data/outputs/report.md",
      "/mnt/user-data/outputs/plot.png",
    ]);
  });
});

describe("stream helpers", () => {
  it("should create optimistic user and assistant placeholder messages", () => {
    const optimisticUser = createOptimisticUserMessage("Explain vectorization");
    const optimisticAssistant = createOptimisticAssistantPlaceholder();

    expect(optimisticUser).toEqual({
      id: expect.stringContaining("user-"),
      role: "user",
      createdAt: expect.any(String),
      parts: [{ type: "text", text: "Explain vectorization" }],
    });

    expect(optimisticAssistant).toEqual({
      id: expect.stringContaining("assistant-pending-"),
      role: "assistant",
      createdAt: expect.any(String),
      parts: [],
      isStreaming: true,
    });
  });

  it("should upsert assistant drafts from values payloads", () => {
    const messages = [
      createOptimisticUserMessage("How does NumPy broadcasting work?"),
      createOptimisticAssistantPlaceholder(),
    ];

    const nextMessages = upsertAssistantDraftFromValues(messages, {
      messages: [
        {
          id: "human-1",
          type: "human",
          content: "How does NumPy broadcasting work?",
        },
        {
          id: "ai-1",
          type: "ai",
          additional_kwargs: {
            reasoning_content: "先识别维度规则。",
          },
          content: "Broadcasting compares shapes from right to left.",
        },
      ],
    });

    expect(nextMessages).toEqual([
      messages[0],
      {
        id: messages[1]?.id,
        role: "assistant",
        createdAt: expect.any(String),
        isStreaming: true,
        parts: [
          {
            type: "thinking",
            text: "先识别维度规则。",
          },
          {
            type: "text",
            text: "Broadcasting compares shapes from right to left.",
          },
        ],
      },
    ]);
  });

  it("should clear streaming flags after stream completion", () => {
    const finalizedMessages = finalizeStreamingMessages([
      {
        id: "assistant-1",
        role: "assistant",
        createdAt: new Date().toISOString(),
        isStreaming: true,
        parts: [{ type: "text", text: "Done." }],
      },
    ]);

    expect(finalizedMessages).toEqual([
      {
        id: "assistant-1",
        role: "assistant",
        createdAt: expect.any(String),
        isStreaming: false,
        parts: [{ type: "text", text: "Done." }],
      },
    ]);
  });

  it("should extract todos from write_todos tool arguments", () => {
    const todos = extractTodosFromMessages([
      {
        id: "assistant-1",
        role: "assistant",
        createdAt: new Date().toISOString(),
        parts: [
          {
            type: "tool",
            name: "write_todos",
            arguments: {
              todos: [
                { id: "todo-1", content: "Research official UI gaps", status: "completed" },
                { id: "todo-2", content: "Restore todo panel", status: "in_progress" },
              ],
            },
            state: "completed",
          },
        ],
      },
    ]);

    expect(todos).toEqual([
      { id: "todo-1", content: "Research official UI gaps", status: "completed" },
      { id: "todo-2", content: "Restore todo panel", status: "in_progress" },
    ]);
  });

  it("should extract todos from thread metadata", () => {
    const todos = extractTodosFromThreadMetadata({
      todos: [
        { id: "todo-1", content: "Open new thread", status: "completed" },
        { id: "todo-2", content: "Send first message", status: "pending" },
      ],
    });

    expect(todos).toEqual([
      { id: "todo-1", content: "Open new thread", status: "completed" },
      { id: "todo-2", content: "Send first message", status: "pending" },
    ]);
  });
});

describe("extractTodosFromStreamValuesPayload", () => {
  it("should read todos from LangGraph values root", () => {
    const todos = extractTodosFromStreamValuesPayload({
      todos: [{ id: "a", content: "One", status: "pending" }],
    });
    expect(todos).toEqual([{ id: "a", content: "One", status: "pending" }]);
  });

  it("should map title to content when content is absent", () => {
    const todos = extractTodosFromStreamValuesPayload({
      todos: [{ id: "b", title: "Titled item", status: "in_progress" }],
    });
    expect(todos).toEqual([{ id: "b", content: "Titled item", status: "in_progress" }]);
  });

  it("should read nested values.todos", () => {
    const todos = extractTodosFromStreamValuesPayload({
      values: { todos: [{ id: "c", content: "Nested", status: "pending" }] },
    });
    expect(todos).toEqual([{ id: "c", content: "Nested", status: "pending" }]);
  });
});

describe("hasTodosFieldInStreamValuesPayload", () => {
  it("returns false when no todos keys", () => {
    expect(hasTodosFieldInStreamValuesPayload({ messages: [] })).toBe(false);
  });

  it("returns true when todos key exists", () => {
    expect(hasTodosFieldInStreamValuesPayload({ todos: [] })).toBe(true);
  });
});

describe("coalesceConsecutiveAssistantMessages", () => {
  it("should merge adjacent assistant messages into one timeline row", () => {
    const t1 = "2026-04-04T08:25:21.000Z";
    const t2 = "2026-04-04T08:25:23.000Z";
    const t3 = "2026-04-04T08:25:25.000Z";

    const merged = coalesceConsecutiveAssistantMessages([
      {
        id: "a1",
        role: "assistant",
        createdAt: t1,
        isStreaming: false,
        parts: [
          {
            type: "tool",
            name: "deep_research",
            state: "completed",
            isError: true,
            result: "deep_research is not a valid tool",
          },
        ],
      },
      {
        id: "a2",
        role: "assistant",
        createdAt: t2,
        isStreaming: false,
        parts: [
          {
            type: "tool",
            name: "search",
            state: "completed",
            result: "Ray 学习路径",
          },
        ],
      },
      {
        id: "a3",
        role: "assistant",
        createdAt: t3,
        isStreaming: true,
        parts: [{ type: "text", text: "打开网页 https://example.com" }],
      },
    ]);

    expect(merged).toHaveLength(1);
    expect(merged[0]).toMatchObject({
      id: "a1",
      role: "assistant",
      createdAt: t3,
      isStreaming: true,
    });
    expect(merged[0]?.parts).toHaveLength(3);
  });

  it("should not merge assistant blocks separated by a user message", () => {
    const merged = coalesceConsecutiveAssistantMessages([
      {
        id: "a1",
        role: "assistant",
        createdAt: new Date().toISOString(),
        isStreaming: false,
        parts: [{ type: "text", text: "First reply" }],
      },
      {
        id: "u1",
        role: "user",
        createdAt: new Date().toISOString(),
        parts: [{ type: "text", text: "Follow up" }],
      },
      {
        id: "a2",
        role: "assistant",
        createdAt: new Date().toISOString(),
        isStreaming: false,
        parts: [{ type: "text", text: "Second reply" }],
      },
    ]);

    expect(merged).toHaveLength(3);
    expect(merged[0]?.id).toBe("a1");
    expect(merged[1]?.id).toBe("u1");
    expect(merged[2]?.id).toBe("a2");
  });
});

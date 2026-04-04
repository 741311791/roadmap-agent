import { describe, expect, it } from "vitest";

import {
  buildMentorAssistantMessage,
  mapMentorMessageToThreadMessage,
} from "@/components/mentor/mentor-adapter";

describe("mentor adapter tool parts", () => {
  it("should build assistant-ui message with tool-call parts", () => {
    const message = buildMentorAssistantMessage({
      contentParts: [
        {
          type: "tool-call",
          toolCallId: "tool-1",
          toolName: "web_search",
          arguments: { query: "React Hooks" },
          state: "completed",
          result: "Found latest docs",
        },
        {
          type: "text",
          text: "这是最终回答。",
        },
      ],
      metadata: {
        threadId: "thread-1",
        modelId: "model-1",
        agentKind: "qa",
        qaStyle: "casual",
      },
    });

    expect(message.content).toEqual([
      {
        type: "tool-call",
        toolCallId: "tool-1",
        toolName: "web_search",
        arguments: { query: "React Hooks" },
        state: "completed",
        result: "Found latest docs",
        isError: undefined,
      },
      {
        type: "text",
        text: "这是最终回答。",
      },
    ]);
  });

  it("should preserve thinking parts before final text", () => {
    const message = buildMentorAssistantMessage({
      contentParts: [
        {
          type: "thinking",
          text: "先分析问题。",
        },
        {
          type: "text",
          text: "这是最终回答。",
        },
      ],
      metadata: {
        threadId: "thread-1",
        modelId: "model-1",
        agentKind: "qa",
        qaStyle: "casual",
      },
    });

    expect(message.content).toEqual([
      {
        type: "thinking",
        text: "先分析问题。",
      },
      {
        type: "text",
        text: "这是最终回答。",
      },
    ]);
  });

  it("should restore tool-call parts from persisted mentor metadata", () => {
    const threadMessage = mapMentorMessageToThreadMessage({
      message_id: "assistant-message-1",
      session_id: "session-1",
      role: "assistant",
      content: "这是最终回答。",
      agent_kind: "qa",
      qa_style: "casual",
      model_id: "model-1",
      trace_id: "trace-1",
      message_metadata: {
        contentParts: [
          {
            type: "thinking",
            text: "先分析页面结构。",
          },
          {
            type: "tool-call",
            toolCallId: "tool-1",
            toolName: "web_fetch",
            arguments: { url: "https://example.com" },
            state: "completed",
            result: "Fetched page content",
          },
          {
            type: "text",
            text: "这是最终回答。",
          },
        ],
      },
      created_at: "2026-03-29T00:00:00Z",
    });

    expect(threadMessage.content).toEqual([
      {
        type: "thinking",
        text: "先分析页面结构。",
      },
      {
        type: "tool-call",
        toolCallId: "tool-1",
        toolName: "web_fetch",
        arguments: { url: "https://example.com" },
        state: "completed",
        result: "Fetched page content",
        isError: undefined,
      },
      {
        type: "text",
        text: "这是最终回答。",
      },
    ]);
  });
});

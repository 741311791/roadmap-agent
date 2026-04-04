import { describe, expect, it } from "vitest";

import { buildDeerFlowContentParts } from "@/components/mentor/use-mentor-deerflow-runtime";

describe("buildDeerFlowContentParts", () => {
  it("should rebuild thinking, tool, and text parts from values snapshots", () => {
    const contentParts = buildDeerFlowContentParts([
      {
        id: "human-1",
        type: "human",
        content: [{ type: "text", text: "Explain this concept" }],
      },
      {
        id: "ai-1",
        type: "ai",
        content: "",
        additional_kwargs: {
          reasoning_content: "先分析上下文。",
        },
        tool_calls: [
          {
            id: "tool-1",
            name: "web_search",
            args: { query: "concept docs" },
          },
        ],
      },
      {
        id: "tool-msg-1",
        type: "tool",
        name: "web_search",
        tool_call_id: "tool-1",
        content: "找到相关文档",
      },
      {
        id: "ai-2",
        type: "ai",
        content: "这是最终回答。",
      },
    ]);

    expect(contentParts).toEqual([
      {
        type: "thinking",
        text: "先分析上下文。",
      },
      {
        type: "tool-call",
        toolCallId: "tool-1",
        toolName: "web_search",
        arguments: { query: "concept docs" },
        state: "completed",
        result: "找到相关文档",
        isError: false,
      },
      {
        type: "text",
        text: "这是最终回答。",
      },
    ]);
  });
});

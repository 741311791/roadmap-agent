import { describe, expect, it } from "vitest";

import { partitionAssistantParts } from "@/components/deerflow-chat-test/deerflow-assistant-segments";
import type { DeerFlowChatMessagePart } from "@/components/deerflow-chat-test/deerflow-chat-state";

describe("partitionAssistantParts", () => {
  it("将思考与工具归入 cot，再分子任务与正文", () => {
    const parts: DeerFlowChatMessagePart[] = [
      { type: "thinking", text: "plan" },
      { type: "tool", name: "web_search", arguments: { query: "x" } },
      { type: "tool", name: "task", arguments: { description: "d" } },
      { type: "tool", name: "task", arguments: { description: "e" } },
      { type: "text", text: "done" },
    ];
    const segments = partitionAssistantParts(parts);
    expect(segments).toHaveLength(3);
    expect(segments[0]).toMatchObject({ type: "cot" });
    expect((segments[0] as { parts: unknown[] }).parts).toHaveLength(2);
    expect(segments[1]).toMatchObject({ type: "subagent" });
    expect((segments[1] as { parts: unknown[] }).parts).toHaveLength(2);
    expect(segments[2]).toMatchObject({ type: "text", part: { text: "done" } });
  });

  it("present_files 独立成段并打断 cot", () => {
    const parts: DeerFlowChatMessagePart[] = [
      { type: "tool", name: "write_todos", arguments: {} },
      {
        type: "tool",
        name: "present_files",
        arguments: { filepaths: ["/a.md"] },
      },
      { type: "text", text: "ok" },
    ];
    const segments = partitionAssistantParts(parts);
    expect(segments.map((s) => s.type)).toEqual(["cot", "present_files", "text"]);
  });
});

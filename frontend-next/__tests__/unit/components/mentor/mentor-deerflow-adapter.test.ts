import { describe, expect, it } from "vitest";

import { extractTodosFromMentorContentParts } from "@/components/mentor/mentor-deerflow-adapter";
import type { MentorContentPart } from "@/components/mentor/types";

describe("extractTodosFromMentorContentParts", () => {
  it("应从 write_todos 工具参数的 todos 数组解析待办", () => {
    const parts: MentorContentPart[] = [
      {
        type: "tool-call",
        toolCallId: "call-1",
        toolName: "write_todos",
        arguments: {
          todos: [
            { id: "a", content: "第一步", status: "completed" },
            { id: "b", content: "第二步", status: "in_progress" },
          ],
        },
        state: "running",
      },
    ];

    expect(extractTodosFromMentorContentParts(parts)).toEqual([
      { id: "a", content: "第一步", status: "completed" },
      { id: "b", content: "第二步", status: "in_progress" },
    ]);
  });

  it("参数为空时应回退解析工具结果字符串", () => {
    const parts: MentorContentPart[] = [
      {
        type: "tool-call",
        toolCallId: "call-2",
        toolName: "write_todos",
        arguments: {},
        state: "completed",
        result: JSON.stringify([
          { id: "x", content: "仅结果里有的任务", status: "pending" },
        ]),
      },
    ];

    expect(extractTodosFromMentorContentParts(parts)).toEqual([
      { id: "x", content: "仅结果里有的任务", status: "pending" },
    ]);
  });
});

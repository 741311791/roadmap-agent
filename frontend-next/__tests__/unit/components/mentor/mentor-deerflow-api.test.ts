import { describe, expect, it } from "vitest";

import { parseDeerFlowSseFrame } from "@/components/mentor/mentor-deerflow-api";

describe("parseDeerFlowSseFrame", () => {
  it("should parse metadata event frames", () => {
    const event = parseDeerFlowSseFrame(
      'event: metadata\ndata: {"run_id":"run-1","thread_id":"thread-1"}\nid: evt-1\n\n'
    );

    expect(event).toEqual({
      event: "metadata",
      data: {
        run_id: "run-1",
        thread_id: "thread-1",
      },
      id: "evt-1",
    });
  });

  it("should ignore heartbeat comment frames", () => {
    expect(parseDeerFlowSseFrame(": heartbeat")).toBeNull();
  });
});

import { describe, expect, it } from "vitest";

import { splitMentorDeltaForDisplay } from "@/components/mentor/use-mentor-runtime";

describe("splitMentorDeltaForDisplay", () => {
  it("should keep short delta unchanged", () => {
    expect(splitMentorDeltaForDisplay("短句")).toEqual(["短句"]);
  });

  it("should split long delta into multiple display chunks", () => {
    const chunks = splitMentorDeltaForDisplay(
      "广播机制的关键是右对齐比较维度，只要某一维相等或者其中一方为 1，就可以在逻辑上扩展后再参与逐元素计算。"
    );

    expect(chunks.length).toBeGreaterThan(1);
    expect(chunks.join("")).toBe(
      "广播机制的关键是右对齐比较维度，只要某一维相等或者其中一方为 1，就可以在逻辑上扩展后再参与逐元素计算。"
    );
  });
});

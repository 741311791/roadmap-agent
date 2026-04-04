import type {
  DeerFlowChatMessagePart,
  DeerFlowChatMessagePartText,
  DeerFlowChatMessagePartTool,
} from "@/components/deerflow-chat-test/deerflow-chat-state";

/**
 * 助手消息分段类型，用于对齐官方 MessageList 的 MessageGroup / present-files / subagent 结构。
 */
export type DeerFlowAssistantSegment =
  | { type: "cot"; parts: DeerFlowChatMessagePart[] }
  | { type: "present_files"; part: DeerFlowChatMessagePartTool }
  | { type: "subagent"; parts: DeerFlowChatMessagePartTool[] }
  | { type: "text"; part: DeerFlowChatMessagePartText };

/**
 * 判断是否为可并入工具链（MessageGroup）的片段：思考与非 task、非 present_files 的工具。
 */
function isCotEligiblePart(part: DeerFlowChatMessagePart): boolean {
  if (part.type === "thinking") {
    return true;
  }
  if (part.type === "tool") {
    return part.name !== "task" && part.name !== "present_files";
  }
  return false;
}

/**
 * 将助手消息的 parts 按官方分组语义拆成有序段落。
 *
 * Args:
 *   parts: 单条助手消息内的片段序列
 *
 * Returns:
 *   与渲染顺序一致的分段数组
 */
export function partitionAssistantParts(parts: DeerFlowChatMessagePart[]): DeerFlowAssistantSegment[] {
  const segments: DeerFlowAssistantSegment[] = [];
  let cotBuffer: DeerFlowChatMessagePart[] = [];

  const flushCot = () => {
    if (cotBuffer.length === 0) {
      return;
    }
    segments.push({ type: "cot", parts: cotBuffer });
    cotBuffer = [];
  };

  const appendSubagentTool = (tool: DeerFlowChatMessagePartTool) => {
    const last = segments.at(-1);
    if (last?.type === "subagent") {
      last.parts.push(tool);
      return;
    }
    segments.push({ type: "subagent", parts: [tool] });
  };

  for (const part of parts) {
    if (part.type === "text") {
      flushCot();
      segments.push({ type: "text", part });
      continue;
    }

    if (part.type === "tool" && part.name === "task") {
      flushCot();
      appendSubagentTool(part);
      continue;
    }

    if (part.type === "tool" && part.name === "present_files") {
      flushCot();
      segments.push({ type: "present_files", part });
      continue;
    }

    if (isCotEligiblePart(part)) {
      cotBuffer.push(part);
      continue;
    }

    flushCot();
  }

  flushCot();
  return segments;
}

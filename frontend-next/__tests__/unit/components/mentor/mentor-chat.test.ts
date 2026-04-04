import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildMentorChatRequest,
} from "@/components/mentor/mentor-adapter";
import {
  streamMentorChat,
  type MentorChatRequestPayload,
  type MentorChatStreamEvent,
} from "@/components/mentor/mentor-api";
import {
  type MentorChapterContext,
} from "@/components/mentor/types";
import { API_PREFIX } from "@/lib/constants";
import { authService } from "@/lib/services/auth-service";

const CHAPTER_CONTEXT: MentorChapterContext = {
  roadmapId: "roadmap-1",
  conceptId: "concept-1",
  conceptName: "React Hooks",
  conceptSummary: "当前章节聚焦 useEffect 与 useMemo。",
};

const TEST_MODEL_OPTIONS = [
  { id: "google/gemini-3.1-pro-preview" },
  { id: "anthropic/claude-sonnet-4" },
];

function buildSseResponseBody(modelId: string): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const frames = [
    `data: ${JSON.stringify({
      type: "meta",
      session_id: "session-1",
      trace_id: "trace-1",
      user_message_id: "user-message-1",
      assistant_message_id: "assistant-message-1",
      model_id: modelId,
    })}\n\n`,
    `data: ${JSON.stringify({
      type: "thinking",
      delta: "先分析需求",
    })}\n\n`,
    `data: ${JSON.stringify({
      type: "tool_start",
      tool_call_id: "tool-1",
      tool_name: "web_search",
      arguments: {
        query: "React Hooks",
      },
    })}\n\n`,
    `data: ${JSON.stringify({
      type: "tool_result",
      tool_call_id: "tool-1",
      tool_name: "web_search",
      arguments: {
        query: "React Hooks",
      },
      result: "Found latest React Hooks docs",
      is_error: false,
    })}\n\n`,
    `data: ${JSON.stringify({
      type: "delta",
      delta: `stream:${modelId}`,
    })}\n\n`,
    "data: [DONE]\n\n",
  ];

  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const frame of frames) {
        controller.enqueue(encoder.encode(frame));
      }
      controller.close();
    },
  });
}

describe("mentor chat stream models", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(crypto, "randomUUID").mockReturnValue("trace-123");
    vi.spyOn(authService, "getToken").mockReturnValue("token-123");
    vi.spyOn(authService, "getCurrentUserId").mockReturnValue("user-123");
  });

  it.each(TEST_MODEL_OPTIONS)(
    "should build /mentor/chat payload with model $id",
    (modelOption) => {
      const payload = buildMentorChatRequest({
        message: "请解释这个章节",
        remoteSessionId: "session-remote-1",
        agentKind: "qa",
        qaStyle: "casual",
        modelId: modelOption.id,
        chapterContext: CHAPTER_CONTEXT,
      });

      expect(payload).toEqual({
        message: "请解释这个章节",
        session_id: "session-remote-1",
        agent_kind: "qa",
        qa_style: "casual",
        model_id: modelOption.id,
        context: {
          roadmap_id: "roadmap-1",
          concept_id: "concept-1",
          concept_title: "React Hooks",
          roadmap_context: "当前章节聚焦 useEffect 与 useMemo。",
          tutorial_excerpt: "当前章节聚焦 useEffect 与 useMemo。",
        },
      });
    }
  );

  it.each(TEST_MODEL_OPTIONS)(
    "should stream /mentor/chat with model $id",
    async (modelOption) => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        body: buildSseResponseBody(modelOption.id),
      });
      vi.stubGlobal("fetch", fetchMock);

      const payload: MentorChatRequestPayload = buildMentorChatRequest({
        message: "请解释这个章节",
        remoteSessionId: "session-remote-1",
        agentKind: "qa",
        qaStyle: "casual",
        modelId: modelOption.id,
        chapterContext: CHAPTER_CONTEXT,
      });

      const events: MentorChatStreamEvent[] = [];
      const abortController = new AbortController();

      for await (const event of streamMentorChat(payload, abortController.signal)) {
        events.push(event);
      }

      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(fetchMock).toHaveBeenCalledWith(
        `${API_PREFIX}/learning/mentor/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Trace-ID": "trace-123",
            Authorization: "Bearer token-123",
            "X-User-ID": "user-123",
          },
          body: JSON.stringify(payload),
          signal: abortController.signal,
          cache: "no-store",
        }
      );
      expect(events).toEqual([
        {
          type: "meta",
          session_id: "session-1",
          trace_id: "trace-1",
          user_message_id: "user-message-1",
          assistant_message_id: "assistant-message-1",
          model_id: modelOption.id,
        },
        {
          type: "thinking",
          delta: "先分析需求",
        },
        {
          type: "tool_start",
          tool_call_id: "tool-1",
          tool_name: "web_search",
          arguments: {
            query: "React Hooks",
          },
        },
        {
          type: "tool_result",
          tool_call_id: "tool-1",
          tool_name: "web_search",
          arguments: {
            query: "React Hooks",
          },
          result: "Found latest React Hooks docs",
          is_error: false,
        },
        {
          type: "delta",
          delta: `stream:${modelOption.id}`,
        },
      ]);
    }
  );
});

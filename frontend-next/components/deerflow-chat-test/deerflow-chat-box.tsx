"use client";

import type { ComponentRef, ReactNode } from "react";
import { FilesIcon, XIcon } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";

import { ConversationEmptyState } from "@/components/deerflow-native/ai-elements/conversation";
import { DeerFlowArtifactDetail } from "@/components/deerflow-chat-test/deerflow-artifact-detail";
import { DeerFlowArtifactFileList } from "@/components/deerflow-chat-test/deerflow-artifact-file-list";
import { useDeerFlowArtifacts } from "@/components/deerflow-chat-test/deerflow-artifacts-context";
import { useDeerFlowThread } from "@/components/deerflow-chat-test/deerflow-thread-context";
import { Button } from "@/components/ui/button";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { cn } from "@/lib/utils";

/** 与官方 chat-box 一致：收起时聊天占满宽，展开时约 60/40 */
const CLOSE_LAYOUT = [100, 0] as const;
const OPEN_LAYOUT = [60, 40] as const;

/**
 * Deer-Flow ChatBox：右侧 Artifacts 侧栏仅在有产物或用户主动打开时展示，对齐官方 `artifactsOpen` 行为。
 */
export function DeerFlowChatBox({
  children,
}: {
  children: ReactNode;
}) {
  const layoutRef = useRef<ComponentRef<typeof ResizablePanelGroup> | null>(null);
  const { thread } = useDeerFlowThread();
  const { open, setOpen, artifacts, selectedArtifact } = useDeerFlowArtifacts();

  const mergedArtifactPaths = useMemo(
    () =>
      Array.from(
        new Set(
          [...artifacts, ...thread.artifacts].filter(
            (path): path is string => typeof path === "string" && path.trim().length > 0
          )
        )
      ),
    [artifacts, thread.artifacts]
  );

  const threadIdRef = useRef(thread.id);
  const prevArtifactCountRef = useRef(0);

  /**
   * 同一线程内产物数量增加时自动展开侧栏（对应官方 write_file / present_files 触发体验）。
   * 切换线程时不自动弹出，避免打断阅读。
   */
  useEffect(() => {
    if (threadIdRef.current !== thread.id) {
      threadIdRef.current = thread.id;
      prevArtifactCountRef.current = mergedArtifactPaths.length;
      return;
    }

    if (
      mergedArtifactPaths.length > prevArtifactCountRef.current &&
      mergedArtifactPaths.length > 0
    ) {
      setOpen(true);
    }

    prevArtifactCountRef.current = mergedArtifactPaths.length;
  }, [mergedArtifactPaths.length, setOpen, thread.id]);

  useEffect(() => {
    if (!layoutRef.current) {
      return;
    }

    layoutRef.current.setLayout(open ? [...OPEN_LAYOUT] : [...CLOSE_LAYOUT]);
  }, [open]);

  return (
    <ResizablePanelGroup
      autoSaveId="deerflow-chat-test-v2-artifacts-toggle"
      className="size-full"
      direction="horizontal"
      ref={layoutRef}
    >
      <ResizablePanel defaultSize={100} minSize={40}>
        <div className="relative size-full min-h-0">{children}</div>
      </ResizablePanel>
      <ResizableHandle
        className={cn(
          "bg-black/8 opacity-50 transition-opacity hover:opacity-100",
          !open && "pointer-events-none w-0 max-w-0 border-0 opacity-0"
        )}
      />
      <ResizablePanel
        className={cn(
          "border-l border-black/10 bg-[#f3f2eb] transition-opacity duration-300",
          !open && "min-w-0 overflow-hidden opacity-0"
        )}
        defaultSize={0}
        maxSize={open ? 50 : 0}
        minSize={0}
      >
        <div
          className={cn(
            "flex h-full flex-col transition-transform duration-300 ease-in-out",
            open ? "translate-x-0" : "translate-x-full"
          )}
        >
          <div className="border-b border-black/10 px-4 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <FilesIcon className="h-4 w-4" />
                Artifacts
              </div>
              <Button
                size="icon"
                type="button"
                variant="ghost"
                onClick={() => setOpen(false)}
              >
                <XIcon className="size-4" />
              </Button>
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-hidden px-4 py-4">
            <div
              className={cn(
                "relative flex w-full flex-col",
                mergedArtifactPaths.length > 0
                  ? "h-full min-h-0"
                  : "min-h-[260px] justify-center"
              )}
            >
              {selectedArtifact ? (
                <DeerFlowArtifactDetail
                  availableFiles={mergedArtifactPaths}
                  filepath={selectedArtifact}
                  threadId={thread.id}
                />
              ) : mergedArtifactPaths.length > 0 ? (
                <div className="flex size-full max-w-full min-h-0 flex-col">
                  <main className="min-h-0 grow overflow-auto">
                    <DeerFlowArtifactFileList files={mergedArtifactPaths} threadId={thread.id} />
                  </main>
                </div>
              ) : (
                <ConversationEmptyState
                  className="min-h-[220px] rounded-2xl border border-black/8 bg-white/60"
                  icon={<FilesIcon className="size-6" />}
                  title="No artifact selected"
                  description="Select an artifact to view its details"
                />
              )}
            </div>
          </div>
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}

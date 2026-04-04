"use client";

import { cn } from "@/lib/utils";

/**
 * DeerFlowWelcome - Deer-Flow 工作区欢迎区（标题与说明，不含品牌 pill）
 */
export function DeerFlowWelcome({
  className,
}: {
  className?: string;
}) {
  return (
    <div
      className={cn(
        "mx-auto flex w-full max-w-2xl flex-col items-center px-2 text-center sm:px-4",
        className
      )}
    >
      <div className="space-y-3">
        <h2 className="text-[1.65rem] font-semibold tracking-[-0.04em] text-slate-950 sm:text-3xl">
          今天我能为你做些什么？
        </h2>
        <p className="mx-auto max-w-xl text-sm leading-relaxed text-slate-500">
          DeerFlow 会在一个统一工作区中展示对话、工具调用、Artifacts 与后续建议。
        </p>
      </div>
    </div>
  );
}

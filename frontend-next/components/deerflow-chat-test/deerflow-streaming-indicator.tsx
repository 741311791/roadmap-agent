import { cn } from "@/lib/utils";
import type { ComponentProps } from "react";

export type DeerFlowStreamingIndicatorProps = {
  size?: "normal" | "sm";
  /** `minimal`：仅圆点，用于列表底部（与官方 message-list 一致）；`labeled`：空消息占位时带文案 */
  variant?: "minimal" | "labeled";
} & Omit<ComponentProps<"div">, "children">;

/**
 * Deer-Flow 风格流式指示器（圆点动画对齐官方 `streaming-indicator.tsx`）。
 */
export function DeerFlowStreamingIndicator({
  className,
  size = "normal",
  variant = "minimal",
  ...divProps
}: DeerFlowStreamingIndicatorProps) {
  const dotSize = size === "sm" ? "mx-0.5 h-1.5 w-1.5" : "mx-1 h-2 w-2";

  const dots = (
    <div className="flex items-center">
      <div
        className={cn(
          dotSize,
          "animate-bouncing rounded-full bg-[#a3a1a1] opacity-100"
        )}
      />
      <div
        className={cn(
          dotSize,
          "animate-bouncing rounded-full bg-[#a3a1a1] opacity-100 [animation-delay:0.2s]"
        )}
      />
      <div
        className={cn(
          dotSize,
          "animate-bouncing rounded-full bg-[#a3a1a1] opacity-100 [animation-delay:0.4s]"
        )}
      />
    </div>
  );

  if (variant === "labeled") {
    return (
      <div className={cn("flex items-center gap-2", className)} {...divProps}>
        <span className="text-xs font-medium tracking-[0.22em] text-slate-400 uppercase">
          Thinking
        </span>
        {dots}
      </div>
    );
  }

  return (
    <div className={cn("flex", className)} {...divProps}>
      {dots}
    </div>
  );
}

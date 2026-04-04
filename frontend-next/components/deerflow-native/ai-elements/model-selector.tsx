"use client";

import type { ComponentProps, ReactNode } from "react";

import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/deerflow-native/ui/command";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { getLobeModelIconFallbackSrc, getLobeModelIconSrc } from "@/lib/lobe-model-icon";
import { cn } from "@/lib/utils";

/**
 * Deer-Flow 风格模型选择器容器。
 */
export type ModelSelectorProps = ComponentProps<typeof Dialog>;

export function ModelSelector(props: ModelSelectorProps) {
  return <Dialog {...props} />;
}

/**
 * 模型选择器触发器。
 */
export type ModelSelectorTriggerProps = ComponentProps<typeof DialogTrigger>;

export function ModelSelectorTrigger(props: ModelSelectorTriggerProps) {
  return <DialogTrigger {...props} />;
}

/**
 * 模型选择器内容。
 */
export type ModelSelectorContentProps = ComponentProps<typeof DialogContent> & {
  title?: ReactNode;
};

export function ModelSelectorContent({
  className,
  children,
  title = "Model Selector",
  ...props
}: ModelSelectorContentProps) {
  return (
    <DialogContent
      className={cn(
        "gap-0 overflow-hidden p-0 sm:max-w-md rounded-2xl border-border/70 shadow-2xl",
        className
      )}
      {...props}
    >
      <DialogTitle className="sr-only">{title}</DialogTitle>
      <Command
        className={cn(
          "rounded-none bg-popover **:data-[slot=command-input-wrapper]:h-auto",
          "[&_[cmdk-input-wrapper]]:border-b [&_[cmdk-input-wrapper]]:border-border/60"
        )}
      >
        {children}
      </Command>
    </DialogContent>
  );
}

/**
 * 模型选择器输入框。
 */
export type ModelSelectorInputProps = ComponentProps<typeof CommandInput>;

export function ModelSelectorInput({
  className,
  ...props
}: ModelSelectorInputProps) {
  return (
    <CommandInput
      className={cn("h-11 py-0 text-sm placeholder:text-muted-foreground/70", className)}
      {...props}
    />
  );
}

/**
 * 模型选择器列表。
 */
export type ModelSelectorListProps = ComponentProps<typeof CommandList>;

export function ModelSelectorList(props: ModelSelectorListProps) {
  return <CommandList {...props} />;
}

/**
 * 模型选择器空态。
 */
export type ModelSelectorEmptyProps = ComponentProps<typeof CommandEmpty>;

export function ModelSelectorEmpty(props: ModelSelectorEmptyProps) {
  return <CommandEmpty {...props} />;
}

/**
 * 模型选择器分组。
 */
export type ModelSelectorGroupProps = ComponentProps<typeof CommandGroup>;

export function ModelSelectorGroup(props: ModelSelectorGroupProps) {
  return <CommandGroup {...props} />;
}

/**
 * 模型选择器项。
 */
export type ModelSelectorItemProps = ComponentProps<typeof CommandItem>;

export function ModelSelectorItem(props: ModelSelectorItemProps) {
  return <CommandItem {...props} />;
}

/**
 * 模型选择器分隔线。
 */
export type ModelSelectorSeparatorProps = ComponentProps<typeof CommandSeparator>;

export function ModelSelectorSeparator(props: ModelSelectorSeparatorProps) {
  return <CommandSeparator {...props} />;
}

/**
 * 模型品牌 Logo（仅由展示名决定图标，与 provider 字段无关）。
 */
export function ModelSelectorLogo({
  displayName,
  className,
  onError,
  ...props
}: Omit<ComponentProps<"img">, "src" | "alt"> & {
  /** 模型展示名，用于匹配 Lobe Icons（如 Doubao-xxx → 字节，Gemini → 谷歌） */
  displayName: string;
}) {
  const src = getLobeModelIconSrc(displayName);
  const fallback = getLobeModelIconFallbackSrc();

  return (
    // eslint-disable-next-line @next/next/no-img-element -- Lobe Icons 为外链 SVG，体积极小且域名随版本变化，不使用 next/image
    <img
      {...props}
      alt=""
      role="presentation"
      loading="lazy"
      decoding="async"
      className={cn(
        "size-7 shrink-0 rounded-lg bg-muted/40 object-contain p-0.5 ring-1 ring-border/50 dark:bg-muted/25",
        className
      )}
      height={28}
      src={src}
      width={28}
      onError={(event) => {
        const el = event.currentTarget;
        if (el.dataset.lobeFallback === "1") {
          return;
        }
        el.dataset.lobeFallback = "1";
        el.src = fallback;
        onError?.(event);
      }}
    />
  );
}

/**
 * 模型提供商 Logo 组。
 */
export function ModelSelectorLogoGroup({
  className,
  ...props
}: ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "[&>img]:bg-background dark:[&>img]:bg-foreground flex shrink-0 items-center -space-x-1 [&>img]:rounded-full [&>img]:p-px [&>img]:ring-1",
        className
      )}
      {...props}
    />
  );
}

/**
 * 模型名称。
 */
export function ModelSelectorName({
  className,
  ...props
}: ComponentProps<"span">) {
  return (
    <span
      className={cn("flex-1 truncate text-left text-xs", className)}
      {...props}
    />
  );
}

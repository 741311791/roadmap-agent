"use client";

import type { HTMLAttributes } from "react";
import {
  RichStreamdown,
  type DeerFlowMarkdownProfile,
} from "@/components/markdown/rich-streamdown";
import { cn } from "@/lib/utils";

export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: "user" | "assistant";
};

export const Message = ({
  className,
  from,
  ...props
}: MessageProps) => (
  <div
    className={cn(
      "group flex w-full flex-col gap-2",
      from === "user" ? "is-user ml-auto justify-end" : "is-assistant",
      className
    )}
    {...props}
  />
);

export type MessageContentProps = HTMLAttributes<HTMLDivElement>;

export const MessageContent = ({
  children,
  className,
  ...props
}: MessageContentProps) => (
  <div
    className={cn(
      "is-user:dark flex w-fit max-w-full min-w-0 flex-col gap-2 overflow-visible",
      "group-[.is-user]:overflow-hidden",
      "group-[.is-user]:bg-secondary group-[.is-user]:text-foreground group-[.is-user]:ml-auto group-[.is-user]:rounded-lg group-[.is-user]:px-4 group-[.is-user]:py-3",
      "group-[.is-assistant]:text-foreground",
      className
    )}
    {...props}
  >
    {children}
  </div>
);

export function MessageText({
  className,
  children,
  markdownProfile = "assistant",
}: {
  className?: string;
  children: string;
  /** 用户气泡与官方一致时使用 `human`（无 GFM 自动链接）；助手正文使用 `assistant` */
  markdownProfile?: DeerFlowMarkdownProfile;
}) {
  return (
    <RichStreamdown
      className={cn(
        "size-full max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
        className
      )}
      markdownProfile={markdownProfile}
    >
      {children}
    </RichStreamdown>
  );
}

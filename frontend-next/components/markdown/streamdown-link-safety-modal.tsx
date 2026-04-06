"use client";

import { Check, Copy, ExternalLink, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { defaultTranslations, type LinkSafetyModalProps } from "streamdown";

import { cn } from "@/lib/utils";

/**
 * 使用真实 DOM 导航打开新标签页。
 *
 * Streamdown 内置实现将 `noreferrer` 作为 `window.open` 的 features 字符串，在部分浏览器中与弹窗策略不兼容，
 * 表现为点击「Open link」无反应；程序化点击带 `rel` 的 `<a>` 与用户直接点击链接一致，更稳定。
 *
 * Args:
 *   url: 目标 URL。
 *
 * Returns:
 *   无。
 *
 * Raises:
 *   无。
 */
function openUrlInNewTab(url: string): void {
  if (typeof document === "undefined") {
    return;
  }
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.target = "_blank";
  anchor.rel = "noopener noreferrer";
  anchor.referrerPolicy = "no-referrer";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

/** 与 Streamdown 内置实现一致：避免多个弹窗同时打开时过早恢复 body 滚动 */
let bodyScrollLockCount = 0;

function lockBodyScroll(): void {
  bodyScrollLockCount += 1;
  if (bodyScrollLockCount === 1) {
    document.body.style.overflow = "hidden";
  }
}

function unlockBodyScroll(): void {
  bodyScrollLockCount = Math.max(0, bodyScrollLockCount - 1);
  if (bodyScrollLockCount === 0) {
    document.body.style.overflow = "";
  }
}

const t = defaultTranslations;

/**
 * Streamdown 外部链接确认弹窗：通过 Portal 挂到 `document.body`，避免祖先层叠上下文裁剪或遮挡点击。
 *
 * Args:
 *   props: Streamdown 传入的 `LinkSafetyModalProps`。
 *
 * Returns:
 *   打开时返回 Portal 渲染结果；关闭或 SSR 时返回 null。
 *
 * Raises:
 *   无。
 */
export function StreamdownLinkSafetyModal({
  url,
  isOpen,
  onClose,
}: LinkSafetyModalProps) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    lockBodyScroll();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      unlockBodyScroll();
    };
  }, [isOpen, onClose]);

  const handleCopy = useCallback(async () => {
    if (!navigator.clipboard?.writeText) {
      return;
    }
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }, [url]);

  const handleOpen = useCallback(() => {
    if (url.trim().length > 0) {
      openUrlInNewTab(url);
    }
    onClose();
  }, [onClose, url]);

  if (!isOpen || typeof document === "undefined") {
    return null;
  }

  return createPortal(
    <div
      className={cn(
        "fixed inset-0 z-[200] flex items-center justify-center bg-background/50 backdrop-blur-sm"
      )}
      data-streamdown="link-safety-modal"
      onClick={onClose}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          onClose();
        }
      }}
      role="presentation"
    >
      <div
        className="relative mx-4 flex w-full max-w-md flex-col gap-4 rounded-xl border bg-background p-6 shadow-lg"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="streamdown-external-link-title"
      >
        <button
          type="button"
          className="text-muted-foreground hover:bg-muted hover:text-foreground absolute top-4 right-4 rounded-md p-1 transition-all"
          onClick={onClose}
          title={t.close}
        >
          <X className="size-4" />
        </button>

        <div className="flex flex-col gap-2">
          <div
            id="streamdown-external-link-title"
            className="flex items-center gap-2 text-lg font-semibold"
          >
            <ExternalLink className="size-5 shrink-0" />
            <span>{t.openExternalLink}</span>
          </div>
          <p className="text-muted-foreground text-sm">{t.externalLinkWarning}</p>
        </div>

        <div
          className={cn(
            "bg-muted font-mono text-sm break-all rounded-md p-3",
            url.length > 100 && "max-h-32 overflow-y-auto"
          )}
        >
          {url}
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            className="bg-background hover:bg-muted flex flex-1 items-center justify-center gap-2 rounded-md border px-4 py-2 text-sm font-medium transition-all"
            onClick={handleCopy}
          >
            {copied ? (
              <>
                <Check className="size-3.5 shrink-0" />
                <span>{t.copied}</span>
              </>
            ) : (
              <>
                <Copy className="size-3.5 shrink-0" />
                <span>{t.copyLink}</span>
              </>
            )}
          </button>
          <button
            type="button"
            className="bg-primary text-primary-foreground hover:bg-primary/90 flex flex-1 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all"
            onClick={handleOpen}
          >
            <ExternalLink className="size-3.5 shrink-0" />
            <span>{t.openLink}</span>
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}

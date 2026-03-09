'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { cn } from '@/lib/utils';

interface MentorMarkdownMessageProps {
  content: string;
  className?: string;
}

/**
 * Mentor 聊天消息 Markdown 渲染器。
 *
 * 说明：
 * - 面向实时流式内容，保持渲染逻辑轻量。
 * - 默认不启用 HTML 直出，避免不必要的富文本注入风险。
 */
export function MentorMarkdownMessage({
  content,
  className,
}: MentorMarkdownMessageProps) {
  return (
    <div
      className={cn(
        'prose prose-sm max-w-none dark:prose-invert',
        'prose-p:my-1 prose-pre:my-2 prose-ul:my-1 prose-ol:my-1',
        'prose-li:my-0 prose-code:text-[12px] prose-pre:text-[12px]',
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ children, href, ...props }) {
            const isExternal = href?.startsWith('http');
            return (
              <a
                href={href}
                target={isExternal ? '_blank' : undefined}
                rel={isExternal ? 'noopener noreferrer' : undefined}
                {...props}
              >
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

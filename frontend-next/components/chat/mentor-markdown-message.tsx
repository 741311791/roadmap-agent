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
        'prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1',
        'prose-li:my-0 prose-pre:my-2 prose-code:text-[12px] prose-pre:text-[12px]',
        'prose-pre:rounded-xl prose-pre:border prose-pre:bg-background/80',
        'prose-code:before:content-none prose-code:after:content-none',
        'prose-a:text-primary prose-a:no-underline hover:prose-a:underline',
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ children, className: codeClassName, ...props }) {
            const isBlock = Boolean(codeClassName?.includes('language-'));
            if (isBlock) {
              return (
                <code className={cn('block overflow-x-auto', codeClassName)} {...props}>
                  {children}
                </code>
              );
            }
            return (
              <code className="rounded bg-background/80 px-1 py-0.5 text-[12px]" {...props}>
                {children}
              </code>
            );
          },
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

'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { CodeBlock } from './code-block';
import { MermaidDiagram } from './mermaid-diagram';
import { cn } from '@/lib/utils';

// Import highlight.js styles
import 'highlight.js/styles/github-dark.css';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/**
 * MarkdownRenderer - Markdown 渲染器
 * 
 * 功能:
 * - GitHub Flavored Markdown 支持
 * - 代码语法高亮
 * - 自定义组件样式
 * - 响应式表格
 * - 图片懒加载
 */
export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={cn('prose prose-slate dark:prose-invert max-w-none', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // 代码块自定义渲染
          code({ node, className, children, ...props }) {
            const isInline = !className?.includes('language-');
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : '';
            const code = String(children).replace(/\n$/, '');

            // 检查是否是 Mermaid 图表
            if (!isInline && language === 'mermaid') {
              return <MermaidDiagram chart={code} />;
            }

            if (!isInline && language) {
              return (
                <CodeBlock
                  code={code}
                  language={language}
                  showLineNumbers
                />
              );
            }

            // 行内代码
            return (
              <code
                className={cn(
                  'px-1.5 py-0.5 rounded-md bg-muted text-sm font-mono',
                  className
                )}
                {...props}
              >
                {children}
              </code>
            );
          },

          // 自定义 pre 标签（避免 Mermaid 图表被包裹）
          pre({ children, ...props }: any) {
            // 检查是否包含 Mermaid 图表
            const codeChild = Array.isArray(children) ? children[0] : children;
            const className = codeChild?.props?.className || '';
            const isMermaid = className.includes('language-mermaid');
            
            if (isMermaid) {
              // Mermaid 图表不需要 pre 包裹
              return <>{children}</>;
            }
            
            // 普通代码块使用 pre 标签
            return <pre {...props}>{children}</pre>;
          },

          // 标题自定义（添加锚点）
          h1({ children, ...props }) {
            const id = String(children).toLowerCase().replace(/\s+/g, '-');
            return (
              <h1 id={id} {...props}>
                {children}
              </h1>
            );
          },
          h2({ children, ...props }) {
            const id = String(children).toLowerCase().replace(/\s+/g, '-');
            return (
              <h2 id={id} {...props}>
                {children}
              </h2>
            );
          },
          h3({ children, ...props }) {
            const id = String(children).toLowerCase().replace(/\s+/g, '-');
            return (
              <h3 id={id} {...props}>
                {children}
              </h3>
            );
          },

          // 图片懒加载
          img({ src, alt, ...props }) {
            return (
              <img
                src={src}
                alt={alt}
                loading="lazy"
                className="rounded-lg shadow-sm"
                {...props}
              />
            );
          },

          // 表格响应式包装
          table({ children, ...props }) {
            return (
              <div className="overflow-x-auto">
                <table {...props}>{children}</table>
              </div>
            );
          },

          // 引用块样式
          blockquote({ children, ...props }) {
            return (
              <blockquote
                className="border-l-4 border-primary pl-4 italic my-4"
                {...props}
              >
                {children}
              </blockquote>
            );
          },

          // 链接样式（外部链接新标签打开）
          a({ href, children, ...props }) {
            const isExternal = href?.startsWith('http');
            return (
              <a
                href={href}
                target={isExternal ? '_blank' : undefined}
                rel={isExternal ? 'noopener noreferrer' : undefined}
                className="text-primary hover:underline"
                {...props}
              >
                {children}
              </a>
            );
          },

          // 列表样式
          ul({ children, ...props }) {
            return (
              <ul className="list-disc pl-6 space-y-2" {...props}>
                {children}
              </ul>
            );
          },
          ol({ children, ...props }) {
            return (
              <ol className="list-decimal pl-6 space-y-2" {...props}>
                {children}
              </ol>
            );
          },

          // 段落间距
          p({ children, ...props }) {
            return (
              <p className="my-4 leading-7" {...props}>
                {children}
              </p>
            );
          },

          // 分割线
          hr({ ...props }) {
            return <hr className="my-8 border-border" {...props} />;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

/**
 * CompactMarkdownRenderer - 紧凑版 Markdown 渲染器
 * 用于预览、摘要等场景
 */
export function CompactMarkdownRenderer({
  content,
  className,
  maxLines = 3
}: MarkdownRendererProps & { maxLines?: number }) {
  return (
    <div
      className={cn(
        'prose prose-sm prose-slate dark:prose-invert max-w-none',
        `line-clamp-${maxLines}`,
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // 简化代码块
          code({ className, children }) {
            const isInline = !className?.includes('language-');
            if (!isInline) return null; // 忽略代码块
            return (
              <code className="px-1 py-0.5 rounded bg-muted text-xs font-mono">
                {children}
              </code>
            );
          },
          // 忽略图片
          img() {
            return null;
          },
          // 简化标题
          h1({ children }) {
            return <strong>{children}</strong>;
          },
          h2({ children }) {
            return <strong>{children}</strong>;
          },
          h3({ children }) {
            return <strong>{children}</strong>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}


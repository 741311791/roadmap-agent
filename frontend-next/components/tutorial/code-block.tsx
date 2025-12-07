'use client';

import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface CodeBlockProps {
  code: string;
  language: string;
  showLineNumbers?: boolean;
  className?: string;
  filename?: string;
}

/**
 * CodeBlock - 代码块组件
 * 
 * 功能:
 * - 语法高亮（通过 rehype-highlight 和 highlight.js）
 * - 复制代码
 * - 行号显示
 * - 文件名显示
 * - 支持的语言提示
 */
export function CodeBlock({
  code,
  language,
  showLineNumbers = false,
  className,
  filename
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy code:', error);
    }
  };

  // 分割代码行
  const lines = code.split('\n');

  return (
    <div className={cn('group relative my-6 overflow-hidden rounded-lg border bg-zinc-950', className)}>
      {/* 头部：语言标签 + 文件名 + 复制按钮 */}
      <div className="flex items-center justify-between bg-zinc-900 px-4 py-2 text-sm border-b border-zinc-800">
        <div className="flex items-center gap-3">
          {/* 语言标签 */}
          <span className="text-zinc-400 font-mono text-xs uppercase">
            {language}
          </span>
          
          {/* 文件名 */}
          {filename && (
            <>
              <span className="text-zinc-600">•</span>
              <span className="text-zinc-300 font-mono text-xs">
                {filename}
              </span>
            </>
          )}
        </div>

        {/* 复制按钮 */}
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className={cn(
            'h-7 px-2 text-xs opacity-0 group-hover:opacity-100 transition-opacity',
            copied && 'opacity-100'
          )}
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 mr-1.5 text-green-500" />
              <span className="text-green-500">已复制</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3 mr-1.5" />
              复制
            </>
          )}
        </Button>
      </div>

      {/* 代码内容 */}
      <div className="overflow-x-auto">
        <pre className="p-4 text-sm leading-6">
          <code className={`language-${language}`}>
            {showLineNumbers ? (
              <table className="w-full border-collapse">
                <tbody>
                  {lines.map((line, index) => (
                    <tr key={index}>
                      {/* 行号 */}
                      <td className="pr-4 text-right select-none text-zinc-600 w-8">
                        {index + 1}
                      </td>
                      {/* 代码内容 */}
                      <td className="pl-4 border-l border-zinc-800">
                        {line || '\n'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              code
            )}
          </code>
        </pre>
      </div>
    </div>
  );
}

/**
 * InlineCode - 行内代码
 */
export function InlineCode({
  children,
  className
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <code
      className={cn(
        'px-1.5 py-0.5 rounded-md',
        'bg-zinc-100 dark:bg-zinc-900',
        'text-sm font-mono',
        'text-zinc-800 dark:text-zinc-200',
        'border border-zinc-200 dark:border-zinc-800',
        className
      )}
    >
      {children}
    </code>
  );
}

/**
 * 获取语言的友好显示名称
 */
export function getLanguageDisplayName(language: string): string {
  const languageMap: Record<string, string> = {
    js: 'JavaScript',
    jsx: 'React JSX',
    ts: 'TypeScript',
    tsx: 'React TSX',
    py: 'Python',
    python: 'Python',
    java: 'Java',
    cpp: 'C++',
    c: 'C',
    cs: 'C#',
    go: 'Go',
    rs: 'Rust',
    rb: 'Ruby',
    php: 'PHP',
    swift: 'Swift',
    kt: 'Kotlin',
    scala: 'Scala',
    html: 'HTML',
    css: 'CSS',
    scss: 'SCSS',
    sass: 'Sass',
    less: 'Less',
    json: 'JSON',
    xml: 'XML',
    yaml: 'YAML',
    yml: 'YAML',
    md: 'Markdown',
    markdown: 'Markdown',
    sql: 'SQL',
    sh: 'Shell',
    bash: 'Bash',
    powershell: 'PowerShell',
    dockerfile: 'Dockerfile',
    docker: 'Docker',
    nginx: 'Nginx',
    apache: 'Apache',
    graphql: 'GraphQL',
    proto: 'Protocol Buffers',
  };

  return languageMap[language.toLowerCase()] || language;
}


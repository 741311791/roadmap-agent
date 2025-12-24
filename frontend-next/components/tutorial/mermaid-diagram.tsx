'use client';

import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

interface MermaidDiagramProps {
  chart: string;
  className?: string;
}

/**
 * MermaidDiagram - Mermaid 图表渲染组件
 * 
 * 功能：
 * - 渲染 Mermaid 语法的流程图、时序图、类图等
 * - 自动适配深色/亮色模式
 * - 监听系统主题变化并重新渲染
 * - 错误处理和加载状态
 */
export function MermaidDiagram({ chart, className }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDark, setIsDark] = useState(false); // 默认亮色主题

  // 检测当前主题模式
  useEffect(() => {
    // 优先检查 HTML 元素是否有 dark 类
    const checkTheme = () => {
      const htmlElement = document.documentElement;
      const hasDarkClass = htmlElement.classList.contains('dark');
      
      // 只在明确有 dark 类时才使用深色主题
      // 默认使用亮色主题，不依赖系统偏好
      if (hasDarkClass) {
        setIsDark(true);
      } else {
        setIsDark(false);
      }
    };

    checkTheme();

    // 监听 HTML class 变化（支持未来的主题切换功能）
    const observer = new MutationObserver(checkTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    });

    return () => {
      observer.disconnect();
    };
  }, []);

  // 初始化 Mermaid 配置（根据主题动态调整）
  useEffect(() => {
    // 亮色主题使用 'neutral'，深色主题使用 'dark'
    // 'neutral' 主题默认是浅色背景，更容易自定义
    mermaid.initialize({
      startOnLoad: false,
      theme: isDark ? 'dark' : 'neutral',
      themeVariables: isDark ? {
        // 深色主题配置
        primaryColor: '#6366f1',
        primaryTextColor: '#fff',
        primaryBorderColor: '#4f46e5',
        lineColor: '#94a3b8',
        secondaryColor: '#8b5cf6',
        tertiaryColor: '#06b6d4',
        background: '#27272a',
        mainBkg: '#3f3f46',
        secondaryBkg: '#52525b',
        tertiaryBkg: '#71717a',
        textColor: '#fafafa',
        // sequenceDiagram 特定变量
        actorBkg: '#3f3f46',
        actorBorder: '#4f46e5',
        actorTextColor: '#fafafa',
        actorLineColor: '#94a3b8',
        signalColor: '#fafafa',
        signalTextColor: '#fafafa',
        labelBoxBkgColor: '#3f3f46',
        labelBoxBorderColor: '#4f46e5',
        labelTextColor: '#fafafa',
        loopTextColor: '#fafafa',
        noteBkgColor: '#52525b',
        noteTextColor: '#fafafa',
        noteBorderColor: '#71717a',
        activationBkgColor: '#52525b',
        activationBorderColor: '#6366f1',
        sequenceNumberColor: '#fff',
      } : {
        // 亮色主题配置 - 使用浅色背景
        primaryColor: '#4f46e5',
        primaryTextColor: '#fff',
        primaryBorderColor: '#4338ca',
        lineColor: '#64748b',
        secondaryColor: '#7c3aed',
        tertiaryColor: '#0891b2',
        background: '#F5F3EF',
        mainBkg: '#F5F3EF',
        secondaryBkg: '#EBE8E3',
        tertiaryBkg: '#E1DDD6',
        textColor: '#1e293b',
        // sequenceDiagram 特定变量 - 亮色
        actorBkg: '#F5F3EF',
        actorBorder: '#4f46e5',
        actorTextColor: '#1e293b',
        actorLineColor: '#64748b',
        signalColor: '#1e293b',
        signalTextColor: '#1e293b',
        labelBoxBkgColor: '#F5F3EF',
        labelBoxBorderColor: '#4f46e5',
        labelTextColor: '#1e293b',
        loopTextColor: '#1e293b',
        noteBkgColor: '#fef3c7',
        noteTextColor: '#92400e',
        noteBorderColor: '#f59e0b',
        activationBkgColor: '#e0e7ff',
        activationBorderColor: '#6366f1',
        sequenceNumberColor: '#fff',
      },
      fontFamily: 'ui-sans-serif, system-ui, sans-serif',
      securityLevel: 'loose',
    });
  }, [isDark]);

  // 渲染图表
  useEffect(() => {
    const renderDiagram = async () => {
      if (!containerRef.current || !chart) return;

      setIsLoading(true);
      setError(null);

      try {
        // 清空容器
        containerRef.current.innerHTML = '';

        // 第一步：语法预验证（捕获语法错误）
        // 使用 suppressErrors: true 避免抛出异常，返回 false 表示语法错误
        const parseResult = await mermaid.parse(chart, { suppressErrors: true });
        if (parseResult === false) {
          // 语法错误 - 静默失败
          console.warn('[Mermaid] Syntax validation failed, skipping diagram. Chart:', chart.substring(0, 100) + '...');
          setError('Invalid diagram syntax');
          setIsLoading(false);
          return;
        }

        // 第二步：生成唯一 ID
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

        // 第三步：渲染图表
        const { svg } = await mermaid.render(id, chart);
        
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
          
          // 后处理：确保背景色正确
          const svgElement = containerRef.current.querySelector('svg');
          if (svgElement) {
            // 设置 SVG 背景色
            const bgColor = isDark ? '#27272a' : '#F5F3EF';
            svgElement.style.backgroundColor = bgColor;
            
            // 修复 sequenceDiagram 的深色背景问题
            // sequenceDiagram 会生成一个 rect 作为背景，颜色是 #1f2020
            const firstRect = svgElement.querySelector('rect');
            if (firstRect) {
              const currentFill = firstRect.getAttribute('fill');
              // 如果是默认的深色背景，替换为正确的颜色
              if (currentFill === '#1f2020' || currentFill === 'rgb(31, 32, 32)') {
                firstRect.setAttribute('fill', bgColor);
              }
            }
          }
        }
      } catch (err) {
        // 渲染阶段错误 - 静默失败
        console.error('[Mermaid] Rendering error:', err);
        setError(err instanceof Error ? err.message : 'Failed to render diagram');
      } finally {
        setIsLoading(false);
      }
    };

    renderDiagram();
  }, [chart, isDark]); // 主题变化时重新渲染

  // 静默失败：渲染失败时不显示任何内容
  if (error) {
    // 仅在控制台记录错误，方便开发者调试
    console.warn('[Mermaid] Rendering failed, hiding diagram:', error);
    return null;
  }

  return (
    <div className={`my-6 ${className || ''}`}>
      {isLoading && (
        <div className="flex items-center justify-center p-8">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <svg
              className="animate-spin h-5 w-5"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>Rendering diagram...</span>
          </div>
        </div>
      )}
      <div
        ref={containerRef}
        className="flex justify-center items-center mermaid-container"
        style={{ minHeight: isLoading ? '200px' : 'auto' }}
      />
    </div>
  );
}


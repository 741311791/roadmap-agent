'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import mermaid from 'mermaid';
import { ZoomIn, ZoomOut, Maximize2, Expand } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';

// ===================== 常量 =====================
const MIN_SCALE = 0.3;
const MAX_SCALE = 5;
const ZOOM_STEP = 0.2;
const WHEEL_SENSITIVITY = 0.001;
const INLINE_FIT_PADDING = 32;
const DIALOG_FIT_PADDING = 48;
const INLINE_DEFAULT_SCALE_RATIO = 0.88;
const DIALOG_DEFAULT_SCALE_RATIO = 0.96;

interface DiagramViewState {
  scale: number;
  translate: {
    x: number;
    y: number;
  };
}

/**
 * 获取 SVG 的自然尺寸，优先使用 viewBox，避免 transform 后的视觉尺寸干扰适配计算。
 *
 * Args:
 * svgEl: Mermaid 渲染后的 SVG 元素
 *
 * Returns:
 * SVG 的自然宽高
 */
function getSvgIntrinsicSize(svgEl: SVGSVGElement): { width: number; height: number } {
  const viewBox = svgEl.viewBox?.baseVal;
  if (viewBox && viewBox.width > 0 && viewBox.height > 0) {
    return {
      width: viewBox.width,
      height: viewBox.height,
    };
  }

  const width = Number(svgEl.getAttribute('width')) || svgEl.getBoundingClientRect().width;
  const height = Number(svgEl.getAttribute('height')) || svgEl.getBoundingClientRect().height;

  return {
    width,
    height,
  };
}

// ===================== useZoomPan Hook =====================
/**
 * 封装缩放和平移逻辑，供多个容器实例独立复用
 *
 * @param outerRef - 接收鼠标/触摸事件的外层容器（用于 wheel 监听和焦点计算）
 * @param wrapperRef - 应用 transform 的内层容器（用于边界计算）
 * @param svgContainerRef - SVG 所在的叶子容器（用于 scrollWidth/scrollHeight）
 */
function useZoomPan(
  outerRef: React.RefObject<HTMLDivElement | null>,
  wrapperRef: React.RefObject<HTMLDivElement | null>,
  svgContainerRef: React.RefObject<HTMLDivElement | null>,
) {
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const defaultViewRef = useRef<DiagramViewState>({
    scale: 1,
    translate: { x: 0, y: 0 },
  });
  const isDragging = useRef(false);
  const lastPointer = useRef({ x: 0, y: 0 });
  const lastPinchDist = useRef<number | null>(null);
  const scaleRef = useRef(scale);
  scaleRef.current = scale;

  /**
   * 统一设置当前视图，可选择同步更新“重置视图”的默认值。
   *
   * Args:
   * nextView: 目标缩放和平移状态
   * persistAsDefault: 是否将该视图保存为默认视图
   *
   * Returns:
   * 无
   */
  const applyView = useCallback((nextView: DiagramViewState, persistAsDefault = false) => {
    const normalizedScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, nextView.scale));
    const normalizedTranslate = nextView.translate;

    if (persistAsDefault) {
      defaultViewRef.current = {
        scale: normalizedScale,
        translate: normalizedTranslate,
      };
    }

    setScale(normalizedScale);
    setTranslate(normalizedTranslate);
  }, []);

  /** 将平移量限制在合理边界内，防止图表完全移出视野 */
  const clampTranslate = useCallback(
    (tx: number, ty: number, nextScale: number) => {
      const outer = outerRef.current;
      const svgEl = svgContainerRef.current?.querySelector('svg') as SVGSVGElement | null;
      if (!outer || !svgEl) return { x: tx, y: ty };

      const svgW = svgEl.scrollWidth * nextScale;
      const svgH = svgEl.scrollHeight * nextScale;
      const outerW = outer.clientWidth;
      const outerH = outer.clientHeight;

      const marginX = Math.max(outerW * 0.2, 80);
      const marginY = Math.max(outerH * 0.2, 80);
      const maxX = Math.max(0, (svgW - outerW) / 2 + marginX);
      const maxY = Math.max(0, (svgH - outerH) / 2 + marginY);

      return {
        x: Math.min(maxX, Math.max(-maxX, tx)),
        y: Math.min(maxY, Math.max(-maxY, ty)),
      };
    },
    [outerRef, svgContainerRef],
  );

  /** 以指定焦点坐标（相对容器中心的偏移）为中心进行缩放 */
  const zoomAt = useCallback(
    (delta: number, focalX: number, focalY: number) => {
      setScale((prev) => {
        const next = Math.min(MAX_SCALE, Math.max(MIN_SCALE, prev + delta));
        const ratio = next / prev;
        setTranslate((t) => {
          const nx = focalX + (t.x - focalX) * ratio;
          const ny = focalY + (t.y - focalY) * ratio;
          return clampTranslate(nx, ny, next);
        });
        return next;
      });
    },
    [clampTranslate],
  );

  /** 重置到初始视图 */
  const resetView = useCallback(() => {
    applyView(defaultViewRef.current);
  }, [applyView]);

  // 鼠标滚轮缩放（必须 passive:false 以 preventDefault）
  useEffect(() => {
    const outer = outerRef.current;
    if (!outer) return;

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = outer.getBoundingClientRect();
      const focalX = e.clientX - rect.left - rect.width / 2;
      const focalY = e.clientY - rect.top - rect.height / 2;
      const delta = -e.deltaY * WHEEL_SENSITIVITY * MAX_SCALE;
      zoomAt(delta, focalX, focalY);
    };

    outer.addEventListener('wheel', onWheel, { passive: false });
    return () => outer.removeEventListener('wheel', onWheel);
  }, [outerRef, zoomAt]);

  // 鼠标拖拽平移 - React 合成事件处理函数
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    isDragging.current = true;
    lastPointer.current = { x: e.clientX, y: e.clientY };
    e.preventDefault();
  }, []);

  const onMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging.current) return;
      const dx = e.clientX - lastPointer.current.x;
      const dy = e.clientY - lastPointer.current.y;
      lastPointer.current = { x: e.clientX, y: e.clientY };
      setTranslate((t) => clampTranslate(t.x + dx, t.y + dy, scaleRef.current));
    },
    [clampTranslate],
  );

  const onMouseUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  // 触摸事件（捏合缩放 + 单指平移）
  const onTouchStart = useCallback((e: React.TouchEvent) => {
    if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      lastPinchDist.current = Math.hypot(dx, dy);
    } else if (e.touches.length === 1) {
      lastPointer.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
  }, []);

  const onTouchMove = useCallback(
    (e: React.TouchEvent) => {
      e.preventDefault();
      if (e.touches.length === 2 && lastPinchDist.current !== null) {
        const dx = e.touches[0].clientX - e.touches[1].clientX;
        const dy = e.touches[0].clientY - e.touches[1].clientY;
        const dist = Math.hypot(dx, dy);
        const delta = (dist - lastPinchDist.current) * 0.01;
        lastPinchDist.current = dist;

        const outer = outerRef.current;
        if (outer) {
          const rect = outer.getBoundingClientRect();
          const midX = (e.touches[0].clientX + e.touches[1].clientX) / 2 - rect.left - rect.width / 2;
          const midY = (e.touches[0].clientY + e.touches[1].clientY) / 2 - rect.top - rect.height / 2;
          zoomAt(delta, midX, midY);
        }
      } else if (e.touches.length === 1) {
        const dx = e.touches[0].clientX - lastPointer.current.x;
        const dy = e.touches[0].clientY - lastPointer.current.y;
        lastPointer.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        setTranslate((t) => clampTranslate(t.x + dx, t.y + dy, scaleRef.current));
      }
    },
    [outerRef, zoomAt, clampTranslate],
  );

  const onTouchEnd = useCallback(() => {
    lastPinchDist.current = null;
  }, []);

  return {
    scale,
    translate,
    isDragging,
    applyView,
    zoomAt,
    resetView,
    onMouseDown,
    onMouseMove,
    onMouseUp,
    onTouchStart,
    onTouchMove,
    onTouchEnd,
  };
}

// ===================== ZoomableContainer 组件 =====================
interface ZoomableContainerProps {
  /** 已渲染好的 SVG HTML 字符串 */
  svgHtml: string;
  /**
   * 撑满父容器高度模式（用于对话框内）
   * - false（默认）：容器高度由 SVG 内容决定，适合内联嵌入
   * - true：容器 h-full，SVG 居中展示，适合全屏对话框
   */
  fillHeight?: boolean;
  /** 内联模式下的最小高度（fillHeight=false 时生效） */
  minHeight?: number;
  className?: string;
  /** 额外操作按钮插槽（如全屏按钮）*/
  extraControls?: React.ReactNode;
  /** 控制按钮组距右边缘的偏移量（用于在对话框中避开关闭按钮）*/
  controlsRightOffset?: number;
}

/**
 * ZoomableContainer - 支持缩放和平移的 SVG 展示容器
 *
 * 每次使用都拥有独立的缩放/平移状态，可在内联视图和对话框中复用。
 * 通过 fillHeight 区分两种尺寸模式：内联自适应高度 / 对话框撑满高度。
 */
function ZoomableContainer({
  svgHtml,
  fillHeight = false,
  minHeight = 120,
  className,
  extraControls,
  controlsRightOffset = 8,
}: ZoomableContainerProps) {
  const outerRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const svgContainerRef = useRef<HTMLDivElement>(null);

  const { scale, translate, isDragging, applyView, zoomAt, resetView, onMouseDown, onMouseMove, onMouseUp, onTouchStart, onTouchMove, onTouchEnd } =
    useZoomPan(outerRef, wrapperRef, svgContainerRef);

  // 将 svgHtml 注入 DOM（innerHTML 方式保留 SVG 原生特性）
  useEffect(() => {
    if (svgContainerRef.current) {
      svgContainerRef.current.innerHTML = svgHtml;
      const svgEl = svgContainerRef.current.querySelector('svg');
      if (svgEl) {
        // 移除 mermaid 默认的宽度限制，确保缩放时 SVG 不被裁剪
        svgEl.style.maxWidth = 'none';
        svgEl.style.display = 'block';
      }
    }
  }, [svgHtml]);

  useEffect(() => {
    if (!svgHtml) return;

    const updateDefaultView = () => {
      const outer = outerRef.current;
      const svgEl = svgContainerRef.current?.querySelector('svg') as SVGSVGElement | null;

      if (!outer || !svgEl) {
        return;
      }

      const { width, height } = getSvgIntrinsicSize(svgEl);
      if (!width || !height) {
        return;
      }

      // 默认先按容器做 fit，再额外缩小一点，让流程图初始展示更紧凑但仍然完整可见。
      const padding = fillHeight ? DIALOG_FIT_PADDING : INLINE_FIT_PADDING;
      const scaleRatio = fillHeight ? DIALOG_DEFAULT_SCALE_RATIO : INLINE_DEFAULT_SCALE_RATIO;
      const availableWidth = Math.max(outer.clientWidth - padding * 2, 1);
      const availableHeight = fillHeight ? Math.max(outer.clientHeight - padding * 2, 1) : Number.POSITIVE_INFINITY;
      const widthScale = availableWidth / width;
      const heightScale = Number.isFinite(availableHeight) ? availableHeight / height : Number.POSITIVE_INFINITY;
      const fittedScale = Math.min(widthScale, heightScale, 1);
      const defaultScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, fittedScale * scaleRatio));

      applyView(
        {
          scale: defaultScale,
          translate: { x: 0, y: 0 },
        },
        true,
      );
    };

    const frameId = window.requestAnimationFrame(updateDefaultView);
    return () => window.cancelAnimationFrame(frameId);
  }, [applyView, fillHeight, svgHtml]);

  return (
    <div className={cn('relative', fillHeight ? 'h-full' : '', className)}>
      {/* 控制按钮浮层 */}
      <div
        className="absolute top-2 z-10 flex items-center gap-1 bg-background/80 backdrop-blur-sm border border-border rounded-lg p-1 shadow-sm"
        style={{ right: controlsRightOffset }}
      >
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => zoomAt(ZOOM_STEP, 0, 0)}
          title="放大"
        >
          <ZoomIn className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => zoomAt(-ZOOM_STEP, 0, 0)}
          title="缩小"
        >
          <ZoomOut className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={resetView}
          title="重置视图"
        >
          <Maximize2 className="h-3.5 w-3.5" />
        </Button>
        <span className="text-xs text-muted-foreground px-1 min-w-[3rem] text-center tabular-nums">
          {Math.round(scale * 100)}%
        </span>
        {/* 额外按钮插槽（如全屏按钮）*/}
        {extraControls}
      </div>

      {/* 交互区域
          - fillHeight 模式：h-full + flex 居中，撑满父容器（对话框场景）
          - 普通模式：由内容撑起高度，加 minHeight 兜底（内联场景）
      */}
      <div
        ref={outerRef}
        className={cn(
          'overflow-hidden rounded-lg border border-border/40',
          fillHeight ? 'h-full flex items-center justify-center' : '',
        )}
        style={{
          cursor: isDragging.current ? 'grabbing' : 'grab',
          minHeight: fillHeight ? undefined : minHeight,
          touchAction: 'none',
        }}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        {/* 可变换的内层：transform 以容器中心为原点 */}
        <div
          ref={wrapperRef}
          style={{
            transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
            transformOrigin: 'center center',
            transition: isDragging.current ? 'none' : 'transform 0.05s ease-out',
            willChange: 'transform',
          }}
        >
          <div ref={svgContainerRef} className="flex justify-center items-center mermaid-container" />
        </div>
      </div>
    </div>
  );
}

// ===================== MermaidDiagram 主组件 =====================
interface MermaidDiagramProps {
  chart: string;
  className?: string;
}

/**
 * MermaidDiagram - Mermaid 图表渲染组件
 *
 * 功能：
 * - 渲染 Mermaid 语法的流程图、时序图、类图等
 * - 支持鼠标滚轮缩放、拖拽平移、触摸捏合缩放
 * - 点击全屏按钮可在对话框中查看完整图表
 * - 对话框内拥有独立的缩放/平移状态
 * - 自动适配深色/亮色模式
 */
export function MermaidDiagram({ chart, className }: MermaidDiagramProps) {
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDark, setIsDark] = useState(false);
  /** 渲染完成后的 SVG HTML 字符串，供内联视图和对话框共享 */
  const [svgHtml, setSvgHtml] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);

  // 主题检测
  useEffect(() => {
    const checkTheme = () => setIsDark(document.documentElement.classList.contains('dark'));
    checkTheme();
    const observer = new MutationObserver(checkTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  // Mermaid 初始化
  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: isDark ? 'dark' : 'neutral',
      themeVariables: isDark
        ? {
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
          }
        : {
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

  // SVG 渲染：结果存入 state，后续分别注入两个容器
  useEffect(() => {
    const renderDiagram = async () => {
      if (!chart) return;

      setIsLoading(true);
      setError(null);
      setSvgHtml('');

      try {
        const parseResult = await mermaid.parse(chart, { suppressErrors: true });
        if (parseResult === false) {
          console.warn('[Mermaid] 语法验证失败，跳过渲染。Chart:', chart.substring(0, 100) + '...');
          setError('Invalid diagram syntax');
          setIsLoading(false);
          return;
        }

        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
        const { svg } = await mermaid.render(id, chart);

        // 后处理：修正背景色
        const parser = new DOMParser();
        const doc = parser.parseFromString(svg, 'image/svg+xml');
        const svgEl = doc.querySelector('svg');
        if (svgEl) {
          const bgColor = isDark ? '#27272a' : '#F5F3EF';
          svgEl.style.backgroundColor = bgColor;
          svgEl.style.maxWidth = 'none';
          svgEl.style.display = 'block';

          const firstRect = svgEl.querySelector('rect');
          if (firstRect) {
            const fill = firstRect.getAttribute('fill');
            if (fill === '#1f2020' || fill === 'rgb(31, 32, 32)') {
              firstRect.setAttribute('fill', bgColor);
            }
          }
        }
        setSvgHtml(new XMLSerializer().serializeToString(doc.documentElement));
      } catch (err) {
        console.error('[Mermaid] 渲染错误:', err);
        setError(err instanceof Error ? err.message : 'Failed to render diagram');
      } finally {
        setIsLoading(false);
      }
    };

    renderDiagram();
  }, [chart, isDark]);

  if (error) {
    console.warn('[Mermaid] 渲染失败，隐藏图表:', error);
    return null;
  }

  return (
    <div className={cn('my-6', className)}>
      {/* 加载状态 */}
      {isLoading && (
        <div className="flex items-center justify-center p-8 rounded-lg border border-border/40">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
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

      {/* 内联缩放视图 */}
      {!isLoading && svgHtml && (
        <ZoomableContainer
          svgHtml={svgHtml}
          minHeight={200}
          extraControls={
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 border-l border-border ml-0.5"
              onClick={() => setDialogOpen(true)}
              title="全屏查看"
            >
              <Expand className="h-3.5 w-3.5" />
            </Button>
          }
        />
      )}

      {/* 全屏对话框 */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent
          className="max-w-[95vw] w-[95vw] h-[90vh] p-0 flex flex-col gap-0 overflow-hidden"
        >
          {/* 对话框标题（屏幕阅读器可见，视觉隐藏）*/}
          <DialogTitle className="sr-only">流程图全屏预览</DialogTitle>

          {/* 对话框头部工具栏区域由 ZoomableContainer 内部的按钮提供，此处仅留关闭按钮空间 */}
          {svgHtml && (
            <ZoomableContainer
              svgHtml={svgHtml}
              fillHeight
              className="flex-1"
              controlsRightOffset={52}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

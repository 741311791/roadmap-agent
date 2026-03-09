'use client';

/**
 * 工作流动画组件 V2 - SVG viewBox 架构
 *
 * 核心改进：
 * - 彻底移除 react-xarrows，改用原生 SVG path + Framer Motion pathLength 动画
 * - 所有节点坐标预先定义在 layout-config.ts，无需 DOM 测量
 * - 通过 foreignObject 将 React/Tailwind/Framer Motion 组件嵌入 SVG 虚拟画布
 * - 浏览器原生处理 viewBox 缩放（GPU 加速），彻底解决响应式拉伸导致连线断裂的问题
 */

import React, { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'motion/react';
import { Sparkles, Database, Code, LineChart, CheckCircle, type LucideIcon } from 'lucide-react';
import { CANVAS, NODES, getSmoothPath } from '@/components/landing/workflow-animation-svg/layout-config';

// ─────────────────────────────────────────────────────────────────────────────
// 类型定义
// ─────────────────────────────────────────────────────────────────────────────

/** NODES 字典中的所有键名（字符串联合类型，避免 symbol 类型导致的 TS 报错） */
type NodeKey = keyof typeof NODES & string;

interface ChildNodeData {
  id: NodeKey;
  label: string;
  delay: number;
  progress: number;
}

interface BranchNodeData {
  id: NodeKey;
  label: string;
  icon: LucideIcon;
  delay: number;
  children: ChildNodeData[];
}

// ─────────────────────────────────────────────────────────────────────────────
// 主组件
// ─────────────────────────────────────────────────────────────────────────────

export function WorkflowAnimationSvg() {
  const t = useTranslations('workflow');

  /**
   * 动画状态机
   * 0: Initial（空白）
   * 1: Typing（打字机效果）
   * 2: Generating（按钮点击脉冲）
   * 3: Expanded（树状结构展开 + 连线生长）
   * 4: Complete（庆祝效果）
   */
  const [step, setStep] = useState(0);

  const treeData: BranchNodeData[] = [
    {
      id: 'foundation',
      label: t('foundation'),
      icon: Code,
      delay: 0.2,
      children: [
        { id: 'syntax', label: t('pythonSyntax'), delay: 0.8, progress: 85 },
        { id: 'env', label: t('virtualEnv'), delay: 1.0, progress: 100 },
        { id: 'types', label: t('typeHinting'), delay: 1.2, progress: 65 },
      ],
    },
    {
      id: 'data',
      label: t('dataHandling'),
      icon: Database,
      delay: 0.6,
      children: [
        { id: 'pandas', label: t('pandas'), delay: 1.2, progress: 75 },
        { id: 'sql', label: t('sqlBasics'), delay: 1.4, progress: 90 },
        { id: 'etl', label: t('etlPipelines'), delay: 1.6, progress: 55 },
      ],
    },
    {
      id: 'analysis',
      label: t('analysis'),
      icon: LineChart,
      delay: 1.0,
      children: [
        { id: 'viz', label: t('dataViz'), delay: 1.6, progress: 80 },
        { id: 'stats', label: t('statistics'), delay: 1.8, progress: 70 },
        { id: 'bi', label: t('biTools'), delay: 2.0, progress: 45 },
      ],
    },
  ];

  // 状态机循环（与原版时序完全一致）
  useEffect(() => {
    const loop = async () => {
      setStep(0);
      await new Promise(r => setTimeout(r, 1000));
      setStep(1);
      await new Promise(r => setTimeout(r, 2000));
      setStep(2);
      await new Promise(r => setTimeout(r, 800));
      setStep(3);
      await new Promise(r => setTimeout(r, 3500));
      setStep(4);
      await new Promise(r => setTimeout(r, 8500));
    };

    loop();
    const timer = setInterval(loop, 17800);
    return () => clearInterval(timer);
  }, []);

  // 预计算连线坐标（起点 = 节点右侧中心，终点 = 节点左侧中心）
  const inputCardRightX = NODES.inputCard.x + NODES.inputCard.width;
  const inputCardCenterY = NODES.inputCard.y + NODES.inputCard.height / 2;

  return (
    <div className="relative w-full py-2">
      {/* 背景光晕（保持在 SVG 外部，避免 filter 性能开销） */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/2 left-1/3 w-64 h-64 bg-sage/10 rounded-full blur-[100px] mix-blend-multiply animate-pulse-slow" />
        <div className="absolute bottom-1/3 right-1/3 w-64 h-64 bg-primary/5 rounded-full blur-[100px] mix-blend-multiply animate-pulse-slow delay-1000" />
      </div>

      {/* ═══════════════════════════════════════════════════════════════
          移动端：纯 DOM 垂直布局（避免 SVG foreignObject 在 WebKit 中的渲染偏差）
      ═══════════════════════════════════════════════════════════════ */}
      <div className="lg:hidden flex flex-col gap-4 max-w-sm mx-auto">
        <InputCard step={step} t={t} />

        <AnimatePresence>
          {step >= 3 && (
            <motion.div
              className="flex flex-col gap-3 pl-4 border-l-2 border-sage/30 ml-4"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.5 }}
            >
              {treeData.map((branch) => {
                const Icon = branch.icon;
                return (
                  <motion.div
                    key={branch.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    transition={{ delay: branch.delay, duration: 0.4 }}
                    className="flex flex-col gap-2"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-sage/10 flex items-center justify-center text-sage shrink-0">
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <span className="text-sm font-medium text-gray-800">{branch.label}</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 pl-9">
                      {branch.children.map((child) => (
                        <motion.span
                          key={child.id}
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: child.delay, duration: 0.3 }}
                          className="text-xs bg-sage/10 text-sage-700 px-2.5 py-1 rounded-full font-medium"
                        >
                          {child.label}
                        </motion.span>
                      ))}
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/*
        桌面端：SVG 主画布
        - viewBox：定义虚拟坐标空间，浏览器原生处理缩放（GPU 加速）
        - overflow-visible：允许庆祝粒子溢出画布边界
      */}
      <svg
        viewBox="0 50 770 680"
        className="relative w-full h-auto hidden lg:block"
        style={{ overflow: 'visible' }}
      >
        {/* ═══════════════════════════════════════════════════════════════
            层级 1：连接路径（底层，不遮挡节点）
            使用 pathLength 动画实现"线条生长"效果，替代 Xarrow
        ═══════════════════════════════════════════════════════════════ */}
        {step >= 3 && treeData.map((branch) => {
          const branchNode = NODES[branch.id];
          const branchLeftX = branchNode.x;
          const branchCenterY = branchNode.y + branchNode.height / 2;
          const branchRightX = branchNode.x + branchNode.width;

          // 入卡 -> 分支节点 的延迟（与原版 Delayed wait 对齐）
          const branchLineDelay = Math.max(0, (branch.delay - 0.2));

          return (
            <React.Fragment key={`paths-${branch.id}`}>
              {/* InputCard → Branch Node */}
              <motion.path
                d={getSmoothPath(inputCardRightX, inputCardCenterY, branchLeftX, branchCenterY)}
                fill="none"
                stroke="hsl(var(--sage))"
                strokeWidth={2.5}
                strokeLinecap="round"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ duration: 0.8, delay: branchLineDelay, ease: 'easeOut' }}
              />

              {/* Branch Node → Child Nodes */}
              {branch.children.map((child) => {
                const childNode = NODES[child.id];
                const childLeftX = childNode.x;
                const childCenterY = childNode.y + childNode.height / 2;
                const childLineDelay = Math.max(0, (child.delay - 0.2));

                return (
                  <motion.path
                    key={`path-${child.id}`}
                    d={getSmoothPath(branchRightX, branchCenterY, childLeftX, childCenterY)}
                    fill="none"
                    stroke="hsl(var(--sage))"
                    strokeWidth={1.5}
                    strokeLinecap="round"
                    initial={{ pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: 1 }}
                    transition={{ duration: 0.6, delay: childLineDelay, ease: 'easeOut' }}
                  />
                );
              })}
            </React.Fragment>
          );
        })}

        {/* ═══════════════════════════════════════════════════════════════
            层级 2：InputCard 节点（始终显示）
        ═══════════════════════════════════════════════════════════════ */}
        <foreignObject
          x={NODES.inputCard.x}
          y={NODES.inputCard.y}
          width={NODES.inputCard.width}
          height={NODES.inputCard.height}
        >
          <div className="w-full h-full">
            <InputCard step={step} t={t} />
          </div>
        </foreignObject>

        {/* ═══════════════════════════════════════════════════════════════
            层级 3：分支节点 + 子节点（step >= 3 时展开）
        ═══════════════════════════════════════════════════════════════ */}
        <AnimatePresence>
          {step >= 3 && treeData.map((branch) => {
            const branchNode = NODES[branch.id];
            const Icon = branch.icon;

            return (
              <React.Fragment key={`nodes-${branch.id}`}>
                {/* Branch Node */}
                <foreignObject
                  x={branchNode.x}
                  y={branchNode.y}
                  width={branchNode.width}
                  height={branchNode.height}
                >
                  <div className="w-full h-full">
                    <BranchCard
                      label={branch.label}
                      icon={Icon}
                      delay={branch.delay}
                    />
                  </div>
                </foreignObject>

                {/* Child Nodes */}
                {branch.children.map((child) => {
                  const childNode = NODES[child.id];
                  return (
                    <foreignObject
                      key={`node-${child.id}`}
                      x={childNode.x}
                      y={childNode.y}
                      width={childNode.width}
                      height={childNode.height}
                    >
                      <div className="w-full h-full">
                        <ChildCard
                          label={child.label}
                          delay={child.delay}
                          progress={child.progress}
                        />
                      </div>
                    </foreignObject>
                  );
                })}
              </React.Fragment>
            );
          })}
        </AnimatePresence>
      </svg>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 子组件：InputCard（左侧输入卡片）
// ─────────────────────────────────────────────────────────────────────────────

function InputCard({ step, t }: { step: number; t: ReturnType<typeof useTranslations> }) {
  return (
    <motion.div
      className="w-full h-full bg-white/70 backdrop-blur-2xl border border-white/50 rounded-3xl p-5 shadow-[0_20px_40px_-12px_rgba(0,0,0,0.1)] relative overflow-hidden"
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* 磨砂玻璃高光反射 */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/40 to-transparent pointer-events-none rounded-3xl" />

      <div className="relative z-10 flex flex-col gap-5 h-full justify-center">
        <h3 className="text-xl font-serif font-semibold text-gray-800">
          {t('inputTitle')}
        </h3>

        {/* 模拟输入框 */}
        <div className="relative">
          <div className="w-full h-10 bg-white/50 border border-sage/30 rounded-xl flex items-center px-3 shadow-inner">
            <span className="text-gray-800 font-medium text-sm whitespace-nowrap overflow-hidden">
              {step === 0 && <span className="animate-pulse">|</span>}
              {step >= 1 && <Typewriter text={t('inputPlaceholder')} />}
            </span>
          </div>

          {/* 鼠标光标动画 */}
          <motion.div
            className="absolute top-6 left-8 pointer-events-none z-50"
            animate={
              step === 1 ? { x: 150, y: 18, opacity: 1 } :
              step === 2 ? { x: 100, y: 55, opacity: 1 } :
              step === 3 ? { x: 100, y: 55, opacity: 0.3 } :
              { opacity: 0 }
            }
            initial={{ opacity: 0 }}
            transition={{ opacity: { duration: step === 3 ? 0.5 : 0.3 } }}
          >
            <motion.div
              animate={
                step === 2 ? {
                  scale: [1, 0.85, 1],
                  transition: { duration: 0.3, times: [0, 0.5, 1], ease: 'easeInOut', delay: 0.3 },
                } : { scale: 1 }
              }
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="drop-shadow-lg">
                <path d="M3 3L10.07 19.97L12.58 12.58L19.97 10.07L3 3Z" fill="black" stroke="white" strokeWidth="2" />
              </svg>
            </motion.div>

            {step === 2 && (
              <motion.div
                className="absolute top-1/2 left-1/2 w-6 h-6 rounded-full border-2 border-black/30 -translate-x-1/2 -translate-y-1/2"
                initial={{ scale: 0.5, opacity: 0.8 }}
                animate={{ scale: 2, opacity: 0 }}
                transition={{ duration: 0.5, ease: 'easeOut', delay: 0.3 }}
              />
            )}
          </motion.div>
        </div>

        {/* 生成按钮 */}
        <motion.div
          animate={
            step === 2 ? { scale: 0.95 } :
            step === 4 ? { scale: [1, 1.05, 1], transition: { duration: 0.5, times: [0, 0.5, 1] } } :
            { scale: 1 }
          }
          className="relative group cursor-pointer"
        >
          {/* 庆祝粒子爆发 */}
          {step === 4 && (
            <>
              {[...Array(8)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute top-1/2 left-1/2 w-2 h-2 rounded-full bg-gradient-to-r from-yellow-400 to-orange-400"
                  initial={{ scale: 0, x: 0, y: 0, opacity: 1 }}
                  animate={{
                    scale: [0, 1, 0],
                    x: Math.cos((i * Math.PI * 2) / 8) * 55,
                    y: Math.sin((i * Math.PI * 2) / 8) * 55,
                    opacity: [1, 1, 0],
                  }}
                  transition={{ duration: 0.8, ease: 'easeOut' }}
                />
              ))}
            </>
          )}

          <div className="absolute -inset-1 bg-gradient-to-r from-sage to-sage/80 rounded-xl blur opacity-20 group-hover:opacity-40 transition duration-200" />
          <div
            className={[
              'relative w-full h-10 bg-sage rounded-xl flex items-center justify-center text-white text-sm font-medium shadow-lg transition-all duration-300 overflow-hidden',
              step >= 2 ? 'shadow-sage/25' : '',
              step === 4 ? 'bg-gradient-to-r from-sage to-emerald-600' : '',
            ].join(' ')}
          >
            {step === 4 ? (
              <motion.span
                className="flex items-center gap-2"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.3 }}
              >
                <CheckCircle className="w-4 h-4" />
                {t('pathComplete')}
              </motion.span>
            ) : step === 3 ? (
              <span className="flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 animate-spin-slow" />
                {t('generating')}
              </span>
            ) : (
              t('generatePath')
            )}

            {/* 点击涟漪效果 */}
            {step === 2 && (
              <motion.div
                className="absolute inset-0 bg-white rounded-xl"
                initial={{ scale: 0, opacity: 0.6 }}
                animate={{ scale: 2, opacity: 0 }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
              />
            )}

            {/* 成功光泽扫过效果 */}
            {step === 4 && (
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                initial={{ x: '-100%' }}
                animate={{ x: '200%' }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
              />
            )}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 子组件：BranchCard（中间层分支节点）
// ─────────────────────────────────────────────────────────────────────────────

function BranchCard({
  label,
  icon: Icon,
  delay,
}: {
  label: string;
  icon: LucideIcon;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.5, delay }}
      className="w-full h-full bg-white/85 backdrop-blur-md border border-sage/30 px-3 py-2 rounded-2xl shadow-[0_2px_10px_rgba(0,0,0,0.08)] flex items-center gap-2.5"
    >
      <div className="w-7 h-7 rounded-full bg-sage/10 flex items-center justify-center text-sage shrink-0">
        <Icon className="w-3.5 h-3.5" />
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-sm font-medium text-gray-800 block mb-1 truncate">{label}</span>
        {/* 分支进度条（始终填满，表示"已规划"） */}
        <div className="h-1 w-full bg-sage/10 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-sage"
            initial={{ width: 0 }}
            animate={{ width: '100%' }}
            transition={{ duration: 1.5, delay: delay + 0.5, ease: 'easeOut' }}
          />
        </div>
      </div>
      {/* 右侧输出连接点 */}
      <div className="absolute top-1/2 -right-1 w-2 h-2 rounded-full bg-white border border-sage -translate-y-1/2 translate-x-1/2" />
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 子组件：ChildCard（右侧子节点）
// ─────────────────────────────────────────────────────────────────────────────

function ChildCard({
  label,
  delay,
  progress,
}: {
  label: string;
  delay: number;
  progress: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -8 }}
      transition={{ duration: 0.4, delay }}
      className="w-full h-full bg-white/70 backdrop-blur-sm border border-sage/25 px-3 py-1.5 rounded-xl shadow-[0_1px_6px_rgba(0,0,0,0.07)] flex flex-col justify-center gap-1.5"
    >
      <div className="flex items-center gap-2">
        <div className="w-1.5 h-1.5 rounded-full bg-sage/60 shrink-0" />
        <span className="text-xs font-medium text-gray-700 truncate">{label}</span>
      </div>
      <div className="h-1 w-full bg-sage/20 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-sage"
          initial={{ width: '0%' }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 1.2, delay: delay + 0.3, ease: 'easeOut' }}
        />
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 工具子组件：打字机效果
// ─────────────────────────────────────────────────────────────────────────────

function Typewriter({ text }: { text: string }) {
  const [displayed, setDisplayed] = useState('');

  useEffect(() => {
    let i = 0;
    const timer = setInterval(() => {
      if (i < text.length) {
        setDisplayed(text.substring(0, i + 1));
        i++;
      } else {
        clearInterval(timer);
      }
    }, 50);
    return () => clearInterval(timer);
  }, [text]);

  return (
    <>
      {displayed}
      <span className="animate-pulse">|</span>
    </>
  );
}

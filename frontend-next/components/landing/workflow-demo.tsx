'use client';

/**
 * WorkflowDemoLanding - 落地页工作流进度演示组件
 *
 * 功能：
 * - 展示 5 个与特性卡片 1:1 映射的工作流节点
 * - 根据当前激活特性 ID 计算各节点状态（completed / current / pending）
 * - 已完成的连线显示 GradientTracing 电流脉冲动画
 * - 当前节点下方显示 AI 动作描述文字（淡入动画）
 * - 纯展示组件，无任务 API 依赖
 */

import dynamic from 'next/dynamic';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'motion/react';
import {
  CheckCircle2,
  Loader2,
  Clock,
  Target,
  Layers,
  ShieldCheck,
  UserCheck,
  BookOpen,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// 动态导入 GradientTracing 避免 SSR 问题
const GradientTracing = dynamic(
  () => import('@/components/ui/gradient-tracing').then(mod => ({ default: mod.GradientTracing })),
  {
    ssr: false,
    loading: () => <div className="w-full h-1 bg-sage-600 rounded-full" />,
  }
);

// ============================================================================
// 类型与常量
// ============================================================================

/** 工作流节点状态 */
type NodeStatus = 'completed' | 'current' | 'pending';

/** 节点 ID → 特性 ID 的反向映射 */
const NODE_TO_FEATURE: Record<string, string> = {
  'analysis': 'identify-gaps',
  'design': 'structured-path',
  'validate': 'structure-validate',
  'review': 'human-review',
  'content': 'content-generation',
};

/** 特性 ID 与工作流节点 ID 的 1:1 映射 */
const FEATURE_TO_NODE: Record<string, string> = {
  'identify-gaps': 'analysis',
  'structured-path': 'design',
  'structure-validate': 'validate',
  'human-review': 'review',
  'content-generation': 'content',
};

/** 节点的排列顺序（用于计算 completed / pending） */
const NODE_ORDER = ['analysis', 'design', 'validate', 'review', 'content'];

/** 节点配置 */
const NODES_CONFIG = [
  {
    id: 'analysis',
    icon: Target,
    labelKey: 'analysis',
    descKey: 'workflowAnalysisDesc',
  },
  {
    id: 'design',
    icon: Layers,
    labelKey: 'design',
    descKey: 'workflowDesignDesc',
  },
  {
    id: 'validate',
    icon: ShieldCheck,
    labelKey: 'validate',
    descKey: 'workflowValidateDesc',
  },
  {
    id: 'review',
    icon: UserCheck,
    labelKey: 'review',
    descKey: 'workflowReviewDesc',
  },
  {
    id: 'content',
    icon: BookOpen,
    labelKey: 'content',
    descKey: 'workflowContentDesc',
  },
];

// ============================================================================
// Props
// ============================================================================

interface WorkflowDemoLandingProps {
  /** 当前激活的特性 ID，由父组件的轮播状态传入 */
  activeFeatureId: string;
  /** 点击节点时通知父组件切换到对应特性，同时暂停轮播 */
  onNodeSelect?: (featureId: string) => void;
}

// ============================================================================
// 主组件
// ============================================================================

export function WorkflowDemoLanding({ activeFeatureId, onNodeSelect }: WorkflowDemoLandingProps) {
  const t = useTranslations('features');

  /** 根据激活特性计算每个节点的状态 */
  const getNodeStatus = (nodeId: string): NodeStatus => {
    const activeNodeId = FEATURE_TO_NODE[activeFeatureId] ?? 'analysis';
    const activeIndex = NODE_ORDER.indexOf(activeNodeId);
    const nodeIndex = NODE_ORDER.indexOf(nodeId);

    if (nodeIndex < activeIndex) return 'completed';
    if (nodeIndex === activeIndex) return 'current';
    return 'pending';
  };

  const activeNodeId = FEATURE_TO_NODE[activeFeatureId] ?? 'analysis';

  return (
    <div className="relative w-full py-6 px-4">
      {/* 节点行 */}
      <div className="relative flex items-start justify-between">
        {/* 连接线层（绝对定位，位于节点下方） */}
        {NODES_CONFIG.map((node, index) => {
          if (index >= NODES_CONFIG.length - 1) return null;

          const fromStatus = getNodeStatus(node.id);
          const toStatus = getNodeStatus(NODES_CONFIG[index + 1].id);
          const isLineCompleted = fromStatus === 'completed' && toStatus !== 'pending'
            || fromStatus === 'completed' && toStatus === 'completed';
          const isLineActive = fromStatus === 'completed';

          const leftPercent = ((index + 0.5) * 100) / NODES_CONFIG.length;
          const widthPercent = 100 / NODES_CONFIG.length;

          return (
            <div
              key={`connector-${index}`}
              className="absolute z-0"
              style={{
                left: `${leftPercent}%`,
                width: `${widthPercent}%`,
                top: '22px',
                height: '4px',
              }}
            >
              {isLineActive ? (
                <div className="w-full h-full">
                  <GradientTracing
                    width={200}
                    height={4}
                    baseColor="#4d6a5b"
                    gradientColors={['#5f8a70', '#7ba88d', '#98c4a9']}
                    animationDuration={1.8}
                    strokeWidth={3}
                    path="M0,2 L200,2"
                    animate={true}
                  />
                </div>
              ) : (
                <div className="w-full h-0 border-t-2 border-dashed border-border" />
              )}
            </div>
          );
        })}

        {/* 节点列 */}
        {NODES_CONFIG.map((node) => {
          const status = getNodeStatus(node.id);
          const Icon = node.icon;
          const isCurrent = status === 'current';
          const isCompleted = status === 'completed';
          const featureId = NODE_TO_FEATURE[node.id];

          return (
            <div
              key={node.id}
              className="relative z-10 flex flex-col items-center"
              style={{ width: `${100 / NODES_CONFIG.length}%` }}
            >
              {/* 节点圆圈 — 可点击按钮 */}
              <motion.button
                initial={false}
                animate={{ scale: isCurrent ? 1.15 : 1 }}
                whileHover={{ scale: isCurrent ? 1.2 : 1.1 }}
                whileTap={{ scale: 0.95 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                onClick={() => onNodeSelect?.(featureId)}
                title={t(node.labelKey as any)}
                className={cn(
                  'flex items-center justify-center w-11 h-11 rounded-full border-4 transition-colors duration-500 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-400 focus-visible:ring-offset-2',
                  isCompleted && 'bg-sage-600 border-sage-600 text-white shadow-md shadow-sage-600/30 hover:bg-sage-700 hover:border-sage-700',
                  isCurrent && 'bg-sage-500 border-sage-500 text-white shadow-lg shadow-sage-500/50',
                  status === 'pending' && 'bg-card border-border text-muted-foreground hover:border-sage-400 hover:text-sage-600'
                )}
              >
                {isCompleted && <CheckCircle2 className="w-5 h-5" />}
                {isCurrent && <Loader2 className="w-5 h-5 animate-spin" />}
                {status === 'pending' && <Icon className="w-5 h-5 opacity-40" />}
              </motion.button>

              {/* 节点标签 */}
              <p
                className={cn(
                  'mt-2 text-xs font-medium text-center transition-colors duration-300',
                  isCompleted && 'text-sage-700',
                  isCurrent && 'text-foreground font-semibold',
                  status === 'pending' && 'text-muted-foreground'
                )}
              >
                {t(node.labelKey as any)}
              </p>

              {/* 当前节点的动作描述文字 */}
              <AnimatePresence mode="wait">
                {isCurrent && (
                  <motion.p
                    key={node.id}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.35 }}
                    className="mt-1 text-[10px] text-center text-sage-600 leading-tight max-w-[80px] hidden sm:block"
                  >
                    {t(node.descKey as any)}
                  </motion.p>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </div>
  );
}

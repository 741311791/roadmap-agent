'use client';

/**
 * TreeConnector - SVG 连接线组件
 * 
 * 使用贝塞尔曲线绘制树节点之间的连接线
 */

import { ConnectionLine, TREE_LAYOUT_CONFIG } from './types';

interface TreeConnectorProps {
  /** 连接线数据列表 */
  connections: ConnectionLine[];
  /** 画布宽度 */
  width: number;
  /** 画布高度 */
  height: number;
}

/**
 * 生成贝塞尔曲线路径
 * 从左向右的水平树连接线
 */
function generatePath(from: { x: number; y: number }, to: { x: number; y: number }): string {
  const radius = TREE_LAYOUT_CONFIG.connectionRadius;
  const midX = from.x + (to.x - from.x) / 2;
  
  // 使用三次贝塞尔曲线，控制点在中间偏向两端
  return `M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`;
}

export function TreeConnector({ connections, width, height }: TreeConnectorProps) {
  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={width}
      height={height}
      style={{ overflow: 'visible' }}
    >
      <defs>
        {/* 渐变定义 - 从 sage 到透明 */}
        <linearGradient id="connection-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="rgb(var(--sage-400))" stopOpacity="0.6" />
          <stop offset="100%" stopColor="rgb(var(--sage-400))" stopOpacity="0.3" />
        </linearGradient>
      </defs>
      
      {connections.map((connection) => (
        <path
          key={connection.id}
          d={generatePath(connection.fromPosition, connection.toPosition)}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          className="text-sage-300/60"
        />
      ))}
    </svg>
  );
}


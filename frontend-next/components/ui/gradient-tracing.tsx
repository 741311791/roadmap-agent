"use client"

/**
 * GradientTracing - 渐变轨迹动画组件
 * 
 * 功能：
 * - 支持自定义路径的渐变轨迹动画
 * - 可配置基础颜色、渐变颜色、动画时长、线宽等
 * - 用于实现拓扑图中已完成路径的电流脉冲效果
 */

import React from "react"
import { motion } from "framer-motion"

interface GradientTracingProps {
  /** 宽度 */
  width: number
  /** 高度 */
  height: number
  /** 基础颜色（背景路径颜色） */
  baseColor?: string
  /** 渐变颜色数组 [起始色, 中间色, 结束色] */
  gradientColors?: [string, string, string]
  /** 动画时长（秒） */
  animationDuration?: number
  /** 线宽 */
  strokeWidth?: number
  /** SVG 路径字符串 */
  path?: string
  /** 是否启用动画 */
  animate?: boolean
}

export const GradientTracing: React.FC<GradientTracingProps> = ({
  width,
  height,
  baseColor = "black",
  gradientColors = ["#2EB9DF", "#2EB9DF", "#9E00FF"],
  animationDuration = 2,
  strokeWidth = 2,
  path = `M0,${height / 2} L${width},${height / 2}`,
  animate = true,
}) => {
  const gradientId = `pulse-${Math.random().toString(36).substr(2, 9)}`

  return (
    <div className="relative w-full h-full">
      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${width} ${height}`}
        fill="none"
        preserveAspectRatio="none"
      >
        {/* 基础路径（静态背景） */}
        <path
          d={path}
          stroke={baseColor}
          strokeOpacity="0.2"
          strokeWidth={strokeWidth}
          vectorEffect="non-scaling-stroke"
        />
        {/* 渐变动画路径 */}
        <path
          d={path}
          stroke={`url(#${gradientId})`}
          strokeLinecap="round"
          strokeWidth={strokeWidth}
          vectorEffect="non-scaling-stroke"
        />
        <defs>
          <motion.linearGradient
            animate={animate ? {
              x1: [0, width * 2],
              x2: [0, width],
            } : undefined}
            transition={{
              duration: animationDuration,
              repeat: Infinity,
              ease: "linear",
            }}
            id={gradientId}
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor={gradientColors[0]} stopOpacity="0" />
            <stop stopColor={gradientColors[1]} />
            <stop offset="1" stopColor={gradientColors[2]} stopOpacity="0" />
          </motion.linearGradient>
        </defs>
      </svg>
    </div>
  )
}


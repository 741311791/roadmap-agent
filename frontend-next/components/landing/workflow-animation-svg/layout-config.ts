/**
 * 工作流动画 - 画布坐标配置
 *
 * 基于 SVG viewBox 的虚拟坐标系（1200 × 800）。
 * 所有节点坐标预先定义，无需 DOM 测量，连线由数学计算生成。
 */

/** 画布尺寸（viewBox 虚拟单位） */
export const CANVAS = { width: 1200, height: 800 };

/**
 * 节点坐标与尺寸（x, y 为左上角，width/height 为宽高）
 *
 * 垂直分布说明：
 * - InputCard 垂直居中于整个画布（y=240，高300，中心 y=390）
 * - 三个分支节点等距分布：centers 在 y=175 / 400 / 625
 * - 每组 3 个子节点以对应分支为中心垂直排列，间距 62px
 */
export const NODES = {
  /** 左侧输入卡片 */
  inputCard: { x: 15, y: 240, width: 295, height: 300 },

  /** 分支节点（中间层，与 InputCard 右边缘间距 50px） */
  foundation: { x: 360, y: 140, width: 165, height: 70 },
  data:       { x: 360, y: 365, width: 165, height: 70 },
  analysis:   { x: 360, y: 590, width: 165, height: 70 },

  /** 子节点（右侧层，与分支右边缘间距 50px，每组间距 62px） */
  syntax: { x: 575, y:  87, width: 160, height: 52 },
  env:    { x: 575, y: 149, width: 160, height: 52 },
  types:  { x: 575, y: 211, width: 160, height: 52 },

  pandas: { x: 575, y: 312, width: 160, height: 52 },
  sql:    { x: 575, y: 374, width: 160, height: 52 },
  etl:    { x: 575, y: 436, width: 160, height: 52 },

  viz:    { x: 575, y: 537, width: 160, height: 52 },
  stats:  { x: 575, y: 599, width: 160, height: 52 },
  bi:     { x: 575, y: 661, width: 160, height: 52 },
} as const;

/**
 * 生成平滑贝塞尔曲线路径（替代 react-xarrows）
 *
 * 使用 cubic bezier：以水平方向中点作为两个控制点，
 * 实现左右连线的平滑 S 形过渡。
 *
 * @param startX 起点 X（通常为节点右侧边缘）
 * @param startY 起点 Y（通常为节点垂直中心）
 * @param endX   终点 X（通常为目标节点左侧边缘）
 * @param endY   终点 Y（通常为目标节点垂直中心）
 * @returns SVG path 的 d 属性字符串
 */
export function getSmoothPath(
  startX: number,
  startY: number,
  endX: number,
  endY: number,
): string {
  const midX = startX + (endX - startX) / 2;
  return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
}

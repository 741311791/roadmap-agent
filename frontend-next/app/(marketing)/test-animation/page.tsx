/**
 * 工作流动画测试页面
 *
 * 用于在真实落地页布局外独立预览 SVG 动画组件。
 * 访问路径：/test-animation
 */

import { WorkflowAnimationSvg } from '@/components/landing/workflow-animation-svg';

export default function TestAnimationPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-cream/50 to-white py-12">
      <section className="max-w-6xl mx-auto px-4 space-y-4">
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700 border border-emerald-200">
            SVG viewBox
          </span>
          <h2 className="text-lg font-semibold text-gray-800">
            工作流动画组件预览
          </h2>
        </div>
        <div className="rounded-2xl border border-sage/20 bg-white/60 backdrop-blur-sm shadow-sm overflow-hidden">
          <WorkflowAnimationSvg />
        </div>
      </section>
    </div>
  );
}

'use client';

/**
 * 工作流动画组件 - Frosted Glass Mind Map (磨砂树脂思维导图)
 * 
 * 视觉风格：
 * - 核心：Input Card (What are your goals?)
 * - 展开：分支结构 (Tree Structure)
 * - 质感：高级磨砂玻璃 (Frosted Resin/Glass)
 * - 动画：生成路径的流体动画 (从左向右生长)
 * - 主题：Sage & Cream
 * - 连线：使用 react-xarrows 实现精准连接
 */

import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Sparkles, Database, Code, LineChart, CheckCircle, PartyPopper } from 'lucide-react';
import Xarrow, { Xwrapper, useXarrow } from 'react-xarrows';

// 丰富的数据结构
const treeData = [
  {
    id: 'foundation',
    label: 'Foundation',
    icon: Code,
    delay: 0.2,
    children: [
      { id: 'syntax', label: 'Python Syntax', delay: 0.8, progress: 85 },
      { id: 'env', label: 'Virtual Env', delay: 1.0, progress: 100 },
      { id: 'types', label: 'Type Hinting', delay: 1.2, progress: 65 },
    ]
  },
  {
    id: 'data',
    label: 'Data Handling',
    icon: Database,
    delay: 0.6,
    children: [
      { id: 'pandas', label: 'Pandas', delay: 1.2, progress: 75 },
      { id: 'sql', label: 'SQL Basics', delay: 1.4, progress: 90 },
      { id: 'etl', label: 'ETL Pipelines', delay: 1.6, progress: 55 },
    ]
  },
  {
    id: 'analysis',
    label: 'Analysis',
    icon: LineChart,
    delay: 1.0,
    children: [
      { id: 'viz', label: 'Data Viz', delay: 1.6, progress: 80 },
      { id: 'stats', label: 'Statistics', delay: 1.8, progress: 70 },
      { id: 'bi', label: 'BI Tools', delay: 2.0, progress: 45 },
    ]
  }
];

export function WorkflowAnimation() {
  const [step, setStep] = useState(0);
  // 0: Initial
  // 1: Typing
  // 2: Generating (Pulse)
  // 3: Expanded
  // 4: Complete (Celebration)

  useEffect(() => {
    const loop = async () => {
      // Reset
      setStep(0);
      
      // Step 1: Start Typing
      await new Promise(r => setTimeout(r, 1000));
      setStep(1);
      
      // Step 2: Generate Click
      await new Promise(r => setTimeout(r, 2000));
      setStep(2);
      
      // Step 3: Expand Tree
      await new Promise(r => setTimeout(r, 800));
      setStep(3);

      // Step 4: Complete (等待所有动画完成)
      await new Promise(r => setTimeout(r, 3500));
      setStep(4);

      // Loop delay
      await new Promise(r => setTimeout(r, 8500));
      // Loop restarts
    };

    loop();
    // 整个循环周期
    const timer = setInterval(loop, 17800); 
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="relative w-full h-[600px] flex items-center justify-center p-4">
      {/* Background Glows (Theme Adapted) */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/3 w-64 h-64 bg-sage/10 rounded-full blur-[100px] mix-blend-multiply animate-pulse-slow" />
        <div className="absolute bottom-1/3 right-1/3 w-64 h-64 bg-primary/5 rounded-full blur-[100px] mix-blend-multiply animate-pulse-slow delay-1000" />
      </div>

      <Xwrapper>
        <div className="relative z-10 flex items-center w-full max-w-6xl">
          
          {/* Left: Input Card */}
          <div className="relative z-20 shrink-0 mr-12 lg:mr-24 self-center">
            <InputCard step={step} />
            
            {/* Connection Point (Output) - Visible only when connecting */}
            {step >= 3 && (
              <motion.div 
                id="input-card-output"
                className="absolute top-1/2 -right-3 w-4 h-4 rounded-full bg-sage border-2 border-white shadow-[0_0_10px_hsl(var(--sage))] z-30 translate-y-[-50%]"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
              />
            )}
          </div>

          {/* Right: Tree Structure */}
          <div className="flex-1 relative">
            <AnimatePresence>
              {step >= 3 && (
                <TreeStructure />
              )}
            </AnimatePresence>
          </div>

          {/* Arrows Layer - Global Overlay */}
          <div className="absolute inset-0 pointer-events-none z-0">
             {step >= 3 && <ArrowsLayer />}
          </div>

        </div>
      </Xwrapper>
    </div>
  );
}

function InputCard({ step }: { step: number }) {
  return (
    <motion.div 
      className="w-[300px] sm:w-[340px] bg-white/70 backdrop-blur-2xl border border-white/50 rounded-3xl p-6 shadow-[0_20px_40px_-12px_rgba(0,0,0,0.1)] relative overflow-hidden"
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* Glossy Reflection */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/40 to-transparent pointer-events-none" />
      
      <div className="relative z-10 space-y-6">
        <div>
          <h3 className="text-2xl font-serif font-semibold text-gray-800 mb-2">
            What are your goals?
          </h3>
        </div>

        {/* Input Field Simulation */}
        <div className="relative">
          <div className="w-full h-12 bg-white/50 border border-sage/30 rounded-xl flex items-center px-4 shadow-inner transition-colors duration-300 focus-within:border-sage">
            <span className="text-gray-800 font-medium whitespace-nowrap overflow-hidden">
              {step === 0 && <span className="animate-pulse">|</span>}
              {step >= 1 && (
                <Typewriter text="Master Python data science" />
              )}
            </span>
          </div>
          {/* Cursor Mouse */}
          <motion.div
            className="absolute top-8 left-10 pointer-events-none z-50"
            animate={
              step === 1 ? { x: 180, y: 20, opacity: 1 } : 
              step === 2 ? { x: 120, y: 60, opacity: 1 } : 
              step === 3 ? { x: 120, y: 60, opacity: 0.3 } : 
              { opacity: 0 }
            }
            initial={{ opacity: 0 }}
            transition={{ opacity: { duration: step === 3 ? 0.5 : 0.3 } }}
          >
            {/* Mouse Cursor with Click Animation */}
            <motion.div
              animate={
                step === 2 ? {
                  scale: [1, 0.85, 1],
                  transition: { 
                    duration: 0.3,
                    times: [0, 0.5, 1],
                    ease: "easeInOut",
                    delay: 0.3
                  }
                } : { scale: 1 }
              }
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="drop-shadow-lg">
                <path d="M3 3L10.07 19.97L12.58 12.58L19.97 10.07L3 3Z" fill="black" stroke="white" strokeWidth="2"/>
              </svg>
            </motion.div>
            
            {/* Click Flash Effect */}
            {step === 2 && (
              <motion.div
                className="absolute top-1/2 left-1/2 w-8 h-8 rounded-full border-2 border-black/30 -translate-x-1/2 -translate-y-1/2"
                initial={{ scale: 0.5, opacity: 0.8 }}
                animate={{ scale: 2, opacity: 0 }}
                transition={{ duration: 0.5, ease: "easeOut", delay: 0.3 }}
              />
            )}
          </motion.div>
        </div>

        {/* Button */}
        <motion.div
          animate={
            step === 2 ? { scale: 0.95 } : 
            step === 4 ? { scale: [1, 1.05, 1], transition: { duration: 0.5, times: [0, 0.5, 1] } } : 
            { scale: 1 }
          }
          className="relative group cursor-pointer"
        >
          {/* Celebration Burst Effect */}
          {step === 4 && (
            <>
              {[...Array(8)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute top-1/2 left-1/2 w-2 h-2 rounded-full bg-gradient-to-r from-yellow-400 to-orange-400"
                  initial={{ scale: 0, x: 0, y: 0, opacity: 1 }}
                  animate={{ 
                    scale: [0, 1, 0],
                    x: Math.cos((i * Math.PI * 2) / 8) * 60,
                    y: Math.sin((i * Math.PI * 2) / 8) * 60,
                    opacity: [1, 1, 0]
                  }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                />
              ))}
            </>
          )}
          
          <div className="absolute -inset-1 bg-gradient-to-r from-sage to-sage/80 rounded-xl blur opacity-20 group-hover:opacity-40 transition duration-200" />
          <div className={`relative w-full h-12 bg-sage rounded-xl flex items-center justify-center text-white font-medium shadow-lg transition-all duration-300 overflow-hidden ${step >= 2 ? 'shadow-sage/25' : ''} ${step === 4 ? 'bg-gradient-to-r from-sage to-emerald-600' : ''}`}>
            {step === 4 ? (
              <motion.span 
                className="flex items-center gap-2"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.3 }}
              >
                <CheckCircle className="w-5 h-5" />
                Path Complete!
              </motion.span>
            ) : step === 3 ? (
              <span className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 animate-spin-slow" />
                Generating...
              </span>
            ) : (
              "Generate Path"
            )}
            
            {/* Click Ripple Effect */}
            {step === 2 && (
              <motion.div
                className="absolute inset-0 bg-white rounded-xl"
                initial={{ scale: 0, opacity: 0.6 }}
                animate={{ scale: 2, opacity: 0 }}
                transition={{ duration: 0.6, ease: "easeOut" }}
              />
            )}
            
            {/* Success Shine Effect */}
            {step === 4 && (
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                initial={{ x: "-100%" }}
                animate={{ x: "200%" }}
                transition={{ duration: 0.8, ease: "easeOut" }}
              />
            )}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}

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

  return <>{displayed}<span className="animate-pulse">|</span></>;
}

// 延迟显示组件，用于控制箭头绘制时机
function Delayed({ children, wait }: { children: React.ReactNode; wait: number }) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setShow(true), wait);
    return () => clearTimeout(timer);
  }, [wait]);
  return show ? <>{children}</> : null;
}

function TreeStructure() {
  return (
    <div className="relative w-full h-full flex flex-col justify-center">
      {/* DOM Nodes Layer */}
      <div className="flex flex-col gap-12 py-4"> {/* Increased gap from 10 to 12 */}
        {treeData.map((branch, i) => (
           <BranchNodeRow key={branch.id} branch={branch} />
        ))}
      </div>
    </div>
  );
}

function ArrowsLayer() {
  const updateXarrow = useXarrow();
  const [ready, setReady] = useState(false);

  // 延迟渲染以确保节点已布局
  useEffect(() => {
    const timer = setTimeout(() => {
        setReady(true);
        updateXarrow();
    }, 600);
    return () => clearTimeout(timer);
  }, [updateXarrow]);

  if (!ready) return null;

  return (
    <>
      {treeData.map((branch) => (
        <React.Fragment key={`arrows-${branch.id}`}>
            {/* Input Card -> Branch Node */}
            <Delayed wait={Math.max(0, (branch.delay - 0.2) * 1000)}>
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                >
                    <Xarrow
                        start="input-card-output"
                        end={`branch-${branch.id}-input`}
                        startAnchor="right"
                        endAnchor="left"
                        curveness={0.5}
                        color="hsl(var(--sage))"
                        strokeWidth={2}
                        headSize={0}
                        path="smooth"
                        zIndex={0}
                    />
                </motion.div>
            </Delayed>
            
            {/* Branch Node -> Child Nodes */}
            {branch.children.map((child) => (
                <Delayed key={`arrow-wrapper-${child.id}`} wait={Math.max(0, (child.delay - 0.2) * 1000)}>
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.6, ease: "easeOut" }}
                    >
                        <Xarrow
                            key={`arrow-${child.id}`}
                            start={`branch-${branch.id}-output`}
                            end={`child-${child.id}-input`}
                            startAnchor="right"
                            endAnchor="left"
                            curveness={0.4}
                            color="hsl(var(--sage))"
                            strokeWidth={1.5}
                            headSize={0}
                            path="smooth"
                            zIndex={0}
                            showHead={false}
                        />
                    </motion.div>
                </Delayed>
            ))}
        </React.Fragment>
      ))}
    </>
  );
}

function BranchNodeRow({ branch }: { branch: any }) {
  const Icon = branch.icon;
  
  return (
    <div className="flex items-center gap-12 w-full">
      {/* Level 1: Branch Node Wrapper - Static Layout */}
      <div className="relative group">
        
        {/* Connection Anchors (Static) */}
        <div id={`branch-${branch.id}-input`} className="absolute top-1/2 -left-3 w-2 h-2 rounded-full bg-transparent transform -translate-y-1/2" />
        <div id={`branch-${branch.id}-output`} className="absolute top-1/2 -right-3 w-2 h-2 rounded-full bg-transparent transform -translate-y-1/2" />
        
        {/* Animated Content */}
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: branch.delay }}
            className="glass-capsule bg-white/80 backdrop-blur-md border border-white/60 px-4 py-3 rounded-2xl shadow-sm hover:shadow-md transition-all flex items-center gap-3 w-[180px] relative z-10 hover:shadow-sage/20 hover:border-sage/30"
        >
          {/* Node Glow Effect */}
          <div className="absolute inset-0 rounded-2xl bg-sage/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-xl -z-10" />
          
          <div className="w-8 h-8 rounded-full bg-sage/10 flex items-center justify-center text-sage">
            <Icon className="w-4 h-4" />
          </div>
          <div className="flex-1">
            <span className="text-sm font-medium text-gray-800 block mb-1">{branch.label}</span>
            {/* Progress Bar */}
            <div className="h-1 w-full bg-sage/10 rounded-full overflow-hidden">
                <motion.div 
                    className="h-full bg-sage"
                    initial={{ width: 0 }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 1.5, delay: branch.delay + 0.5, ease: "easeOut" }}
                />
            </div>
          </div>
          
          {/* Subtle Output Dot on Node */}
          <div className="absolute top-1/2 -right-1 w-2 h-2 rounded-full bg-white border border-sage transform -translate-y-1/2 translate-x-[50%]" />
        </motion.div>
      </div>

      {/* Level 2: Children Column */}
      <div className="flex flex-col gap-4"> {/* Increased gap from 3 to 4 */}
        {branch.children.map((child: any) => (
          <div key={child.id} className="relative z-10 group/child">
            {/* Connection Anchor (Static) */}
            <div id={`child-${child.id}-input`} className="absolute top-1/2 -left-3 w-1 h-1 rounded-full bg-transparent transform -translate-y-1/2" />
            
            {/* Animated Content */}
            <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: child.delay }}
                className="glass-capsule-sm bg-white/50 backdrop-blur-sm border border-white/40 px-3 py-2.5 rounded-xl shadow-sm flex flex-col gap-2 min-w-[160px] hover:shadow-sage/10 hover:bg-white/60 transition-all"
            >
               <div className="flex items-center gap-2">
                   <div className="w-1.5 h-1.5 rounded-full bg-sage/50" />
                   <span className="text-xs font-medium text-gray-700">{child.label}</span>
                   {/* Circular Progress Indicator */}
                   <motion.div
                     className="ml-auto relative"
                     initial={{ opacity: 0 }}
                     animate={{ opacity: 1 }}
                     transition={{ delay: child.delay + 0.5 }}
                   >
                     <svg
                       width="24"
                       height="24"
                       viewBox="0 0 24 24"
                       role="img"
                       aria-label={`Progress: ${child.progress}%`}
                       className="transform -rotate-90"
                     >
                       {/* Background track */}
                       <circle
                         cx="12"
                         cy="12"
                         r="9"
                         fill="transparent"
                         stroke="hsl(var(--sage))"
                         strokeOpacity="0.15"
                         strokeWidth="2.5"
                       />
                       {/* Animated foreground progress bar */}
                       <motion.circle
                         cx="12"
                         cy="12"
                         r="9"
                         fill="transparent"
                         stroke="hsl(var(--sage))"
                         strokeWidth="2.5"
                         strokeLinecap="round"
                         strokeDasharray={56.55} // 2 * PI * r = 2 * 3.14159 * 9 ≈ 56.55
                         initial={{ strokeDashoffset: 56.55 }}
                         animate={{ strokeDashoffset: 56.55 * (1 - child.progress / 100) }}
                         transition={{ duration: 1.5, delay: child.delay + 0.6, ease: "easeOut" }}
                       />
                     </svg>
                   </motion.div>
               </div>
               
               {/* Child Progress Bar */}
               <div className="px-2">
                   <div className="h-1 w-full bg-sage/20 rounded-full overflow-hidden">
                        <motion.div 
                            className="h-full bg-sage"
                            initial={{ width: "0%" }}
                            animate={{ width: `${child.progress}%` }}
                            transition={{ duration: 1.2, delay: child.delay + 0.3, ease: "easeOut" }}
                        />
                   </div>
               </div>
            </motion.div>
          </div>
        ))}
      </div>
    </div>
  );
}

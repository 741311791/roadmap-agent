"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence, useScroll, useTransform } from "framer-motion";
import { 
  ArrowRight, 
  Brain, 
  Sparkles, 
  Layers, 
  MessageSquare, 
  CheckCircle2, 
  Play, 
  Code2, 
  FileText,
  Menu,
  X
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

// --- THEME CONSTANTS (Editorial Sage) ---
const THEME = {
  bg: "#1c1917", // Deep Warm Charcoal
  text: "#fafaf9", // Editorial Cream
  sage: "#7d9c86", // Luminous Sage
  sageDim: "rgba(125, 156, 134, 0.1)",
  sageGlow: "rgba(125, 156, 134, 0.4)",
  glass: "rgba(255, 255, 255, 0.03)",
  glassBorder: "rgba(255, 255, 255, 0.08)",
};

// --- COMPONENTS ---

// 知识粒子球组件 - 增强版
const KnowledgeSphere = () => {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isHovering, setIsHovering] = useState(false);

  // 生成粒子位置（球面分布算法）
  const particles = React.useMemo(() => {
    const particleCount = 60;
    const particles = [];
    
    for (let i = 0; i < particleCount; i++) {
      // 使用 Fibonacci Sphere 算法实现均匀分布
      const phi = Math.acos(-1 + (2 * i) / particleCount);
      const theta = Math.sqrt(particleCount * Math.PI) * phi;
      
      // 不同半径创建多层
      const layer = Math.floor(i / 20);
      const radius = 35 + layer * 8; // 35%, 43%, 51%
      
      const x = 50 + radius * Math.cos(theta) * Math.sin(phi);
      const y = 50 + radius * Math.sin(theta) * Math.sin(phi);
      const z = Math.cos(phi); // -1 to 1 (用于深度感)
      
      particles.push({
        id: i,
        x,
        y,
        z,
        layer,
        size: z > 0 ? 12 : 8, // 前景粒子更大
        brightness: (z + 1) / 2, // 0 到 1
      });
    }
    return particles;
  }, []);

  // 生成连接线（距离近的粒子连接）
  const connections = React.useMemo(() => {
    const connections = [];
    const maxDistance = 25; // 连接阈值
    
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < maxDistance) {
          connections.push({
            from: particles[i],
            to: particles[j],
            opacity: (1 - distance / maxDistance) * 0.3,
          });
        }
      }
    }
    return connections;
  }, [particles]);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setMousePosition({
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    });
  };

  return (
    <div 
      className="relative h-[500px] flex items-center justify-center"
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {/* 中央核心光晕 */}
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
        <motion.div
          className="w-24 h-24 rounded-full bg-[#7d9c86]/30 blur-2xl"
          animate={{
            scale: isHovering ? [1, 1.15, 1] : [1, 1.05, 1],
            opacity: [0.3, 0.4, 0.3],
          }}
          transition={{
            duration: 5,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      </div>

      <motion.div 
        animate={{ rotate: 360 }}
        transition={{ duration: 120, repeat: Infinity, ease: "linear" }}
        className="relative w-full h-full max-w-[500px] max-h-[500px]"
      >
        {/* SVG 容器 - 用于绘制连接线 */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
          <defs>
            {/* 发光效果滤镜 */}
            <filter id="glow">
              <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
            
            {/* 脉冲动画渐变 */}
            <linearGradient id="pulseGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#7d9c86" stopOpacity="0">
                <animate attributeName="offset" values="0;1;0" dur="5s" repeatCount="indefinite" />
              </stop>
              <stop offset="50%" stopColor="#7d9c86" stopOpacity="0.6">
                <animate attributeName="offset" values="0.5;1;0.5" dur="5s" repeatCount="indefinite" />
              </stop>
              <stop offset="100%" stopColor="#7d9c86" stopOpacity="0">
                <animate attributeName="offset" values="1;1;1" dur="5s" repeatCount="indefinite" />
              </stop>
            </linearGradient>
          </defs>

          {/* 绘制连接线 */}
          {connections.map((conn, i) => (
            <motion.line
              key={i}
              x1={`${conn.from.x}%`}
              y1={`${conn.from.y}%`}
              x2={`${conn.to.x}%`}
              y2={`${conn.to.y}%`}
              stroke="#7d9c86"
              strokeWidth="1"
              strokeOpacity={conn.opacity}
              initial={{ pathLength: 0 }}
              animate={{ 
                pathLength: 1,
                strokeOpacity: isHovering ? conn.opacity * 1.5 : conn.opacity,
              }}
              transition={{ 
                pathLength: { duration: 3, delay: i * 0.015, ease: "easeInOut" },
                strokeOpacity: { duration: 1, ease: "easeInOut" }
              }}
            />
          ))}

          {/* 轨道圈 */}
          {[30, 40, 50].map((r, i) => (
            <circle
              key={i}
              cx="50%"
              cy="50%"
              r={`${r}%`}
              stroke="#7d9c86"
              strokeWidth="0.5"
              fill="none"
              opacity={0.05 + i * 0.02}
              strokeDasharray="4 8"
            >
              <animateTransform
                attributeName="transform"
                type="rotate"
                from={`0 250 250`}
                to={`${360 * (i % 2 === 0 ? 1 : -1)} 250 250`}
                dur={`${50 + i * 15}s`}
                repeatCount="indefinite"
              />
            </circle>
          ))}
        </svg>

        {/* 粒子节点 */}
        {particles.map((particle) => {
          const distanceToMouse = isHovering
            ? Math.sqrt(
                Math.pow(particle.x - mousePosition.x, 2) +
                Math.pow(particle.y - mousePosition.y, 2)
              )
            : 100;
          const isNearMouse = distanceToMouse < 15;

          return (
            <motion.div
              key={particle.id}
              className="absolute rounded-full"
              style={{
                top: `${particle.y}%`,
                left: `${particle.x}%`,
                width: `${particle.size}px`,
                height: `${particle.size}px`,
                transform: 'translate(-50%, -50%)',
                zIndex: Math.floor(particle.brightness * 10),
              }}
              animate={{
                scale: isNearMouse ? [1, 1.5, 1.3] : [1, 1.08, 1],
                opacity: particle.brightness * 0.5 + 0.4,
              }}
              transition={{
                scale: {
                  duration: isNearMouse ? 0.5 : 4 + Math.random() * 3,
                  repeat: Infinity,
                  ease: "easeInOut",
                },
                opacity: {
                  duration: 5 + Math.random() * 2,
                  repeat: Infinity,
                  repeatType: "reverse",
                  ease: "easeInOut",
                },
              }}
            >
              {/* 粒子核心 */}
              <div 
                className="absolute inset-0 rounded-full bg-[#7d9c86]"
                style={{
                  boxShadow: `0 0 ${isNearMouse ? '20px' : '10px'} rgba(125, 156, 134, ${particle.brightness * 0.8})`,
                }}
              />
              
              {/* 粒子光晕 */}
              <motion.div
                className="absolute inset-0 rounded-full bg-[#7d9c86] blur-sm"
                animate={{
                  scale: [1, 1.3, 1],
                  opacity: [0.3, 0.15, 0.3],
                }}
                transition={{
                  duration: 4,
                  repeat: Infinity,
                  delay: particle.id * 0.05,
                  ease: "easeInOut",
                }}
              />

              {/* 脉冲波纹（前景粒子特效）*/}
              {particle.z > 0.5 && (
                <motion.div
                  className="absolute inset-0 rounded-full border border-[#7d9c86]"
                  initial={{ scale: 1, opacity: 0.4 }}
                  animate={{
                    scale: [1, 2.2],
                    opacity: [0.4, 0],
                  }}
                  transition={{
                    duration: 3.5,
                    repeat: Infinity,
                    delay: particle.id * 0.1,
                    ease: "easeOut",
                  }}
                />
              )}
            </motion.div>
          );
        })}

        {/* 能量流动路径（随机出现的流光）*/}
        {[...Array(2)].map((_, i) => (
          <motion.div
            key={`flow-${i}`}
            className="absolute w-1 h-1 rounded-full bg-[#7d9c86]"
            style={{
              top: `${50 + 40 * Math.sin(i * 2)}%`,
              left: `${50 + 40 * Math.cos(i * 2)}%`,
              filter: 'blur(2px)',
            }}
            animate={{
              x: [0, Math.random() * 80 - 40, 0],
              y: [0, Math.random() * 80 - 40, 0],
              opacity: [0, 0.6, 0],
              scale: [0, 1.5, 0],
            }}
            transition={{
              duration: 6 + Math.random() * 3,
              repeat: Infinity,
              delay: i * 3,
              ease: "easeInOut",
            }}
          />
        ))}
      </motion.div>
    </div>
  );
};

const Navigation = () => (
  <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-[#1c1917]/80 backdrop-blur-md">
    <div className="container mx-auto px-6 h-16 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-full bg-[#7d9c86] flex items-center justify-center">
          <Brain className="w-5 h-5 text-[#1c1917]" />
        </div>
        <span className="font-serif text-xl font-bold tracking-tight text-[#fafaf9]">Muset</span>
      </div>
      <div className="hidden md:flex items-center gap-8 text-sm font-medium text-[#fafaf9]/70">
        <a href="#" className="hover:text-[#7d9c86] transition-colors">Methodology</a>
        <a href="#" className="hover:text-[#7d9c86] transition-colors">Pricing</a>
        <a href="#" className="hover:text-[#7d9c86] transition-colors">About</a>
        <Button variant="ghost" className="text-[#fafaf9] hover:text-[#7d9c86]">Sign In</Button>
        <Button className="bg-[#7d9c86] text-[#1c1917] hover:bg-[#6b8a74]">Get Started</Button>
      </div>
    </div>
  </nav>
);

const HeroSection = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-20">
      {/* Background Noise Texture */}
      <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='1'/%3E%3C/svg%3E")` }} />
      
      {/* Animated Gradient Orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[#7d9c86]/20 rounded-full blur-[128px] animate-pulse-slow" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[#7d9c86]/10 rounded-full blur-[128px] animate-pulse-slow delay-1000" />

      <div className="container mx-auto px-6 relative z-10 grid md:grid-cols-2 gap-12 items-center">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="space-y-8"
        >
          <Badge variant="outline" className="border-[#7d9c86]/50 text-[#7d9c86] px-4 py-1 uppercase tracking-wider text-xs">
            <Sparkles className="w-3 h-3 mr-2" />
            AI-Powered Cognitive Evolution
          </Badge>
          
          <h1 className="font-serif text-6xl md:text-7xl lg:text-8xl leading-[0.9] text-[#fafaf9]">
            Master Any Skill<br />
            <span className="text-[#7d9c86] italic">Intelligently.</span>
          </h1>
          
          <p className="text-xl text-[#fafaf9]/60 max-w-md leading-relaxed">
            Stop learning randomly. Our AI architects analyze your blind spots and build a dynamic, living curriculum tailored to your brain.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 pt-4">
            <div className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-[#7d9c86] to-[#5a7561] rounded-lg blur opacity-30 group-hover:opacity-100 transition duration-1000 group-hover:duration-200"></div>
              <Input 
                placeholder="Enter email to join waitlist" 
                className="relative bg-[#1c1917] border-[#7d9c86]/30 text-[#fafaf9] placeholder:text-[#fafaf9]/30 h-12 min-w-[300px]"
              />
            </div>
            <Button size="lg" className="bg-[#7d9c86] text-[#1c1917] hover:bg-[#6b8a74] h-12 px-8 font-semibold">
              Join Waitlist
            </Button>
          </div>
          
          <div className="flex items-center gap-4 text-sm text-[#fafaf9]/40">
            <div className="flex -space-x-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="w-8 h-8 rounded-full bg-[#2c2927] border border-[#1c1917] flex items-center justify-center text-xs">
                  {i}
                </div>
              ))}
            </div>
            <span>2,400+ learners in queue</span>
          </div>
        </motion.div>

        {/* 3D Particle Sphere Simulation */}
        <KnowledgeSphere />
      </div>
    </section>
  );
};

const RoadmapSection = () => {
  const { scrollYProgress } = useScroll();
  
  return (
    <section className="py-32 relative bg-[#1c1917] overflow-hidden">
      <div className="container mx-auto px-6">
        <div className="text-center mb-20 space-y-4">
          <h2 className="font-serif text-4xl md:text-5xl text-[#fafaf9]">Structured for Mastery</h2>
          <p className="text-[#fafaf9]/60 max-w-2xl mx-auto">
            From macro stages to micro concepts. See the forest and the trees.
          </p>
        </div>

        <div className="relative max-w-4xl mx-auto">
          {/* Vertical Line */}
          <div className="absolute left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-[#7d9c86] to-transparent opacity-50 transform -translate-x-1/2" />

          <div className="space-y-24 relative z-10">
            {/* Stage Card */}
            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              className="bg-[#2c2927]/50 backdrop-blur-md border border-[#7d9c86]/20 p-8 rounded-2xl relative"
            >
              <div className="absolute -left-3 top-1/2 w-6 h-6 bg-[#1c1917] border-2 border-[#7d9c86] rounded-full transform -translate-y-1/2 hidden md:block" style={{ left: 'calc(-1.5rem - 1px)' }}></div>
              <Badge className="bg-[#7d9c86] text-[#1c1917] mb-4">Stage 1</Badge>
              <h3 className="font-serif text-3xl text-[#fafaf9] mb-2">Foundations of Cognitive Science</h3>
              <p className="text-[#fafaf9]/60">Master the core principles of memory, attention, and learning theory.</p>
            </motion.div>

            {/* Module Card */}
            <motion.div 
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="ml-auto w-full md:w-2/3 bg-[#2c2927]/30 backdrop-blur-md border border-white/5 p-6 rounded-xl relative group hover:border-[#7d9c86]/30 transition-colors"
            >
              <div className="absolute -left-[calc(16.666%+1.5rem)] top-1/2 w-4 h-4 bg-[#7d9c86] rounded-full transform -translate-y-1/2 hidden md:block shadow-[0_0_10px_#7d9c86]"></div>
              <div className="flex items-center gap-3 mb-2">
                <Layers className="w-5 h-5 text-[#7d9c86]" />
                <h4 className="font-medium text-xl text-[#fafaf9]">Module 1.2: Neural Plasticity</h4>
              </div>
              <p className="text-sm text-[#fafaf9]/50">Understanding how the brain rewires itself during skill acquisition.</p>
            </motion.div>

            {/* Concept Nodes */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 pl-0 md:pl-20">
              {['Synaptic Pruning', 'Long-term Potentiation', 'Myelination'].map((concept, i) => (
                <motion.div 
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  className="bg-[#2c2927]/20 border border-white/5 p-4 rounded-lg flex items-center gap-2 hover:bg-[#7d9c86]/10 transition-colors cursor-pointer"
                >
                  <div className="w-2 h-2 rounded-full bg-[#7d9c86]" />
                  <span className="text-sm text-[#fafaf9]/80">{concept}</span>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

const DualModeSection = () => {
  const [mode, setMode] = useState<'companion' | 'tutor'>('companion');

  return (
    <section className="py-32 bg-[#171513]">
      <div className="container mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="font-serif text-4xl md:text-5xl text-[#fafaf9] mb-4">Two Modes. One Goal.</h2>
          <div className="inline-flex items-center bg-[#2c2927] p-1 rounded-full border border-white/5 relative">
            <div 
              className={`absolute top-1 bottom-1 w-[140px] bg-[#7d9c86] rounded-full transition-all duration-300 ${mode === 'companion' ? 'left-1' : 'left-[145px]'}`} 
            />
            <button 
              onClick={() => setMode('companion')}
              className={`relative z-10 w-[140px] py-2 px-4 text-sm font-medium rounded-full transition-colors ${mode === 'companion' ? 'text-[#1c1917]' : 'text-[#fafaf9]/60'}`}
            >
              Companion Mode
            </button>
            <button 
              onClick={() => setMode('tutor')}
              className={`relative z-10 w-[140px] py-2 px-4 text-sm font-medium rounded-full transition-colors ${mode === 'tutor' ? 'text-[#1c1917]' : 'text-[#fafaf9]/60'}`}
            >
              Tutor Mode
            </button>
          </div>
        </div>

        <div className="max-w-4xl mx-auto h-[500px] relative perspective-1000">
          <AnimatePresence mode="wait">
            {mode === 'companion' ? (
              <motion.div 
                key="companion"
                initial={{ opacity: 0, rotateY: -10, scale: 0.95 }}
                animate={{ opacity: 1, rotateY: 0, scale: 1 }}
                exit={{ opacity: 0, rotateY: 10, scale: 0.95 }}
                transition={{ duration: 0.4 }}
                className="w-full h-full bg-[#2c2927]/40 backdrop-blur-xl border border-white/5 rounded-2xl p-8 flex gap-8"
              >
                {/* Companion UI Content */}
                <div className="w-1/2 space-y-4 border-r border-white/5 pr-8 hidden md:block">
                  <div className="p-4 bg-[#1c1917] rounded-lg border border-white/5 opacity-50">
                    <div className="h-2 w-20 bg-white/10 rounded mb-2" />
                    <div className="h-2 w-full bg-white/5 rounded mb-1" />
                    <div className="h-2 w-3/4 bg-white/5 rounded" />
                  </div>
                  <div className="p-4 bg-[#1c1917] rounded-lg border border-[#7d9c86]/20">
                    <h4 className="text-[#fafaf9] font-medium mb-2">Complex Theory</h4>
                    <p className="text-sm text-[#fafaf9]/60">"Polymorphism allows objects of different classes to be treated as objects of a common superclass."</p>
                  </div>
                </div>
                <div className="flex-1 flex flex-col">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-full bg-[#7d9c86] flex items-center justify-center">
                      <Sparkles className="w-5 h-5 text-[#1c1917]" />
                    </div>
                    <div>
                      <h4 className="text-[#fafaf9] font-medium">AI Companion</h4>
                      <p className="text-xs text-[#fafaf9]/40">Demystifying concepts</p>
                    </div>
                  </div>
                  <div className="flex-1 space-y-4">
                     <div className="bg-[#7d9c86]/10 border border-[#7d9c86]/20 p-4 rounded-tr-xl rounded-bl-xl rounded-br-xl">
                       <p className="text-[#fafaf9]/90 text-sm leading-relaxed">
                         Think of it like a <strong>Universal Remote</strong>. You can press "Power" (the method), and it works on a TV, a Stereo, or a DVD player (the objects), even though they're all different devices underneath.
                       </p>
                     </div>
                  </div>
                  <div className="mt-4 relative">
                    <Input placeholder="Ask me anything..." className="bg-[#1c1917] border-white/10 pr-10" />
                    <ArrowRight className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#7d9c86]" />
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div 
                key="tutor"
                initial={{ opacity: 0, rotateY: 10, scale: 0.95 }}
                animate={{ opacity: 1, rotateY: 0, scale: 1 }}
                exit={{ opacity: 0, rotateY: -10, scale: 0.95 }}
                transition={{ duration: 0.4 }}
                className="w-full h-full bg-[#1c1917] border border-[#7d9c86]/20 rounded-2xl p-8"
              >
                {/* Tutor UI Content */}
                 <div className="flex items-center justify-between mb-8">
                   <div>
                     <h3 className="text-xl text-[#fafaf9] font-medium">Session Goals</h3>
                     <p className="text-sm text-[#fafaf9]/50">Step-by-step guidance</p>
                   </div>
                   <div className="text-right">
                     <span className="text-2xl text-[#7d9c86] font-bold">80%</span>
                     <p className="text-xs text-[#fafaf9]/40">Mastery</p>
                   </div>
                 </div>

                 <div className="space-y-6">
                   {[
                     { step: 1, title: "Review Prerequisites", status: "completed" },
                     { step: 2, title: "Core Concept Analysis", status: "completed" },
                     { step: 3, title: "Practical Application", status: "active" },
                     { step: 4, title: "Final Assessment", status: "locked" },
                   ].map((item, i) => (
                     <div key={i} className={`flex items-center gap-4 ${item.status === 'locked' ? 'opacity-30' : 'opacity-100'}`}>
                       <div className={`w-8 h-8 rounded-full flex items-center justify-center border ${item.status === 'completed' ? 'bg-[#7d9c86] border-[#7d9c86] text-[#1c1917]' : item.status === 'active' ? 'border-[#7d9c86] text-[#7d9c86]' : 'border-white/20 text-white/20'}`}>
                         {item.status === 'completed' ? <CheckCircle2 className="w-4 h-4" /> : <span>{item.step}</span>}
                       </div>
                       <div className="flex-1 p-4 rounded-lg bg-[#2c2927]/50 border border-white/5 flex justify-between items-center">
                         <span className="text-[#fafaf9]">{item.title}</span>
                         {item.status === 'active' && <Button size="sm" className="bg-[#7d9c86] text-[#1c1917] h-7 text-xs">Start</Button>}
                       </div>
                     </div>
                   ))}
                 </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
};

const BentoGridSection = () => (
  <section className="py-32 bg-[#1c1917] relative">
     <div className="container mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="font-serif text-4xl md:text-5xl text-[#fafaf9]">Curated for You</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-4 grid-rows-4 gap-4 h-[800px]">
          {/* Main Feature - Profile */}
          <Card className="md:col-span-2 md:row-span-2 bg-[#2c2927]/30 border-white/5 hover:border-[#7d9c86]/30 transition-all p-6 flex flex-col justify-between overflow-hidden group">
            <div className="space-y-2 relative z-10">
              <Badge variant="outline" className="text-[#fafaf9]/50 border-white/10">Your Profile</Badge>
              <h3 className="text-2xl text-[#fafaf9] font-serif">Product Manager -> Python</h3>
            </div>
            <div className="absolute right-0 bottom-0 w-48 h-48 bg-[#7d9c86]/10 rounded-full blur-[50px] group-hover:bg-[#7d9c86]/20 transition-all" />
          </Card>

          {/* Video Resource */}
          <Card className="md:col-span-1 md:row-span-2 bg-[#2c2927]/30 border-white/5 p-6 hover:border-[#7d9c86]/30 transition-all flex flex-col items-center justify-center gap-4 group cursor-pointer">
            <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Play className="w-6 h-6 text-[#fafaf9]" fill="currentColor" />
            </div>
            <span className="text-[#fafaf9]/60 text-sm">Intro to Algorithms</span>
          </Card>

           {/* Quiz Resource */}
           <Card className="md:col-span-1 md:row-span-1 bg-[#7d9c86] border-none p-6 flex flex-col justify-center items-center text-center">
            <h3 className="text-[#1c1917] font-bold text-3xl">92%</h3>
            <span className="text-[#1c1917]/80 text-sm font-medium">Accuracy Score</span>
          </Card>

          {/* Code Resource */}
          <Card className="md:col-span-2 md:row-span-2 bg-[#151413] border-white/5 p-6 font-mono text-xs text-[#fafaf9]/70 overflow-hidden relative">
            <div className="absolute top-2 right-2 text-[#7d9c86]"><Code2 className="w-4 h-4" /></div>
            <pre className="opacity-80">
{`def optimize_learning(user):
  gaps = analyze_blind_spots(user)
  path = generate_roadmap(gaps)
  return path.execute()`}
            </pre>
            <div className="mt-4 p-2 bg-[#7d9c86]/10 text-[#7d9c86] rounded">
              > Optimization complete.
            </div>
          </Card>

          {/* Article Resource */}
          <Card className="md:col-span-2 md:row-span-1 bg-[#fafaf9] text-[#1c1917] p-6 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <FileText className="w-8 h-8 text-[#1c1917]" />
              <div>
                <h4 className="font-bold">System Design 101</h4>
                <p className="text-sm opacity-60">5 min read</p>
              </div>
            </div>
            <ArrowRight className="w-5 h-5" />
          </Card>
        </div>
     </div>
  </section>
);

const Footer = () => (
  <footer className="py-20 border-t border-white/5 bg-[#1c1917] text-center">
    <div className="container mx-auto px-6">
       <h2 className="font-serif text-3xl md:text-5xl text-[#fafaf9] mb-8">Join the Future of Learning</h2>
       <div className="max-w-md mx-auto relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-[#7d9c86] to-transparent opacity-20 group-hover:opacity-50 blur transition duration-500"></div>
          <div className="relative flex gap-2">
            <Input className="bg-[#1c1917] border-white/10 text-[#fafaf9] h-12" placeholder="email@example.com" />
            <Button className="bg-[#7d9c86] text-[#1c1917] hover:bg-[#6b8a74] h-12">Join</Button>
          </div>
       </div>
       <div className="mt-12 text-[#fafaf9]/20 text-sm">
         © 2025 Muset Inc. All rights reserved.
       </div>
    </div>
  </footer>
);

export default function MockupPage() {
  return (
    <div className="min-h-screen bg-[#1c1917] text-[#fafaf9] selection:bg-[#7d9c86] selection:text-[#1c1917]">
      <Navigation />
      <HeroSection />
      <RoadmapSection />
      <DualModeSection />
      <BentoGridSection />
      <Footer />
    </div>
  );
}





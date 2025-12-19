"use client"

import { useRef } from "react"
import { motion } from "framer-motion"
import { Sparkles, Target, BookOpen, Trophy } from "lucide-react"
import { AnimatedBeam } from "@/components/ui/animated-beam"
import { cn } from "@/lib/utils"

const Circle = ({ className, children, ref }: { className?: string; children: React.ReactNode; ref?: React.Ref<HTMLDivElement> }) => {
  return (
    <div
      ref={ref}
      className={cn(
        "z-10 flex h-16 w-16 items-center justify-center rounded-full border-2 border-sage-200 bg-white/95 shadow-lg backdrop-blur-sm",
        className
      )}
    >
      {children}
    </div>
  )
}

export function LearningPathDemo() {
  const containerRef = useRef<HTMLDivElement>(null)
  const goalRef = useRef<HTMLDivElement>(null)
  const stage1Ref = useRef<HTMLDivElement>(null)
  const stage2Ref = useRef<HTMLDivElement>(null)
  const masteryRef = useRef<HTMLDivElement>(null)

  return (
    <div className="w-full max-w-4xl mx-auto py-12">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="text-center mb-12"
      >
        <h3 className="text-2xl font-bold text-sage-900 mb-2">
          AI-Powered Learning Path
        </h3>
        <p className="text-sage-600">
          Watch how AI constructs your personalized learning journey
        </p>
      </motion.div>

      <div
        ref={containerRef}
        className="relative flex items-center justify-between w-full h-48 px-8"
      >
        {/* Goal Node */}
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          whileInView={{ scale: 1, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
        >
          <Circle ref={goalRef} className="border-sage-400">
            <Target className="h-8 w-8 text-sage-700" />
          </Circle>
          <p className="text-xs text-center mt-2 text-sage-700 font-medium">
            Your Goal
          </p>
        </motion.div>

        {/* Stage 1 Node */}
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          whileInView={{ scale: 1, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3, type: "spring", stiffness: 200 }}
        >
          <Circle ref={stage1Ref} className="border-sage-400">
            <Sparkles className="h-8 w-8 text-sage-700" />
          </Circle>
          <p className="text-xs text-center mt-2 text-sage-700 font-medium">
            Foundation
          </p>
        </motion.div>

        {/* Stage 2 Node */}
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          whileInView={{ scale: 1, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.5, type: "spring", stiffness: 200 }}
        >
          <Circle ref={stage2Ref} className="border-sage-400">
            <BookOpen className="h-8 w-8 text-sage-700" />
          </Circle>
          <p className="text-xs text-center mt-2 text-sage-700 font-medium">
            Practice
          </p>
        </motion.div>

        {/* Mastery Node */}
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          whileInView={{ scale: 1, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.7, type: "spring", stiffness: 200 }}
        >
          <Circle ref={masteryRef} className="border-sage-600 bg-gradient-to-br from-sage-100 to-white">
            <Trophy className="h-8 w-8 text-sage-800" />
          </Circle>
          <p className="text-xs text-center mt-2 text-sage-800 font-semibold">
            Mastery
          </p>
        </motion.div>

        {/* Animated Beams */}
        <AnimatedBeam
          containerRef={containerRef}
          fromRef={goalRef}
          toRef={stage1Ref}
          gradientStartColor="#7d8f7d"
          gradientStopColor="#d8e0d8"
          duration={3}
          delay={1}
        />
        <AnimatedBeam
          containerRef={containerRef}
          fromRef={stage1Ref}
          toRef={stage2Ref}
          gradientStartColor="#7d8f7d"
          gradientStopColor="#d8e0d8"
          duration={3}
          delay={1.3}
        />
        <AnimatedBeam
          containerRef={containerRef}
          fromRef={stage2Ref}
          toRef={masteryRef}
          gradientStartColor="#7d8f7d"
          gradientStopColor="#d8e0d8"
          duration={3}
          delay={1.6}
        />
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 2, duration: 0.5 }}
        className="mt-8 text-center"
      >
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-sage-100/50 border border-sage-200">
          <Sparkles className="h-4 w-4 text-sage-700" />
          <span className="text-sm text-sage-700">
            Powered by AI - Adapts to your progress
          </span>
        </div>
      </motion.div>
    </div>
  )
}


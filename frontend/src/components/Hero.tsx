import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

const Hero: React.FC = () => {
    // Generate random nodes for the background animation
    const nodes = Array.from({ length: 20 }).map((_, i) => ({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: Math.random() * 4 + 2,
    }));

    return (
        <section className="relative min-h-screen flex flex-col items-center justify-center pt-20 overflow-hidden">
            {/* Background Animated Nodes */}
            <div className="absolute inset-0 z-0 opacity-20 pointer-events-none">
                {nodes.map((node) => (
                    <motion.div
                        key={node.id}
                        className="absolute bg-foreground rounded-full"
                        style={{
                            left: `${node.x}%`,
                            top: `${node.y}%`,
                            width: node.size,
                            height: node.size,
                        }}
                        animate={{
                            y: [0, -20, 0],
                            opacity: [0.5, 1, 0.5],
                        }}
                        transition={{
                            duration: Math.random() * 3 + 2,
                            repeat: Infinity,
                            ease: "easeInOut",
                        }}
                    />
                ))}
                <svg className="absolute inset-0 w-full h-full">
                    {/* Simple connecting lines simulation */}
                    <motion.path
                        d="M100,100 Q400,50 600,300 T1000,200"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1"
                        className="text-muted-foreground/40"
                        initial={{ pathLength: 0 }}
                        animate={{ pathLength: 1 }}
                        transition={{ duration: 3, ease: "easeInOut" }}
                    />
                </svg>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto text-center px-6">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8 }}
                >
                    <span className="inline-block px-4 py-1.5 rounded-full bg-sage-100 text-foreground text-xs font-bold tracking-wider mb-6 uppercase">
                        The Future of Self-Learning
                    </span>
                    <h1 className="text-5xl md:text-7xl font-serif font-medium leading-tight mb-6 text-foreground">
                        Turn Ambition into a <br />
                        <span className="italic text-sage">Concrete Path.</span>
                    </h1>
                    <p className="text-lg md:text-xl text-muted-foreground mb-10 max-w-2xl mx-auto font-light leading-relaxed">
                        The world's first multi-agent learning architect. You define the goal;
                        we engineer the Stage → Module → Concept roadmap to get you there.
                    </p>

                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <button className="px-8 py-4 bg-primary text-primary-foreground rounded-full text-lg font-medium hover:bg-primary/90 transition-all flex items-center gap-2 group shadow-lg shadow-primary/20">
                            Generate My Roadmap
                            <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
                        </button>
                        <button className="px-8 py-4 bg-card text-foreground border border-border rounded-full text-lg font-medium hover:bg-sage-50 transition-all">
                            Explore Examples
                        </button>
                    </div>
                </motion.div>
            </div>
        </section>
    );
};

export default Hero;

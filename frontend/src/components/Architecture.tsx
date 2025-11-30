import React from 'react';
import { motion } from 'framer-motion';
import { Layers, Box, FileText } from 'lucide-react';

const Architecture: React.FC = () => {
    const layers = [
        { title: 'Stage', icon: Layers, desc: 'High-level milestones', color: 'bg-sage-200' },
        { title: 'Module', icon: Box, desc: 'Key skill clusters', color: 'bg-sage-500/50' },
        { title: 'Concept', icon: FileText, desc: 'Atomic knowledge units', color: 'bg-primary text-primary-foreground' },
    ];

    return (
        <section className="py-24 px-6 bg-background overflow-hidden">
            <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center gap-16">
                <div className="flex-1">
                    <span className="text-sage-500 font-bold tracking-wider uppercase text-sm mb-4 block">The Core Mechanism</span>
                    <h2 className="text-4xl md:text-5xl font-serif font-medium text-foreground mb-6">Depth by Design.</h2>
                    <p className="text-lg text-foreground/70 leading-relaxed mb-8">
                        We don't just list topics. We architect a 3-layer cognitive structure that maps exactly how your brain builds mastery.
                    </p>

                    <div className="space-y-6">
                        {layers.map((layer, i) => (
                            <div key={i} className="flex items-center gap-4 group cursor-pointer">
                                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${i === 2 ? 'bg-primary text-primary-foreground' : 'bg-white border border-border/10 text-foreground'} transition-colors`}>
                                    <layer.icon size={24} />
                                </div>
                                <div>
                                    <h4 className="font-serif font-bold text-lg">{layer.title}</h4>
                                    <p className="text-sm text-foreground/60">{layer.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="flex-1 relative h-[500px] w-full flex items-center justify-center perspective-1000">
                    {/* 3D Layers Visualization */}
                    <div className="relative w-64 h-80 transform rotate-x-60 rotate-z-45 preserve-3d">
                        {layers.map((layer, i) => (
                            <motion.div
                                key={i}
                                className={`absolute inset-0 rounded-3xl shadow-xl flex items-center justify-center border border-white/20 backdrop-blur-sm ${layer.color}`}
                                style={{
                                    translateZ: i * 60,
                                    zIndex: layers.length - i,
                                }}
                                initial={{ opacity: 0, y: 100 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.2, duration: 0.8 }}
                                whileHover={{ translateZ: i * 80 + 20 }}
                            >
                                <div className="text-center transform -rotate-z-45 -rotate-x-60">
                                    <layer.icon size={32} className="mx-auto mb-2 opacity-80" />
                                    <span className="font-bold text-lg">{layer.title}</span>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </div>
        </section>
    );
};

export default Architecture;

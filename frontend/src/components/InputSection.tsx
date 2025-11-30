import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Send } from 'lucide-react';

const InputSection: React.FC = () => {
    return (
        <section className="py-20 px-6 relative z-20 -mt-20">
            <div className="max-w-3xl mx-auto">
                <motion.div
                    className="glass-panel rounded-3xl p-2 shadow-xl shadow-sage-500/10"
                    initial={{ opacity: 0, y: 40 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.8 }}
                >
                    <div className="bg-white/60 rounded-2xl p-6 md:p-8 flex flex-col gap-4">
                        <div className="flex items-center gap-2 text-sage-500 mb-2">
                            <Sparkles size={18} />
                            <span className="text-sm font-medium uppercase tracking-wide">Context-Aware Intelligence</span>
                        </div>

                        <div className="relative">
                            <textarea
                                className="w-full bg-transparent text-2xl md:text-3xl font-serif text-foreground placeholder:text-foreground/30 outline-none resize-none min-h-[120px]"
                                placeholder="I have 3 months, I know Python basics, and I want to master Generative AI..."
                            />
                            <div className="absolute bottom-0 right-0 flex items-center gap-2">
                                <span className="text-xs text-foreground/40 font-medium">Press Enter to generate</span>
                                <button className="w-10 h-10 bg-primary text-primary-foreground rounded-full flex items-center justify-center hover:scale-105 transition-transform">
                                    <Send size={18} />
                                </button>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>
        </section>
    );
};

export default InputSection;

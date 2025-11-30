import React from 'react';
import { motion } from 'framer-motion';
import { Bot, Search, PenTool } from 'lucide-react';

const Agents: React.FC = () => {
    return (
        <section className="py-24 px-6 bg-card/50">
            <div className="max-w-4xl mx-auto text-center mb-16">
                <h2 className="text-4xl md:text-5xl font-serif font-medium text-foreground mb-6">A University Faculty in the Cloud.</h2>
                <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                    One agent structures the path. Another curates resources. A third writes the tutorial. All working in sync for your mastery.
                </p>
            </div>

            <div className="max-w-5xl mx-auto relative h-[400px] bg-background rounded-3xl border border-border overflow-hidden flex items-center justify-center">
                <div className="absolute inset-0 bg-gradient-radial from-sage-100/50 to-transparent opacity-50"></div>

                {/* Central Hub */}
                <motion.div
                    className="w-24 h-24 bg-primary rounded-full flex items-center justify-center text-primary-foreground relative z-10 shadow-2xl"
                    animate={{ scale: [1, 1.05, 1] }}
                    transition={{ duration: 4, repeat: Infinity }}
                >
                    <span className="font-serif font-bold text-xl">You</span>
                </motion.div>

                {/* Better Orbit Implementation */}
                {[
                    { icon: Bot, label: "Architect", x: 0, y: -150 },
                    { icon: Search, label: "Researcher", x: 130, y: 75 },
                    { icon: PenTool, label: "Writer", x: -130, y: 75 }
                ].map((agent, i) => (
                    <motion.div
                        key={i}
                        className="absolute w-32 h-32 flex flex-col items-center justify-center"
                        initial={{ x: agent.x, y: agent.y, opacity: 0 }}
                        whileInView={{ opacity: 1 }}
                        animate={{
                            y: [agent.y, agent.y - 10, agent.y],
                        }}
                        transition={{
                            y: { duration: 3, repeat: Infinity, delay: i * 0.5 }
                        }}
                    >
                        <div className="w-16 h-16 bg-card rounded-2xl shadow-lg border border-border flex items-center justify-center text-foreground mb-3 relative group hover:scale-110 transition-transform cursor-pointer">
                            <agent.icon size={24} />
                            <div className="absolute inset-0 bg-sage-200/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
                        </div>
                        <span className="font-medium text-sm tracking-wide uppercase text-muted-foreground">{agent.label}</span>

                        {/* Connecting Line */}
                        <motion.div
                            className="absolute top-1/2 left-1/2 w-1 h-1 bg-sage rounded-full"
                            style={{ top: '30%' }}
                            animate={{
                                scale: [1, 20, 1],
                                opacity: [0, 0.2, 0]
                            }}
                            transition={{ duration: 2, repeat: Infinity, delay: i * 0.8 }}
                        />
                    </motion.div>
                ))}
            </div>
        </section>
    );
};

export default Agents;

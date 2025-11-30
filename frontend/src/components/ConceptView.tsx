import React from 'react';
import { CheckCircle, ChevronRight, BookOpen } from 'lucide-react';

const ConceptView: React.FC = () => {
    return (
        <section className="py-24 px-6 bg-background">
            <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center gap-16">
                <div className="flex-1 order-2 md:order-1">
                    <div className="relative bg-white rounded-3xl shadow-2xl shadow-charcoal/5 border border-border/5 overflow-hidden max-w-md mx-auto md:mx-0 transform rotate-[-2deg] hover:rotate-0 transition-transform duration-500">
                        {/* Mockup Header */}
                        <div className="h-12 border-b border-border/5 flex items-center justify-between px-4 bg-background/50">
                            <div className="flex gap-2">
                                <div className="w-3 h-3 rounded-full bg-sage-400/20"></div>
                                <div className="w-3 h-3 rounded-full bg-yellow-400/20"></div>
                                <div className="w-3 h-3 rounded-full bg-sage-400/20"></div>
                            </div>
                            <div className="text-xs font-medium text-foreground/40">Concept: Neural Networks</div>
                        </div>

                        {/* Mockup Content */}
                        <div className="p-8">
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sage-100 text-foreground/70 text-xs font-medium mb-6">
                                <BookOpen size={12} />
                                Estimated time: 15 min
                            </div>
                            <h3 className="text-2xl font-serif font-bold text-foreground mb-4">Understanding Backpropagation</h3>
                            <p className="text-foreground/70 text-sm leading-relaxed mb-6">
                                At its core, backpropagation is simply the chain rule of calculus applied to the computation graph of the network. It allows us to calculate gradients efficiently.
                            </p>

                            <div className="bg-primary/5 rounded-xl p-4 mb-6 font-mono text-xs text-foreground/80">
                                def backprop(self, x, y):<br />
                                &nbsp;&nbsp;nabla_b = [np.zeros(b.shape) for b in self.biases]<br />
                                &nbsp;&nbsp;nabla_w = [np.zeros(w.shape) for w in self.weights]<br />
                                &nbsp;&nbsp;# ...
                            </div>

                            <button className="w-full py-3 bg-primary text-primary-foreground rounded-xl font-medium text-sm flex items-center justify-center gap-2 hover:bg-primary/90 transition-colors">
                                <CheckCircle size={16} />
                                Mark as Complete
                            </button>
                        </div>
                    </div>
                </div>

                <div className="flex-1 order-1 md:order-2">
                    <span className="text-sage-500 font-bold tracking-wider uppercase text-sm mb-4 block">The Experience</span>
                    <h2 className="text-4xl md:text-5xl font-serif font-medium text-foreground mb-6">Learn. Practice. Master.</h2>
                    <p className="text-lg text-foreground/70 leading-relaxed mb-8">
                        A distraction-free environment designed for deep work. Track your progress, run code snippets, and build momentum concept by concept.
                    </p>
                    <ul className="space-y-4">
                        {['Distraction-free reading mode', 'Interactive code playgrounds', 'Progress tracking & streaks'].map((item, i) => (
                            <li key={i} className="flex items-center gap-3 text-foreground/80">
                                <div className="w-6 h-6 rounded-full bg-sage-200 flex items-center justify-center text-foreground">
                                    <ChevronRight size={14} />
                                </div>
                                {item}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>
        </section>
    );
};

export default ConceptView;

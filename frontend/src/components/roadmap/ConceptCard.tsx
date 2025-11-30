import React from 'react';
import { motion } from 'framer-motion';
import { PlayCircle, Feather, Zap, Mountain, Clock } from 'lucide-react';

interface ConceptCardProps {
    conceptId: string;
    name: string;
    description: string;
    estimatedHours: number;
    difficulty: string;
    onClick?: () => void;
}

const ConceptCard: React.FC<ConceptCardProps> = ({ conceptId, name, description, estimatedHours, difficulty, onClick }) => {
    // Difficulty configuration
    const difficultyConfig = {
        easy: { icon: Feather, color: 'text-emerald-600', label: 'Easy' },
        medium: { icon: Zap, color: 'text-amber-600', label: 'Medium' },
        hard: { icon: Mountain, color: 'text-rose-600', label: 'Hard' },
    };

    const config = difficultyConfig[difficulty as keyof typeof difficultyConfig] || difficultyConfig.medium;
    const DifficultyIcon = config.icon;

    return (
        <motion.div
            layoutId={`concept-card-${conceptId}`}
            onClick={onClick}
            whileHover={{ y: -2, borderColor: 'hsl(var(--sage))' }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            className="relative bg-card/60 backdrop-blur-sm border border-sage-200/60 rounded-lg p-3 shadow-sm cursor-pointer group w-full transition-colors duration-300"
        >
            <div className="flex items-start gap-4">
                {/* Icon - Elegant container */}
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-sage-100/50 flex items-center justify-center border border-sage-200 group-hover:bg-sage-200/50 transition-colors">
                    <PlayCircle className="text-sage-700" size={20} strokeWidth={1.5} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <h5 className="text-lg font-serif font-semibold text-foreground leading-tight mb-2 group-hover:text-sage-900 transition-colors">
                        {name}
                    </h5>
                    <p className="text-sm text-muted-foreground leading-relaxed mb-4 line-clamp-2 font-light">
                        {description}
                    </p>

                    {/* Metadata Row */}
                    <div className="flex items-center justify-between pt-2 border-t border-sage-100/50">
                        <div className="flex items-center gap-4">
                            {/* Duration */}
                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground/80">
                                <Clock size={14} className="text-sage-400" />
                                <span>{estimatedHours}h</span>
                            </div>

                            {/* Difficulty */}
                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground/80">
                                <DifficultyIcon size={14} className={config.color} />
                                <span className="capitalize">{difficulty}</span>
                            </div>
                        </div>

                        {/* "Start" text that appears on hover could be cool, but let's keep it clean for now */}
                    </div>
                </div>
            </div>
        </motion.div>
    );
};

export default ConceptCard;

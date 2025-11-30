import React from 'react';
import { Lightbulb, ChevronDown, ChevronRight } from 'lucide-react';

interface StageCardProps {
    name: string;
    description: string;
    order: number;
    isExpanded: boolean;
    onToggle: () => void;
}

const StageCard: React.FC<StageCardProps> = ({ name, description, order, isExpanded, onToggle }) => {
    return (
        <div
            onClick={onToggle}
            className={`relative bg-card border transition-all duration-300 rounded-xl p-4 cursor-pointer group ${isExpanded ? 'border-sage shadow-md' : 'border-border hover:border-sage-300 hover:shadow-sm'
                }`}
        >
            {/* Connector point for child lines */}
            <div className="absolute bottom-0 left-8 w-1 h-4 bg-transparent" data-connector="stage" />

            <div className="flex items-start gap-4">
                {/* Icon */}
                <div className="flex-shrink-0 w-12 h-12 rounded-2xl bg-sage flex items-center justify-center shadow-lg">
                    <Lightbulb className="text-primary-foreground" size={24} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-2">
                        <div>
                            <div className="text-xs font-semibold text-sage uppercase tracking-wider mb-1">
                                Stage {order}
                            </div>
                            <h3 className="text-lg font-serif font-bold text-foreground leading-tight">
                                {name}
                            </h3>
                        </div>
                        <button className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center hover:bg-sage-100 transition-colors">
                            {isExpanded ? (
                                <ChevronDown size={18} className="text-muted-foreground" />
                            ) : (
                                <ChevronRight size={18} className="text-muted-foreground" />
                            )}
                        </button>
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                        {description}
                    </p>
                </div>
            </div>
        </div>
    );
};

export default StageCard;

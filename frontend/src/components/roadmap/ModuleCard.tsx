import React from 'react';
import { Layers, ChevronDown, ChevronRight } from 'lucide-react';

interface ModuleCardProps {
    name: string;
    description: string;
    isExpanded: boolean;
    onToggle: () => void;
}

const ModuleCard: React.FC<ModuleCardProps> = ({ name, description, isExpanded, onToggle }) => {
    return (
        <div
            onClick={onToggle}
            className={`relative bg-card/50 backdrop-blur-sm border transition-all duration-200 rounded-lg p-3 cursor-pointer hover:bg-card ${isExpanded ? 'border-sage-300 shadow-sm' : 'border-border hover:border-sage-200'
                }`}
        >  {/* Connector point for child lines */}
            <div className="absolute bottom-0 left-6 w-1 h-4 bg-transparent" data-connector="module" />

            <div className="flex items-start gap-3">
                {/* Icon */}
                <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-sage flex items-center justify-center shadow-md">
                    <Layers className="text-primary-foreground" size={20} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                        <h4 className="text-base font-serif font-semibold text-foreground leading-tight">
                            {name}
                        </h4>
                        <button className="flex-shrink-0 w-7 h-7 rounded-full bg-muted flex items-center justify-center hover:bg-sage-100 transition-colors">
                            {isExpanded ? (
                                <ChevronDown size={16} className="text-muted-foreground" />
                            ) : (
                                <ChevronRight size={16} className="text-muted-foreground" />
                            )}
                        </button>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                        {description}
                    </p>
                </div>
            </div>
        </div>
    );
};

export default ModuleCard;

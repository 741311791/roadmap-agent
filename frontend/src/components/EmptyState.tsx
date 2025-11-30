import React from 'react';
import { BookOpen } from 'lucide-react';

interface EmptyStateProps {
    title: string;
    description: string;
    icon?: React.ElementType;
    compact?: boolean;
}

const EmptyState: React.FC<EmptyStateProps> = ({ title, description, icon: Icon = BookOpen, compact = false }) => {
    return (
        <div className={`h-full flex flex-col items-center justify-center text-center animate-fade-in ${compact ? 'p-4' : 'p-8'}`}>
            <div className={`rounded-full flex items-center justify-center border border-sage-100 shadow-sm ${compact ? 'w-12 h-12 mb-3 bg-sage-50/50' : 'w-24 h-24 mb-6 bg-sage-50'
                }`}>
                <Icon size={compact ? 20 : 40} className="text-sage-400" strokeWidth={1.5} />
            </div>
            <h3 className={`font-serif font-semibold text-foreground ${compact ? 'text-lg mb-1' : 'text-2xl mb-3'}`}>
                {title}
            </h3>
            <p className={`text-muted-foreground leading-relaxed ${compact ? 'text-xs max-w-[200px]' : 'max-w-md'}`}>
                {description}
            </p>
        </div>
    );
};

export default EmptyState;

import React from 'react';
import { motion } from 'framer-motion';
import { ChevronLeft, Menu } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/Button';

interface TOCItem {
    id: string;
    label: string;
}

interface TOCSidebarProps {
    items: TOCItem[];
    activeSection: string;
    onSectionClick?: (id: string) => void;
    isCollapsed: boolean;
    onToggleCollapse: () => void;
    onBack: () => void;
}

const TOCSidebar: React.FC<TOCSidebarProps> = ({
    items,
    activeSection,
    onSectionClick,
    isCollapsed,
    onToggleCollapse,
    onBack
}) => {
    return (
        <motion.div
            initial={false}
            animate={{ width: isCollapsed ? 60 : 240 }}
            className="flex-shrink-0 border-r border-stone-200/60 h-full relative bg-[#FFFCF9] z-10 flex flex-col transition-all duration-300"
        >
            {/* Header / Back Button */}
            <div className="p-4 flex items-center justify-between h-14 border-b border-stone-100/50">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={onBack}
                    className="text-stone-500 hover:text-stone-800 hover:bg-stone-100"
                    title="Back to Dashboard"
                >
                    <ChevronLeft size={20} />
                </Button>
                {!isCollapsed && (
                    <span className="text-xs font-bold tracking-widest text-stone-400 uppercase">Outline</span>
                )}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto py-4 px-3">
                {!isCollapsed ? (
                    <nav className="space-y-1">
                        {items.map((item) => (
                            <a
                                key={item.id}
                                href={`#${item.id}`}
                                onClick={(e) => {
                                    if (onSectionClick) {
                                        e.preventDefault();
                                        onSectionClick(item.id);
                                    }
                                }}
                                className={cn(
                                    "group flex items-center justify-between py-2 px-3 rounded-md text-sm transition-all",
                                    activeSection === item.id
                                        ? "bg-sage-100 text-sage-800 font-medium"
                                        : "text-stone-500 hover:text-stone-900 hover:bg-stone-100"
                                )}
                            >
                                <span className="truncate">{item.label}</span>
                                {activeSection === item.id && (
                                    <motion.div layoutId="active-toc" className="w-1 h-1 rounded-full bg-sage-500" />
                                )}
                            </a>
                        ))}
                    </nav>
                ) : (
                    <div className="flex flex-col items-center gap-4">
                        {items.map((item) => (
                            <div
                                key={item.id}
                                className={cn(
                                    "w-2 h-2 rounded-full transition-colors cursor-pointer",
                                    activeSection === item.id ? "bg-sage-500 scale-125" : "bg-stone-300 hover:bg-sage-300"
                                )}
                                title={item.label}
                                onClick={() => onSectionClick && onSectionClick(item.id)}
                            />
                        ))}
                    </div>
                )}
            </div>

            {/* Footer / Collapse Toggle */}
            <div className="p-4 border-t border-stone-100 flex justify-center">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={onToggleCollapse}
                    className="text-stone-400 hover:text-stone-600"
                >
                    {isCollapsed ? <Menu size={16} /> : <ChevronLeft size={16} />}
                </Button>
            </div>
        </motion.div>
    );
};

export default TOCSidebar;

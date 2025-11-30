import React, { createContext, useContext, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';

const SheetContext = createContext<{ open: boolean; setOpen: (open: boolean) => void } | null>(null);

export const Sheet = ({ children }: { children: React.ReactNode }) => {
    const [open, setOpen] = useState(false);
    return <SheetContext.Provider value={{ open, setOpen }}>{children}</SheetContext.Provider>;
};

export const SheetTrigger = ({ children, className }: { children: React.ReactNode, className?: string }) => {
    const context = useContext(SheetContext);
    if (!context) throw new Error("SheetTrigger must be used within Sheet");
    return <div onClick={() => context.setOpen(true)} className={cn("cursor-pointer", className)}>{children}</div>;
};

export const SheetContent = ({ children, className }: { children: React.ReactNode, className?: string }) => {
    const context = useContext(SheetContext);
    if (!context) throw new Error("SheetContent must be used within Sheet");

    return (
        <AnimatePresence>
            {context.open && (
                <>
                    <motion.div
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50"
                        onClick={() => context.setOpen(false)}
                    />
                    <motion.div
                        initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
                        transition={{ type: "spring", damping: 25, stiffness: 300 }}
                        className={cn("fixed right-0 top-0 h-full w-[400px] bg-white shadow-2xl z-50 p-6 border-l border-stone-100", className)}
                    >
                        <button
                            onClick={() => context.setOpen(false)}
                            className="absolute top-4 right-4 p-2 rounded-full hover:bg-stone-100 text-stone-400 hover:text-stone-600 transition-colors"
                        >
                            <X size={20} />
                        </button>
                        {children}
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
};

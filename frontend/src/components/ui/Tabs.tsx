import React, { createContext, useContext, useState } from 'react';
import { cn } from '../../lib/utils';

const TabsContext = createContext<{ value: string; setValue: (value: string) => void } | null>(null);

export const Tabs = ({ defaultValue, children, className }: { defaultValue: string, children: React.ReactNode, className?: string }) => {
    const [value, setValue] = useState(defaultValue);
    return (
        <TabsContext.Provider value={{ value, setValue }}>
            <div className={className}>{children}</div>
        </TabsContext.Provider>
    );
};

export const TabsList = ({ children, className }: { children: React.ReactNode, className?: string }) => (
    <div className={cn("flex items-center p-1 bg-stone-100 rounded-lg", className)}>{children}</div>
);

export const TabsTrigger = ({ value, children, className }: { value: string, children: React.ReactNode, className?: string }) => {
    const context = useContext(TabsContext);
    if (!context) throw new Error("TabsTrigger must be used within Tabs");

    const isActive = context.value === value;
    return (
        <button
            onClick={() => context.setValue(value)}
            className={cn(
                "flex-1 px-3 py-1.5 text-sm font-medium rounded-md transition-all",
                isActive
                    ? "bg-white text-stone-800 shadow-sm"
                    : "text-stone-500 hover:text-stone-700 hover:bg-stone-200/50",
                className
            )}
        >
            {children}
        </button>
    );
};

export const TabsContent = ({ value, children, className }: { value: string, children: React.ReactNode, className?: string }) => {
    const context = useContext(TabsContext);
    if (!context) throw new Error("TabsContent must be used within Tabs");

    if (context.value !== value) return null;
    return <div className={cn("mt-4", className)}>{children}</div>;
};

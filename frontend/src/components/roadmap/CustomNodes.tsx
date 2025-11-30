import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { ChevronRight, ChevronDown } from 'lucide-react';

// STAGE NODE
export const StageNode = memo(({ data, isConnectable }: NodeProps) => {
    return (
        <div className="bg-card/90 backdrop-blur-sm border border-border rounded-2xl p-5 min-w-[240px] shadow-lg hover:shadow-xl transition-all cursor-pointer group">
            <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{String(data.label)}</span>
                <div className="w-5 h-5 rounded-full bg-muted flex items-center justify-center">
                    {data.expanded ? <ChevronDown size={14} className="text-foreground/40" /> : <ChevronRight size={14} className="text-foreground/40" />}
                </div>
            </div>
            <div className="text-xs text-muted-foreground leading-relaxed">{String(data.description)}</div>

            <Handle type="source" position={Position.Right} isConnectable={isConnectable} className="!bg-foreground/20 !w-2.5 !h-2.5 !-right-1.5 !border-2 !border-card" />
            <Handle type="target" position={Position.Left} isConnectable={isConnectable} className="!bg-foreground/20 !w-2.5 !h-2.5 !-left-1.5 !border-2 !border-card" />
        </div>
    );
});

// MODULE NODE
export const ModuleNode = memo(({ data, isConnectable }: NodeProps) => {
    return (
        <div className="bg-card/85 backdrop-blur-sm border border-border/80 rounded-xl p-4 min-w-[200px] shadow-md hover:shadow-lg transition-all cursor-pointer group">
            <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-foreground">{String(data.label)}</span>
                <div className="w-4 h-4 rounded flex items-center justify-center">
                    {data.expanded ? <ChevronDown size={12} className="text-foreground/30" /> : <ChevronRight size={12} className="text-foreground/30" />}
                </div>
            </div>

            <Handle type="source" position={Position.Right} isConnectable={isConnectable} className="!bg-foreground/15 !w-2 !h-2 !-right-1 !border !border-card" />
            <Handle type="target" position={Position.Left} isConnectable={isConnectable} className="!bg-foreground/15 !w-2 !h-2 !-left-1 !border !border-card" />
        </div>
    );
});

// CONCEPT NODE
export const ConceptNode = memo(({ data, isConnectable }: NodeProps) => {
    return (
        <div className="bg-card/80 backdrop-blur-sm border border-border/50 rounded-xl px-4 py-3 min-w-[180px] shadow-md hover:shadow-lg transition-all cursor-pointer">
            <div className="text-sm font-medium text-foreground">{String(data.label)}</div>
            <div className="text-xs text-muted-foreground mt-1">{String(data.time)}</div>
            <Handle type="target" position={Position.Left} isConnectable={isConnectable} className="!bg-foreground/10 !w-1.5 !h-1.5 !-left-0.5 !border !border-card/50" />
        </div>
    );
});

import React from 'react';
import { motion } from 'motion/react';
import { Roadmap, RoadmapNode } from '../services/gemini';
import { ChevronRight, Circle, CheckCircle2, PlayCircle } from 'lucide-react';
import { cn } from '../lib/utils';

interface RoadmapViewProps {
  roadmap: Roadmap;
  onNodeClick: (node: RoadmapNode) => void;
  activeNodeId?: string;
}

export const RoadmapView: React.FC<RoadmapViewProps> = ({ roadmap, onNodeClick, activeNodeId }) => {
  const renderNode = (node: RoadmapNode, level = 0) => {
    const isActive = activeNodeId === node.id;
    const isCompleted = node.status === 'completed';
    const isInProgress = node.status === 'in-progress';

    return (
      <div key={node.id} className={cn("space-y-2", level > 0 && "ml-8 border-l border-slate-200 pl-6 py-2")}>
        <motion.div
          whileHover={{ x: 4 }}
          onClick={() => onNodeClick(node)}
          className={cn(
            "group flex items-center gap-4 p-4 rounded-2xl cursor-pointer transition-all border",
            isActive 
              ? "bg-brand-50 border-brand-200 shadow-sm" 
              : "bg-white border-slate-100 hover:border-brand-200 hover:shadow-sm"
          )}
        >
          <div className={cn(
            "shrink-0 w-10 h-10 rounded-xl flex items-center justify-center",
            isCompleted ? "bg-green-50 text-green-600" : 
            isInProgress ? "bg-brand-50 text-brand-600" : "bg-slate-50 text-slate-400"
          )}>
            {isCompleted ? <CheckCircle2 size={20} /> : 
             isInProgress ? <PlayCircle size={20} /> : <Circle size={20} />}
          </div>
          
          <div className="flex-1">
            <h4 className={cn(
              "font-display font-semibold text-sm",
              isActive ? "text-brand-900" : "text-slate-700"
            )}>
              {node.title}
            </h4>
            <p className="text-xs text-slate-500 line-clamp-1">{node.description}</p>
          </div>

          <ChevronRight size={16} className={cn(
            "text-slate-300 group-hover:text-brand-400 transition-colors",
            isActive && "text-brand-500"
          )} />
        </motion.div>

        {node.children && node.children.length > 0 && (
          <div className="space-y-2">
            {node.children.map(child => renderNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-3xl mx-auto py-12 px-6">
      <header className="mb-12 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <span className="inline-block px-3 py-1 bg-brand-50 text-brand-600 text-[10px] font-bold uppercase tracking-widest rounded-full mb-4">
            Generated Roadmap
          </span>
          <h1 className="text-4xl font-display font-bold text-slate-900 mb-4">{roadmap.title}</h1>
          <p className="text-slate-500">Click on a module to start your learning journey.</p>
        </motion.div>
      </header>

      <div className="space-y-6">
        {roadmap.nodes.map(node => renderNode(node))}
      </div>
    </div>
  );
};

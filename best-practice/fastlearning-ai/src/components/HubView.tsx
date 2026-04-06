import React, { useState } from 'react';
import { Search, Plus, Clock, BookMarked, ArrowRight } from 'lucide-react';
import { motion } from 'motion/react';
import { Workspace } from '../types';
import { cn } from '../lib/utils';

interface HubViewProps {
  workspaces: Workspace[];
  onNewWorkspace: (topic: string) => void;
  onSelectWorkspace: (id: string) => void;
}

export const HubView: React.FC<HubViewProps> = ({ workspaces, onNewWorkspace, onSelectWorkspace }) => {
  const [input, setInput] = useState('');

  const suggestions = [
    "Zero to Hero: Python Web Scraper",
    "Frontend Mastery: React & Framer Motion",
    "Go Concurrency Patterns",
    "System Design for Scale"
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      onNewWorkspace(input.trim());
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <main className="flex-1 flex flex-col items-center justify-center p-6 max-w-4xl mx-auto w-full">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full text-center space-y-8"
        >
          <div className="space-y-2">
            <h1 className="text-5xl font-display font-bold text-slate-900 tracking-tight">
              Fast<span className="text-brand-600">Learning</span>
            </h1>
            <p className="text-slate-500 text-lg">Your AI-native workspace for accelerated mastery.</p>
          </div>

          <form onSubmit={handleSubmit} className="relative group">
            <div className="absolute inset-0 bg-brand-500/10 blur-2xl group-focus-within:bg-brand-500/20 transition-all rounded-full" />
            <div className="relative flex items-center">
              <div className="absolute left-6 text-slate-400">
                <Search size={24} />
              </div>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="What do you want to learn today?"
                className="w-full pl-16 pr-24 py-6 bg-white border-2 border-transparent shadow-xl rounded-3xl text-xl focus:outline-none focus:border-brand-500 transition-all"
              />
              <button
                type="submit"
                className="absolute right-3 px-6 py-3 bg-brand-600 text-white font-bold rounded-2xl hover:bg-brand-700 transition-all flex items-center gap-2"
              >
                Start
                <ArrowRight size={20} />
              </button>
            </div>
          </form>

          <div className="flex flex-wrap justify-center gap-3">
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => setInput(s)}
                className="px-4 py-2 bg-white border border-slate-200 rounded-full text-sm text-slate-600 hover:border-brand-300 hover:text-brand-600 transition-all"
              >
                {s}
              </button>
            ))}
          </div>
        </motion.div>

        {workspaces.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="w-full mt-24 space-y-6"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-display font-bold text-slate-800 flex items-center gap-2">
                <Clock size={20} className="text-brand-500" />
                Resume Learning
              </h2>
              <button className="text-sm font-bold text-brand-600 hover:underline">View All</button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {workspaces.map((ws) => (
                <motion.div
                  key={ws.id}
                  whileHover={{ y: -4 }}
                  onClick={() => onSelectWorkspace(ws.id)}
                  className="bg-white p-5 rounded-3xl border border-slate-200 shadow-sm hover:shadow-md hover:border-brand-200 cursor-pointer transition-all flex items-center justify-between group"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center">
                      <BookMarked size={24} />
                    </div>
                    <div>
                      <h3 className="font-display font-bold text-slate-800 group-hover:text-brand-600 transition-colors">
                        {ws.title}
                      </h3>
                      <div className="flex items-center gap-3 mt-1">
                        <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-brand-500 transition-all" 
                            style={{ width: `${ws.progress}%` }} 
                          />
                        </div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase">{ws.progress}% Complete</span>
                      </div>
                    </div>
                  </div>
                  <ArrowRight size={18} className="text-slate-300 group-hover:text-brand-500 transition-all" />
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </main>

      <footer className="p-8 text-center text-slate-400 text-sm">
        Built with AI for the next generation of learners.
      </footer>
    </div>
  );
};

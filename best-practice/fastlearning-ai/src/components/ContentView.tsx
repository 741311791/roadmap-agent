import React, { useState } from 'react';
import Markdown from 'react-markdown';
import { motion, AnimatePresence } from 'motion/react';
import { LearningContent } from '../services/gemini';
import { Artifact } from '../types';
import { ArrowLeft, BookOpen, Share2, Download, Wand2, FileText, Presentation, Video, Headphones, Radio, Library } from 'lucide-react';
import { cn } from '../lib/utils';

interface ContentViewProps {
  content: LearningContent;
  onBack: () => void;
  onAction: (type: string) => void;
  generatedTypes: string[];
  chapterArtifacts: Artifact[];
  onPreviewArtifact: (id: string) => void;
}

export const ContentView: React.FC<ContentViewProps> = ({ content, onBack, onAction, generatedTypes, chapterArtifacts, onPreviewArtifact }) => {
  const [isCollectorOpen, setIsCollectorOpen] = useState(false);
  const renderButton = (type: string, label: string, Icon: any) => {
    const isGenerated = generatedTypes.includes(type);
    return (
      <button
        key={type}
        onClick={() => onAction(type)}
        className={cn(
          "flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-all",
          isGenerated 
            ? "border-solid border-brand-300 bg-white text-brand-700 shadow-sm" 
            : "border-dashed border-slate-300 bg-transparent text-slate-500 hover:border-brand-300 hover:text-brand-600"
        )}
        title={isGenerated ? `View ${label}` : `Generate ${label}`}
      >
        <Icon size={14} />
        {label}
      </button>
    );
  };

  return (
    <div className="h-full flex flex-col bg-white">
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-slate-100 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 hover:bg-slate-100 rounded-xl text-slate-500 transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="flex items-center gap-2">
            <BookOpen size={18} className="text-brand-500" />
            <h2 className="font-display font-bold text-slate-800 line-clamp-1 max-w-[200px]">{content.title}</h2>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-slate-50 p-1 rounded-xl border border-slate-100">
            {renderButton('markdown', 'MD', FileText)}
            {renderButton('ppt', 'PPT', Presentation)}
            {renderButton('mindmap', 'Map', Share2)}
          </div>
          <div className="flex items-center gap-1.5 bg-slate-50 p-1 rounded-xl border border-slate-100">
            {renderButton('video', 'Video', Video)}
            {renderButton('audio', 'Audio', Headphones)}
            {renderButton('podcast', 'Cast', Radio)}
          </div>

          <div className="w-px h-4 bg-slate-200 mx-1" />

          <button className="p-2 hover:bg-slate-100 rounded-lg text-slate-400 transition-colors" title="Share">
            <Share2 size={16} />
          </button>

          <div className="relative">
            <button 
              onClick={() => setIsCollectorOpen(!isCollectorOpen)}
              className={cn(
                "p-2 rounded-lg transition-colors relative",
                isCollectorOpen ? "bg-brand-100 text-brand-700" : "bg-brand-50 text-brand-600 hover:bg-brand-100"
              )}
              title="Material Collector"
            >
              <Library size={16} />
              {chapterArtifacts.length > 0 && (
                <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-red-500 rounded-full" />
              )}
            </button>

            <AnimatePresence>
              {isCollectorOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  className="absolute right-0 mt-2 w-64 bg-white border border-slate-200 shadow-xl rounded-xl p-2 z-50"
                >
                  <div className="px-3 py-2 border-b border-slate-100 mb-2">
                    <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Chapter Materials</h3>
                  </div>
                  <div className="max-h-64 overflow-y-auto space-y-1">
                    {chapterArtifacts.length === 0 ? (
                      <p className="text-xs text-slate-500 px-3 py-4 text-center">No materials generated yet.</p>
                    ) : (
                      chapterArtifacts.map(art => (
                        <div key={art.id} className="group flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-slate-50 transition-colors">
                          <button
                            onClick={() => {
                              onPreviewArtifact(art.id);
                              setIsCollectorOpen(false);
                            }}
                            className="flex-1 text-left flex flex-col gap-0.5"
                          >
                            <span className="text-sm font-medium text-slate-700 line-clamp-1">{art.title}</span>
                            <span className="text-[10px] font-bold text-brand-500 uppercase tracking-wider">{art.type}</span>
                          </button>
                          <button 
                            className="p-1.5 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-md opacity-0 group-hover:opacity-100 transition-all"
                            title="Download"
                            onClick={(e) => {
                              e.stopPropagation();
                              // Mock download action
                              const link = document.createElement('a');
                              link.href = `data:text/plain;charset=utf-8,${encodeURIComponent(art.content)}`;
                              link.download = `${art.title}.${art.type === 'markdown' ? 'md' : art.type}`;
                              link.click();
                            }}
                          >
                            <Download size={14} />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto py-12 px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="markdown-body"
          >
            <Markdown>{content.markdown}</Markdown>
          </motion.div>

          {content.codeSnippets && content.codeSnippets.length > 0 && (
            <div className="mt-12 space-y-8">
              <h3 className="text-lg font-display font-bold text-slate-800 flex items-center gap-2">
                <span className="w-1.5 h-6 bg-brand-500 rounded-full" />
                Code Examples
              </h3>
              {content.codeSnippets.map((snippet, idx) => (
                <div key={idx} className="rounded-2xl overflow-hidden border border-slate-200 shadow-sm">
                  <div className="bg-slate-50 px-4 py-2 border-b border-slate-200 flex items-center justify-between">
                    <span className="text-xs font-mono text-slate-500 uppercase">{snippet.language}</span>
                    <button className="text-[10px] font-bold text-brand-600 hover:text-brand-700 uppercase tracking-wider">Copy</button>
                  </div>
                  <pre className="p-4 bg-slate-900 text-slate-100 font-mono text-sm overflow-x-auto m-0 rounded-none">
                    <code>{snippet.code}</code>
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

import React, { useState } from 'react';
import Markdown from 'react-markdown';
import { motion } from 'motion/react';
import { Artifact } from '../types';
import { ArrowLeft, Presentation, FileText, ChevronLeft, ChevronRight, Share2, Video, Headphones, Radio, Play } from 'lucide-react';

interface ArtifactPreviewProps {
  artifact: Artifact;
  onBack: () => void;
}

export const ArtifactPreview: React.FC<ArtifactPreviewProps> = ({ artifact, onBack }) => {
  const [currentSlide, setCurrentSlide] = useState(0);

  const getIcon = (type: string) => {
    switch(type) {
      case 'ppt': return <Presentation size={18} className="text-orange-500" />;
      case 'mindmap': return <Share2 size={18} className="text-blue-500" />;
      case 'video': return <Video size={18} className="text-red-500" />;
      case 'audio': return <Headphones size={18} className="text-purple-500" />;
      case 'podcast': return <Radio size={18} className="text-green-500" />;
      default: return <FileText size={18} className="text-brand-500" />;
    }
  };

  const renderContent = () => {
    if (['video', 'audio', 'podcast'].includes(artifact.type)) {
      return (
        <div className="flex flex-col h-full items-center justify-center p-8 bg-slate-900">
          <div className="w-full max-w-2xl aspect-video bg-slate-800 rounded-3xl shadow-2xl flex flex-col items-center justify-center border border-slate-700 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-brand-500/20 to-purple-500/20" />
            <div className="w-20 h-20 rounded-full bg-white/10 flex items-center justify-center backdrop-blur-md border border-white/20 cursor-pointer hover:bg-white/20 transition-all z-10">
              <Play size={32} className="text-white ml-2" />
            </div>
            <p className="mt-6 text-white font-medium z-10">{artifact.title}</p>
            <p className="text-slate-400 text-sm z-10 mt-2">Mock {artifact.type.toUpperCase()} Player</p>
          </div>
        </div>
      );
    }

    if (artifact.type === 'mindmap') {
      return (
        <div className="flex flex-col h-full items-center justify-center p-8 bg-slate-50">
           <div className="w-full max-w-4xl h-[600px] bg-white rounded-3xl shadow-sm border border-slate-200 flex items-center justify-center">
              <div className="text-center">
                <Share2 size={48} className="text-brand-300 mx-auto mb-4" />
                <h3 className="text-xl font-display font-bold text-slate-700 mb-2">{artifact.title}</h3>
                <p className="text-slate-500">Interactive Mindmap Visualization (Mock)</p>
              </div>
           </div>
        </div>
      );
    }
    if (artifact.type === 'ppt') {
      const slides = artifact.content.split('---').map(s => s.trim());
      return (
        <div className="flex flex-col h-full items-center justify-center p-8 bg-slate-900">
          <div className="w-full max-w-4xl aspect-video bg-white rounded-2xl shadow-2xl p-12 flex flex-col justify-center relative">
            <div className="markdown-body prose-lg max-w-none">
              <Markdown>{slides[currentSlide]}</Markdown>
            </div>
            
            <div className="absolute bottom-6 left-0 right-0 flex justify-center items-center gap-6">
              <button 
                onClick={() => setCurrentSlide(s => Math.max(0, s - 1))}
                disabled={currentSlide === 0}
                className="p-2 rounded-full bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 transition-colors"
              >
                <ChevronLeft size={24} />
              </button>
              <span className="text-sm font-medium text-slate-400">
                {currentSlide + 1} / {slides.length}
              </span>
              <button 
                onClick={() => setCurrentSlide(s => Math.min(slides.length - 1, s + 1))}
                disabled={currentSlide === slides.length - 1}
                className="p-2 rounded-full bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 transition-colors"
              >
                <ChevronRight size={24} />
              </button>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="max-w-3xl mx-auto py-12 px-8">
        <div className="markdown-body">
          <Markdown>{artifact.content}</Markdown>
        </div>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-white">
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-slate-100 px-6 py-4 flex items-center gap-4">
        <button
          onClick={onBack}
          className="p-2 hover:bg-slate-100 rounded-xl text-slate-500 transition-colors"
        >
          <ArrowLeft size={20} />
        </button>
        <div className="flex items-center gap-2">
          {getIcon(artifact.type)}
          <h2 className="font-display font-bold text-slate-800">{artifact.title}</h2>
        </div>
      </header>
      <main className="flex-1 overflow-y-auto">
        {renderContent()}
      </main>
    </div>
  );
};

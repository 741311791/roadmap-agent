import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { HubView } from './components/HubView';
import { Copilot } from './components/Copilot';
import { RoadmapView } from './components/RoadmapView';
import { ContentView } from './components/ContentView';
import { ArtifactPreview } from './components/ArtifactPreview';
import { Workspace, ViewState, Message, Artifact, ChatSession } from './types';
import { geminiService, RoadmapNode, LearningContent } from './services/gemini';
import { LayoutGrid, FolderOpen, Settings, LogOut, Sparkles } from 'lucide-react';
import { cn } from './lib/utils';

export default function App() {
  const [view, setView] = useState<ViewState>(() => {
    const saved = localStorage.getItem('fastlearning_view');
    return (saved as ViewState) || 'hub';
  });
  const [workspaces, setWorkspaces] = useState<Workspace[]>(() => {
    const saved = localStorage.getItem('fastlearning_workspaces');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return parsed.map((ws: any) => {
          if (ws.messages && !ws.chatSessions) {
            return {
              ...ws,
              chatSessions: [{
                id: 'default_session',
                title: 'Initial Chat',
                targetId: 'roadmap',
                createdAt: ws.createdAt || Date.now(),
                messages: ws.messages
              }],
              messages: undefined
            };
          }
          return ws;
        });
      } catch (e) {
        return [];
      }
    }
    return [];
  });
  const [activeSessionId, setActiveSessionId] = useState<string | null>(() => {
    return localStorage.getItem('fastlearning_activeSessionId');
  });
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(() => {
    return localStorage.getItem('fastlearning_activeWorkspaceId');
  });
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentContent, setCurrentContent] = useState<LearningContent | null>(() => {
    const saved = localStorage.getItem('fastlearning_currentContent');
    return saved ? JSON.parse(saved) : null;
  });
  const [activeNodeId, setActiveNodeId] = useState<string | undefined>(() => {
    return localStorage.getItem('fastlearning_activeNodeId') || undefined;
  });
  const [activeArtifactId, setActiveArtifactId] = useState<string | null>(() => {
    return localStorage.getItem('fastlearning_activeArtifactId');
  });
  const [isVaultOpen, setIsVaultOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem('fastlearning_view', view);
    localStorage.setItem('fastlearning_workspaces', JSON.stringify(workspaces));
    if (activeWorkspaceId) localStorage.setItem('fastlearning_activeWorkspaceId', activeWorkspaceId);
    else localStorage.removeItem('fastlearning_activeWorkspaceId');
    
    if (activeSessionId) localStorage.setItem('fastlearning_activeSessionId', activeSessionId);
    else localStorage.removeItem('fastlearning_activeSessionId');
    
    if (currentContent) localStorage.setItem('fastlearning_currentContent', JSON.stringify(currentContent));
    else localStorage.removeItem('fastlearning_currentContent');
    
    if (activeNodeId) localStorage.setItem('fastlearning_activeNodeId', activeNodeId);
    else localStorage.removeItem('fastlearning_activeNodeId');

    if (activeArtifactId) localStorage.setItem('fastlearning_activeArtifactId', activeArtifactId);
    else localStorage.removeItem('fastlearning_activeArtifactId');
  }, [view, workspaces, activeWorkspaceId, currentContent, activeNodeId, activeArtifactId]);

  const activeWorkspace = workspaces.find(ws => ws.id === activeWorkspaceId);
  const activeArtifact = activeWorkspace?.artifacts.find(a => a.id === activeArtifactId);
  const currentTargetId = (view === 'learning' || view === 'preview') && activeNodeId ? activeNodeId : 'roadmap';

  // Ensure a session exists for the current target and auto-switch
  useEffect(() => {
    if (!activeWorkspaceId) return;
    
    setWorkspaces(prev => {
      const ws = prev.find(w => w.id === activeWorkspaceId);
      if (!ws) return prev;
      
      const targetSessions = ws.chatSessions.filter(s => s.targetId === currentTargetId);
      if (targetSessions.length === 0) {
        const newSession: ChatSession = {
          id: Date.now().toString(),
          title: currentTargetId === 'roadmap' ? 'Roadmap Discussion' : 'Chapter Discussion',
          targetId: currentTargetId,
          createdAt: Date.now(),
          messages: [{
            id: Date.now().toString(),
            role: 'assistant',
            content: currentTargetId === 'roadmap' 
              ? "Hi! I can help you adjust this learning roadmap. What would you like to change?"
              : "Hi! I'm here to help you with this chapter. Any questions?"
          }]
        };
        return prev.map(w => w.id === activeWorkspaceId ? { ...w, chatSessions: [...w.chatSessions, newSession] } : w);
      }
      return prev;
    });
  }, [activeWorkspaceId, currentTargetId]);

  useEffect(() => {
    const ws = workspaces.find(w => w.id === activeWorkspaceId);
    if (!ws) return;
    
    const currentSession = ws.chatSessions.find(s => s.id === activeSessionId);
    if (!currentSession || currentSession.targetId !== currentTargetId) {
      const targetSessions = ws.chatSessions.filter(s => s.targetId === currentTargetId);
      if (targetSessions.length > 0) {
        const latest = [...targetSessions].sort((a, b) => b.createdAt - a.createdAt)[0];
        setActiveSessionId(latest.id);
      }
    }
  }, [activeWorkspaceId, currentTargetId, workspaces, activeSessionId]);

  const handleNewWorkspace = async (topic: string) => {
    setIsGenerating(true);
    const id = Math.random().toString(36).substring(7);
    const newWs: Workspace = {
      id,
      title: topic,
      topic,
      roadmap: null,
      chatSessions: [{
        id: Date.now().toString(),
        title: 'Roadmap Discussion',
        targetId: 'roadmap',
        createdAt: Date.now(),
        messages: [{
          id: '1',
          role: 'assistant',
          content: `Hello! I'm your learning copilot. I'm generating a personalized roadmap for "${topic}". Please wait a moment...`
        }]
      }],
      artifacts: [],
      currentPath: [],
      progress: 0
    };

    setWorkspaces(prev => [...prev, newWs]);
    setActiveWorkspaceId(id);
    setView('roadmap');

    try {
      const roadmap = await geminiService.generateRoadmap(topic, "Beginner level, focused on practical application.");
      setWorkspaces(prev => prev.map(ws => 
        ws.id === id ? { 
          ...ws, 
          roadmap, 
          chatSessions: ws.chatSessions.map(cs => 
            cs.targetId === 'roadmap' ? {
              ...cs,
              messages: [...cs.messages, {
                id: '2',
                role: 'assistant',
                content: `I've created a roadmap for you! You can see it on the right. Where would you like to start?`
              }]
            } : cs
          )
        } : ws
      ));
    } catch (error) {
      console.error(error);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSelectWorkspace = (id: string) => {
    setActiveWorkspaceId(id);
    setView('roadmap');
  };

  const handleSendMessage = async (content: string) => {
    if (!activeWorkspaceId || !activeSessionId) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content };
    setWorkspaces(prev => prev.map(ws => 
      ws.id === activeWorkspaceId ? {
        ...ws,
        chatSessions: ws.chatSessions.map(cs => 
          cs.id === activeSessionId ? { ...cs, messages: [...cs.messages, userMsg] } : cs
        )
      } : ws
    ));

    setIsGenerating(true);
    
    // Mock dynamic response
    setTimeout(() => {
      let responseText = `Regarding "${content}", in the context of ${activeWorkspace?.topic}, it usually means breaking down the problem into smaller, manageable pieces. Would you like me to generate a specific example for this?`;
      if (currentTargetId !== 'roadmap') {
        responseText = `For the chapter "${currentContent?.title}", ${responseText}`;
      }

      const botMsg: Message = { 
        id: (Date.now() + 1).toString(), 
        role: 'assistant', 
        content: responseText
      };
      setWorkspaces(prev => prev.map(ws => 
        ws.id === activeWorkspaceId ? {
          ...ws,
          chatSessions: ws.chatSessions.map(cs => 
            cs.id === activeSessionId ? { ...cs, messages: [...cs.messages, botMsg] } : cs
          )
        } : ws
      ));
      setIsGenerating(false);
    }, 1500);
  };

  const handleNodeClick = async (node: RoadmapNode) => {
    if (!activeWorkspaceId) return;
    setActiveNodeId(node.id);
    setIsGenerating(true);
    setView('learning');

    try {
      const content = await geminiService.generateContent(node.title, activeWorkspace?.topic || "");
      setCurrentContent(content);
      
      // Update node status to in-progress
      setWorkspaces(prev => prev.map(ws => {
        if (ws.id === activeWorkspaceId && ws.roadmap) {
          const updateNodes = (nodes: RoadmapNode[]): RoadmapNode[] => {
            return nodes.map(n => {
              if (n.id === node.id) return { ...n, status: 'in-progress' };
              if (n.children) return { ...n, children: updateNodes(n.children) };
              return n;
            });
          };
          return { ...ws, roadmap: { ...ws.roadmap, nodes: updateNodes(ws.roadmap.nodes) } };
        }
        return ws;
      }));

      // Generate a quiz after a delay
      setTimeout(async () => {
        const quiz = await geminiService.generateQuiz(content.markdown);
        const quizMsg: Message = {
          id: Date.now().toString(),
          role: 'assistant',
          content: "Ready for a quick check? Here's a question based on what you just read.",
          type: 'quiz',
          data: quiz
        };
        setWorkspaces(prev => prev.map(ws => 
          ws.id === activeWorkspaceId ? {
            ...ws,
            chatSessions: ws.chatSessions.map(cs => 
              cs.id === activeSessionId ? { ...cs, messages: [...cs.messages, quizMsg] } : cs
            )
          } : ws
        ));
      }, 3000);

    } catch (error) {
      console.error(error);
    } finally {
      setIsGenerating(false);
    }
  };

  const generatedTypes = activeWorkspace?.artifacts
    .filter(a => a.title.includes(currentContent?.title || ''))
    .map(a => a.type) || [];

  const chapterArtifacts = activeWorkspace?.artifacts
    .filter(a => a.title.includes(currentContent?.title || '')) || [];

  const handleArtifactAction = (type: string) => {
    if (!activeWorkspaceId || !currentContent) return;
    
    const existing = activeWorkspace?.artifacts.find(a => a.type === type && a.title.includes(currentContent.title));
    if (existing) {
      handlePreviewArtifact(existing.id);
      return;
    }

    setIsGenerating(true);
    
    setTimeout(() => {
      let content = "Generated content here...";
      if (type === 'ppt') {
        content = `# ${currentContent.title}\n\nGenerated Presentation\n\n---\n\n## Key Concepts\n\n- Understand the basics\n- Apply practically\n- Review and iterate\n\n---\n\n## Summary\n\nGreat job completing this module!`;
      } else if (type === 'markdown') {
        content = `# ${currentContent.title} - Summary\n\nHere is the detailed markdown view of the concepts we discussed.\n\n### Core Points\n- **Point 1**: Detail about point 1.\n- **Point 2**: Detail about point 2.\n\n> "Learning is a continuous process."`;
      }

      const artifact: Artifact = {
        id: Date.now().toString(),
        type: type as any,
        title: `${type.toUpperCase()}: ${currentContent.title}`,
        content,
        createdAt: Date.now()
      };

      setWorkspaces(prev => prev.map(ws => 
        ws.id === activeWorkspaceId ? { ...ws, artifacts: [...ws.artifacts, artifact] } : ws
      ));

      const msg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `I've generated a ${type} for you! You can find it in your resource vault or preview it here.`,
        type: 'artifact',
        data: artifact
      };

      setWorkspaces(prev => prev.map(ws => 
        ws.id === activeWorkspaceId ? {
          ...ws,
          chatSessions: ws.chatSessions.map(cs => 
            cs.id === activeSessionId ? { ...cs, messages: [...cs.messages, msg] } : cs
          )
        } : ws
      ));
      setIsGenerating(false);
    }, 1500);
  };

  const handleNewSession = () => {
    if (!activeWorkspaceId) return;
    const newSessionId = Date.now().toString();
    const newSession: ChatSession = {
      id: newSessionId,
      title: `New ${currentTargetId === 'roadmap' ? 'Roadmap' : 'Chapter'} Chat`,
      targetId: currentTargetId,
      createdAt: Date.now(),
      messages: [{
        id: Date.now().toString(),
        role: 'assistant',
        content: currentTargetId === 'roadmap' 
          ? "Hi! I can help you adjust this learning roadmap. What would you like to change?"
          : "Hi! I'm here to help you with this chapter. Any questions?"
      }]
    };
    setWorkspaces(prev => prev.map(ws => 
      ws.id === activeWorkspaceId ? { ...ws, chatSessions: [...ws.chatSessions, newSession] } : ws
    ));
    setActiveSessionId(newSessionId);
  };

  const handlePreviewArtifact = (id: string) => {
    setActiveArtifactId(id);
    setView('preview');
  };

  if (view === 'hub') {
    return (
      <HubView 
        workspaces={workspaces} 
        onNewWorkspace={handleNewWorkspace} 
        onSelectWorkspace={handleSelectWorkspace} 
      />
    );
  }

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-16 bg-slate-900 flex flex-col items-center py-6 gap-8 shrink-0">
        <div className="w-10 h-10 rounded-xl bg-brand-500 flex items-center justify-center text-white shadow-lg shadow-brand-500/20">
          <Sparkles size={20} />
        </div>
        
        <nav className="flex-1 flex flex-col gap-4">
          <button 
            onClick={() => setView('hub')}
            className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-400 hover:bg-slate-800 hover:text-white transition-all"
          >
            <LayoutGrid size={20} />
          </button>
          <button 
            onClick={() => setIsVaultOpen(true)}
            className={cn(
              "relative w-10 h-10 rounded-xl flex items-center justify-center transition-all",
              isVaultOpen ? "bg-slate-800 text-white" : "text-slate-400 hover:bg-slate-800 hover:text-white"
            )}
            title="Resource Vault"
          >
            <FolderOpen size={20} />
            {activeWorkspace?.artifacts && activeWorkspace.artifacts.length > 0 && (
              <span className="absolute top-2 right-2 w-2 h-2 bg-brand-500 rounded-full" />
            )}
          </button>
        </nav>

        <div className="flex flex-col gap-4">
          <button className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-400 hover:bg-slate-800 hover:text-white transition-all">
            <Settings size={20} />
          </button>
          <button className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-400 hover:bg-slate-800 hover:text-white transition-all">
            <LogOut size={20} />
          </button>
        </div>
      </aside>

      {/* Copilot (Left Brain) */}
      <div className="w-[400px] shrink-0">
        <Copilot 
          session={activeWorkspace?.chatSessions.find(s => s.id === activeSessionId)}
          sessions={activeWorkspace?.chatSessions || []}
          currentTargetId={currentTargetId}
          onSendMessage={handleSendMessage}
          onNewSession={handleNewSession}
          onSwitchSession={setActiveSessionId}
          isGenerating={isGenerating}
          onPreviewArtifact={handlePreviewArtifact}
        />
      </div>

      {/* Canvas (Right Brain) */}
      <main className="flex-1 relative overflow-hidden bg-white">
        <AnimatePresence mode="wait">
          {view === 'roadmap' && activeWorkspace?.roadmap && (
            <motion.div
              key="roadmap"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="h-full overflow-y-auto"
            >
              <RoadmapView 
                roadmap={activeWorkspace.roadmap} 
                onNodeClick={handleNodeClick}
                activeNodeId={activeNodeId}
              />
            </motion.div>
          )}

          {view === 'learning' && currentContent && (
            <motion.div
              key="learning"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="h-full"
            >
              <ContentView 
                content={currentContent} 
                onBack={() => setView('roadmap')}
                onAction={handleArtifactAction}
                generatedTypes={generatedTypes}
                chapterArtifacts={chapterArtifacts}
                onPreviewArtifact={handlePreviewArtifact}
              />
            </motion.div>
          )}

          {view === 'preview' && activeArtifact && (
            <motion.div
              key="preview"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="h-full absolute inset-0 z-10 bg-white"
            >
              <ArtifactPreview 
                artifact={activeArtifact} 
                onBack={() => setView(currentContent ? 'learning' : 'roadmap')}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Vault Drawer */}
        <AnimatePresence>
          {isVaultOpen && (
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              className="absolute top-0 right-0 bottom-0 w-80 bg-white border-l border-slate-200 shadow-2xl z-30 flex flex-col"
            >
              <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                <h3 className="font-display font-bold text-slate-800 flex items-center gap-2">
                  <FolderOpen size={18} className="text-brand-500" />
                  Resource Vault
                </h3>
                <button 
                  onClick={() => setIsVaultOpen(false)} 
                  className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 transition-colors"
                >
                  &times;
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {activeWorkspace?.artifacts.map(art => (
                  <div 
                    key={art.id} 
                    className="p-3 border border-slate-100 rounded-xl hover:border-brand-300 hover:bg-brand-50 cursor-pointer transition-colors" 
                    onClick={() => { 
                      handlePreviewArtifact(art.id); 
                      setIsVaultOpen(false); 
                    }}
                  >
                    <p className="font-medium text-sm text-slate-800">{art.title}</p>
                    <p className="text-[10px] font-bold text-slate-400 uppercase mt-1 tracking-wider">{art.type}</p>
                  </div>
                ))}
                {(!activeWorkspace?.artifacts || activeWorkspace.artifacts.length === 0) && (
                  <p className="text-sm text-slate-500 text-center mt-8">No resources generated yet.</p>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

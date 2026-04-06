import { Roadmap, RoadmapNode } from "./services/gemini";

export type ViewState = 'hub' | 'roadmap' | 'learning' | 'preview';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  type?: 'text' | 'quiz' | 'artifact';
  data?: any;
}

export interface ChatSession {
  id: string;
  title: string;
  targetId: string;
  createdAt: number;
  messages: Message[];
}

export interface Artifact {
  id: string;
  type: 'markdown' | 'mindmap' | 'ppt' | 'pdf' | 'video' | 'audio' | 'podcast';
  title: string;
  content: string;
  createdAt: number;
}

export interface Workspace {
  id: string;
  title: string;
  topic: string;
  roadmap: Roadmap | null;
  chatSessions: ChatSession[];
  artifacts: Artifact[];
  currentPath: string[]; // Node IDs
  progress: number;
}

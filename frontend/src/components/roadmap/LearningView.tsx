import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { motion } from 'framer-motion';
import {
    ChevronLeft,
    Menu,
    Plus,
    Trash2,
    Pencil,
    Layers,
    BookOpen,
    FileText,
    Clock,
    CheckCircle2
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Sheet, SheetContent, SheetTrigger } from '../ui/Sheet'; // Assuming shadcn/ui components
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/Tabs'; // Assuming shadcn/ui components

// --- Types ---
interface Note {
    id: string;
    quote: string;
    text: string;
    createdAt: Date;
}

interface ConceptData {
    concept_id: string;
    name: string;
    description: string;
    estimated_hours: number;
    difficulty: string;
    keywords: string[];
    content_status?: string;
    // Add other fields as needed from JSON
}

interface LearningViewProps {
    concept: ConceptData;
    onBack: () => void;
    onPrevious: () => void;
    onNext: () => void;
    hasPrevious: boolean;
    hasNext: boolean;
}

// --- Mock Markdown Content Generator ---
const generateMarkdownContent = (concept: ConceptData) => {
    return `
# ${concept.name}

## Introduction
${concept.description}

This concept is fundamental to understanding the broader topic. We will explore the key principles, practical applications, and common pitfalls.

## Key Concepts

### 1. The Core Principle
At its heart, **${concept.name}** is about structure and logic. 
> "Good code is its own best documentation." 

When working with this, remember to keep things simple and modular.

### 2. Implementation Details
Here is a basic example of how this might look in code:

\`\`\`javascript
function init${concept.name.replace(/\s+/g, '')}() {
  console.log("Initializing ${concept.name}...");
  return true;
}
\`\`\`

## Best Practices
*   **Consistency:** Always follow the established patterns.
*   **Readability:** Write code for humans first, machines second.
*   **Testing:** Verify your assumptions with unit tests.

## Common Mistakes
1.  Over-engineering the solution.
2.  Ignoring edge cases.
3.  Forgetting to handle errors gracefully.

## Conclusion
Mastering **${concept.name}** takes time and practice. Start small, build often, and don't be afraid to break things.

## Further Reading
*   [Official Documentation](#)
*   [Community Guide](#)
`;
};

const LearningView: React.FC<LearningViewProps> = ({
    concept,
    onBack,
    onPrevious,
    onNext,
    hasPrevious,
    hasNext
}) => {
    // const { conceptId } = useParams<{ conceptId: string }>(); // Removed internal routing
    // const navigate = useNavigate(); // Removed internal navigation
    // const [concept, setConcept] = useState<ConceptData | null>(null); // Removed internal state
    const [markdownContent, setMarkdownContent] = useState('');

    // UI State
    const [isTocCollapsed, setIsTocCollapsed] = useState(false);
    const [notes, setNotes] = useState<Note[]>([]);
    const [newNoteText, setNewNoteText] = useState('');
    const [activeSection, setActiveSection] = useState<string>('');

    // Refs
    // const contentRef = useRef<HTMLDivElement>(null);

    // --- Data Fetching ---
    useEffect(() => {
        if (concept) {
            setMarkdownContent(generateMarkdownContent(concept));
        }
    }, [concept]);

    // --- TOC Logic (Mock) ---
    // In a real app, parse markdown headers. Here we hardcode based on our generator.
    const tocItems = [
        { id: 'introduction', label: 'Introduction' },
        { id: 'key-concepts', label: 'Key Concepts' },
        { id: 'best-practices', label: 'Best Practices' },
        { id: 'common-mistakes', label: 'Common Mistakes' },
        { id: 'conclusion', label: 'Conclusion' },
    ];

    // --- Notes Logic ---
    const handleAddNote = () => {
        if (!newNoteText.trim()) return;

        const newNote: Note = {
            id: Date.now().toString(),
            quote: "Selected text placeholder...", // MVP: Mock selection
            text: newNoteText,
            createdAt: new Date(),
        };

        setNotes([newNote, ...notes]);
        setNewNoteText('');
    };

    const handleDeleteNote = (id: string) => {
        setNotes(notes.filter(n => n.id !== id));
    };

    // if (!concept) return <div className="flex items-center justify-center h-screen bg-[#FFFCF9]">Loading...</div>;

    return (
        <div className="flex h-full bg-[#FFFCF9] overflow-hidden font-sans text-stone-800">

            {/* --- ZONE 1: Floating TOC (Left) --- */}
            <motion.div
                initial={false}
                animate={{ width: isTocCollapsed ? 60 : 240 }}
                className="flex-shrink-0 border-r border-stone-200/60 h-full relative bg-[#FFFCF9] z-10 hidden md:flex flex-col"
            >
                <div className="p-4 flex items-center justify-between">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onBack}
                        className="text-stone-500 hover:text-stone-800 hover:bg-stone-100"
                        title="Back to Dashboard"
                    >
                        <ChevronLeft size={20} />
                    </Button>
                    {!isTocCollapsed && (
                        <span className="text-xs font-bold tracking-widest text-stone-400 uppercase">Outline</span>
                    )}
                </div>

                <div className="flex-1 flex flex-col justify-center px-4">
                    {!isTocCollapsed ? (
                        <nav className="space-y-1">
                            {tocItems.map(item => (
                                <a
                                    key={item.id}
                                    href={`#${item.id}`}
                                    className={`block py-1.5 px-3 text-sm rounded-md transition-colors ${activeSection === item.id
                                        ? 'bg-sage-100 text-sage-800 font-medium'
                                        : 'text-stone-500 hover:text-stone-800 hover:bg-stone-100'
                                        }`}
                                    onClick={() => setActiveSection(item.id)}
                                >
                                    {item.label}
                                </a>
                            ))}
                        </nav>
                    ) : (
                        <div className="flex flex-col items-center gap-4">
                            {tocItems.map(item => (
                                <div
                                    key={item.id}
                                    className="w-2 h-2 rounded-full bg-stone-300 hover:bg-sage-500 transition-colors cursor-pointer"
                                    title={item.label}
                                />
                            ))}
                        </div>
                    )}
                </div>

                <div className="p-4 border-t border-stone-100 flex justify-center">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setIsTocCollapsed(!isTocCollapsed)}
                        className="text-stone-400 hover:text-stone-600"
                    >
                        {isTocCollapsed ? <Menu size={16} /> : <ChevronLeft size={16} />}
                    </Button>
                </div>
            </motion.div>


            {/* --- ZONE 2: Core Reader (Center) --- */}
            <div className="flex-1 h-full overflow-y-auto relative scroll-smooth" id="reader-scroll-container">
                <div className="max-w-[85ch] mx-auto py-12 px-8 min-h-full">

                    {/* Paper Container */}
                    <div className="bg-white shadow-sm border border-stone-100 rounded-xl p-12 md:p-16 min-h-[80vh]">
                        {/* Header */}
                        <header className="mb-12 border-b border-stone-100 pb-8">
                            <div className="flex items-center gap-2 text-sm text-sage-600 font-medium mb-4">
                                <span className="px-2 py-0.5 bg-sage-50 rounded-full border border-sage-100">
                                    {concept.difficulty}
                                </span>
                                <span className="flex items-center gap-1">
                                    <Clock size={14} /> {concept.estimated_hours}h
                                </span>
                            </div>
                            <h1 className="text-4xl md:text-5xl font-serif font-bold text-stone-900 mb-6 leading-tight">
                                {concept.name}
                            </h1>
                            <p className="text-lg text-stone-500 leading-relaxed max-w-2xl">
                                {concept.description}
                            </p>
                        </header>

                        {/* Markdown Content */}
                        <article className="prose prose-stone prose-lg max-w-none 
                            prose-headings:font-serif prose-headings:font-bold prose-headings:text-stone-800
                            prose-p:text-stone-600 prose-p:leading-loose
                            prose-blockquote:border-l-sage-400 prose-blockquote:bg-sage-50/50 prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:not-italic prose-blockquote:text-stone-700
                            prose-code:text-sage-700 prose-code:bg-sage-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:before:content-none prose-code:after:content-none
                            prose-pre:bg-stone-900 prose-pre:shadow-lg prose-pre:rounded-xl
                            prose-li:text-stone-600
                            prose-strong:text-stone-800 prose-strong:font-semibold
                        ">
                            <ReactMarkdown>{markdownContent}</ReactMarkdown>
                        </article>

                        {/* Footer Area */}
                        <div className="mt-20 pt-10 border-t border-stone-100 flex justify-between items-center">
                            <div className="text-sm text-stone-400">
                                Last updated: Just now
                            </div>
                            <Button className="bg-sage-600 hover:bg-sage-700 text-white rounded-full px-8">
                                Mark as Complete <CheckCircle2 size={16} className="ml-2" />
                            </Button>
                        </div>
                    </div>
                </div>
            </div>


            {/* --- ZONE 3: Notes Manager (Right) --- */}
            <div className="w-[320px] bg-white border-l border-stone-200 flex flex-col h-full shadow-[-4px_0_24px_rgba(0,0,0,0.02)] z-20 hidden lg:flex">
                <div className="p-5 border-b border-stone-100 flex items-center justify-between bg-white/80 backdrop-blur-sm sticky top-0 z-10">
                    <h3 className="font-serif font-bold text-stone-800 text-lg flex items-center gap-2">
                        <Pencil size={18} className="text-sage-600" />
                        My Notes
                    </h3>
                    <span className="text-xs font-medium text-stone-400 bg-stone-100 px-2 py-1 rounded-full">
                        {notes.length}
                    </span>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-stone-50/30">
                    {notes.length === 0 ? (
                        <div className="text-center py-10 px-4">
                            <div className="w-12 h-12 bg-stone-100 rounded-full flex items-center justify-center mx-auto mb-3 text-stone-400">
                                <Pencil size={20} />
                            </div>
                            <p className="text-stone-500 font-medium text-sm">No notes yet</p>
                            <p className="text-stone-400 text-xs mt-1">Highlight text to add a note</p>
                        </div>
                    ) : (
                        notes.map(note => (
                            <div key={note.id} className="group bg-white p-4 rounded-xl border border-stone-100 shadow-sm hover:shadow-md transition-all">
                                <div className="mb-2 pl-3 border-l-2 border-sage-300">
                                    <p className="text-xs text-stone-400 italic line-clamp-2 font-serif">
                                        "{note.quote}"
                                    </p>
                                </div>
                                <p className="text-sm text-stone-700 leading-relaxed mb-3">
                                    {note.text}
                                </p>
                                <div className="flex items-center justify-between mt-2 pt-2 border-t border-stone-50">
                                    <span className="text-[10px] text-stone-400">
                                        {note.createdAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                    <button
                                        onClick={() => handleDeleteNote(note.id)}
                                        className="text-stone-300 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100 p-1"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>

                <div className="p-4 bg-white border-t border-stone-200">
                    <div className="relative">
                        <textarea
                            value={newNoteText}
                            onChange={(e) => setNewNoteText(e.target.value)}
                            placeholder="Type a note..."
                            className="w-full bg-stone-50 border border-stone-200 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500 transition-all resize-none h-24"
                        />
                        <div className="absolute bottom-2 right-2">
                            <Button
                                size="sm"
                                onClick={handleAddNote}
                                disabled={!newNoteText.trim()}
                                className="h-8 w-8 rounded-lg p-0 bg-sage-600 hover:bg-sage-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <Plus size={16} />
                            </Button>
                        </div>
                    </div>
                </div>
            </div>


            {/* --- ZONE 4: Magic Ball (FAB) --- */}
            <Sheet>
                <SheetTrigger className="fixed bottom-8 right-8 lg:right-[350px] z-50">
                    <Button
                        className="h-14 w-14 rounded-full bg-sage-600 hover:bg-sage-700 text-white shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center p-0"
                    >
                        <Layers size={24} />
                    </Button>
                </SheetTrigger>
                <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
                    <div className="mt-8">
                        <h2 className="text-2xl font-serif font-bold text-stone-800 mb-6">{concept.name}</h2>

                        <Tabs defaultValue="overview" className="w-full">
                            <TabsList className="w-full grid grid-cols-3 mb-6">
                                <TabsTrigger value="overview">Overview</TabsTrigger>
                                <TabsTrigger value="resources">Resources</TabsTrigger>
                                <TabsTrigger value="quiz">Quiz</TabsTrigger>
                            </TabsList>

                            <TabsContent value="overview" className="space-y-4">
                                <div className="p-4 bg-sage-50 rounded-xl border border-sage-100">
                                    <h3 className="font-semibold text-sage-800 mb-2 flex items-center gap-2">
                                        <Clock size={16} /> Estimated Time
                                    </h3>
                                    <p className="text-stone-600">{concept.estimated_hours} hours</p>
                                </div>

                                <div className="space-y-2">
                                    <h3 className="font-semibold text-stone-800">Description</h3>
                                    <p className="text-stone-600 leading-relaxed">{concept.description}</p>
                                </div>

                                <div className="space-y-2">
                                    <h3 className="font-semibold text-stone-800">Keywords</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {concept.keywords.map(k => (
                                            <span key={k} className="px-2 py-1 bg-stone-100 text-stone-600 rounded-md text-sm">
                                                {k}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </TabsContent>

                            <TabsContent value="resources" className="space-y-4">
                                <div className="p-4 border border-stone-200 rounded-xl hover:border-sage-300 transition-colors cursor-pointer group">
                                    <div className="flex items-start gap-3">
                                        <div className="p-2 bg-sage-100 text-sage-600 rounded-lg group-hover:bg-sage-600 group-hover:text-white transition-colors">
                                            <BookOpen size={20} />
                                        </div>
                                        <div>
                                            <h4 className="font-medium text-stone-800 group-hover:text-sage-700">Official Documentation</h4>
                                            <p className="text-sm text-stone-500 mt-1">Read the official guide for deep understanding.</p>
                                        </div>
                                    </div>
                                </div>
                                <div className="p-4 border border-stone-200 rounded-xl hover:border-sage-300 transition-colors cursor-pointer group">
                                    <div className="flex items-start gap-3">
                                        <div className="p-2 bg-sage-100 text-sage-600 rounded-lg group-hover:bg-sage-600 group-hover:text-white transition-colors">
                                            <FileText size={20} />
                                        </div>
                                        <div>
                                            <h4 className="font-medium text-stone-800 group-hover:text-sage-700">Cheat Sheet</h4>
                                            <p className="text-sm text-stone-500 mt-1">Quick reference for common commands.</p>
                                        </div>
                                    </div>
                                </div>
                            </TabsContent>

                            <TabsContent value="quiz">
                                <div className="text-center py-12 bg-stone-50 rounded-xl border border-stone-100 border-dashed">
                                    <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mx-auto mb-4 text-sage-500">
                                        <CheckCircle2 size={32} />
                                    </div>
                                    <h3 className="font-serif font-bold text-xl text-stone-800 mb-2">Ready to test your knowledge?</h3>
                                    <p className="text-stone-500 mb-6 max-w-xs mx-auto">Take a quick 5-question quiz to verify your understanding of {concept.name}.</p>
                                    <Button className="bg-sage-600 hover:bg-sage-700 text-white px-8">
                                        Start Quiz
                                    </Button>
                                </div>
                            </TabsContent>
                        </Tabs>
                    </div>
                </SheetContent>
            </Sheet>

        </div>
    );
};

export default LearningView;

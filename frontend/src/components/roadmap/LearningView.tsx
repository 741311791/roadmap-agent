import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
    Clock,
    CheckCircle2
} from 'lucide-react';
import { Button } from '../ui/Button';
import TOCSidebar from './TOCSidebar';
import ReflectionSection from './ReflectionSection';
import RightSidebar from '../agents/RightSidebar';


// --- Types ---
interface ConceptData {
    concept_id: string;
    name: string;
    description: string;
    estimated_hours: number;
    difficulty: string;
    keywords: string[];
    content_status?: string;
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
    const [activeSection, setActiveSection] = useState<string>('');

    // Layout State
    const [isTocCollapsed, setIsTocCollapsed] = useState(false);
    const [isAiSidebarCollapsed, setIsAiSidebarCollapsed] = useState(false);
    const [aiSidebarWidth] = useState(400);

    // Responsive: Auto-collapse TOC on smaller screens
    useEffect(() => {
        const handleResize = () => {
            if (window.innerWidth < 1440) {
                setIsTocCollapsed(true);
            } else {
                setIsTocCollapsed(false);
            }
        };

        // Initial check
        handleResize();

        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

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

    // if (!concept) return <div className="flex items-center justify-center h-screen bg-[#FFFCF9]">Loading...</div>;

    return (
        <div className="flex h-full bg-[#FFFCF9] overflow-hidden font-sans text-stone-800">

            {/* --- ZONE 1: Floating TOC (Left) --- */}
            {/* --- ZONE 1: TOC Sidebar (Left) --- */}
            <TOCSidebar
                items={tocItems}
                activeSection={activeSection}
                onSectionClick={(id) => {
                    setActiveSection(id);
                    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
                }}
                isCollapsed={isTocCollapsed}
                onToggleCollapse={() => setIsTocCollapsed(!isTocCollapsed)}
                onBack={onBack}
            />

            {/* --- ZONE 2: Core Reader (Center) --- */}
            <div className="flex-1 h-full overflow-y-auto relative scroll-smooth" id="reader-scroll-container">
                <div className="max-w-[85ch] mx-auto py-12 px-8 min-h-full">

                    {/* Paper Container */}
                    <div className="bg-white shadow-sm border border-stone-100 rounded-xl p-12 md:p-16 min-h-[80vh]">
                        {/* Header */}
                        <header className="mb-12 border-b border-stone-100 pb-8" id="introduction">
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

                        {/* Reflection Section */}
                        <ReflectionSection conceptId={concept.concept_id} />

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

        </div>
    );
};

export default LearningView;

import React, { useRef, useState, useLayoutEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import RoadmapTree from '../components/roadmap/RoadmapTree';
import ProfileSidebar from '../components/roadmap/ProfileSidebar';
import LearningView from '../components/roadmap/LearningView';
import roadmapData from '../examples/demo_roadmap.json';
import EmptyState from '../components/EmptyState';
import { Layers, Clock, Calendar, Sparkles, ChevronLeft } from 'lucide-react';
import { Button } from '../components/ui/Button';

interface ConceptWithContext {
    concept_id: string;
    name: string;
    description: string;
    estimated_hours: number;
    difficulty: string;
    keywords: string[];
    moduleName: string;
    stageName: string;
    moduleId: string;
    stageId: string;
}

const RoadmapDetail: React.FC = () => {
    const navigate = useNavigate();
    const [selectedConcept, setSelectedConcept] = useState<ConceptWithContext | null>(null);
    const mainContentRef = useRef<HTMLDivElement>(null);
    const savedScrollPosition = useRef(0);

    // Scroll restoration
    useLayoutEffect(() => {
        if (!selectedConcept && mainContentRef.current) {
            mainContentRef.current.scrollTop = savedScrollPosition.current;
        }
    }, [selectedConcept]);

    // Handle concept selection
    const handleSelectConcept = (concept: ConceptWithContext) => {
        if (mainContentRef.current) {
            savedScrollPosition.current = mainContentRef.current.scrollTop;
        }
        setSelectedConcept(concept);
    };

    const handleBackToDashboard = () => {
        navigate('/agents/home');
    };

    const handleBackToRoadmap = () => {
        setSelectedConcept(null);
    };

    // Navigation helpers
    const findPreviousConcept = (): ConceptWithContext | null => {
        if (!selectedConcept) return null;

        const concepts: ConceptWithContext[] = [];
        roadmapData.stages.forEach(stage => {
            stage.modules.forEach(module => {
                module.concepts.forEach(concept => {
                    concepts.push({
                        ...concept,
                        moduleName: module.name,
                        stageName: stage.name,
                        moduleId: module.module_id,
                        stageId: stage.stage_id
                    });
                });
            });
        });

        const currentIndex = concepts.findIndex(c => c.concept_id === selectedConcept.concept_id);
        return currentIndex > 0 ? concepts[currentIndex - 1] : null;
    };

    const findNextConcept = (): ConceptWithContext | null => {
        if (!selectedConcept) return null;

        const concepts: ConceptWithContext[] = [];
        roadmapData.stages.forEach(stage => {
            stage.modules.forEach(module => {
                module.concepts.forEach(concept => {
                    concepts.push({
                        ...concept,
                        moduleName: module.name,
                        stageName: stage.name,
                        moduleId: module.module_id,
                        stageId: stage.stage_id
                    });
                });
            });
        });

        const currentIndex = concepts.findIndex(c => c.concept_id === selectedConcept.concept_id);
        return currentIndex < concepts.length - 1 ? concepts[currentIndex + 1] : null;
    };

    const handlePreviousLesson = () => {
        const prev = findPreviousConcept();
        if (prev) setSelectedConcept(prev);
    };

    const handleNextLesson = () => {
        const next = findNextConcept();
        if (next) setSelectedConcept(next);
    };

    return (
        <div ref={mainContentRef} className="h-full overflow-y-auto relative bg-background bg-noise">
            <AnimatePresence mode="popLayout">
                {selectedConcept ? (
                    <LearningView
                        key="learning-view"
                        concept={selectedConcept}
                        onBack={handleBackToRoadmap}
                        onPrevious={handlePreviousLesson}
                        onNext={handleNextLesson}
                        hasPrevious={findPreviousConcept() !== null}
                        hasNext={findNextConcept() !== null}
                    />
                ) : (
                    <div key="roadmap-view" className="max-w-7xl mx-auto py-12 px-6">
                        {/* Hero Section */}
                        <div className="mb-10">
                            <div className="flex items-center gap-4 mb-4">
                                <Button variant="ghost" size="sm" onClick={handleBackToDashboard} className="text-muted-foreground hover:text-foreground -ml-2">
                                    <ChevronLeft className="h-4 w-4 mr-1" /> Back to Dashboard
                                </Button>
                            </div>
                            <h1 className="text-4xl font-serif font-bold text-foreground mb-4 leading-tight">
                                {roadmapData.title}
                            </h1>

                            {/* Stats Badges */}
                            <div className="flex items-center gap-3 flex-wrap">
                                <div className="flex items-center gap-2 px-4 py-2 bg-sage-50 border border-sage-200 rounded-full">
                                    <Layers size={16} className="text-sage-700" />
                                    <span className="text-sm font-medium text-sage-800">
                                        {roadmapData.stages.length} Stages
                                    </span>
                                </div>
                                <div className="flex items-center gap-2 px-4 py-2 bg-muted border border-border rounded-full">
                                    <Clock size={16} className="text-foreground/70" />
                                    <span className="text-sm font-medium text-foreground">
                                        {roadmapData.total_estimated_hours} Hours
                                    </span>
                                </div>
                                <div className="flex items-center gap-2 px-4 py-2 bg-sage-100 border border-sage-300 rounded-full">
                                    <Calendar size={16} className="text-sage-700" />
                                    <span className="text-sm font-medium text-sage-800">
                                        {roadmapData.recommended_completion_weeks} Weeks
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* 2-Column Grid Layout */}
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                            {/* Left Column: Roadmap */}
                            <div className="lg:col-span-8">
                                <RoadmapTree data={roadmapData} onSelectConcept={handleSelectConcept} />
                            </div>

                            {/* Right Column: Profile Sidebar (Sticky) */}
                            <div className="lg:col-span-4 space-y-3 sticky top-6">
                                <div className="bg-card rounded-2xl border border-border overflow-hidden">
                                    <EmptyState
                                        title="Start Journey"
                                        description="Select a concept to begin."
                                        icon={Sparkles}
                                        compact={true}
                                    />
                                </div>
                                <ProfileSidebar />
                            </div>
                        </div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default RoadmapDetail;

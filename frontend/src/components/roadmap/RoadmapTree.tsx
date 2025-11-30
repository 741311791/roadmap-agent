import React, { useState } from 'react';
import { Circle } from 'lucide-react';
import StageCard from './StageCard';
import ModuleCard from './ModuleCard';
import ConceptCard from './ConceptCard';

interface Concept {
    concept_id: string;
    name: string;
    description: string;
    estimated_hours: number;
    difficulty: string;
    prerequisites: string[];
    keywords: string[];
}

interface Module {
    module_id: string;
    name: string;
    description: string;
    concepts: Concept[];
}

interface Stage {
    stage_id: string;
    name: string;
    description: string;
    order: number;
    modules: Module[];
}

interface RoadmapData {
    roadmap_id: string;
    title: string;
    stages: Stage[];
    total_estimated_hours: number;
    recommended_completion_weeks: number;
}

interface RoadmapTreeProps {
    data: RoadmapData;
    onSelectConcept?: (concept: Concept & { moduleName: string; stageName: string; moduleId: string; stageId: string }) => void;
}

const RoadmapTree: React.FC<RoadmapTreeProps> = ({ data, onSelectConcept }) => {
    // Manage expansion state for all nodes - Default to all stages expanded
    const [expandedStages, setExpandedStages] = useState<Set<string>>(new Set(data.stages.map(s => s.stage_id)));
    const [expandedModules, setExpandedModules] = useState<Set<string>>(new Set());

    const toggleStage = (stageId: string) => {
        setExpandedStages(prev => {
            const next = new Set(prev);
            if (next.has(stageId)) {
                next.delete(stageId);
            } else {
                next.add(stageId);
            }
            return next;
        });
    };

    const toggleModule = (moduleId: string) => {
        setExpandedModules(prev => {
            const next = new Set(prev);
            if (next.has(moduleId)) {
                next.delete(moduleId);
            } else {
                next.add(moduleId);
            }
            return next;
        });
    };

    return (
        <div className="relative pl-8">
            {/* Main Vertical Timeline Line */}
            <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-sage-200" />

            <div className="space-y-3">
                {data.stages.map((stage) => (
                    <div key={stage.stage_id} className="relative">
                        {/* Circular Node Dot */}
                        <div className="absolute left-[-26px] top-4 w-7 h-7 bg-gradient-to-br from-sage-500 to-sage-600 rounded-full ring-4 ring-white shadow-lg flex items-center justify-center z-10">
                            <Circle size={12} className="text-white fill-white" />
                        </div>

                        {/* Horizontal Branch (Curved Line) */}
                        <div className="absolute left-[-2px] top-[26px] w-8 h-0.5 bg-sage-300" />

                        {/* Stage Card */}
                        <div className="ml-8">
                            <StageCard
                                name={stage.name}
                                description={stage.description}
                                order={stage.order}
                                isExpanded={expandedStages.has(stage.stage_id)}
                                onToggle={() => toggleStage(stage.stage_id)}
                            />
                        </div>

                        {/* Modules (when expanded) */}
                        {expandedStages.has(stage.stage_id) && (
                            <div className="ml-16 mt-3 space-y-2 relative">
                                {/* Vertical connector line from stage to modules */}
                                <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-gradient-to-b from-sage-400 to-transparent" />

                                {stage.modules.map((module) => (
                                    <div key={module.module_id} className="relative pl-6">
                                        {/* Horizontal connector line */}
                                        <div className="absolute left-0 top-4 w-6 h-0.5 bg-sage-400" style={{ borderRadius: '2px 0 0 2px' }} />

                                        {/* Module Card */}
                                        <ModuleCard
                                            name={module.name}
                                            description={module.description}
                                            isExpanded={expandedModules.has(module.module_id)}
                                            onToggle={() => toggleModule(module.module_id)}
                                        />

                                        {/* Concepts (when expanded) */}
                                        {expandedModules.has(module.module_id) && (
                                            <div className="ml-8 mt-2 space-y-2 relative">
                                                {/* Vertical connector line from module to concepts */}
                                                <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-gradient-to-b from-sage-300 to-transparent" />

                                                {module.concepts.map((concept) => (
                                                    <div key={concept.concept_id} className="relative pl-6">
                                                        {/* Horizontal connector line */}
                                                        <div className="absolute left-0 top-3.5 w-6 h-0.5 bg-sage-300" style={{ borderRadius: '2px 0 0 2px' }} />

                                                        {/* Concept Card */}
                                                        <ConceptCard
                                                            conceptId={concept.concept_id}
                                                            name={concept.name}
                                                            description={concept.description}
                                                            estimatedHours={concept.estimated_hours}
                                                            difficulty={concept.difficulty}
                                                            onClick={() => onSelectConcept?.({
                                                                ...concept,
                                                                moduleName: module.name,
                                                                stageName: stage.name,
                                                                moduleId: module.module_id,
                                                                stageId: stage.stage_id
                                                            })}
                                                        />
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default RoadmapTree;

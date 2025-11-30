import { useState, useMemo } from 'react';
import { type Node as FlowNode, type Edge as FlowEdge } from '@xyflow/react';
import roadmapData from '../../examples/demo_roadmap.json';

export const useRoadmapData = () => {
    // const [nodes, setNodes] = useState<Node[]>([]); // Unused
    // const [edges, setEdges] = useState<Edge[]>([]); // Unused
    const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

    // Toggle Expansion Logic
    const toggleNode = (nodeId: string) => {
        setExpandedNodes(prev => {
            const next = new Set(prev);
            if (next.has(nodeId)) {
                next.delete(nodeId);
            } else {
                next.add(nodeId);
            }
            return next;
        });
    };

    // Re-calculate Graph based on Expanded State
    // Note: In a real app, we might want to preserve positions or be smarter, 
    // but for now we regenerate and let Dagre re-layout.
    const { graphNodes, graphEdges } = useMemo(() => {
        const newNodes: FlowNode[] = [];
        const newEdges: FlowEdge[] = [];

        roadmapData.stages.forEach((stage) => {
            // 1. Add Stage Node
            newNodes.push({
                id: stage.stage_id,
                type: 'stage',
                data: {
                    label: stage.name,
                    description: stage.description,
                    order: stage.order,
                    expanded: expandedNodes.has(stage.stage_id)
                },
                position: { x: 0, y: 0 }
            });

            // Connect Stages - REMOVED to allow columnar alignment
            // We want all Stages to be in the first column (Rank 0)
            // if (sIndex > 0) {
            //     newEdges.push({
            //         id: `e-${roadmapData.stages[sIndex - 1].stage_id}-${stage.stage_id}`,
            //         source: roadmapData.stages[sIndex - 1].stage_id,
            //         target: stage.stage_id,
            //         type: 'smoothstep',
            //         animated: true,
            //         style: { stroke: '#D4D4D8', strokeWidth: 2 }
            //     });
            // }

            // 2. If Stage Expanded -> Add Modules
            if (expandedNodes.has(stage.stage_id)) {
                stage.modules.forEach((mod) => {
                    newNodes.push({
                        id: mod.module_id,
                        type: 'module',
                        data: {
                            label: mod.name,
                            expanded: expandedNodes.has(mod.module_id)
                        },
                        position: { x: 0, y: 0 }
                    });

                    newEdges.push({
                        id: `e-${stage.stage_id}-${mod.module_id}`,
                        source: stage.stage_id,
                        target: mod.module_id,
                        type: 'smoothstep',
                        style: { stroke: 'hsl(var(--sage))', strokeWidth: 1.5 }
                    });

                    // 3. If Module Expanded -> Add Concepts
                    if (expandedNodes.has(mod.module_id)) {
                        mod.concepts.forEach((concept) => {
                            newNodes.push({
                                id: concept.concept_id,
                                type: 'concept',
                                data: {
                                    label: concept.name,
                                    time: `${concept.estimated_hours}h`
                                },
                                position: { x: 0, y: 0 }
                            });

                            newEdges.push({
                                id: `e-${mod.module_id}-${concept.concept_id}`,
                                source: mod.module_id,
                                target: concept.concept_id,
                                type: 'smoothstep',
                                style: { stroke: 'hsl(var(--border))', strokeWidth: 1 }
                            });
                        });
                    }
                });
            }
        });

        return { graphNodes: newNodes, graphEdges: newEdges };
    }, [expandedNodes]);

    return { nodes: graphNodes, edges: graphEdges, toggleNode };
};

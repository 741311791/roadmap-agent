import React, { useEffect } from 'react';
import { ReactFlow, Controls, useNodesState, useEdgesState, ReactFlowProvider, type Node as FlowNode, type Edge as FlowEdge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { StageNode, ModuleNode, ConceptNode } from './CustomNodes';
import { useRoadmapData } from './useRoadmapData';
import { useAutoLayout } from './useAutoLayout';

const nodeTypes = {
    stage: StageNode,
    module: ModuleNode,
    concept: ConceptNode,
};

const RoadmapCanvasContent: React.FC = () => {
    const { nodes: initialNodes, edges: initialEdges, toggleNode } = useRoadmapData();
    const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<FlowEdge>([]);
    const { onLayout } = useAutoLayout();

    // Sync data hook with React Flow state
    useEffect(() => {
        const { nodes: layoutedNodes, edges: layoutedEdges } = onLayout(initialNodes, initialEdges);
        setNodes(layoutedNodes);
        setEdges(layoutedEdges);
    }, [initialNodes, initialEdges, onLayout, setNodes, setEdges]);

    const onNodeClick = (_: React.MouseEvent, node: any) => {
        if (node.type === 'stage' || node.type === 'module') {
            toggleNode(node.id);
        }
    };

    return (
        <div className="w-full h-full bg-gradient-to-br from-sage-50 via-background to-sage-100/30">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                nodeTypes={nodeTypes}
                fitView
                minZoom={0.1}
                maxZoom={1.5}
                nodesDraggable={false}
                nodesConnectable={false}
                defaultEdgeOptions={{
                    type: 'default',
                    style: { stroke: 'hsl(var(--muted-foreground))', strokeWidth: 2 },
                    animated: false
                }}
            >
                <Controls className="!bg-card/80 !backdrop-blur-sm !border-border !shadow-md !text-foreground" />
            </ReactFlow>
        </div>
    );
};

const RoadmapCanvas: React.FC = () => {
    return (
        <ReactFlowProvider>
            <RoadmapCanvasContent />
        </ReactFlowProvider>
    );
};

export default RoadmapCanvas;

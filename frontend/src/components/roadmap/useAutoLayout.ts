import { useCallback } from 'react';
import dagre from 'dagre';
import { useReactFlow, type Node as FlowNode, type Edge as FlowEdge, Position } from '@xyflow/react';

const nodeWidth = 350;
const nodeHeight = 200;

export const useAutoLayout = () => {
    const { fitView } = useReactFlow();

    const onLayout = useCallback(
        (nodes: FlowNode[], edges: FlowEdge[], direction = 'LR') => {
            const dagreGraph = new dagre.graphlib.Graph();
            dagreGraph.setDefaultEdgeLabel(() => ({}));

            const isHorizontal = direction === 'LR';
            dagreGraph.setGraph({
                rankdir: direction,
                ranksep: 150, // Increased horizontal spacing
                nodesep: 80   // Increased vertical spacing
            });

            nodes.forEach((node) => {
                dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
            });

            edges.forEach((edge) => {
                dagreGraph.setEdge(edge.source, edge.target);
            });

            dagre.layout(dagreGraph);

            const layoutedNodes = nodes.map((node) => {
                const nodeWithPosition = dagreGraph.node(node.id);

                // We are shifting the dagre node position (anchor=center center) to the top left
                // so it matches the React Flow node anchor point (top left).
                return {
                    ...node,
                    targetPosition: isHorizontal ? Position.Left : Position.Top,
                    sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
                    position: {
                        x: nodeWithPosition.x - nodeWidth / 2,
                        y: nodeWithPosition.y - nodeHeight / 2,
                    },
                };
            });

            return { nodes: layoutedNodes, edges };
        },
        [fitView]
    );

    return { onLayout };
};

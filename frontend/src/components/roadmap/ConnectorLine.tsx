import React from 'react';
import { motion } from 'framer-motion';

interface ConnectorLineProps {
    fromTop: number;
    fromLeft: number;
    toTop: number;
    toLeft: number;
}

const ConnectorLine: React.FC<ConnectorLineProps> = ({ fromTop, fromLeft, toTop, toLeft }) => {
    // Calculate the SVG path for a smooth curved L-shape
    const height = toTop - fromTop;

    // Control point for bezier curve
    const controlPoint1X = fromLeft;
    const controlPoint1Y = fromTop + height * 0.5;
    const controlPoint2X = toLeft;
    const controlPoint2Y = fromTop + height * 0.5;

    const path = `M ${fromLeft} ${fromTop} 
                  C ${controlPoint1X} ${controlPoint1Y}, 
                    ${controlPoint2X} ${controlPoint2Y}, 
                    ${toLeft} ${toTop}`;

    return (
        <svg
            className="absolute top-0 left-0 pointer-events-none"
            style={{
                width: '100%',
                height: '100%',
                zIndex: 0,
            }}
        >
            <motion.path
                d={path}
                className="stroke-sage-300"
                strokeWidth="2"
                fill="none"
                strokeLinecap="round"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ duration: 1.5, ease: "easeInOut" }}
            />
        </svg>
    );
};

export default ConnectorLine;
